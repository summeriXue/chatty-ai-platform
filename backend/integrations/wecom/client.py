"""WeCom integration — API client helpers."""

import logging

import httpx

logger = logging.getLogger(__name__)

WECOM_API_BASE = "https://qyapi.weixin.qq.com/cgi-bin"


def get_access_token(corp_id: str, corp_secret: str) -> str | None:
    """Get a WeCom access token using Corp ID and application Secret."""
    try:
        response = httpx.get(
            f"{WECOM_API_BASE}/gettoken",
            params={
                "corpid": corp_id,
                "corpsecret": corp_secret,
            },
            timeout=10.0,
        )
        response.raise_for_status()

        data = response.json()

        if data.get("errcode") != 0:
            logger.warning(
                "WeCom access token request failed: errcode=%s errmsg=%s",
                data.get("errcode"),
                data.get("errmsg"),
            )
            return None

        return data.get("access_token") or None

    except Exception:
        logger.exception("WeCom access token request failed")
        return None


def validate_credentials(corp_id: str, corp_secret: str) -> bool:
    """Validate WeCom Corp ID and application Secret."""
    return bool(
        get_access_token(
            corp_id=corp_id,
            corp_secret=corp_secret,
        )
    )

def send_text_message(
    user_id: str,
    content: str,
) -> bool:
    """Send a text message to a WeCom user through the configured app."""

    from integrations.registry import get_credentials

    creds = get_credentials("wecom")

    corp_id = creds.get("corp_id", "")
    corp_secret = creds.get("corp_secret", "")
    app_agent_id = creds.get("app_agent_id", "")

    if not corp_id or not corp_secret or not app_agent_id:
        logger.warning(
            "Cannot send WeCom message: incomplete application credentials"
        )
        return False

    access_token = get_access_token(
        corp_id=corp_id,
        corp_secret=corp_secret,
    )

    if not access_token:
        logger.warning(
            "Cannot send WeCom message: failed to obtain access token"
        )
        return False

    try:
        response = httpx.post(
            f"{WECOM_API_BASE}/message/send",
            params={
                "access_token": access_token,
            },
            json={
                "touser": user_id,
                "msgtype": "text",
                "agentid": int(app_agent_id),
                "text": {
                    "content": content,
                },
                "safe": 0,
            },
            timeout=10.0,
        )

        response.raise_for_status()

        data = response.json()

        if data.get("errcode") != 0:
            logger.warning(
                "WeCom send message failed: errcode=%s errmsg=%s",
                data.get("errcode"),
                data.get("errmsg"),
            )
            return False

        logger.info(
            "WeCom message sent successfully: user=%s",
            user_id,
        )
        return True

    except Exception:
        logger.exception(
            "WeCom send message request failed"
        )
        return False
