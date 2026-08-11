"""Simple receiver-side access control helpers.

These helpers enforce that certain routes are only accessible from private
or loopback IP ranges (trusted receiver/local/corporate side). They intentionally
avoid complex auth and rely on network boundaries as requested.
"""

from __future__ import annotations

import ipaddress
from fastapi import HTTPException, Request


def _extract_client_ip(request: Request) -> str:
    # Prefer X-Forwarded-For when present (comma-separated list)
    xff = request.headers.get("x-forwarded-for")
    if xff:
        first = xff.split(",")[0].strip()
        return first
    # Fallback to client.host provided by ASGI server
    client = request.client
    if client is None:
        return ""
    return client.host


def require_receiver(request: Request) -> None:
    """Raise HTTP 403 unless the request originates from a private/loopback IP.

    This keeps receiver/dashboard routes inaccessible from the public Cloudflare
    endpoint while leaving upload endpoints public.
    """
    ip_str = _extract_client_ip(request)
    try:
        ip = ipaddress.ip_address(ip_str)
    except Exception:
        raise HTTPException(status_code=403, detail="Forbidden")

    if not (ip.is_private or ip.is_loopback):
        # Deny if not from a private/corporate network or loopback
        raise HTTPException(status_code=403, detail="Forbidden")
