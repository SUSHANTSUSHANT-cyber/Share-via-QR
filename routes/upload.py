"""Upload-related routes for the enterprise transfer workflow."""

from __future__ import annotations

import logging
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse

from config.settings import settings
from services.session_service import SessionService

router = APIRouter(prefix="/upload", tags=["upload"])
service = SessionService()
logger = logging.getLogger("qr_transfer_system")


@router.get("/{session_id}", response_class=HTMLResponse)
async def upload_page(session_id: str, request: Request) -> HTMLResponse:
    """Render the upload page for a valid session."""
    try:
        record = service.validate_session(session_id)
    except HTTPException as exc:
        if exc.status_code == 404:
            logger.warning("Invalid session: %s", session_id)
        elif exc.status_code == 410:
            logger.warning("Expired session: %s", session_id)
        raise

    logger.info("Upload page opened: %s", session_id)
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="upload.html",
        context={
            "request": request,
            "session": record,
            "max_file_size_mb": settings.max_file_size_mb,
        },
    )


@router.post("/{session_id}")
async def upload_file(
    session_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile | None = File(None),
    files: list[UploadFile] = File(default=[]),
) -> dict[str, object]:
    """Handle file uploads for a validated transfer session."""
    upload_files: list[UploadFile] = []
    if files:
        upload_files.extend(files)
    if file is not None:
        upload_files.append(file)

    if not upload_files:
        raise HTTPException(status_code=400, detail="At least one file must be uploaded.")

    result, filenames = await service.process_uploads(session_id, upload_files)
    if settings.storage_backend.lower() == "sharepoint":
        background_tasks.add_task(service.upload_staged_files_to_sharepoint, session_id, filenames)

    logger.info("Files accepted for session %s: %s", session_id, ", ".join(filenames))
    return {
        "success": True,
        "session_id": result.session_id,
        "filenames": filenames,
        "status": result.status,
        "message": "File(s) queued for SharePoint upload." if result.status == "uploading" else "File(s) uploaded successfully.",
    }
