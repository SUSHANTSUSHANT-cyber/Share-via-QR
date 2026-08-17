"""Constants used throughout the AISIN Secure File Transfer application.

These constants provide reusable status values and defaults to keep the codebase
consistent and free of magic strings.
"""

from __future__ import annotations

APP_NAME = "AISIN Secure File Transfer"
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 9000
DEFAULT_SERVER_URL = "https://your-public-domain.example.com"

STATUS_CREATED = "created"
STATUS_UPLOADING = "uploading"
STATUS_UPLOADED = "uploaded"
STATUS_FAILED = "failed"
STATUS_DOWNLOADED = "downloaded"
STATUS_EXPIRED = "expired"
DEFAULT_SESSION_STATUS = STATUS_CREATED
