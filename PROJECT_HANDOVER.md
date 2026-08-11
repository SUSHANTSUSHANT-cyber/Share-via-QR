# Project Handover

## Project Purpose

AISIN Secure File Transfer is a FastAPI-based web application for creating QR-driven transfer sessions, uploading files, and retrieving them later. The current implementation supports both local filesystem storage and a SharePoint backend via Microsoft Graph.

## Architecture Overview

- `app.py`: FastAPI application bootstrap. Mounts static files, Jinja2 templates, initializes the SQLite database, and includes route modules.
- `config/settings.py`: Loads configuration from environment variables (and `.env`) into a frozen `Settings` dataclass.
- `database/database.py`: SQLite persistence layer for `transfer_sessions`; includes storage metadata serialization/deserialization and session lifecycle helpers.
- `models/session.py`: Pydantic models for session creation, session state, and uploaded file metadata.
- `services/session_service.py`: Core business logic for session creation, validation, upload handling, download handling, expiration, and SharePoint metadata integration.
- `services/sharepoint_service.py`: Minimal SharePoint helper that uses `GraphService` to upload files to `Documents/<session_id>` and download by Graph item ID.
- `services/graph_service.py`: Microsoft Graph authentication using MSAL client credentials.
- `services/qr_service.py`: Builds QR target URLs and generates QR PNG assets.
- `routes/`: HTTP route definitions for session management, upload pages, download endpoints, transfer start page, and home page.

## Storage Backend Support

The app supports two storage modes controlled by `STORAGE_BACKEND`:

- `local` (default): Files are stored under `uploads/<session_id>/` on the local filesystem.
- `sharepoint`: Files are uploaded to SharePoint using Microsoft Graph. Session rows store `storage_metadata` with per-file `item_id`, `web_url`, `content_type`, and `size`.

Branching behavior is implemented in:

- `services/session_service.py`: upload persistence and metadata storage.
- `routes/download.py`: file download and ZIP archive generation.
- `services/sharepoint_service.py`: actual Graph upload/download operations.

## Key Interfaces and Flows

### Session Creation

- Route: `POST /session/create`
- Creates a session in SQLite with `status = created` and expiry.
- Returns session ID and metadata.

### QR Transfer Start

- Route: `GET /transfer/start`
- Creates a session and renders `transfer.html` with embedded QR code.
- QR encodes `https://<server_url>/upload/<session_id>`.

### Upload Page and Upload API

- Route: `GET /upload/{session_id}` renders the upload page.
- Route: `POST /upload/{session_id}` accepts one or multiple files.
- Validation includes duplicate filenames, blocked extensions, MIME restrictions, max file size, and empty file checks.
- After upload, session status is updated to `uploaded`.

### Download

- Route: `GET /download/{session_id}` supports single-file download or `archive=true` ZIP download.
- `HEAD /download/{session_id}` returns metadata for the uploaded file path in local mode.
- `sharepoint` mode streams content from Graph and creates an in-memory ZIP when requested.
- After a successful download request, session status is updated to `downloaded`.

## Configuration and Environment

The app reads from environment variables and `.env` via `python-dotenv`.

Important settings:

- `APP_NAME`
- `APP_VERSION`
- `HOST`
- `PORT`
- `SERVER_URL`
- `DATABASE_PATH`
- `SESSION_EXPIRY_MINUTES`
- `MAX_FILE_SIZE_MB`
- `ALLOWED_MIME_TYPES`
- `BLOCKED_EXTENSIONS`
- `CLEANUP_INTERVAL_MINUTES`
- `GRAPH_CLIENT_ID`
- `GRAPH_CLIENT_SECRET`
- `GRAPH_TENANT_ID`
- `SHAREPOINT_SITE_ID`
- `SHAREPOINT_DRIVE_ID`
- `STORAGE_BACKEND` (`local` or `sharepoint`)

> Note: Graph credentials are validated in `services/graph_service.py`. Placeholders will raise runtime errors.

## Dependencies

Defined in `requirements.txt`:

- `fastapi`
- `uvicorn`
- `jinja2`
- `python-dotenv`
- `python-multipart`
- `msal`
- `requests`
- `qrcode[pil]`

## Current Limitations and Known Issues

- `routes/status.py` is a placeholder and does not provide real application status.
- The current `assets` and templates support the existing upload/download flow but may need frontend updates for SharePoint-specific UX.
- Download `HEAD` behavior for SharePoint uses a synthetic `FileResponse` path; it does not stream real file content from disk.
- There is no cleanup job currently implemented in this codebase; expired sessions are only marked on access.
- Session expiration enforcement is done at lookup time, not via background cleanup.
- No authentication layer is present for end users, aside from session ID ownership.

## Deployment Notes

- Ensure `DATABASE_PATH` points to a writable location.
- If using SharePoint, set `STORAGE_BACKEND=sharepoint` and provide valid Graph configuration values.
- Run the app with Uvicorn: `uvicorn app:app --reload` for development.
- Static assets are served from `static/`, templates are rendered from `templates/`.

## Handoff Recommendations

1. Confirm SharePoint drive and site IDs with the corporate tenant.
2. Add robust error handling around Graph API rate limits and token expiry.
3. Add a cleanup background task for expired sessions and stale local uploads.
4. Update `README.md` to reflect SharePoint support and current runtime requirements.
5. Add tests for SharePoint upload/download flow and session metadata persistence.

## Contact and Next Steps

- The core integration is complete for local and SharePoint-backed file transfer.
- The most important next step is to validate the Graph/SharePoint credentials in a real tenant and test full end-to-end upload/download behavior.
- If you want, I can also create a small `README` section or `docs/` entry summarizing the SharePoint backend wiring.
