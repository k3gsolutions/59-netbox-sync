"""Compliance candidate discovery — identify eligible devices from NetBox.

Eligibility rules (ALL must pass):
1. device.status == "active" (string or dict)
2. custom_fields["Compliance"] is True (case-insensitive key)
3. device.tenant is present
4. device.tenant.group.name == "K3G Solutions" or slug == "k3g-solutions"

No writes. No device connections. Read-only enumeration only.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .netbox_client import NetBoxClient, NetBoxClientError


def get_status_value(device: dict) -> str:
    """
    Extract status value from device dict.

    Handles:
        - "active" (string)
        - {"value": "active", "label": "Active"} (dict)

    Args:
        device: Device dict from NetBox

    Returns:
        Status string, or empty string if not found
    """
    status = device.get("status", "")

    if isinstance(status, str):
        return status
    elif isinstance(status, dict):
        return status.get("value", "")

    return ""


def get_custom_field_bool(device: dict, *names: str) -> bool:
    """
    Check if custom field is True (case-insensitive key lookup).

    Args:
        device: Device dict from NetBox
        *names: Possible custom field key names (case variants)

    Returns:
        True only if the field value is exactly True (bool)
    """
    custom_fields = device.get("custom_fields", {})

    if not custom_fields:
        return False

    for name in names:
        for key in custom_fields:
            if key.lower() == name.lower():
                value = custom_fields[key]
                return value is True

    return False


def get_tenant_group_name(device: dict) -> Optional[str]:
    """
    Extract tenant group name (handles nested structure + id fallback).

    Args:
        device: Device dict from NetBox

    Returns:
        Tenant group name/slug, or None if not found
    """
    tenant = device.get("tenant")

    if not tenant:
        return None

    if isinstance(tenant, dict):
        group = tenant.get("group")
        if isinstance(group, dict):
            # Try name first
            name = group.get("name")
            if name:
                return name
            # Then slug
            slug = group.get("slug")
            if slug:
                return slug
            # Then id if configured
            group_id = group.get("id")
            if group_id:
                return str(group_id)

    return None


def get_rejection_reason(device: dict) -> Optional[str]:
    """
    Determine why device is not eligible (or return None if eligible).

    Returns single reason string for UI display.
    """
    status = get_status_value(device)
    if status != "active":
        return "inactive"

    if not get_custom_field_bool(device, "Compliance", "compliance"):
        return "compliance_disabled"

    if not device.get("tenant"):
        return "no_tenant"

    group_name = get_tenant_group_name(device)
    if not group_name or group_name not in ("K3G Solutions", "k3g-solutions"):
        import os
        expected_id = os.getenv("K3G_SOLUTIONS_TENANT_GROUP_ID", "").strip()
        if expected_id and group_name == expected_id:
            return None  # Eligible
        return "wrong_tenant_group"

    return None  # Eligible


def is_compliance_candidate(device: dict) -> bool:
    """
    Check if device meets all 4 eligibility gates.

    Gates:
        1. status == "active"
        2. custom_fields["Compliance"] is True (case-insensitive)
        3. tenant present
        4. tenant.group.name == "K3G Solutions" or slug == "k3g-solutions"

    Args:
        device: Device dict from NetBox

    Returns:
        True if all gates pass, False otherwise
    """
    # Gate 1: status active
    status = get_status_value(device)
    if status != "active":
        return False

    # Gate 2: Compliance enabled (case-insensitive field lookup)
    if not get_custom_field_bool(device, "Compliance", "compliance"):
        return False

    # Gate 3: tenant present
    tenant = device.get("tenant")
    if not tenant:
        return False

    # Gate 4: tenant group name or slug
    group_name = get_tenant_group_name(device)
    if not group_name:
        return False

    if group_name not in ("K3G Solutions", "k3g-solutions"):
        # Check if it's an ID match against env var
        import os

        expected_id = os.getenv("K3G_SOLUTIONS_TENANT_GROUP_ID", "").strip()
        if expected_id and group_name == expected_id:
            return True
        return False

    return True


def sanitize_device_for_candidate(device: dict) -> dict:
    """
    Extract only allowed fields, never return config_context/local_context_data/payload.

    Keeps only:
    - id, name, status, tenant, site, device_role/role, device_type
    - primary_ip4, primary_ip6, custom_fields["Compliance"]

    Removes:
    - config_context, local_context_data, all raw config payload
    - full custom_fields object (only extract Compliance bool)
    - comments, interfaces, full nested objects
    """
    return {
        "id": device.get("id"),
        "name": device.get("name"),
        "status": device.get("status"),
        "tenant": device.get("tenant"),
        "site": device.get("site"),
        "device_role": device.get("device_role"),
        "role": device.get("role"),
        "device_type": device.get("device_type"),
        "primary_ip4": device.get("primary_ip4"),
        "primary_ip6": device.get("primary_ip6"),
        # Only Compliance custom field value, not full object
        "compliance_field_value": get_custom_field_bool(device, "Compliance", "compliance"),
    }


def normalize_compliance_candidate(device: dict) -> dict:
    """
    Convert device dict to normalized candidate response.

    Args:
        device: Device dict from NetBox

    Returns:
        Normalized candidate dict per API spec
    """
    # Determine candidate reasons (for debugging)
    reasons = []
    if get_status_value(device) == "active":
        reasons.append("device_active")
    if get_custom_field_bool(device, "Compliance", "compliance"):
        reasons.append("compliance_enabled")
    if device.get("tenant"):
        reasons.append("tenant_present")
    if get_tenant_group_name(device) in ("K3G Solutions", "k3g-solutions"):
        reasons.append("tenant_group_match")

    # Extract primary IPs
    primary_ip4 = None
    primary_ip6 = None
    if device.get("primary_ip4"):
        ip4 = device["primary_ip4"]
        primary_ip4 = ip4.get("address") if isinstance(ip4, dict) else str(ip4)
    if device.get("primary_ip6"):
        ip6 = device["primary_ip6"]
        primary_ip6 = ip6.get("address") if isinstance(ip6, dict) else str(ip6)

    # Extract tenant name
    tenant_name = None
    tenant = device.get("tenant")
    if isinstance(tenant, dict):
        tenant_name = tenant.get("name")
    elif isinstance(tenant, str):
        tenant_name = tenant

    # Extract site name
    site_name = None
    site = device.get("site")
    if isinstance(site, dict):
        site_name = site.get("name")
    elif isinstance(site, str):
        site_name = site

    # Extract role name
    role_name = None
    role = device.get("device_role") or device.get("role")
    if isinstance(role, dict):
        role_name = role.get("name")
    elif isinstance(role, str):
        role_name = role

    # Extract manufacturer and model
    device_type = device.get("device_type", {})
    manufacturer_name = None
    model_name = None
    if isinstance(device_type, dict):
        manufacturer = device_type.get("manufacturer", {})
        if isinstance(manufacturer, dict):
            manufacturer_name = manufacturer.get("name")
        elif isinstance(manufacturer, str):
            manufacturer_name = manufacturer

        model_name = device_type.get("model")

    return {
        "id": device.get("id"),
        "name": device.get("name"),
        "status": get_status_value(device),
        "tenant": tenant_name,
        "tenant_group": get_tenant_group_name(device),
        "compliance_enabled": get_custom_field_bool(device, "Compliance", "compliance"),
        "primary_ip4": primary_ip4,
        "primary_ip6": primary_ip6,
        "site": site_name,
        "role": role_name,
        "manufacturer": manufacturer_name,
        "model": model_name,
        "candidate_reason": reasons,
    }


def list_compliance_candidates(
    netbox_client: NetBoxClient,
    device_id: Optional[int] = None,
    name: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
    include_rejected: bool = False,
    filters: Optional[dict] = None,
) -> dict:
    """
    Fetch and filter devices to return only compliance candidates.

    Selective search: if id/name/q provided, search specifically. Otherwise return empty.

    Args:
        netbox_client: NetBoxClient instance
        device_id: Optional device ID (exact match)
        name: Optional device name (exact match)
        q: Optional search query (partial match, limit max 25)
        limit: Max results per page (default 10)
        offset: Pagination offset
        include_rejected: If True, include rejected devices with reasons
        filters: Optional additional query filters

    Returns:
        Response dict with candidates + optional rejected + safety block

    Raises:
        NetBoxClientError: if NetBox request fails
        NetBoxAuthError: if authentication fails
    """
    if filters is None:
        filters = {}

    devices = []
    message = None

    # Selective search logic
    if device_id:
        device = netbox_client.get_device_by_id(device_id)
        devices = [device] if device else []
    elif name:
        devices = netbox_client.search_devices_by_name(name, limit=limit)
    elif q:
        devices = netbox_client.search_devices(q, limit=limit, offset=offset)
    else:
        # No search criteria
        message = "Informe id, name ou q para buscar candidatos."
        devices = []

    # Filter to candidates
    candidates = []
    rejected = []

    for device in devices:
        if is_compliance_candidate(device):
            candidates.append(normalize_compliance_candidate(device))
        elif include_rejected:
            reason = get_rejection_reason(device)
            rejected.append({
                "id": device.get("id"),
                "name": device.get("name"),
                "reason": reason,
            })

    result = {
        "count": len(candidates),
        "results": candidates,
        "safety": {
            "read_only": True,
            "netbox_write": False,
            "device_connection": False,
            "auto_compliance_started": False,
        },
    }

    if message:
        result["message"] = message

    if include_rejected and rejected:
        result["rejected"] = rejected

    return result
