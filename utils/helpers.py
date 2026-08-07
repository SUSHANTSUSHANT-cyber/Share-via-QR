"""Utility helper functions for future application features.

Keep shared helper logic here and keep it lightweight.
"""

from __future__ import annotations


def build_message(prefix: str, value: str) -> str:
    """Create a simple formatted message.

    Args:
        prefix: A short label to prefix the message.
        value: The value to include in the message.

    Returns:
        A formatted message string.
    """
    return f"{prefix}: {value}"
