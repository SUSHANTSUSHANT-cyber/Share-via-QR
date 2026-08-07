"""Upload-related routes placeholder."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/upload", tags=["upload"])


@router.get("", include_in_schema=False)
def placeholder_upload() -> dict[str, str]:
    """Placeholder endpoint for future upload functionality."""
    return {"message": "TODO: Implement upload handling in a future phase."}
