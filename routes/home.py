"""Home page router."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    """Render the landing page for the application."""
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request},
    )
