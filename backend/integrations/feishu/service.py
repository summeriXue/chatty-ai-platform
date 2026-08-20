"""Feishu integration — Message processing service.

Routes inbound Feishu private messages to Chatty and returns
the generated response text.
"""

import importlib
import logging

from agents import db as agent_db
from agents.engine import (
    build_agent_config,
    get_context_manager,
    get_chat_service,
)
from core.providers import get_ai_provider
from core.agents.tool_registry import ToolRegistry
from core.agents.reminders.tools import (
    create_reminder_handler,
    list_reminders_handler,
    cancel_reminder_handler,
)
from core.agents.scheduled_actions.tools import (
    create_scheduled_action_handler,
    list_scheduled_actions_handler,
    update_scheduled_action_handler,
    delete_scheduled_action_handler,
)
from core.agents import ai_service

from integrations.registry import get_credentials

from . import state

logger = logging.getLogger(__name__)


_INTEGRATION_MODULES = {
    "crm_lite": ("integrations.crm_lite.tools", "CRM_LITE_TOOL_DEFS"),
    "odoo": ("integrations.odoo.tools", "ODOO_TOOL_DEFS"),
    "bamboohr": ("integrations.bamboohr.tools", "BAMBOOHR_TOOL_DEFS"),
    "quickbooks": ("integrations.quickbooks.tools", "QB_TOOL_DEFS"),
    "qb_csv": ("integrations.qb_csv.tools", "QB_CSV_TOOL_DEFS"),
    "paperclip": ("integrations.paperclip.tools", "PAPERCLIP_TOOL_DEFS"),
    "todoist": ("integrations.todoist.tools", "TODOIST_TOOL_DEFS"),
}


def _load_integration_tools() -> tuple[list[dict], dict]:
    """Load enabled integration tool definitions and executors."""
    from integrations.registry import is_enabled

    tool_defs: list[dict] = []
    executors: dict = {}

    for name, (module_path, defs_attr) in _INTEGRATION_MODULES.items():
        if not is_enabled(name):
            continue

        try:
            if name == "crm_lite":
                from integrations.crm_lite.db import init_db, _connection

                if _connection is None:
                    init_db()

            mod = importlib.import_module(module_path)
            defs = getattr(mod, defs_attr, [])
            execs = getattr(mod, "TOOL_EXECUTORS", {})

            tool_defs.extend(
                {**d, "integration": name}
                for d in defs
            )
            executors.update(execs)

        except Exception as exc:
            logger.warning(
                "Failed to load integration %s: %s",
                name,
                exc,
            )

    return tool_defs, executors


def _build_agent_handlers(agent_slug: str) -> tuple[dict, dict]:
    """Build reminder and scheduled action handlers for an agent."""
    reminder_handlers = {
        "create_reminder": lambda **kw: create_reminder_handler(
            agent_slug,
            **kw,
        ),
        "list_reminders": lambda **kw: list_reminders_handler(
            agent_slug,
            **kw,
        ),
        "cancel_reminder": lambda **kw: cancel_reminder_handler(
            agent_slug,
            **kw,
        ),
    }

    scheduled_action_handlers = {
        "create_scheduled_action": lambda **kw: create_scheduled_action_handler(
            agent_slug,
            **kw,
        ),
        "list_scheduled_actions": lambda **kw: list_scheduled_actions_handler(
            agent_slug,
            **kw,
        ),
        "update_scheduled_action": lambda **kw: update_scheduled_action_handler(
            agent_slug,
            **kw,
        ),
        "delete_scheduled_action": lambda **kw: delete_scheduled_action_handler(
            agent_slug,
            **kw,
        ),
    }

    return reminder_handlers, scheduled_action_handlers


def _resolve_agent() -> dict | None:
    """Resolve the Chatty agent assigned to Feishu."""
    creds = get_credentials("feishu")
    agent_id = creds.get("agent_id", "")

    if not agent_id:
        logger.warning(
            "Feishu integration has no agent assigned"
        )
        return None

    agent = agent_db.get_agent(agent_id)

    if not agent:
        logger.warning(
            "Feishu assigned agent not found: %s",
            agent_id,
        )
        return None

    return agent


async def process_message(
    sender_id: str,
    message_text: str,
) -> str:
    """Process a Feishu private text message through Chatty."""
    agent = _resolve_agent()

    if not agent:
        return "No Chatty agent is available."

    slug = agent["slug"]

    config = build_agent_config(agent)
    ctx_manager = get_context_manager(slug)
    chat_service = get_chat_service(slug)

    provider = get_ai_provider(
        agent_provider=config.provider_override or None,
        agent_model=config.model_override or None,
        agent_model_tier=config.model_tier,
    )

    if not provider:
        return (
            "No AI provider is configured. "
            "Please set up an AI provider in Chatty."
        )

    google_accounts = config.google_accounts
    gmail_ids = google_accounts.get("gmail", [])
    calendar_ids = google_accounts.get("calendar", [])
    drive_ids = google_accounts.get("drive", [])

    google_connected = bool(
        gmail_ids or calendar_ids or drive_ids
    )

    from integrations.registry import list_google_accounts

    all_google_accounts = list_google_accounts()

    account_info_map = {
        account_id: {
            "email": account.get("email", ""),
            "scope_grants": account.get("scope_grants", {}),
            "connection_status": account.get(
                "connection_status",
                "ok",
            ),
        }
        for account_id, account in all_google_accounts.items()
    }

    integration_tool_defs, integration_executors = _load_integration_tools()

    from integrations.registry import get_tool_mode, get_credentials

    integration_tool_modes = {
        name: get_tool_mode(name)
        for name in _INTEGRATION_MODULES
        if "tool_mode" in get_credentials(name)
    }

    reminder_handlers, scheduled_action_handlers = (
        _build_agent_handlers(slug)
    )

    registry = ToolRegistry(
        context_dir=config.context_dir,
        google_connected=google_connected,
        integration_executors=integration_executors,
        agent_slug=slug,
        reminder_handlers=reminder_handlers,
        scheduled_action_handlers=scheduled_action_handlers,
        gmail_account_ids=gmail_ids,
        calendar_account_ids=calendar_ids,
        drive_account_ids=drive_ids,
        account_info_map=account_info_map,
    )

    # Get or create the persistent Feishu conversation mapping.
    feishu_conversation = state.get_or_create_conversation(
        sender_id=sender_id,
        agent_id=agent["id"],
    )

    chatty_conversation_id = feishu_conversation.get(
        "chatty_conversation_id"
    )

    # A Feishu user + Chatty agent should keep using the same
    # Chatty conversation across multiple messages.
    if not chatty_conversation_id and chat_service:
        try:
            conversation = chat_service.create_conversation(
                source="feishu"
            )

            chatty_conversation_id = conversation["id"]

            state.set_chatty_conversation_id(
                feishu_conversation["id"],
                chatty_conversation_id,
            )

            logger.info(
                "Created Chatty conversation for Feishu sender=%s agent=%s",
                sender_id,
                agent["id"],
            )

        except Exception as exc:
            logger.warning(
                "Failed to create Feishu conversation: %s",
                exc,
            )

    # run_sync reconstructs previous turns from Chatty chat history
    # using conversation_id, so only pass the new inbound message.
    messages = [
        {
            "role": "user",
            "content": message_text,
        }
    ]

    response = await ai_service.run_sync(
        config=config,
        provider=provider,
        registry=registry,
        ctx_manager=ctx_manager,
        messages=messages,
        chat_service=chat_service,
        conversation_id=chatty_conversation_id,
        integration_tool_defs=integration_tool_defs or None,
        integration_tool_modes=integration_tool_modes,
        source="feishu",
    )

    return (
        response
        or "I had trouble generating a response. Please try again."
    )
