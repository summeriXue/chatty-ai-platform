"""Feishu integration — Persistent conversation state.

Stores the mapping between a Feishu user, a Chatty agent,
and the corresponding Chatty conversation.
"""

import logging
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from core.storage import safe_init_sqlite

logger = logging.getLogger(__name__)


DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "feishu"
DB_PATH = DATA_DIR / "feishu.db"
GCS_KEY = "feishu/feishu.db"

_connection: sqlite3.Connection | None = None
_write_lock = threading.Lock()


def _get_db() -> sqlite3.Connection:
    if _connection is None:
        raise RuntimeError(
            "Feishu state DB not initialized — call init_db() first"
        )
    return _connection


def get_db() -> sqlite3.Connection:
    return _get_db()


def _setup_connection() -> None:
    """Open the Feishu state database and create its schema."""
    global _connection

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    _connection = sqlite3.connect(
        str(DB_PATH),
        check_same_thread=False,
    )
    _connection.row_factory = sqlite3.Row

    _connection.execute("PRAGMA journal_mode=WAL")
    _connection.execute("PRAGMA foreign_keys=ON")
    _connection.execute("PRAGMA busy_timeout=5000")
    _connection.execute("PRAGMA synchronous=FULL")

    _connection.executescript("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            sender_id TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            chatty_conversation_id TEXT,
            last_active TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(sender_id, agent_id)
        );
    """)

    logger.info(
        "Feishu state DB initialized at %s",
        DB_PATH,
    )


def init_db() -> dict:
    """Initialize the Feishu state database."""
    return safe_init_sqlite(
        DB_PATH,
        GCS_KEY,
        init_fn=_setup_connection,
    )


def close_db() -> None:
    """Close the Feishu state database."""
    global _connection

    if _connection:
        _connection.close()
        _connection = None


def get_or_create_conversation(
    sender_id: str,
    agent_id: str,
) -> dict:
    """Get or create the Feishu-side conversation mapping."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_db()

    with _write_lock:
        row = conn.execute(
            """
            SELECT id, chatty_conversation_id
            FROM conversations
            WHERE sender_id = ? AND agent_id = ?
            """,
            (sender_id, agent_id),
        ).fetchone()

        if row:
            conn.execute(
                """
                UPDATE conversations
                SET last_active = ?
                WHERE id = ?
                """,
                (now, row["id"]),
            )
            conn.commit()

            return {
                "id": row["id"],
                "chatty_conversation_id": row[
                    "chatty_conversation_id"
                ],
                "is_new": False,
            }

        conversation_id = str(uuid.uuid4())

        conn.execute(
            """
            INSERT INTO conversations (
                id,
                sender_id,
                agent_id,
                last_active,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                conversation_id,
                sender_id,
                agent_id,
                now,
                now,
            ),
        )
        conn.commit()

        return {
            "id": conversation_id,
            "chatty_conversation_id": None,
            "is_new": True,
        }


def set_chatty_conversation_id(
    conversation_id: str,
    chatty_conversation_id: str,
) -> None:
    """Attach a Chatty conversation ID to a Feishu conversation."""
    conn = _get_db()

    with _write_lock:
        conn.execute(
            """
            UPDATE conversations
            SET chatty_conversation_id = ?
            WHERE id = ?
            """,
            (
                chatty_conversation_id,
                conversation_id,
            ),
        )
        conn.commit()
