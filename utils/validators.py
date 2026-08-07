"""Validation helpers for future application features.

These helpers are intentionally minimal placeholders.
"""

from __future__ import annotations


def is_non_empty(value: str) -> bool:
    """Return whether the provided string contains content.

    Args:
        value: The string to validate.

    Returns:
        True when the value is not empty after stripping whitespace.
    """
    return bool(value and value.strip())
