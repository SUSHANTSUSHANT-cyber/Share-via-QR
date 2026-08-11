"""Download-related routes for the secure transfer workflow.

Supports both local filesystem and SharePoint-backed files. Receiver-side
access is protected by the `require_receiver` dependency on this router.
"""

from __future__ import annotations

import io
import logging
import mimetypes
import zipfile
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import FileResponse, StreamingResponse
from starlette.background import BackgroundTask

from config.settings import settings

from services.session_service import SessionService
from utils.security import require_receiver

router = APIRouter(prefix="/download", tags=["download"], dependencies=[Depends(require_receiver)])
service = SessionService()
logger = logging.getLogger("qr_transfer_system")


@router.head("/{session_id}")
def download_file_head(session_id: str) -> FileResponse:
    """Return file metadata for a completed transfer session."""
    if settings.storage_backend.lower() == "sharepoint":
        record = service.validate_session(session_id)
        metadata = record.storage_metadata.get("files", {}) if record.storage_metadata else {}
        if not metadata:
            raise HTTPException(status_code=404, detail="Uploaded file not found")
        filename = next(iter(metadata))
        return FileResponse(
            path=str(Path(filename)),
            filename=filename,
            media_type="application/octet-stream",
        )

    file_path = service.get_uploaded_file_path(session_id)
    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type=mimetypes.guess_type(file_path.name, strict=False)[0] or "application/octet-stream",
    )


@router.get("/{session_id}", response_model=None)
def download_file(
    session_id: str,
    filename: str | None = None,
    archive: bool = Query(False),
) -> FileResponse | StreamingResponse:
    """Return the uploaded file or a ZIP archive for a completed transfer session."""
    if archive:
        files = service.get_uploaded_files(session_id)
        if not files:
            raise HTTPException(status_code=404, detail="Uploaded files not found")

        buffer = io.BytesIO()
        archive_filenames: list[str] = []
        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zipf:
            if settings.storage_backend.lower() == "sharepoint":
                for file_info in files:
                    content = service.get_sharepoint_file_content(session_id, file_info["filename"])
                    zipf.writestr(file_info["filename"], content)
                    archive_filenames.append(file_info["filename"])
            else:
                for file_info in files:
                    file_path = service.get_uploaded_file_path(session_id, file_info["filename"])
                    zipf.write(file_path, arcname=file_path.name)
        buffer.seek(0)

        bg_task = None
        if settings.storage_backend.lower() == "sharepoint":
            # finalize_download_and_delete will record per-file downloaded_at and
            # delete SharePoint items once the streaming finishes successfully.
            bg_task = BackgroundTask(service.finalize_download_and_delete, session_id, archive_filenames, "download")

        response = StreamingResponse(
            buffer,
            media_type="application/zip",
            background=bg_task,
            headers={
                "Content-Disposition": f"attachment; filename=files_{session_id}.zip",
            },
        )
    else:
        if settings.storage_backend.lower() == "sharepoint":
            file_name = filename or service.get_uploaded_file_path(session_id, filename).name
            file_bytes = service.get_sharepoint_file_content(session_id, file_name)
            media_type, _ = mimetypes.guess_type(file_name, strict=False)
            bg_task = BackgroundTask(service.finalize_download_and_delete, session_id, [file_name], "download")
            response = StreamingResponse(
                io.BytesIO(file_bytes),
                media_type=media_type or "application/octet-stream",
                background=bg_task,
                headers={
                    "Content-Disposition": f"attachment; filename={file_name}",
                },
            )
        else:
            file_path = service.get_uploaded_file_path(session_id, filename)
            media_type, _ = mimetypes.guess_type(file_path.name, strict=False)
            response = FileResponse(
                path=str(file_path),
                filename=file_path.name,
                media_type=media_type or "application/octet-stream",
            )

    service.mark_downloaded(session_id)
    if archive:
        display_name = "archive"
    else:
        # prefer resolved name from SharePoint branch, fall back to provided filename
        if settings.storage_backend.lower() == "sharepoint":
            display_name = filename or file_name
        else:
            display_name = file_path.name

    logger.info(
        "Download initiated for session %s: %s",
        session_id,
        display_name,
    )
    return response
