"""Pydantic models for transfer session data.

These models are intentionally lightweight and describe the shape of request and
response payloads for future API endpoints.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from config.constants import DEFAULT_SESSION_STATUS


class SessionCreateRequest(BaseModel):
    """Payload for creating a transfer session."""

    employee_code: str | None = Field(default=None, description="Employee identifier")
    folder_name: str | None = Field(default=None, description="Target folder name")


class SessionResponse(BaseModel):
    """Response payload for a newly created session."""

    session_id: str = Field(..., description="Unique session identifier")
    status: str = Field(default=DEFAULT_SESSION_STATUS, description="Current session status")


class SessionStatusResponse(BaseModel):
    """Response payload describing the current session state."""

    session_id: str = Field(..., description="Unique session identifier")
    status: str = Field(default=DEFAULT_SESSION_STATUS, description="Current session status")


class SessionRecord(BaseModel):
    """Persistent session record stored in the database."""

    session_id: str = Field(..., description="Unique session identifier")
    employee_code: str | None = Field(default=None, description="Employee identifier")
    folder_name: str | None = Field(default=None, description="Target folder name")
    status: str = Field(default=DEFAULT_SESSION_STATUS, description="Current session status")
    created_at: str | None = Field(default=None, description="Creation timestamp")
    expires_at: str | None = Field(default=None, description="Expiry timestamp")
    uploaded_at: str | None = Field(default=None, description="Upload timestamp")
    downloaded_at: str | None = Field(default=None, description="Download timestamp")
