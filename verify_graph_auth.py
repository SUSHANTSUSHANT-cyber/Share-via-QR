import base64
import json
import sys

from services.graph_service import GraphService


def _decode_jwt_payload(token: str) -> dict:
    parts = token.split(".")
    if len(parts) < 2:
        raise ValueError("Token is not a JWT")

    payload = parts[1]
    padding = "=" * (-len(payload) % 4)
    decoded = base64.urlsafe_b64decode(payload + padding).decode("utf-8")
    return json.loads(decoded)


def main() -> int:
    try:
        service = GraphService()
        token = service.get_app_token()
        claims = _decode_jwt_payload(token)
        for claim_name in ("aud", "appid", "tid", "roles"):
            print(f"{claim_name}: {claims.get(claim_name)}")
        return 0
    except Exception as exc:
        print("Microsoft Graph authentication verification failed:", str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
