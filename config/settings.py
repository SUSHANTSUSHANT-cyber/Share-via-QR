"""Application configuration loader for the QR transfer system.

The settings are loaded from environment variables and an optional .env file
using python-dotenv. The module exposes a singleton settings object for the
application.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)

logger = logging.getLogger("qr_transfer_system")


@dataclass(frozen=True)
class Settings:
    """Application configuration container."""

    app_name: str
    app_version: str
    host: str
    port: int
    server_url: str
    database_path: str
    session_expiry_minutes: int
    max_file_size_mb: int
    allowed_mime_types: tuple[str, ...]
    blocked_extensions: tuple[str, ...]
    cleanup_interval_minutes: int
    graph_client_id: str
    graph_client_secret: str
    graph_tenant_id: str
    sharepoint_site_id: str
    sharepoint_drive_id: str


def _as_int(value: str | None, default: int) -> int:
    """Convert a string environment value to an integer."""
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _as_tuple(value: str | None, default: tuple[str, ...]) -> tuple[str, ...]:
    """Convert a comma-separated environment value to a tuple."""
    if value is None or value.strip() == "":
        return default
    return tuple(item.strip() for item in value.split(",") if item.strip())


def build_settings() -> Settings:
    """Build settings from environment variables and defaults."""
    settings_values: dict[str, Any] = {
        "app_name": os.getenv("APP_NAME", "QR Transfer System"),
        "app_version": os.getenv("APP_VERSION", "0.2.0"),
        "host": os.getenv("HOST", "127.0.0.1"),
        "port": _as_int(os.getenv("PORT"), 8000),
        "server_url": os.getenv("SERVER_URL", "http://127.0.0.1:8000"),
        "database_path": os.getenv("DATABASE_PATH", str(BASE_DIR / "database.db")),
        "session_expiry_minutes": _as_int(os.getenv("SESSION_EXPIRY_MINUTES"), 60),
        "max_file_size_mb": _as_int(os.getenv("MAX_FILE_SIZE_MB"), 100),
        "allowed_mime_types": _as_tuple(
            os.getenv("ALLOWED_MIME_TYPES"),
            ("application/pdf", "application/octet-stream"),
        ),
        "blocked_extensions": _as_tuple(
            os.getenv("BLOCKED_EXTENSIONS"),
            (".exe", ".bat", ".cmd"),
        ),
        "cleanup_interval_minutes": _as_int(
            os.getenv("CLEANUP_INTERVAL_MINUTES"),
            30,
        ),
        "graph_client_id": os.getenv("GRAPH_CLIENT_ID", "placeholder-client-id"),
        "graph_client_secret": os.getenv("GRAPH_CLIENT_SECRET", "placeholder-client-secret"),
        "graph_tenant_id": os.getenv("GRAPH_TENANT_ID", "placeholder-tenant-id"),
        "sharepoint_site_id": os.getenv("SHAREPOINT_SITE_ID", "placeholder-site-id"),
        "sharepoint_drive_id": os.getenv("SHAREPOINT_DRIVE_ID", "placeholder-drive-id"),
    }
    return Settings(**settings_values)


settings = build_settings()
logger.info("Configuration loaded from %s", ENV_FILE)
