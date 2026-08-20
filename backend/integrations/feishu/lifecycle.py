"""Feishu integration — long-connection lifecycle.

Receives Feishu im.message.receive_v1 events through the official
WebSocket client, routes private text messages into Chatty, and sends
the generated response back to Feishu.
"""

import asyncio
import json
import logging
import threading

from integrations.registry import get_credentials

from . import service
from .client import send_text_message

logger = logging.getLogger(__name__)


_ws_thread: threading.Thread | None = None
_ws_client = None
_ws_lock = threading.Lock()


def _handle_message_event(data) -> None:
    """Handle an inbound Feishu private text message."""
    try:
        event = data.event
        sender = event.sender
        message = event.message

        sender_id = sender.sender_id.open_id or ""
        chat_id = message.chat_id or ""
        chat_type = message.chat_type or ""
        message_type = message.message_type or ""

        logger.info(
            "Feishu message received: sender=%s chat=%s chat_type=%s type=%s",
            sender_id,
            chat_id,
            chat_type,
            message_type,
        )

        # First version only handles private text messages.
        if chat_type != "p2p":
            logger.debug(
                "Skipping Feishu non-private message: chat=%s type=%s",
                chat_id,
                chat_type,
            )
            return

        if message_type != "text":
            logger.debug(
                "Skipping Feishu non-text message: chat=%s type=%s",
                chat_id,
                message_type,
            )
            return

        if not sender_id or not chat_id:
            logger.warning(
                "Skipping Feishu message with missing sender/chat ID"
            )
            return

        try:
            content = json.loads(message.content or "{}")
        except (TypeError, json.JSONDecodeError):
            logger.warning(
                "Failed to parse Feishu message content: %r",
                message.content,
            )
            return

        text = str(content.get("text", "")).strip()
        if not text:
            return

        creds = get_credentials("feishu")
        app_id = creds.get("app_id", "")
        app_secret = creds.get("app_secret", "")

        if not app_id or not app_secret:
            logger.warning(
                "Feishu credentials missing while processing message"
            )
            return

        async def _process_and_reply() -> None:
            try:
                response = await service.process_message(
                    sender_id=sender_id,
                    message_text=text,
                )

                if not response:
                    return

                send_text_message(
                    receive_id=chat_id,
                    text=response,
                    app_id=app_id,
                    app_secret=app_secret,
                    receive_id_type="chat_id",
                )

                logger.info(
                    "Feishu response sent: sender=%s chat=%s",
                    sender_id,
                    chat_id,
                )

            except Exception:
                logger.exception(
                    "Failed to process and reply to Feishu message"
                )

        try:
            running_loop = asyncio.get_running_loop()
            running_loop.create_task(_process_and_reply())
        except RuntimeError:
            asyncio.run(_process_and_reply())

    except Exception:
        logger.exception("Failed to handle Feishu message event")


def start_long_connection() -> bool:
    """Start the Feishu WebSocket long connection.

    Returns:
        True if the client thread was started.
        False if Feishu is not configured or already running.
    """
    global _ws_thread, _ws_client

    with _ws_lock:
        if _ws_thread and _ws_thread.is_alive():
            logger.info("Feishu long connection is already running")
            return False

        creds = get_credentials("feishu")

        if not creds or not creds.get("enabled"):
            logger.info("Feishu integration is not enabled")
            return False

        app_id = creds.get("app_id", "")
        app_secret = creds.get("app_secret", "")

        if not app_id or not app_secret:
            logger.warning(
                "Feishu integration is enabled but credentials are missing"
            )
            return False

        def _run() -> None:
            global _ws_client

            try:
                # Important:
                # Import lark_oapi inside this worker thread so its WebSocket module
                # captures a thread-local event loop instead of FastAPI's running loop.
                import lark_oapi as lark

                event_handler = (
                    lark.EventDispatcherHandler.builder("", "")
                    .register_p2_im_message_receive_v1(_handle_message_event)
                    .build()
                )

                _ws_client = lark.ws.Client(
                    app_id,
                    app_secret,
                    event_handler=event_handler,
                    log_level=lark.LogLevel.INFO,
                )

                logger.info("Starting Feishu long connection")
                _ws_client.start()

            except Exception:
                logger.exception(
                    "Feishu long connection stopped unexpectedly"
                )

        _ws_thread = threading.Thread(
            target=_run,
            daemon=True,
            name="feishu-ws",
        )
        _ws_thread.start()

        logger.info("Feishu long connection thread started")
        return True
    
def stop_long_connection() -> None:
    """Best-effort shutdown of the Feishu WebSocket client.

    Some lark-oapi versions do not expose a public Client.stop().
    In that case the daemon WebSocket thread exits with the backend process.
    """
    global _ws_thread, _ws_client

    with _ws_lock:
        client = _ws_client

        if client is None:
            return

        stop = getattr(client, "stop", None)

        if callable(stop):
            try:
                stop()
                logger.info("Feishu long connection stopped")
            except Exception:
                logger.exception(
                    "Failed to stop Feishu long connection cleanly"
                )
        else:
            logger.info(
                "Current lark-oapi version has no public stop(); "
                "Feishu daemon thread will exit with the process"
            )

        _ws_client = None
        _ws_thread = None
   