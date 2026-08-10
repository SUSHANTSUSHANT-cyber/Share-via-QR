"""Utility helper functions for future application features.

Keep shared helper logic here and keep it lightweight.
"""

from __future__ import annotations

from config.settings import settings


def build_message(prefix: str, value: str) -> str:
    """Create a simple formatted message.

    Args:
        prefix: A short label to prefix the message.
        value: The value to include in the message.

    Returns:
        A formatted message string.
    """
    return f"{prefix}: {value}"


def build_public_url(path: str = "") -> str:
    """Build a public URL from the configured server base URL.

    Args:
        path: An optional route path to append to the base URL.

    Returns:
        A public URL that is independent of local network bindings.
    """
    base_url = settings.server_url.rstrip("/")
    if not path:
        return base_url
    normalized_path = path if path.startswith("/") else f"/{path}"
    return f"{base_url}{normalized_path}"
