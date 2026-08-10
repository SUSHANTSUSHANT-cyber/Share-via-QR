import requests

from config.settings import settings
from services.graph_service import GraphService


def get_graph_headers(service: GraphService) -> dict[str, str]:
    token = service.get_app_token()
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }


def create_folder(drive_id: str, headers: dict[str, str], folder_name: str) -> dict:
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root/children"
    payload = {
        "name": folder_name,
        "folder": {},
        "@microsoft.graph.conflictBehavior": "fail",
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


def upload_text_file(drive_id: str, parent_id: str, file_name: str, content: str, headers: dict[str, str]) -> dict:
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{parent_id}:/{file_name}:/content"
    file_headers = {
        **headers,
        "Content-Type": "text/plain",
    }
    response = requests.put(url, headers=file_headers, data=content.encode("utf-8"))
    response.raise_for_status()
    return response.json()


def main() -> int:
    try:
        service = GraphService()
        headers = get_graph_headers(service)

        folder = create_folder(settings.sharepoint_drive_id, headers, "QR-Test2")
        item = upload_text_file(
            settings.sharepoint_drive_id,
            folder["id"],
            "test.txt",
            "This is a test file uploaded via Microsoft Graph API.",
            headers,
        )

        print(f"item_id: {item.get('id')}")
        print(f"webUrl: {item.get('webUrl')}")
        return 0
    except Exception as exc:
        print(f"SharePoint upload failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
