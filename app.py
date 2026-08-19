"""Application entry point for the .AISIN Secure File Transfer

This module creates the FastAPI application, configures templates and static
files, wires up the routers, and provides a startup hook for logging.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config.settings import settings
from database.database import initialize_database
from routes.download import router as download_router
from routes.home import router as home_router
from routes.session import router as session_router
from routes.status import router as status_router
from routes.transfer import router as transfer_router
from routes.upload import router as upload_router
from services.cleanup_service import start_background_cleanup

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger("qr_transfer_system")

app = FastAPI(
    title=settings.app_name,
    description="Phase 2 configuration and database foundation for the application.",
    version=settings.app_version,
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.state.templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.state.server_url = settings.server_url

app.include_router(home_router)
app.include_router(transfer_router)
app.include_router(session_router)
app.include_router(upload_router)
app.include_router(download_router)
app.include_router(status_router)


@app.get("/api/analytics/transfers")
def get_transfer_analytics() -> list[dict[str, object]]:
    """Return transfer session records for read-only analytics."""
    connection = sqlite3.connect(settings.database_path)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT session_id, employee_code, hostname, status,
                   created_at, uploaded_at, downloaded_at
            FROM transfer_sessions
            ORDER BY created_at DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


@app.get("/api/analytics/hostname-usage")
def get_hostname_usage_analytics() -> list[dict[str, object]]:
    """Return transfer counts grouped by receiver hostname."""
    connection = sqlite3.connect(settings.database_path)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT hostname, COUNT(*) AS transfers
            FROM transfer_sessions
            GROUP BY hostname
            ORDER BY transfers DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


@app.on_event("startup")
def startup_event() -> None:
    """Initialize configuration-backed startup services."""
    logger.info("Application startup initiated for %s", settings.app_name)
    logger.info(
        "Configuration loaded with host=%s port=%s server_url=%s database_path=%s",
        settings.host,
        settings.port,
        settings.server_url,
        settings.database_path,
    )
    initialize_database()
    # start periodic cleanup thread for expired SharePoint files
    app.state.cleanup_stop_event = start_background_cleanup()
    logger.info("Application startup completed successfully.")


@app.on_event("shutdown")
def shutdown_event() -> None:
    """Signal background cleanup to stop on application shutdown."""
    stop_event = getattr(app.state, "cleanup_stop_event", None)
    if stop_event is not None:
        stop_event.set()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host=settings.host, port=settings.port, reload=True)
