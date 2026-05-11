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
        self._tenant_cache: Dict[int, dict] = {}

    def _fetch(self, endpoint: str, params: Dict[str, Any]) -> list[dict]:
        """Helper to fetch from NetBox endpoint."""
        try:
            resp = self.session.get(
                f"{self.url}{endpoint}",
                params=params,
                timeout=10,
            )

            if resp.status_code in (401, 403):
                raise NetBoxAuthError(
                    f"NetBox authentication failed ({resp.status_code})"
                )

            resp.raise_for_status()
            data = resp.json()

            # Handle both single object and list endpoints
            if isinstance(data, dict) and "results" in data:
                return data.get("results", [])
            elif isinstance(data, dict):
                return [data]  # Single device endpoint

            return []

        except requests.RequestException as e:
            raise NetBoxClientError(f"NetBox request failed: {e}")
        except (ValueError, KeyError) as e:
            raise NetBoxClientError(f"NetBox response parsing failed: {e}")

    def get_device_by_id(self, device_id: int) -> Optional[dict]:
        """
        Fetch single device by ID.

        Args:
            device_id: NetBox device ID

        Returns:
            Device dict, or None if not found

        Raises:
            NetBoxAuthError: on 401/403
            NetBoxClientError: on request or parsing error
        """
        try:
            results = self._fetch(f"/api/dcim/devices/{device_id}/", {})
            return results[0] if results else None
        except NetBoxClientError:
            raise

    def search_devices_by_name(self, name: str, limit: int = 10) -> list[dict]:
        """
        Search devices by exact name.

        Args:
            name: Device name
            limit: Max results (capped at 10)

        Returns:
            List of matching devices
        """
        limit = min(limit, 10)
        return self._fetch(
            "/api/dcim/devices/",
            {"name": name, "limit": limit}
        )

    def search_devices(
        self,
        q: str,
        limit: int = 10,
        offset: int = 0,
    ) -> list[dict]:
        """
        Search devices by partial query.

        Args:
            q: Search query
            limit: Max results (capped at 25)
            offset: Pagination offset

        Returns:
            List of matching devices
        """
        limit = min(limit, 25)
        return self._fetch(
            "/api/dcim/devices/",
            {"q": q, "limit": limit, "offset": offset}
        )

    def get_tenant_by_id(self, tenant_id: int) -> Optional[dict]:
        """
        Fetch tenant details by ID (for group enrichment).

        Uses in-memory cache to avoid repeated calls for same tenant.

        Args:
            tenant_id: NetBox tenant ID

        Returns:
            Tenant dict with group details, or None if not found

        Raises:
            NetBoxAuthError: on 401/403
            NetBoxClientError: on request or parsing error
        """
        # Check cache first
        if tenant_id in self._tenant_cache:
            return self._tenant_cache[tenant_id]

        try:
            results = self._fetch(f"/api/tenancy/tenants/{tenant_id}/", {})
            tenant = results[0] if results else None
            if tenant:
                self._tenant_cache[tenant_id] = tenant
            return tenant
        except NetBoxClientError:
            raise

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

        return self._fetch("/api/dcim/devices/", params)

    def list_tenants(self, limit: int = 100) -> list[dict]:
        """
        List all tenants from NetBox.

        Args:
            limit: Max results per page

        Returns:
            List of tenant dicts {id, name, slug, group}

        Raises:
            NetBoxAuthError: on 401/403
            NetBoxClientError: on request or parsing error
        """
        return self._fetch("/api/tenancy/tenants/", {"limit": limit})

    def get_devices_by_tenant(
        self,
        tenant_id: int,
        status: str = "active",
        role: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """
        Fetch devices filtered by tenant ID.

        Args:
            tenant_id: NetBox tenant ID
            status: Device status (default "active")
            role: Optional device role slug
            limit: Max results

        Returns:
            List of device dicts for the tenant

        Raises:
            NetBoxAuthError: on 401/403
            NetBoxClientError: on request or parsing error
        """
        params = {"tenant_id": tenant_id, "status": status, "limit": limit}
        if role:
            params["role"] = role
        return self._fetch("/api/dcim/devices/", params)


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
