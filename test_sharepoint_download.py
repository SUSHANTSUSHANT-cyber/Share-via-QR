import requests
from pathlib import Path

from config.settings import settings
from services.graph_service import GraphService


def get_graph_headers(service: GraphService) -> dict[str, str]:
    token = service.get_app_token()
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }


def download_item(drive_id: str, item_id: str, headers: dict[str, str], output_path: Path) -> tuple[int, str]:
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/content"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    output_path.write_bytes(response.content)
    return len(response.content), response.content.decode("utf-8")


def main() -> int:
    try:
        service = GraphService()
        headers = get_graph_headers(service)
        output_path = Path("sharepoint_download_test.txt")
        item_id = "01VHF6JAXS2VP3NIWESBCJJAGQRWMT2WOU"

        size, contents = download_item(settings.sharepoint_drive_id, item_id, headers, output_path)

        print("download successful")
        print(f"downloaded file size: {size}")
        print("downloaded file contents")
        print(contents)
        return 0
    except Exception as exc:
        print(f"SharePoint download failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
