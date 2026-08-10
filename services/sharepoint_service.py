"""Minimal SharePoint upload helpers for the development storage backend."""

from __future__ import annotations

import requests

from config.settings import settings
from services.graph_service import GraphService


class SharePointService:
    """Upload files to SharePoint using the existing GraphService."""

    def __init__(self) -> None:
        self.graph_service = GraphService()
        self.drive_id = settings.sharepoint_drive_id

    def _get_headers(self) -> dict[str, str]:
        token = self.graph_service.get_app_token()
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

    def _ensure_folder(self, parent_id: str | None, folder_name: str) -> str:
        url = f"https://graph.microsoft.com/v1.0/drives/{self.drive_id}/items/{parent_id}:/{folder_name}"
        response = requests.get(url, headers=self._get_headers())
        if response.status_code == 200:
            return response.json()["id"]
        if response.status_code != 404:
            response.raise_for_status()

        payload = {
            "name": folder_name,
            "folder": {},
            "@microsoft.graph.conflictBehavior": "fail",
        }
        children_url = f"https://graph.microsoft.com/v1.0/drives/{self.drive_id}/items/{parent_id}/children"
        create_response = requests.post(
            children_url,
            headers={**self._get_headers(), "Content-Type": "application/json"},
            json=payload,
        )
        create_response.raise_for_status()
        return create_response.json()["id"]

    def _get_folder_id(self, session_id: str) -> str:
        documents_folder_id = self._ensure_folder("root", "Documents")
        return self._ensure_folder(documents_folder_id, session_id)

    def upload_file(self, session_id: str, filename: str, content_bytes: bytes) -> dict[str, str]:
        """Upload a file into Documents/<session_id>/<filename> on SharePoint."""
        folder_id = self._get_folder_id(session_id)
        destination_url = (
            f"https://graph.microsoft.com/v1.0/drives/{self.drive_id}/items/{folder_id}:/{filename}:/content"
        )
        headers = {
            **self._get_headers(),
            "Content-Type": "application/octet-stream",
        }
        response = requests.put(destination_url, headers=headers, data=content_bytes)
        response.raise_for_status()
        item = response.json()
        return {
            "item_id": item.get("id", ""),
            "web_url": item.get("webUrl", ""),
        }

    def download_file(self, item_id: str) -> bytes:
        """Download a file from SharePoint using its stored Graph item ID."""
        url = f"https://graph.microsoft.com/v1.0/drives/{self.drive_id}/items/{item_id}/content"
        response = requests.get(url, headers=self._get_headers())
        response.raise_for_status()
        return response.content
