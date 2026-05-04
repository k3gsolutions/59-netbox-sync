"""Resolve device connection (host/port) with override priority."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

JOBS_BASE = Path(__file__).parent.parent.parent / "reports" / "compliance" / "jobs"


def load_connection_override(job_id: str, jobs_base: Optional[Path] = None) -> dict:
    """Load connection-override.json if exists, validate, return normalized dict."""
    if jobs_base is None:
        jobs_base = JOBS_BASE

    job_dir = jobs_base / job_id
    override_path = job_dir / "connection-override.json"

    if not override_path.exists():
        return {}

    try:
        data = json.loads(override_path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    # Validate
    device_id = data.get("device_id")
    connection_ip = data.get("connection_ip", "").strip()
    connection_port = data.get("connection_port")

    if not device_id or not connection_ip or connection_port is None:
        return {
            "valid": False,
            "error": "Missing device_id, connection_ip, or connection_port",
        }

    # Port range check
    try:
        port = int(connection_port)
        if port < 1 or port > 65535:
            return {
                "valid": False,
                "error": f"Port {port} out of range [1, 65535]",
            }
    except (ValueError, TypeError):
        return {
            "valid": False,
            "error": f"Port {connection_port} not integer",
        }

    # Safety checks
    safety = data.get("safety", {})
    if safety.get("netbox_write") is not False:
        return {
            "valid": False,
            "error": "safety.netbox_write must be false",
        }

    if safety.get("local_override_only") is not True:
        return {
            "valid": False,
            "error": "safety.local_override_only must be true",
        }

    return {
        "valid": True,
        "device_id": device_id,
        "connection_ip": connection_ip,
        "connection_port": port,
        "reason": data.get("reason", ""),
        "operator": data.get("operator", ""),
    }


def resolve_device_connection(
    job_id: str, device: dict, jobs_base: Optional[Path] = None
) -> dict:
    """Resolve device connection (host/port) with priority: override > selected > primary_ip4 > env > 22."""
    if jobs_base is None:
        jobs_base = JOBS_BASE

    device_id = device.get("id") or device.get("device_id")
    override = load_connection_override(job_id, jobs_base)

    # Priority 1: Override
    if override.get("valid"):
        if override.get("device_id") == device_id:
            return {
                "host": override.get("connection_ip"),
                "port": override.get("connection_port"),
                "source": "connection_override",
                "override_applied": True,
            }

    # Priority 2: selected-devices.json connection_ip (if device has it)
    selected_connection_ip = device.get("connection_ip", "").strip()
    selected_connection_port = device.get("connection_port")
    if selected_connection_ip and selected_connection_port:
        try:
            port = int(selected_connection_port)
            return {
                "host": selected_connection_ip,
                "port": port,
                "source": "selected_devices",
                "override_applied": False,
            }
        except (ValueError, TypeError):
            pass

    # Priority 3: primary_ip4 (strip /mask)
    primary_ip4 = device.get("primary_ip4", "").strip()
    if primary_ip4:
        # Remove CIDR notation if present
        host = primary_ip4.split("/")[0]
        if host:
            # Priority 4: env COMPLIANCE_SSH_PORT
            port_env = os.getenv("COMPLIANCE_SSH_PORT", "22").strip()
            try:
                port = int(port_env)
            except (ValueError, TypeError):
                port = 22

            return {
                "host": host,
                "port": port,
                "source": "primary_ip4",
                "override_applied": False,
            }

    # Fallback
    return {
        "host": None,
        "port": 22,
        "source": "default",
        "override_applied": False,
        "error": "No connection info available",
    }
