import requests

from services.graph_service import GraphService


def get_graph_headers(service: GraphService) -> dict[str, str]:
    token = service.get_app_token()
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }


def discover_sharepoint_site(site_path: str, headers: dict[str, str]) -> dict[str, str]:
    url = f"https://graph.microsoft.com/v1.0/sites/{site_path}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    json_body = response.json()
    return {
        "id": json_body.get("id", ""),
        "displayName": json_body.get("displayName", ""),
        "webUrl": json_body.get("webUrl", ""),
    }


def list_site_drives(site_id: str, headers: dict[str, str]) -> list[dict[str, str]]:
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    json_body = response.json()
    drives = []
    for drive in json_body.get("value", []):
        drives.append(
            {
                "name": drive.get("name", ""),
                "id": drive.get("id", ""),
                "webUrl": drive.get("webUrl", ""),
            }
        )
    return drives


def main() -> int:
    try:
        service = GraphService()
        headers = get_graph_headers(service)

        site_path = "aisin.sharepoint.com:/sites/QRCodeTransferFile"
        site_info = discover_sharepoint_site(site_path, headers)

        print("Site information:")
        print(f"id: {site_info['id']}")
        print(f"displayName: {site_info['displayName']}")
        print(f"webUrl: {site_info['webUrl']}")
        print("")

        if not site_info["id"]:
            print("No site ID was returned.")
            return 1

        drives = list_site_drives(site_info["id"], headers)
        print("Document libraries:")
        if not drives:
            print("No drives found.")
            return 0

        for drive in drives:
            print("---")
            print(f"name: {drive['name']}")
            print(f"id: {drive['id']}")
            print(f"webUrl: {drive['webUrl']}")

        return 0
    except Exception as exc:
        print("SharePoint discovery failed:", str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
