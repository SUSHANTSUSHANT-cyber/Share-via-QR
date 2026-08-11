"""Home page router."""

from __future__ import annotations

import re
import urllib.parse

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse

from utils.security import require_receiver

router = APIRouter(dependencies=[Depends(require_receiver)])


def _validate_receiver_hostname(hostname: str | None) -> tuple[str | None, str | None]:
    if hostname is None:
        return None, "Receiver hostname is required."

    decoded = urllib.parse.unquote_plus(hostname).strip()
    if not decoded:
        return None, "Receiver hostname is required."
    if len(decoded) > 255:
        return None, "Receiver hostname is too long."
    if not re.fullmatch(r"[A-Za-z0-9._-]+", decoded):
        return None, "Receiver hostname is malformed."
    return decoded, None


@router.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    """Render the landing page for the application."""
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "receiver_hostname": "",
            "hostname_error": None,
        },
    )


@router.get("/receiver", response_class=HTMLResponse)
async def receiver(request: Request, hostname: str | None = None) -> HTMLResponse:
    """Render the receiver page with an optional hostname for audit metadata."""
    receiver_hostname, hostname_error = _validate_receiver_hostname(hostname)
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "receiver_hostname": receiver_hostname or "",
            "hostname_error": hostname_error,
        },
    )
