"""Background cleanup service for expired sessions and SharePoint files.

This module provides a minimal periodic cleanup loop that finds expired
transfer sessions and deletes remaining SharePoint-backed files, recording
deletion metadata in the session record.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime

from config.constants import STATUS_EXPIRED
from config.settings import settings
from database.database import list_active_sessions, update_session_status
from services.session_service import SessionService

logger = logging.getLogger("qr_transfer_system")


def perform_cleanup_once() -> None:
    """Perform one pass of cleanup: delete SharePoint files for expired sessions."""
    service = SessionService()
    try:
        sessions = list_active_sessions()
    except Exception:
        logger.exception("Failed to list active sessions for cleanup")
        return

    now = datetime.utcnow()
    for record in sessions:
        # Parse expiry if available
        try:
            expires_at = record.expires_at
            if not expires_at:
                continue
            expires_dt = datetime.fromisoformat(expires_at)
        except Exception:
            # Skip if timestamp malformed
            continue

        if now < expires_dt:
            continue

        # expired — only act on SharePoint-backed sessions
        storage_meta = record.storage_metadata or {}
        backend = storage_meta.get("backend")
        if backend != "sharepoint":
            # do not delete local files here
            try:
                update_session_status(record.session_id, STATUS_EXPIRED)
            except Exception:
                logger.exception("Failed to mark session expired: %s", record.session_id)
            continue

        files_meta = storage_meta.get("files", {})
        filenames = [name for name, meta in files_meta.items() if not meta.get("deleted_at")]
        if not filenames:
            try:
                update_session_status(record.session_id, STATUS_EXPIRED)
            except Exception:
                logger.exception("Failed to mark session expired: %s", record.session_id)
            continue

        logger.info("Cleanup: deleting %d SharePoint files for expired session %s", len(filenames), record.session_id)
        try:
            results = service.delete_sharepoint_files(record.session_id, filenames, "session_expired")
            # After attempts, mark session expired regardless of deletion outcome
            update_session_status(record.session_id, STATUS_EXPIRED)
            # Log per-file failures
            for fname, ok in results.items():
                if not ok:
                    logger.warning("Cleanup deletion failed for %s in session %s", fname, record.session_id)
        except Exception:
            logger.exception("Cleanup run failed for session %s", record.session_id)


def _cleanup_loop(interval_minutes: int, stop_event: threading.Event) -> None:
    interval = max(1, int(interval_minutes)) * 60
    logger.info("Cleanup loop started, interval=%s minutes", interval_minutes)
    while not stop_event.wait(interval):
        try:
            perform_cleanup_once()
        except Exception:
            logger.exception("Unexpected error during cleanup pass")


def start_background_cleanup() -> threading.Event:
    """Start the cleanup loop in a daemon thread and return a stop event.

    The caller may hold the returned threading.Event to signal shutdown.
    """
    stop_event = threading.Event()
    thread = threading.Thread(target=_cleanup_loop, args=(settings.cleanup_interval_minutes, stop_event), daemon=True)
    thread.start()
    return stop_event

