"""Session-related routes placeholder."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/session", tags=["session"])


@router.get("", include_in_schema=False)
def placeholder_session() -> dict[str, str]:
    """Placeholder endpoint for future session functionality."""
    return {"message": "TODO: Implement session handling in a future phase."}
