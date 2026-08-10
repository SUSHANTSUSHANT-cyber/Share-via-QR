"""Microsoft Graph authentication helpers.

This module provides a reusable authentication service for obtaining an
application access token using the OAuth2 client credentials flow.
"""

from __future__ import annotations

import logging

import msal

from config.settings import settings

logger = logging.getLogger("qr_transfer_system")


class GraphService:
    """Service for obtaining Microsoft Graph application tokens."""

    def __init__(self) -> None:
        self.logger = logger
        self.client_id = settings.graph_client_id
        self.client_secret = settings.graph_client_secret
        self.tenant_id = settings.graph_tenant_id
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        self.scopes = ["https://graph.microsoft.com/.default"]

        self._validate_credentials()

        self._client = msal.ConfidentialClientApplication(
            client_id=self.client_id,
            client_credential=self.client_secret,
            authority=self.authority,
        )

    def _validate_credentials(self) -> None:
        """Validate that Graph credentials are present and appear valid."""
        if not self.client_id or self.client_id.startswith("placeholder"):
            raise RuntimeError(
                "Microsoft Graph client ID is missing or invalid. "
                "Set GRAPH_CLIENT_ID in configuration."
            )
        if not self.client_secret or self.client_secret.startswith("placeholder"):
            raise RuntimeError(
                "Microsoft Graph client secret is missing or invalid. "
                "Set GRAPH_CLIENT_SECRET in configuration."
            )
        if not self.tenant_id or self.tenant_id.startswith("placeholder"):
            raise RuntimeError(
                "Microsoft Graph tenant ID is missing or invalid. "
                "Set GRAPH_TENANT_ID in configuration."
            )

    def get_app_token(self) -> str:
        """Obtain an application access token for Microsoft Graph.

        This method returns the raw token for internal use only. It must not be
        exposed in API responses, logs, or front-end assets.
        """
        result = self._client.acquire_token_for_client(scopes=self.scopes)

        if "access_token" not in result:
            error_detail = result.get("error_description") or result.get("error") or "Unknown authentication error"
            self.logger.error("Microsoft Graph token acquisition failed: %s", error_detail)
            raise RuntimeError(
                "Unable to obtain Microsoft Graph access token. "
                "Verify GRAPH_TENANT_ID, GRAPH_CLIENT_ID, and GRAPH_CLIENT_SECRET."
            )

        return result["access_token"]

    def verify_token_acquisition(self) -> bool:
        """Verify that Graph authentication can obtain a token without exposing it."""
        token = self.get_app_token()
        return bool(token)
