"""SQLite persistence helpers for transfer sessions.

This module provides a small, reusable database layer using only the standard
library sqlite3 module. Each operation opens and closes its own connection.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from config.constants import DEFAULT_SESSION_STATUS
from config.settings import settings
from models.session import SessionRecord

logger = logging.getLogger("qr_transfer_system")


def _get_connection() -> sqlite3.Connection:
    """Create a connection to the SQLite database."""
    connection = sqlite3.connect(settings.database_path)
    connection.row_factory = sqlite3.Row
    return connection


def _serialize_storage_metadata(storage_metadata: dict[str, Any] | None) -> str | None:
    """Serialize storage metadata for database persistence."""
    if storage_metadata is None:
        return None
    return json.dumps(storage_metadata)


def _deserialize_storage_metadata(value: str | None) -> dict[str, Any]:
    """Deserialize storage metadata from the database."""
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def initialize_database() -> None:
    """Create the database file and transfer_sessions table if needed."""
    database_path = Path(settings.database_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with _get_connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS transfer_sessions (
                    session_id TEXT PRIMARY KEY,
                    employee_code TEXT,
                    folder_name TEXT,
                    status TEXT,
                    created_at TEXT,
                    expires_at TEXT,
                    uploaded_at TEXT,
                    downloaded_at TEXT,
                    hostname TEXT,
                    storage_metadata TEXT
                )
                """
            )
            columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(transfer_sessions)").fetchall()
            }
            if "storage_metadata" not in columns:
                connection.execute("ALTER TABLE transfer_sessions ADD COLUMN storage_metadata TEXT")
                columns.add("storage_metadata")
            if "hostname" not in columns:
                connection.execute("ALTER TABLE transfer_sessions ADD COLUMN hostname TEXT")
            connection.commit()
        logger.info("Database initialized at %s", database_path)
    except sqlite3.Error as exc:
        logger.exception("Database initialization failed: %s", exc)
        raise


def create_session(
    session_id: str,
    employee_code: str | None = None,
    folder_name: str | None = None,
    status: str = DEFAULT_SESSION_STATUS,
    created_at: str | None = None,
    expires_at: str | None = None,
    hostname: str | None = None,
) -> SessionRecord | None:
    """Create a new transfer session record."""
    if created_at is None:
        created_at = datetime.utcnow().isoformat()

    try:
        with _get_connection() as connection:
            connection.execute(
                """
                INSERT INTO transfer_sessions (
                    session_id,
                    employee_code,
                    folder_name,
                    status,
                    created_at,
                    expires_at,
                    uploaded_at,
                    downloaded_at,
                    hostname
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    employee_code,
                    folder_name,
                    status,
                    created_at,
                    expires_at,
                    None,
                    None,
                    hostname,
                ),
            )
            connection.commit()
        return get_session(session_id)
    except sqlite3.Error as exc:
        logger.exception("Failed to create session %s: %s", session_id, exc)
        raise


def update_storage_metadata(session_id: str, storage_metadata: dict[str, Any]) -> SessionRecord | None:
    """Persist storage metadata for a session."""
    try:
        with _get_connection() as connection:
            connection.execute(
                "UPDATE transfer_sessions SET storage_metadata = ? WHERE session_id = ?",
                (_serialize_storage_metadata(storage_metadata), session_id),
            )
            connection.commit()
        return get_session(session_id)
    except sqlite3.Error as exc:
        logger.exception("Failed to update storage metadata for session %s: %s", session_id, exc)
        raise


def get_session(session_id: str) -> SessionRecord | None:
    """Fetch a single session by its identifier."""
    try:
        with _get_connection() as connection:
            row = connection.execute(
                "SELECT * FROM transfer_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        data = dict(row)
        data["storage_metadata"] = _deserialize_storage_metadata(data.get("storage_metadata"))
        return SessionRecord.model_validate(data)
    except sqlite3.Error as exc:
        logger.exception("Failed to fetch session %s: %s", session_id, exc)
        raise


def update_session_status(session_id: str, status: str) -> SessionRecord | None:
    """Update the status of an existing session."""
    try:
        with _get_connection() as connection:
            connection.execute(
                "UPDATE transfer_sessions SET status = ? WHERE session_id = ?",
                (status, session_id),
            )
            connection.commit()
        return get_session(session_id)
    except sqlite3.Error as exc:
        logger.exception("Failed to update session status %s: %s", session_id, exc)
        raise


def mark_uploaded(session_id: str, uploaded_at: str | None = None) -> SessionRecord | None:
    """Mark a session as uploaded."""
    if uploaded_at is None:
        uploaded_at = datetime.utcnow().isoformat()

    try:
        with _get_connection() as connection:
            connection.execute(
                "UPDATE transfer_sessions SET uploaded_at = ?, status = ? WHERE session_id = ?",
                (uploaded_at, "uploaded", session_id),
            )
            connection.commit()
        return get_session(session_id)
    except sqlite3.Error as exc:
        logger.exception("Failed to mark session %s as uploaded: %s", session_id, exc)
        raise


def mark_downloaded(session_id: str, downloaded_at: str | None = None) -> SessionRecord | None:
    """Mark a session as downloaded."""
    if downloaded_at is None:
        downloaded_at = datetime.utcnow().isoformat()

    try:
        with _get_connection() as connection:
            connection.execute(
                "UPDATE transfer_sessions SET downloaded_at = ?, status = ? WHERE session_id = ?",
                (downloaded_at, "downloaded", session_id),
            )
            connection.commit()
        return get_session(session_id)
    except sqlite3.Error as exc:
        logger.exception("Failed to mark session %s as downloaded: %s", session_id, exc)
        raise


def delete_session(session_id: str) -> None:
    """Delete a session record by identifier."""
    try:
        with _get_connection() as connection:
            connection.execute(
                "DELETE FROM transfer_sessions WHERE session_id = ?",
                (session_id,),
            )
            connection.commit()
    except sqlite3.Error as exc:
        logger.exception("Failed to delete session %s: %s", session_id, exc)
        raise


def delete_expired_sessions() -> int:
    """Delete all expired sessions and return the number removed."""
    try:
        with _get_connection() as connection:
            cursor = connection.execute(
                "DELETE FROM transfer_sessions WHERE status = ?",
                ("expired",),
            )
            connection.commit()
        return cursor.rowcount
    except sqlite3.Error as exc:
        logger.exception("Failed to delete expired sessions: %s", exc)
        raise


def list_active_sessions() -> list[SessionRecord]:
    """Return all non-expired sessions as Pydantic models."""
    try:
        with _get_connection() as connection:
            rows = connection.execute(
                "SELECT * FROM transfer_sessions WHERE status != ? ORDER BY created_at",
                ("expired",),
            ).fetchall()
        return [SessionRecord.model_validate(dict(row)) for row in rows]
    except sqlite3.Error as exc:
        logger.exception("Failed to list active sessions: %s", exc)
        raise
