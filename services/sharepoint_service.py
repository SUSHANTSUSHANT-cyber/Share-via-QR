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

    def upload_file(self, session_id: str, filename: str, upload_file: UploadFile) -> dict[str, str]:
        """Upload a file into Documents/<session_id>/<filename> on SharePoint using a Graph upload session."""
        folder_id = self._get_folder_id(session_id)
        upload_session_url = (
            f"https://graph.microsoft.com/v1.0/drives/{self.drive_id}/items/{folder_id}:/{filename}:/createUploadSession"
        )
        payload = {
            "item": {
                "@microsoft.graph.conflictBehavior": "fail",
                "name": filename,
            }
        }
        response = requests.post(
            upload_session_url,
            headers={**self._get_headers(), "Content-Type": "application/json"},
            json=payload,
        )
        response.raise_for_status()
        upload_data = response.json()
        upload_url = upload_data.get("uploadUrl")
        if not upload_url:
            raise RuntimeError("Unable to initiate SharePoint upload session")

        file_obj = upload_file.file
        try:
            file_obj.seek(0)
        except Exception:
            pass

        total_size = 0
        try:
            current_position = file_obj.tell()
            file_obj.seek(0, 2)
            total_size = file_obj.tell()
            file_obj.seek(current_position)
        except Exception:
            try:
                file_obj.seek(0)
            except Exception:
                pass
            while True:
                chunk_data = file_obj.read(5 * 1024 * 1024)
                if not chunk_data:
                    break
                total_size += len(chunk_data)
            try:
                file_obj.seek(0)
            except Exception:
                pass

        chunk_size = 5 * 1024 * 1024
        bytes_uploaded = 0
        while bytes_uploaded < total_size:
            chunk = file_obj.read(chunk_size)
            if not chunk:
                break

            chunk_end = bytes_uploaded + len(chunk) - 1
            headers = {
                "Content-Length": str(len(chunk)),
                "Content-Range": f"bytes {bytes_uploaded}-{chunk_end}/{total_size}",
            }
            upload_response = requests.put(upload_url, headers=headers, data=chunk)
            if upload_response.status_code not in (200, 201, 202):
                upload_response.raise_for_status()

            if upload_response.status_code in (200, 201):
                item = upload_response.json()
                return {
                    "item_id": item.get("id", ""),
                    "web_url": item.get("webUrl", ""),
                }

            bytes_uploaded = chunk_end + 1

        raise RuntimeError("SharePoint chunked upload did not complete")

    def download_file(self, item_id: str) -> bytes:
        """Download a file from SharePoint using its stored Graph item ID."""
        url = f"https://graph.microsoft.com/v1.0/drives/{self.drive_id}/items/{item_id}/content"
        response = requests.get(url, headers=self._get_headers())
        response.raise_for_status()
        return response.content

    def delete_file(self, item_id: str) -> None:
        """Delete a file in SharePoint by Graph item ID."""
        url = f"https://graph.microsoft.com/v1.0/drives/{self.drive_id}/items/{item_id}"
        response = requests.delete(url, headers=self._get_headers())
        # Raise only on non-404/failed cases; allow idempotent behavior if already deleted
        if response.status_code not in (200, 204, 404):
            response.raise_for_status()
