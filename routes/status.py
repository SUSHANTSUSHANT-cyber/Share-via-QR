"""Status-related routes placeholder."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/status", tags=["status"])


@router.get("", include_in_schema=False)
def placeholder_status() -> dict[str, str]:
    """Placeholder endpoint for future status functionality."""
    return {"message": "TODO: Implement transfer status handling in a future phase."}
