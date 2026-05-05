"""Sync candidate discovery — read-only device enumeration for synchronization."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .netbox_client import get_netbox_client, NetBoxClientError, NetBoxNotConfiguredError, NetBoxAuthError
from .compliance_candidates import normalize_compliance_candidate

REPORTS_DIR = Path(__file__).parent.parent.parent / "reports"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dump_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def discover_sync_candidates(operator: str = "operator") -> dict:
    """Discover devices eligible for synchronization (read-only, no write)."""
    try:
        client = get_netbox_client()
    except NetBoxNotConfiguredError:
        return {
            "success": False,
            "error": "NetBox not configured. Set NETBOX_URL and NETBOX_TOKEN.",
            "count": 0,
            "results": [],
            "safety": {
                "netbox_write": False,
                "sync_executed": False,
                "device_connection": False,
            },
        }
    except NetBoxAuthError:
        return {
            "success": False,
            "error": "NetBox authentication failed (401/403).",
            "count": 0,
            "results": [],
            "safety": {
                "netbox_write": False,
                "sync_executed": False,
                "device_connection": False,
            },
        }

    candidates: list[dict[str, Any]] = []
    errors: list[str] = []

    # Query all active devices
    try:
        devices = client.get_devices(status="active")
    except NetBoxClientError as e:
        return {
            "success": False,
            "error": f"Failed to query devices: {e}",
            "count": 0,
            "results": [],
            "safety": {
                "netbox_write": False,
                "sync_executed": False,
                "device_connection": False,
            },
        }

    # Evaluate readiness for each device
    for device in devices:
        device_id = device.get("id")
        name = device.get("name", "?")

        readiness = {
            "has_tenant": bool(device.get("tenant")),
            "has_site": bool(device.get("site")),
            "has_role": bool(device.get("role")),
            "has_primary_ip": bool(device.get("primary_ip4") or device.get("primary_ip6")),
            "has_platform": bool(device.get("platform")),
            "has_manufacturer": bool(device.get("device_type", {}).get("manufacturer")),
        }

        # Sync candidate if has tenant, site, role, primary_ip, platform
        sync_eligible = all(
            [
                readiness["has_tenant"],
                readiness["has_site"],
                readiness["has_role"],
                readiness["has_primary_ip"],
                readiness["has_platform"],
            ]
        )

        if sync_eligible:
            tenant_obj = device.get("tenant") or {}
            tenant_name = tenant_obj.get("name") if isinstance(tenant_obj, dict) else str(tenant_obj)

            site_obj = device.get("site") or {}
            site_name = site_obj.get("name") if isinstance(site_obj, dict) else str(site_obj)

            role_obj = device.get("role") or {}
            role_name = role_obj.get("name") if isinstance(role_obj, dict) else str(role_obj)

            platform_obj = device.get("platform") or {}
            platform_name = platform_obj.get("name") if isinstance(platform_obj, dict) else str(platform_obj)

            device_type_obj = device.get("device_type") or {}
            manufacturer_obj = device_type_obj.get("manufacturer") or {}
            manufacturer = manufacturer_obj.get("name") if isinstance(manufacturer_obj, dict) else str(manufacturer_obj)
            model = device_type_obj.get("model", "?")

            primary_ip4 = device.get("primary_ip4")
            primary_ip4_str = (
                primary_ip4.get("address") if isinstance(primary_ip4, dict) else str(primary_ip4)
            ) if primary_ip4 else None

            candidates.append(
                {
                    "id": device_id,
                    "name": name,
                    "status": device.get("status", "unknown"),
                    "tenant": tenant_name,
                    "site": site_name,
                    "role": role_name,
                    "manufacturer": manufacturer,
                    "model": model,
                    "platform": platform_name,
                    "primary_ip4": primary_ip4_str,
                    "sync_eligible": True,
                    "readiness": readiness,
                }
            )

    result = {
        "success": True,
        "discovered_at": _now(),
        "operator": operator,
        "count": len(candidates),
        "results": candidates,
        "safety": {
            "netbox_write": False,
            "sync_executed": False,
            "device_connection": False,
            "read_only_only": True,
            "no_device_connection": True,
        },
    }

    return result


def save_sync_candidates(result: dict, reports_base: Optional[Path] = None) -> dict:
    """Save discovered sync candidates to disk."""
    if reports_base is None:
        reports_base = REPORTS_DIR

    candidates_dir = reports_base / "sync" / "candidates"
    candidates_dir.mkdir(parents=True, exist_ok=True)

    # Save JSON
    candidates_json = candidates_dir / "sync-candidates.json"
    _dump_json(candidates_json, result)

    # Save Markdown
    candidates_md = candidates_dir / "SYNC-CANDIDATES.md"
    md_lines = [
        "# Sync Candidates Discovery",
        "",
        f"**Discovered:** {result.get('discovered_at', 'unknown')}",
        f"**Count:** {result.get('count', 0)}",
        f"**Operator:** {result.get('operator', 'unknown')}",
        "",
        "## Readiness Criteria",
        "- Device status: active",
        "- Has tenant ✓",
        "- Has site ✓",
        "- Has role ✓",
        "- Has primary_ip4 or primary_ip6 ✓",
        "- Has platform ✓",
        "",
        "## Candidates",
        "",
    ]

    candidates = result.get("results", [])
    if candidates:
        for device in candidates:
            md_lines.append(f"### {device['id']} — {device['name']}")
            md_lines.append("")
            md_lines.append(f"- Status: {device.get('status', '?')}")
            md_lines.append(f"- Tenant: {device.get('tenant', '?')}")
            md_lines.append(f"- Site: {device.get('site', '?')}")
            md_lines.append(f"- Role: {device.get('role', '?')}")
            md_lines.append(f"- Platform: {device.get('platform', '?')}")
            md_lines.append(f"- Manufacturer: {device.get('manufacturer', '?')} {device.get('model', '?')}")
            md_lines.append(f"- Primary IP: {device.get('primary_ip4', '?')}")
            md_lines.append("")
    else:
        md_lines.append("(no candidates found)")
        md_lines.append("")

    md_lines.extend(
        [
            "## Safety",
            "- NetBox write: false",
            "- Sync executed: false",
            "- Device connection: false",
            "- Read-only only: true",
        ]
    )

    candidates_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    return {
        "success": True,
        "candidates_json": str(candidates_json),
        "candidates_markdown": str(candidates_md),
        "count": result.get("count", 0),
    }
