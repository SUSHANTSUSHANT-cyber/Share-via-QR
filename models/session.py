"""Pydantic models for transfer session data.

These models are intentionally lightweight and describe the shape of request and
response payloads for future API endpoints.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from config.constants import DEFAULT_SESSION_STATUS


class SessionCreateRequest(BaseModel):
    """Payload for creating a transfer session."""

    employee_code: str | None = Field(default=None, description="Employee identifier")
    hostname: str | None = Field(default=None, description="Receiver hostname for audit metadata")


class SessionResponse(BaseModel):
    """Response payload for a newly created session."""

    session_id: str = Field(..., description="Unique session identifier")
    employee_code: str | None = Field(default=None, description="Employee identifier")
    hostname: str | None = Field(default=None, description="Receiver hostname for audit metadata")
    status: str = Field(default=DEFAULT_SESSION_STATUS, description="Current session status")
    created_at: str | None = Field(default=None, description="Creation timestamp")
    expires_at: str | None = Field(default=None, description="Expiry timestamp")
    folder_name: str | None = Field(default=None, description="Placeholder folder name")


class SessionStatusResponse(BaseModel):
    """Response payload describing the current session state."""

    session_id: str = Field(..., description="Unique session identifier")
    employee_code: str | None = Field(default=None, description="Employee identifier")
    status: str = Field(default=DEFAULT_SESSION_STATUS, description="Current session status")
    created_at: str | None = Field(default=None, description="Creation timestamp")
    expires_at: str | None = Field(default=None, description="Expiry timestamp")
    folder_name: str | None = Field(default=None, description="Placeholder folder name")


class SessionFile(BaseModel):
    """Metadata for an uploaded file within a session."""

    filename: str = Field(..., description="Uploaded file name")
    size: int = Field(..., description="Uploaded file size in bytes")
    item_id: str | None = Field(default=None, description="SharePoint item identifier")
    content_type: str | None = Field(default=None, description="Uploaded file MIME type")
    web_url: str | None = Field(default=None, description="SharePoint web URL")


class SessionRecord(BaseModel):
    """Persistent session record stored in the database."""

    session_id: str = Field(..., description="Unique session identifier")
    employee_code: str | None = Field(default=None, description="Employee identifier")
    hostname: str | None = Field(default=None, description="Receiver hostname for audit metadata")
    folder_name: str | None = Field(default=None, description="Target folder name")
    status: str = Field(default=DEFAULT_SESSION_STATUS, description="Current session status")
    created_at: str | None = Field(default=None, description="Creation timestamp")
    expires_at: str | None = Field(default=None, description="Expiry timestamp")
    uploaded_at: str | None = Field(default=None, description="Upload timestamp")
    downloaded_at: str | None = Field(default=None, description="Download timestamp")
    storage_metadata: dict[str, Any] | None = Field(default=None, description="Backend storage metadata")
    files: list[SessionFile] = Field(default_factory=list, description="Uploaded files for this session")
