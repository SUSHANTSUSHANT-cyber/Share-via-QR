"""Session-related routes for creating, retrieving, and deleting sessions."""

from __future__ import annotations

from fastapi import APIRouter, Response

from models.session import SessionCreateRequest, SessionRecord, SessionResponse
from services.qr_service import QRService
from services.session_service import SessionService

router = APIRouter(prefix="/session", tags=["session"])
service = SessionService()
qr_service = QRService()


@router.post("/create", response_model=SessionResponse)
def create_session(request: SessionCreateRequest) -> SessionResponse:
    """Create a new transfer session."""
    return service.create_session(request)


@router.get("/{session_id}", response_model=SessionRecord)
def get_session(session_id: str) -> SessionRecord:
    """Retrieve a transfer session by identifier."""
    result = service.get_session(session_id)
    if isinstance(result, SessionRecord):
        return result
    return result


@router.get("/{session_id}/qr", response_class=Response)
def get_session_qr(session_id: str) -> Response:
    """Return a QR image for the specified session."""
    session = service.validate_session(session_id)
    png_bytes = qr_service.generate_qr_png(session.session_id)
    return Response(content=png_bytes, media_type="image/png")


@router.delete("/{session_id}")
def delete_session(session_id: str) -> dict[str, str]:
    """Delete a transfer session by identifier."""
    return service.delete_session(session_id)
