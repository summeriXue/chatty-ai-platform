"""WeCom integration — callback router."""

import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from integrations.registry import get_credentials

from .crypto import decrypt_message, verify_signature

logger = logging.getLogger(__name__)

router = APIRouter(tags=["wecom"])


@router.get(
    "/callback",
    response_class=PlainTextResponse,
)
def verify_callback(
    msg_signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...),
):
    """Verify the WeCom callback URL."""

    creds = get_credentials("wecom")

    token = creds.get("callback_token", "")
    encoding_aes_key = creds.get(
        "encoding_aes_key",
        "",
    )
    corp_id = creds.get("corp_id", "")

    if not token or not encoding_aes_key or not corp_id:
        logger.warning(
            "WeCom callback verification attempted "
            "without complete callback credentials"
        )
        raise HTTPException(
            status_code=503,
            detail="WeCom callback is not configured",
        )

    if not verify_signature(
        token=token,
        timestamp=timestamp,
        nonce=nonce,
        encrypted=echostr,
        msg_signature=msg_signature,
    ):
        logger.warning(
            "WeCom callback signature verification failed"
        )
        raise HTTPException(
            status_code=403,
            detail="Invalid WeCom callback signature",
        )

    try:
        plaintext = decrypt_message(
            encoding_aes_key=encoding_aes_key,
            encrypted=echostr,
            receive_id=corp_id,
        )
    except Exception:
        logger.exception(
            "Failed to decrypt WeCom callback verification"
        )
        raise HTTPException(
            status_code=400,
            detail="Failed to decrypt WeCom callback",
        )

    logger.info(
        "WeCom callback URL verified successfully"
    )

    return PlainTextResponse(
        content=plaintext,
        media_type="text/plain",
    )

import xml.etree.ElementTree as ET

from fastapi import Request

async def _process_text_message(
    sender_id: str,
    content: str,
) -> None:
    """Process a WeCom text message and send Chatty's reply."""
    try:
        from . import service
        from .client import send_text_message

        response = await service.process_message(
            sender_id=sender_id,
            message_text=content,
        )

        logger.info(
            "WeCom Chatty response generated: sender=%s response=%s",
            sender_id,
        )

        if response:
            sent = send_text_message(
                user_id=sender_id,
                content=response,
            )

            if not sent:
                logger.warning(
                    "Failed to send Chatty response to WeCom sender=%s",
                    sender_id,
                )

    except Exception:
        logger.exception(
            "Failed to process WeCom message through Chatty"
        )

@router.post("/callback")
async def receive_callback(
    request: Request,
    background_tasks: BackgroundTasks,
    msg_signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
):
    """Receive an encrypted WeCom callback message."""

    creds = get_credentials("wecom")

    token = creds.get("callback_token", "")
    encoding_aes_key = creds.get("encoding_aes_key", "")
    corp_id = creds.get("corp_id", "")

    if not token or not encoding_aes_key or not corp_id:
        logger.warning(
            "WeCom callback received without complete callback credentials"
        )
        raise HTTPException(
            status_code=503,
            detail="WeCom callback is not configured",
        )

    raw_body = await request.body()

    try:
        outer_root = ET.fromstring(raw_body)
        encrypted = outer_root.findtext("Encrypt", default="")
    except Exception:
        logger.exception("Failed to parse WeCom callback envelope")
        raise HTTPException(
            status_code=400,
            detail="Invalid WeCom callback XML",
        )

    if not encrypted:
        raise HTTPException(
            status_code=400,
            detail="Missing WeCom encrypted payload",
        )

    if not verify_signature(
        token=token,
        timestamp=timestamp,
        nonce=nonce,
        encrypted=encrypted,
        msg_signature=msg_signature,
    ):
        logger.warning("WeCom callback signature verification failed")
        raise HTTPException(
            status_code=403,
            detail="Invalid WeCom callback signature",
        )

    try:
        plaintext_xml = decrypt_message(
            encoding_aes_key=encoding_aes_key,
            encrypted=encrypted,
            receive_id=corp_id,
        )
    except Exception:
        logger.exception("Failed to decrypt WeCom callback message")
        raise HTTPException(
            status_code=400,
            detail="Failed to decrypt WeCom callback",
        )

    try:
        root = ET.fromstring(plaintext_xml)

        from_user = root.findtext("FromUserName", default="")
        msg_type = root.findtext("MsgType", default="")
        content = root.findtext("Content", default="")
        msg_id = root.findtext("MsgId", default="")

    except Exception:
        logger.exception("Failed to parse decrypted WeCom message")
        raise HTTPException(
            status_code=400,
            detail="Invalid decrypted WeCom XML",
        )

    logger.info(
        "WeCom message received: sender=%s type=%s msg_id=%s",
        from_user,
        msg_type,
        msg_id,
    )

    from . import state

    if msg_id and not state.claim_message(msg_id):
        logger.info(
            "Ignoring duplicate WeCom message: msg_id=%s",
            msg_id,
        )
        return PlainTextResponse(
            content="success",
            media_type="text/plain",
        )

    if msg_type == "text":
        logger.info(
            "WeCom text content: sender=%s content=%s",
            from_user,
        )

        background_tasks.add_task(
            _process_text_message,
            from_user,
            content,
        )

    return PlainTextResponse(
        content="success",
        media_type="text/plain",
    )
