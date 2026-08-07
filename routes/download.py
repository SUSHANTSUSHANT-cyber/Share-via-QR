"""Download-related routes placeholder."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/download", tags=["download"])


@router.get("", include_in_schema=False)
def placeholder_download() -> dict[str, str]:
    """Placeholder endpoint for future download functionality."""
    return {"message": "TODO: Implement download handling in a future phase."}
