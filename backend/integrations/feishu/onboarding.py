"""Feishu integration — onboarding and credential setup."""

import logging

from agents import db as agent_db
from integrations.registry import get_credentials, save_credentials

from .client import validate_credentials

logger = logging.getLogger(__name__)


def setup(app_id: str, app_secret: str, agent_id: str) -> dict:
    """Validate and save Feishu app credentials."""

    app_id = app_id.strip()
    app_secret = app_secret.strip()
    agent_id = agent_id.strip()

    if not app_id:
        return {
            "ok": False,
            "error": "Feishu App ID is required.",
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

    existing = get_credentials("feishu")

    # First-time setup requires an App Secret.
    # On Manage/edit, an empty secret means "keep the existing secret".
    if not app_secret:
        app_secret = existing.get("app_secret", "")

    if not app_secret:
        return {
            "ok": False,
            "error": "Feishu App Secret is required.",
        }
    
    if not validate_credentials(app_id, app_secret):
        return {
            "ok": False,
            "error": "Invalid Feishu App ID or App Secret.",
        }

    save_credentials(
        "feishu",
        {
            "app_id": app_id,
            "app_secret": app_secret,
            "agent_id": agent_id,
            "enabled": True,
            "connection_status": "ok",
        },
    )

    logger.info("Feishu integration configured successfully")

    return {
        "ok": True,
        "enabled": True,
        "connection_status": "ok",
        "agent_id": agent_id,
    }
