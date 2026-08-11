"""Transfer-related routes for the enterprise QR transfer workflow."""

from __future__ import annotations

import base64
import logging
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, Response

from models.session import SessionCreateRequest
from services.qr_service import QRService
from services.session_service import SessionService

from utils.security import require_receiver

router = APIRouter(prefix="/transfer", tags=["transfer"], dependencies=[Depends(require_receiver)])
service = SessionService()
qr_service = QRService()
logger = logging.getLogger("qr_transfer_system")


@router.get("/start", response_class=HTMLResponse)
async def start_transfer(request: Request) -> HTMLResponse:
    """Start a new transfer session and render the QR transfer page."""
    session = service.create_session(SessionCreateRequest(employee_code=None))
    qr_png = qr_service.generate_qr_png(session.session_id)
    qr_data = base64.b64encode(qr_png).decode("ascii")

    logger.info("Transfer session created: %s", session.session_id)
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="transfer.html",
        context={
            "request": request,
            "session": session,
            "qr_data": qr_data,
        },
    )
