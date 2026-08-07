"""Application constants for the QR transfer system.

These constants provide reusable status values and defaults to keep the codebase
consistent and free of magic strings.
"""

from __future__ import annotations

APP_NAME = "QR Transfer System"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000

STATUS_CREATED = "created"
STATUS_UPLOADED = "uploaded"
STATUS_DOWNLOADED = "downloaded"
STATUS_EXPIRED = "expired"
DEFAULT_SESSION_STATUS = STATUS_CREATED
