"""Allowlist enforcement for the WhatsApp MCP server.

Every read in whatsapp.py goes through connect() below. Rather than adding a
WHERE clause to each of the nine queries in that module -- where missing one
would silently open a hole -- this shadows the `chats` and `messages` tables
with filtered views of the same name. Unqualified table names resolve to the
in-memory database before the attached one, so existing SQL is gated as written
and any query added later is gated automatically.

The filter fails closed: a missing, unreadable or malformed config allows
nothing rather than reverting to full access.
"""

import json
import os
import sqlite3
from typing import Any, Dict, List

CONFIG_PATH = os.path.expanduser("~/.config/whatsapp-mcp/allowlist.json")

MESSAGES_DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "whatsapp-bridge", "store", "messages.db"
)


def load_config() -> Dict[str, Any]:
    """Read the allowlist config, falling back to a locked-down default."""
    locked = {"read_allowlist": [], "send_enabled": False, "_status": "no config"}
    try:
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
    except FileNotFoundError:
        return locked
    except (json.JSONDecodeError, OSError) as e:
        locked["_status"] = f"config unreadable ({e}); denying all"
        return locked

    allow = cfg.get("read_allowlist", [])
    if not isinstance(allow, list) or not all(isinstance(j, str) for j in allow):
        locked["_status"] = "read_allowlist must be a list of strings; denying all"
        return locked

    return {
        "read_allowlist": allow,
        "send_enabled": bool(cfg.get("send_enabled", False)),
        "_status": "ok",
    }


def allowed_jids() -> List[str]:
    return load_config()["read_allowlist"]


def _sql_in_list(jids: List[str]) -> str:
    """Render a JID list as a SQL IN clause body, escaping quotes."""
    if not jids:
        return None
    return ", ".join("'" + j.replace("'", "''") + "'" for j in jids)


def connect() -> sqlite3.Connection:
    """Open a connection whose `chats`/`messages` tables are allowlist-filtered.

    The underlying database is attached read-only, so nothing here can modify
    the archive the bridge maintains.
    """
    jids = allowed_jids()
    in_list = _sql_in_list(jids)

    conn = sqlite3.connect(":memory:", uri=True)
    db_uri = "file:" + os.path.abspath(MESSAGES_DB_PATH) + "?mode=ro"
    conn.execute("ATTACH DATABASE ? AS src", (db_uri,))

    # With no allowlist, `WHERE 0` yields an empty but schema-correct view, so
    # callers see "no results" rather than a SQL error.
    predicate_chats = f"jid IN ({in_list})" if in_list else "0"
    predicate_messages = f"chat_jid IN ({in_list})" if in_list else "0"

    # These must be TEMP views: SQLite forbids a view in a persistent schema
    # from referencing an attached database, but the temp schema is exempt.
    # Unqualified names resolve to temp first, so `SELECT ... FROM messages`
    # in existing code hits the filtered view rather than src.messages.
    conn.execute(f"CREATE TEMP VIEW chats AS SELECT * FROM src.chats WHERE {predicate_chats}")
    conn.execute(f"CREATE TEMP VIEW messages AS SELECT * FROM src.messages WHERE {predicate_messages}")
    return conn


def connect_unfiltered() -> sqlite3.Connection:
    """Read-only connection to the full archive, for metadata-only discovery.

    Reserved for the quarantine views, which return senders, timestamps and
    counts. Never use this to return message content: that is precisely the
    untrusted text the allowlist exists to keep out of the model's context.
    """
    db_uri = "file:" + os.path.abspath(MESSAGES_DB_PATH) + "?mode=ro"
    return sqlite3.connect(db_uri, uri=True)
