"""Session service for creating, retrieving, and deleting transfer sessions."""

from __future__ import annotations

import logging
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from fastapi.responses import JSONResponse

from config.constants import (
    STATUS_CREATED,
    STATUS_DOWNLOADED,
    STATUS_EXPIRED,
    STATUS_FAILED,
    STATUS_UPLOADED,
    STATUS_UPLOADING,
)
from config.settings import settings
from database.database import create_session as create_session_record
from database.database import update_storage_metadata
from database.database import delete_session as delete_session_record
from database.database import get_session as get_session_record
from database.database import mark_downloaded as mark_session_downloaded
from database.database import mark_uploaded as mark_session_uploaded
from database.database import update_session_status
from models.session import SessionCreateRequest, SessionFile, SessionRecord, SessionResponse
from services.sharepoint_service import SharePointService

logger = logging.getLogger("qr_transfer_system")


class SessionService:
    """Coordinate session lifecycle operations for the API layer."""

    def __init__(self) -> None:
        """Initialize the service."""
        self.logger = logger
        self.sharepoint_service: SharePointService | None = None
        if settings.storage_backend.lower() == "sharepoint":
            self.sharepoint_service = SharePointService()

    def create_session(self, request: SessionCreateRequest) -> SessionResponse:
        """Create a new session record and return its public response."""
        if request.employee_code is not None:
            try:
                employee_code = self._validate_employee_code(request.employee_code)
            except ValueError as exc:
                self.logger.warning("Invalid session creation request: %s", exc)
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        else:
            employee_code = None

        session_id = self.generate_session_id()
        created_at = self._format_timestamp(datetime.utcnow())
        expires_at = self._format_timestamp(
            datetime.utcnow() + timedelta(minutes=settings.session_expiry_minutes)
        )
        folder_name = self._make_folder_name(session_id, request.hostname)

        try:
            record = create_session_record(
                session_id=session_id,
                employee_code=employee_code,
                folder_name=folder_name,
                status=STATUS_CREATED,
                created_at=created_at,
                expires_at=expires_at,
                hostname=request.hostname,
            )
        except sqlite3.Error as exc:
            self.logger.exception("Failed to create session for employee %s", employee_code)
            raise HTTPException(status_code=500, detail="Unable to create session") from exc

        self.logger.info("Session created: %s", session_id)
        return SessionResponse(
            session_id=record.session_id,
            employee_code=record.employee_code,
            hostname=record.hostname,
            status=record.status,
            created_at=record.created_at,
            expires_at=record.expires_at,
            folder_name=record.folder_name,
        )

    def _store_session_hostname(self, session_id: str, hostname: str) -> None:
        """Persist the receiver hostname into session storage metadata."""
        record = get_session_record(session_id)
        if record is None:
            self.logger.warning("Failed to store hostname for missing session: %s", session_id)
            return

        metadata = record.storage_metadata or {}
        metadata["receiver_hostname"] = hostname
        try:
            update_storage_metadata(session_id, metadata)
        except sqlite3.Error as exc:
            self.logger.exception(
                "Failed to persist receiver hostname for session %s: %s",
                session_id,
                exc,
            )

    def get_session(self, session_id: str) -> SessionRecord | JSONResponse:
        """Retrieve a session record and return a 410 response for expired sessions."""
        try:
            record = get_session_record(session_id)
        except sqlite3.Error as exc:
            self.logger.exception("Failed to retrieve session %s", session_id)
            raise HTTPException(status_code=500, detail="Unable to retrieve session") from exc

        if record is None:
            self.logger.warning("Session not found: %s", session_id)
            raise HTTPException(status_code=404, detail="Session not found")

        if self.is_expired(record):
            self.logger.info("Expired session detected: %s", session_id)
            expired_record = record.model_copy(update={"status": STATUS_EXPIRED})
            return JSONResponse(
                status_code=410,
                content=expired_record.model_dump(),
            )

        files = self.get_uploaded_files(session_id)
        file_models: list[SessionFile] = []
        for f in files:
            file_models.append(
                SessionFile(
                    filename=f.get("filename"),
                    size=int(f.get("size", 0) or 0),
                    item_id=f.get("item_id"),
                    content_type=f.get("content_type"),
                    web_url=f.get("web_url"),
                )
            )
        enriched_record = record.model_copy(update={"files": file_models})
        self.logger.info("Session retrieved: %s", session_id)
        return enriched_record

    def delete_session(self, session_id: str) -> dict[str, str]:
        """Delete a session record from the database."""
        try:
            record = get_session_record(session_id)
        except sqlite3.Error as exc:
            self.logger.exception("Failed to check session before delete %s", session_id)
            raise HTTPException(status_code=500, detail="Unable to delete session") from exc

        if record is None:
            self.logger.warning("Session not found for deletion: %s", session_id)
            raise HTTPException(status_code=404, detail="Session not found")

        try:
            delete_session_record(session_id)
        except sqlite3.Error as exc:
            self.logger.exception("Failed to delete session %s", session_id)
            raise HTTPException(status_code=500, detail="Unable to delete session") from exc

        self.logger.info("Session deleted: %s", session_id)
        return {"message": "Session deleted successfully"}

    def generate_session_id(self) -> str:
        """Generate a unique session identifier."""
        return str(uuid4())

    def _make_folder_name(self, session_id: str, hostname: str | None) -> str:
        """Build a safe SharePoint folder name that includes hostname when available."""
        base_name = f"session_{session_id}"
        if not hostname:
            return base_name

        safe_hostname = re.sub(r"[^A-Za-z0-9 _\-]", "_", hostname.strip())
        safe_hostname = re.sub(r"\s+", "_", safe_hostname)
        safe_hostname = safe_hostname.strip("_ ")
        if not safe_hostname:
            return base_name

        return f"{safe_hostname}_{session_id}"

    def calculate_expiry(self, created_at: datetime) -> datetime:
        """Calculate the expiry timestamp for a session."""
        return created_at + timedelta(minutes=settings.session_expiry_minutes)

    def validate_session(self, session_id: str) -> SessionRecord:
        """Validate that a session exists and is not expired."""
        record = get_session_record(session_id)
        if record is None:
            self.logger.warning("Invalid session validation: %s", session_id)
            raise HTTPException(status_code=404, detail="Session not found")
        if self.is_expired(record):
            self.logger.warning("Expired session validation: %s", session_id)
            raise HTTPException(status_code=410, detail="Session expired")
        return record

    def mark_downloaded(self, session_id: str) -> SessionRecord | None:
        """Mark a session record as downloaded."""
        try:
            updated = mark_session_downloaded(session_id, downloaded_at=self._format_timestamp(datetime.utcnow()))
        except sqlite3.Error as exc:
            self.logger.exception("Failed to update download status for session %s", session_id)
            raise HTTPException(status_code=500, detail="Unable to update session download status") from exc
        if updated is None:
            self.logger.warning("Failed to find session when marking downloaded: %s", session_id)
            raise HTTPException(status_code=404, detail="Session not found")
        return updated

    def record_file_downloaded(self, session_id: str, filename: str) -> None:
        """Record per-file downloaded_at metadata for auditing."""
        record = get_session_record(session_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Session not found")

        metadata = record.storage_metadata or {}
        files_meta = metadata.get("files", {}) if metadata else {}
        file_meta = files_meta.get(filename)
        if not file_meta:
            raise HTTPException(status_code=404, detail="Uploaded file not found")

        file_meta["downloaded_at"] = self._format_timestamp(datetime.utcnow())
        files_meta[filename] = file_meta
        metadata["files"] = files_meta
        update_storage_metadata(session_id, metadata)

    def delete_sharepoint_file(self, session_id: str, filename: str, reason: str) -> bool:
        """Delete a single SharePoint file and update storage metadata.

        Returns True if deletion succeeded or file already deleted, False otherwise.
        """
        if self.sharepoint_service is None:
            return False

        record = get_session_record(session_id)
        if record is None:
            self.logger.warning("Attempted to delete file for missing session: %s", session_id)
            return False

        metadata = record.storage_metadata or {}
        files_meta = metadata.get("files", {}) if metadata else {}
        file_meta = files_meta.get(filename)
        if not file_meta:
            self.logger.warning("No metadata for file to delete: %s / %s", session_id, filename)
            return False

        if file_meta.get("deleted_at"):
            # Already deleted
            return True

        item_id = file_meta.get("item_id")
        if not item_id:
            self.logger.warning("No item_id present for SharePoint file: %s / %s", session_id, filename)
            return False

        try:
            self.sharepoint_service.delete_file(item_id)
        except Exception as exc:
            self.logger.exception("Failed to delete SharePoint file %s for session %s: %s", filename, session_id, exc)
            return False

        # on success update metadata
        file_meta["deleted_at"] = self._format_timestamp(datetime.utcnow())
        file_meta["deletion_reason"] = reason
        file_meta["status"] = "deleted"
        files_meta[filename] = file_meta
        metadata["files"] = files_meta
        try:
            update_storage_metadata(session_id, metadata)
        except Exception:
            self.logger.exception("Failed to persist storage metadata after deletion for session %s", session_id)

        return True

    def delete_sharepoint_files(self, session_id: str, filenames: list[str], reason: str) -> dict[str, bool]:
        """Delete multiple SharePoint files and return per-file success map."""
        results: dict[str, bool] = {}
        for fname in filenames:
            try:
                ok = self.delete_sharepoint_file(session_id, fname, reason)
                results[fname] = ok
            except Exception:
                self.logger.exception("Unexpected error deleting SharePoint file %s for session %s", fname, session_id)
                results[fname] = False
        return results

    def finalize_download_and_delete(self, session_id: str, filenames: list[str], reason: str) -> dict[str, bool]:
        """Record downloaded_at for each file then attempt deletion from SharePoint.

        This is intended to run as a background task after a successful response
        has been streamed to the receiver.
        """
        results: dict[str, bool] = {}
        for fname in filenames:
            try:
                try:
                    self.record_file_downloaded(session_id, fname)
                except Exception:
                    # still attempt deletion even if recording downloaded_at failed
                    self.logger.exception("Failed to record downloaded_at for %s in %s", fname, session_id)

                ok = self.delete_sharepoint_file(session_id, fname, reason)
                results[fname] = ok
            except Exception:
                self.logger.exception("Unexpected finalize error for %s in %s", fname, session_id)
                results[fname] = False
        return results

    def get_uploaded_file_path(self, session_id: str, filename: str | None = None) -> Path:
        """Return the uploaded file path for a completed session."""
        record = get_session_record(session_id)
        if record is None:
            self.logger.warning("Download requested for missing session: %s", session_id)
            raise HTTPException(status_code=404, detail="Session not found")

        if record.status not in {STATUS_UPLOADED, STATUS_DOWNLOADED}:
            self.logger.warning(
                "Download requested for session without uploaded file: %s status=%s",
                session_id,
                record.status,
            )
            raise HTTPException(status_code=409, detail="No uploaded file available for this session")

        if settings.storage_backend.lower() == "sharepoint":
            metadata = record.storage_metadata.get("files", {}) if record.storage_metadata else {}
            if not metadata:
                raise HTTPException(status_code=404, detail="Uploaded file not found")
            file_name = Path(filename).name if filename else next(iter(metadata))
            if file_name not in metadata:
                raise HTTPException(status_code=404, detail="Uploaded file not found")
            return Path(file_name)

        upload_root = Path("uploads").resolve()
        session_dir = (upload_root / session_id).resolve()
        if not session_dir.is_relative_to(upload_root) or not session_dir.is_dir():
            self.logger.warning("Uploaded file directory missing or invalid for session: %s", session_id)
            raise HTTPException(status_code=404, detail="Uploaded file not found")

        if filename:
            safe_name = Path(filename).name
            file_path = (session_dir / safe_name).resolve()
            if not file_path.is_file() or not file_path.is_relative_to(session_dir):
                self.logger.warning(
                    "Requested file missing or invalid for session %s: %s",
                    session_id,
                    safe_name,
                )
                raise HTTPException(status_code=404, detail="Uploaded file not found")
            return file_path

        files = sorted([entry for entry in session_dir.iterdir() if entry.is_file()], key=lambda p: p.name.lower())
        if not files:
            self.logger.warning("No uploaded file found in session directory: %s", session_id)
            raise HTTPException(status_code=404, detail="Uploaded file not found")

        return files[0]

    def get_sharepoint_file_content(self, session_id: str, filename: str) -> bytes:
        """Retrieve a SharePoint-stored file content by session metadata."""
        if self.sharepoint_service is None:
            raise HTTPException(status_code=500, detail="SharePoint storage is not configured")

        record = get_session_record(session_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Session not found")

        metadata = record.storage_metadata.get("files", {}) if record.storage_metadata else {}
        file_meta = metadata.get(filename)
        if not file_meta:
            raise HTTPException(status_code=404, detail="Uploaded file not found")

        item_id = file_meta.get("item_id")
        if not item_id:
            raise HTTPException(status_code=404, detail="Uploaded file not found")

        return self.sharepoint_service.download_file(item_id)

    def get_uploaded_files(self, session_id: str) -> list[dict[str, object]]:
        """Return metadata for all uploaded files in a completed session."""
        record = get_session_record(session_id)
        if record is None:
            return []

        if settings.storage_backend.lower() == "sharepoint":
            metadata = record.storage_metadata.get("files", {}) if record.storage_metadata else {}
            files: list[dict[str, object]] = []
            for filename, file_meta in sorted(metadata.items()):
                files.append(
                    {
                        "filename": filename,
                        "size": int(file_meta.get("size", 0) or 0),
                        "item_id": file_meta.get("item_id", ""),
                        "content_type": file_meta.get("content_type"),
                        "web_url": file_meta.get("web_url"),
                    }
                )
            return files

        upload_root = Path("uploads").resolve()
        session_dir = (upload_root / session_id).resolve()
        if not session_dir.is_relative_to(upload_root) or not session_dir.is_dir():
            return []

        files = []
        for entry in sorted(session_dir.iterdir(), key=lambda p: p.name.lower()):
            if not entry.is_file():
                continue
            try:
                size = entry.stat().st_size
            except OSError:
                size = 0
            files.append(
                {
                    "filename": entry.name,
                    "size": size,
                }
            )
        return files

    def validate_upload_session(self, session_id: str) -> SessionRecord:
        """Validate that a session exists, is active, and is ready for upload."""
        record = get_session_record(session_id)
        if record is None:
            self.logger.warning("Invalid upload session: %s", session_id)
            raise HTTPException(status_code=404, detail="Session not found")
        if self.is_expired(record):
            self.logger.warning("Expired upload session: %s", session_id)
            raise HTTPException(status_code=410, detail="Session expired")
        if record.status != STATUS_CREATED:
            self.logger.warning("Upload attempted on non-created session: %s status=%s", session_id, record.status)
            raise HTTPException(status_code=409, detail="Session is not available for upload")
        return record

    async def process_upload(self, session_id: str, upload_file: UploadFile) -> tuple[SessionRecord, str]:
        """Validate and persist a single file upload for a transfer session."""
        result, filenames = await self.process_uploads(session_id, [upload_file])
        return result, filenames[0]

    async def process_uploads(self, session_id: str, upload_files: list[UploadFile]) -> tuple[SessionRecord, list[str]]:
        """Validate and persist multiple file uploads for a transfer session."""
        record = self.validate_upload_session(session_id)

        if not upload_files:
            self.logger.warning("Upload attempt with no files for session: %s", session_id)
            raise HTTPException(status_code=400, detail="At least one file must be uploaded.")

        filenames: list[str] = []
        seen_names: set[str] = set()
        for upload_file in upload_files:
            filename = self._sanitize_filename(upload_file.filename)
            if filename in seen_names:
                self.logger.warning("Duplicate filename in upload batch for session %s: %s", session_id, filename)
                raise HTTPException(status_code=400, detail=f"Duplicate filename in upload: {filename}")
            seen_names.add(filename)

            extension = Path(filename).suffix.lower()
            if extension in settings.blocked_extensions:
                self.logger.warning("Blocked file extension uploaded for session %s: %s", session_id, extension)
                raise HTTPException(status_code=400, detail=f"File extension '{extension}' is blocked.")

            content_type = upload_file.content_type or "application/octet-stream"
            normalized_content_type = content_type.split(";")[0].strip().lower()
            if normalized_content_type not in settings.allowed_mime_types:
                self.logger.warning(
                    "Rejected MIME type for session %s: %s (normalized: %s)",
                    session_id,
                    content_type,
                    normalized_content_type,
                )
                raise HTTPException(status_code=400, detail="File MIME type is not allowed.")

            filenames.append(filename)

        max_size_bytes = settings.max_file_size_mb * 1024 * 1024
        saved_paths: list[Path] = []
        staged_metadata: dict[str, dict[str, object]] = {}

        try:
            if settings.storage_backend.lower() == "sharepoint":
                if self.sharepoint_service is None:
                    raise HTTPException(status_code=500, detail="SharePoint storage is not configured")

                staging_root = Path("uploads").resolve() / ".staging"
                staging_dir = (staging_root / session_id).resolve()
                if not staging_dir.is_relative_to(staging_root):
                    raise HTTPException(status_code=400, detail="Invalid upload session")
                staging_dir.mkdir(parents=True, exist_ok=True)

                for upload_file in upload_files:
                    filename = self._sanitize_filename(upload_file.filename)
                    target_path = (staging_dir / filename).resolve()
                    if not target_path.is_relative_to(staging_dir):
                        raise HTTPException(status_code=400, detail="Invalid filename")
                    saved_paths.append(target_path)
                    total_bytes = 0
                    with target_path.open("wb") as destination:
                        while True:
                            chunk = await upload_file.read(1024 * 1024)
                            if not chunk:
                                break
                            total_bytes += len(chunk)
                            if total_bytes > max_size_bytes:
                                self.logger.warning("File too large for session %s: %d bytes", session_id, total_bytes)
                                raise HTTPException(
                                    status_code=413,
                                    detail=f"File size exceeds maximum of {settings.max_file_size_mb} MB.",
                                )
                            destination.write(chunk)

                    if total_bytes == 0:
                        self.logger.warning("Empty file upload for session %s", session_id)
                        raise HTTPException(status_code=400, detail="Uploaded files must not be empty.")
                    staged_metadata[filename] = {
                        "content_type": upload_file.content_type,
                        "size": total_bytes,
                    }
                    self.logger.info("Session file staged for SharePoint upload: %s / %s", session_id, filename)
            else:
                upload_root = Path("uploads")
                target_dir = upload_root / session_id
                target_dir.mkdir(parents=True, exist_ok=True)

                for upload_file in upload_files:
                    filename = self._sanitize_filename(upload_file.filename)
                    target_path = target_dir / filename
                    total_bytes = 0

                    with target_path.open("wb") as destination:
                        while True:
                            chunk = await upload_file.read(1024 * 1024)
                            if not chunk:
                                break
                            total_bytes += len(chunk)
                            if total_bytes > max_size_bytes:
                                destination.close()
                                target_path.unlink(missing_ok=True)
                                self.logger.warning("File too large for session %s: %d bytes", session_id, total_bytes)
                                raise HTTPException(
                                    status_code=413,
                                    detail=f"File size exceeds maximum of {settings.max_file_size_mb} MB.",
                                )
                            destination.write(chunk)

                    if total_bytes == 0:
                        target_path.unlink(missing_ok=True)
                        self.logger.warning("Empty file upload for session %s", session_id)
                        raise HTTPException(status_code=400, detail="Uploaded files must not be empty.")

                    saved_paths.append(target_path)
                    self.logger.info("Session file saved for session %s: %s", session_id, filename)
        except HTTPException:
            for path in saved_paths:
                path.unlink(missing_ok=True)
            raise
        except Exception as exc:
            for path in saved_paths:
                path.unlink(missing_ok=True)
            self.logger.exception("Failed to save uploaded files for session %s", session_id)
            raise HTTPException(status_code=500, detail="Unable to save files") from exc
        finally:
            for upload_file in upload_files:
                await upload_file.close()

        if settings.storage_backend.lower() == "sharepoint":
            existing_metadata = record.storage_metadata or {}
            existing_metadata.update({"backend": "sharepoint", "pending_files": staged_metadata})
            update_storage_metadata(session_id, existing_metadata)
            updated = update_session_status(session_id, STATUS_UPLOADING)
            if updated is None:
                raise HTTPException(status_code=500, detail="Unable to queue SharePoint upload")
        else:
            updated = mark_session_uploaded(session_id, uploaded_at=self._format_timestamp(datetime.utcnow()))
            if updated is None:
                self.logger.exception("Failed to update session status after upload %s", session_id)
                raise HTTPException(status_code=500, detail="Unable to update session status")

        return updated, filenames

    def upload_staged_files_to_sharepoint(self, session_id: str, filenames: list[str]) -> None:
        """Upload request-staged files to SharePoint after the HTTP response is sent."""
        staged_paths = [(Path("uploads").resolve() / ".staging" / session_id / filename).resolve() for filename in filenames]
        try:
            if self.sharepoint_service is None:
                raise RuntimeError("SharePoint storage is not configured")
            record = get_session_record(session_id)
            if record is None:
                raise RuntimeError("Session not found")

            pending_files = record.storage_metadata.get("pending_files", {}) if record.storage_metadata else {}
            files_metadata: dict[str, object] = {}
            for filename, staged_path in zip(filenames, staged_paths, strict=True):
                if not staged_path.is_file():
                    raise RuntimeError(f"Staged file is missing: {filename}")
                with staged_path.open("rb") as staged_file:
                    staged_upload = UploadFile(file=staged_file, filename=filename)
                    item_info = self.sharepoint_service.upload_file(
                        record.folder_name or session_id, filename, staged_upload
                    )
                files_metadata[filename] = {
                    "item_id": item_info["item_id"],
                    "web_url": item_info["web_url"],
                    "content_type": pending_files.get(filename, {}).get("content_type"),
                    "size": pending_files.get(filename, {}).get("size", staged_path.stat().st_size),
                    "uploaded_at": self._format_timestamp(datetime.utcnow()),
                }

            metadata = record.storage_metadata or {}
            metadata.update({"backend": "sharepoint", "files": files_metadata})
            metadata.pop("pending_files", None)
            update_storage_metadata(session_id, metadata)
            if mark_session_uploaded(session_id, uploaded_at=self._format_timestamp(datetime.utcnow())) is None:
                raise RuntimeError("Unable to mark session uploaded")
            self.logger.info("Staged SharePoint upload completed for session %s", session_id)
        except Exception:
            self.logger.exception("Staged SharePoint upload failed for session %s", session_id)
            try:
                update_session_status(session_id, STATUS_FAILED)
            except Exception:
                self.logger.exception("Unable to mark failed SharePoint upload for session %s", session_id)
        finally:
            for staged_path in staged_paths:
                staged_path.unlink(missing_ok=True)
            staging_dir = Path("uploads").resolve() / ".staging" / session_id
            try:
                staging_dir.rmdir()
            except OSError:
                pass

    def _sanitize_filename(self, filename: str | None) -> str:
        """Normalize an uploaded filename and prevent path traversal."""
        if filename is None:
            raise HTTPException(status_code=400, detail="Each uploaded file must have a name.")

        safe_name = Path(filename).name
        safe_name = safe_name.replace("/", "").replace("\\", "").strip()
        if not safe_name:
            raise HTTPException(status_code=400, detail="Each uploaded file must have a name.")
        return safe_name

    def _get_upload_file_size(self, upload_file: UploadFile) -> int:
        """Calculate the size of an incoming UploadFile without fully loading it."""
        file_obj = upload_file.file
        try:
            current_position = file_obj.tell()
            file_obj.seek(0, 2)
            total_bytes = file_obj.tell()
            file_obj.seek(current_position)
            return total_bytes
        except (AttributeError, OSError):
            # Fallback to streaming count if the underlying file is not seekable.
            total_bytes = 0
            try:
                file_obj.seek(0)
            except Exception:
                pass
            while True:
                chunk = file_obj.read(1024 * 1024)
                if not chunk:
                    break
                total_bytes += len(chunk)
            try:
                file_obj.seek(0)
            except Exception:
                pass
            return total_bytes

    def is_expired(self, record: SessionRecord) -> bool:
        """Return True when the session expiry timestamp is in the past."""
        if not record.expires_at:
            return False
        try:
            expires_at = datetime.fromisoformat(record.expires_at)
        except ValueError:
            return False
        return datetime.utcnow() >= expires_at

    def _validate_employee_code(self, employee_code: str | None) -> str:
        """Validate the employee code supplied by the client."""
        if employee_code is None:
            raise ValueError("employee_code is required")

        trimmed_code = employee_code.strip()
        if not trimmed_code:
            raise ValueError("employee_code cannot be empty")

        return trimmed_code

    def _format_timestamp(self, timestamp: datetime) -> str:
        """Format timestamps as ISO 8601 strings for persistence."""
        return timestamp.replace(microsecond=0).isoformat()
