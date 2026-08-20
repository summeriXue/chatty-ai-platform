"""WeCom integration — onboarding and credential setup."""

import logging

from agents import db as agent_db
from integrations.registry import get_credentials, save_credentials

from .client import validate_credentials

logger = logging.getLogger(__name__)


def setup(
    corp_id: str,
    app_agent_id: str,
    corp_secret: str,
    callback_token: str,
    encoding_aes_key: str,
    agent_id: str,
) -> dict:
    """Validate and save WeCom application credentials."""

    corp_id = corp_id.strip()
    app_agent_id = app_agent_id.strip()
    corp_secret = corp_secret.strip()
    callback_token = callback_token.strip()
    encoding_aes_key = encoding_aes_key.strip()
    agent_id = agent_id.strip()

    if not corp_id:
        return {
            "ok": False,
            "error": "WeCom Corp ID is required.",
        }

    if not app_agent_id:
        return {
            "ok": False,
            "error": "WeCom application Agent ID is required.",
        }

    if not agent_id:
        return {
            "ok": False,
            "error": "A Chatty agent must be selected.",
        }

    agent = agent_db.get_agent(agent_id)
    if not agent:
        return {
            "ok": False,
            "error": "Selected Chatty agent was not found.",
        }

    existing = get_credentials("wecom")

    # Sensitive fields may be left blank in Manage mode.
    # Blank means "keep the existing value".
    if not corp_secret:
        corp_secret = existing.get("corp_secret", "")

    if not callback_token:
        callback_token = existing.get("callback_token", "")

    if not encoding_aes_key:
        encoding_aes_key = existing.get("encoding_aes_key", "")

    if not corp_secret:
        return {
            "ok": False,
            "error": "WeCom application Secret is required.",
        }

    if not callback_token:
        return {
            "ok": False,
            "error": "WeCom Callback Token is required.",
        }

    if not encoding_aes_key:
        return {
            "ok": False,
            "error": "WeCom EncodingAESKey is required.",
        }

    if not validate_credentials(corp_id, corp_secret):
        return {
            "ok": False,
            "error": "Invalid WeCom Corp ID or application Secret.",
        }

    save_credentials(
        "wecom",
        {
            "corp_id": corp_id,
            "app_agent_id": app_agent_id,
            "corp_secret": corp_secret,
            "callback_token": callback_token,
            "encoding_aes_key": encoding_aes_key,
            "agent_id": agent_id,
            "enabled": True,
            "connection_status": "ok",
        },
    )

    logger.info(
        "WeCom integration configured successfully for Chatty agent %s",
        agent_id,
    )

    return {
        "ok": True,
        "enabled": True,
        "connection_status": "ok",
        "agent_id": agent_id,
        "app_agent_id": app_agent_id,
    }
