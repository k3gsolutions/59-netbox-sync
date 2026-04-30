"""NetBox GET-only client — read device inventory from NetBox API.

No writes. No tokens logged or returned. GET /api/dcim/devices/ only.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import requests


class NetBoxNotConfiguredError(Exception):
    """Raised when NETBOX_URL or NETBOX_TOKEN not set."""
    pass


class NetBoxAuthError(Exception):
    """Raised on 401/403 response."""
    pass


class NetBoxClientError(Exception):
    """Raised on request or parsing error."""
    pass


class NetBoxClient:
    """GET-only NetBox REST API client."""

    def __init__(self, url: str, token: str):
        """
        Args:
            url: Base URL, e.g. "https://docs.k3gsolutions.com.br"
            token: API token (read-only)
        """
        self.url = url.rstrip("/")
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Token {token}",
            "Accept": "application/json",
        })

    def get_devices(
        self,
        limit: int = 100,
        offset: int = 0,
        status: Optional[str] = None,
        site: Optional[str] = None,
        role: Optional[str] = None,
        **filters: str,
    ) -> list[dict]:
        """
        Fetch devices from NetBox.

        Args:
            limit: Max results per page
            offset: Pagination offset
            status: Filter by status (e.g. "active")
            site: Filter by site slug
            role: Filter by role slug
            **filters: Additional query parameters

        Returns:
            List of device dicts from NetBox API

        Raises:
            NetBoxAuthError: on 401/403
            NetBoxClientError: on request or parsing error
        """
        params: Dict[str, Any] = {"limit": limit, "offset": offset}

        if status:
            params["status"] = status
        if site:
            params["site"] = site
        if role:
            params["role"] = role

        params.update(filters)

        try:
            resp = self.session.get(
                f"{self.url}/api/dcim/devices/",
                params=params,
                timeout=10,
            )

            if resp.status_code in (401, 403):
                raise NetBoxAuthError(
                    f"NetBox authentication failed ({resp.status_code})"
                )

            resp.raise_for_status()
            data = resp.json()
            return data.get("results", [])

        except requests.RequestException as e:
            raise NetBoxClientError(f"NetBox request failed: {e}")
        except (ValueError, KeyError) as e:
            raise NetBoxClientError(f"NetBox response parsing failed: {e}")


def get_netbox_client() -> NetBoxClient:
    """
    Get NetBox client from environment variables.

    Reads:
        NETBOX_URL: Base URL of NetBox instance
        NETBOX_TOKEN: Read-only API token

    Returns:
        Configured NetBoxClient

    Raises:
        NetBoxNotConfiguredError: if NETBOX_URL or NETBOX_TOKEN not set
    """
    url = os.getenv("NETBOX_URL", "").strip()
    token = os.getenv("NETBOX_TOKEN", "").strip()

    if not url or not token:
        raise NetBoxNotConfiguredError(
            "NetBox not configured. Set NETBOX_URL and NETBOX_TOKEN environment variables."
        )

    return NetBoxClient(url, token)
