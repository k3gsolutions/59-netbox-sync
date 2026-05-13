"""Sync NetBox → local SQLite database."""

import os
from typing import Dict, List, Optional, Tuple
from .local_db import upsert_tenant, upsert_device, upsert_credentials, get_tenants, get_devices
from .netbox_client import get_netbox_client


SNMP_COMMUNITY_ALIASES = [
    "snmp_community",
    "snmpcommunity",
    "snmp_ro_community",
    "snmp_community_ro",
    "snmp_read_community",
    "snmp_v2c_community",
    "community",
    "comunidade_snmp",
    "compliance_snmp_community",
]


def _lookup_connection_value(
    obj: Optional[Dict],
    field_names: List[str],
    fallback_env: Optional[str] = None
) -> Optional[str]:
    """Look up a connection value in custom_fields, local_context_data, config_context."""
    if not obj:
        return os.getenv(fallback_env) if fallback_env else None

    # Check custom_fields
    if "custom_fields" in obj and obj["custom_fields"]:
        for name in field_names:
            if name in obj["custom_fields"]:
                val = obj["custom_fields"][name]
                if val:
                    return str(val)

    # Check local_context_data
    if "local_context_data" in obj and obj["local_context_data"]:
        for name in field_names:
            if name in obj["local_context_data"]:
                val = obj["local_context_data"][name]
                if val:
                    return str(val)

    # Check config_context
    if "config_context" in obj and obj["config_context"]:
        for name in field_names:
            if name in obj["config_context"]:
                val = obj["config_context"][name]
                if val:
                    return str(val)

    return os.getenv(fallback_env) if fallback_env else None


def _resolve_snmp_community(
    device: Optional[Dict] = None,
    tenant: Optional[Dict] = None
) -> Optional[str]:
    """Resolve SNMP community: device custom_fields > tenant custom_fields > env."""
    # Device-level
    if device:
        val = _lookup_connection_value(device, SNMP_COMMUNITY_ALIASES)
        if val:
            return val

    # Tenant-level
    if tenant:
        val = _lookup_connection_value(tenant, SNMP_COMMUNITY_ALIASES)
        if val:
            return val

    # Env fallback
    return os.getenv("SNMP_COMMUNITY", None)


def sync_netbox_to_local() -> Tuple[int, int, List[str]]:
    """Sync NetBox → local SQLite. Returns (tenants_synced, devices_synced, errors)."""
    errors = []

    try:
        nb = get_netbox_client()
    except Exception as e:
        return 0, 0, [f"NetBox client error: {str(e)}"]

    tenants_synced = 0
    devices_synced = 0

    # ──── SYNC TENANTS ────
    try:
        tenant_list = nb.tenancy.tenants.all()
        for tenant in tenant_list:
            try:
                snmp_community = _resolve_snmp_community(tenant=tenant)

                upsert_tenant(
                    id=tenant.id,
                    name=tenant.name,
                    slug=tenant.slug,
                    group_name=tenant.group.name if tenant.group else None,
                    snmp_community=snmp_community
                )
                tenants_synced += 1
            except Exception as e:
                errors.append(f"Tenant {tenant.name}: {str(e)}")

    except Exception as e:
        errors.append(f"Tenants fetch error: {str(e)}")

    # ──── SYNC DEVICES ────
    try:
        device_list = nb.dcim.devices.all()
        for device in device_list:
            try:
                # Resolve device and tenant objects
                device_dict = device.__dict__.copy()
                tenant = device.tenant if hasattr(device, "tenant") and device.tenant else None

                # Device SNMP community (device-level override)
                snmp_community = _resolve_snmp_community(device=device_dict, tenant=tenant.__dict__.copy() if tenant else None)

                # Upsert device
                upsert_device(
                    id=device.id,
                    name=device.name,
                    tenant_id=device.tenant.id if device.tenant else None,
                    platform=device.platform.name if device.platform else None,
                    manufacturer=device.device_type.manufacturer.name if device.device_type and device.device_type.manufacturer else None,
                    model=device.device_type.model if device.device_type else None,
                    primary_ip=str(device.primary_ip4) if device.primary_ip4 else None,
                    site=device.site.name if device.site else None,
                    role=device.device_role.name if device.device_role else None,
                    status=device.status
                )

                # Upsert credentials
                upsert_credentials(
                    device_id=device.id,
                    snmp_community=snmp_community,
                    ssh_host=device.name,  # Fallback; ideally from custom_fields
                    ssh_port=22,
                    username=None,  # Not stored in NetBox device object; comes from Secrets plugin
                    password=None
                )

                devices_synced += 1

            except Exception as e:
                errors.append(f"Device {device.name}: {str(e)}")

    except Exception as e:
        errors.append(f"Devices fetch error: {str(e)}")

    return tenants_synced, devices_synced, errors
