"""Compliance read-only collection executor.

Local simulation only. No SSH, SNMP, NETCONF, NetBox write, or /sync.
No ApprovalRecord. No ApplyPlan.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .compliance_collection_profiles import (
    get_allowed_commands_for_device,
    select_collection_profile,
    validate_profile,
)
from .compliance_jobs import (
    JOBS_BASE,
    get_compliance_job_safety,
    load_compliance_job,
)


SIMULATION_STATUS = "COLLECTION_SIMULATION_PREPARED"
SAFETY_VALID = "COLLECTION_SAFETY_VALID"
SAFETY_INVALID = "COLLECTION_SAFETY_INVALID"

FORBIDDEN_COMMAND_PARTS = {
    "system-view",
    "configure",
    "commit",
    "save",
    "reset",
    "reboot",
    "delete",
    "undo",
    "shutdown",
    "patch",
    "sync",
}

DISPLAY_ONLY_PATTERNS = ("display ", "show ")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dump_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_text(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _safe_job_dir(job_id: str, jobs_base: Optional[Path] = None) -> Path:
    base = jobs_base or JOBS_BASE
    return base / job_id


def validate_collection_plan(plan: dict) -> tuple[bool, list[str]]:
    """Validate collection plan for read-only execution."""
    issues: list[str] = []

    if not isinstance(plan, dict):
        return False, ["plan not a dict"]

    if plan.get("decision") != "COLLECTION_PLAN_PREPARED":
        issues.append("plan decision not prepared")

    devices = plan.get("devices")
    if not isinstance(devices, list) or not devices:
        issues.append("no devices in plan")
        return False, issues

    if plan.get("collection_started") is True:
        issues.append("collection_started must be false")

    if plan.get("safety") and plan["safety"] != get_compliance_job_safety():
        issues.append("safety block mismatch")

    for device in devices:
        if not isinstance(device, dict):
            issues.append("device entry not a dict")
            continue

        profile = device.get("collection_profile") or {}
        if profile and profile.get("valid") is False:
            issues.append(f"invalid collection profile for device {device.get('device_id')}")

        commands = list(device.get("planned_commands") or build_read_only_commands(device))
        if not commands:
            issues.append(f"no commands for device {device.get('device_id')}")
            continue

        for command in commands:
            lowered = command.lower().strip()
            if not any(lowered.startswith(prefix) for prefix in DISPLAY_ONLY_PATTERNS):
                issues.append(f"non display/show command: {command}")
            for forbidden in FORBIDDEN_COMMAND_PARTS:
                if forbidden in lowered:
                    issues.append(f"forbidden command detected: {command}")
                    break

    return len(issues) == 0, issues


def build_read_only_commands(device: dict) -> list[str]:
    """Build read-only collection commands for a device."""
    return get_allowed_commands_for_device(device)


def _render_execution_markdown(job_id: str, operator: str, simulation_only: bool, devices: list[dict], decision: str) -> str:
    lines = [
        "# COLLECTION-EXECUTION",
        "",
        f"## Job ID\n`{job_id}`",
        "",
        f"## Operator\n`{operator}`",
        "",
        f"## Decision\n`{decision}`",
        "",
        f"## Simulation Only\n`{simulation_only}`",
        "",
        "## Devices",
    ]
    for device in devices:
        lines.extend([
            "",
            f"### {device.get('name')}",
            f"- device_id: {device.get('device_id')}",
            f"- primary_ip4: {device.get('primary_ip4') or 'none'}",
            "- execution_mode: read_only_simulation",
        ])
    lines.extend([
        "",
        "## Safety",
        "",
        "- No SSH connection",
        "- No SNMP query",
        "- No NETCONF session",
        "- No NetBox write",
        "- No /sync",
        "- No ApprovalRecord",
        "- No ApplyPlan",
    ])
    return "\n".join(lines) + "\n"


def _render_validation_markdown(job_id: str, decision: str, issues: list[str], command_count: int) -> str:
    lines = [
        "# COLLECTION-SAFETY-VALIDATION",
        "",
        f"## Job ID\n`{job_id}`",
        "",
        f"## Decision\n`{decision}`",
        "",
        f"## Command Count\n{command_count}",
        "",
        "## Issues",
    ]
    if issues:
        for issue in issues:
            lines.append(f"- {issue}")
    else:
        lines.append("- none")
    lines.extend([
        "",
        "## Safety",
        "",
        "- simulation_only=true",
        "- device_connection_started=false",
        "- netbox_write=false",
        "- sync_called=false",
        "- no ApprovalRecord",
        "- no ApplyPlan",
    ])
    return "\n".join(lines) + "\n"


def execute_collection_job(job_id: str, operator: str, simulation_only: bool = True, jobs_base: Optional[Path] = None) -> dict:
    """Execute collection job in simulation mode only."""
    job = load_compliance_job(job_id, jobs_base)
    job_dir = _safe_job_dir(job_id, jobs_base)

    gate = job.get("collection_start_gate") or {}
    if gate.get("decision") != "COLLECTION_START_GATE_READY":
        raise ValueError("collection start gate not ready")

    plan = job.get("collection_plan") or {}
    if plan.get("decision") != "COLLECTION_PLAN_PREPARED":
        raise ValueError("collection plan not prepared")

    if not operator or not operator.strip():
        raise ValueError("operator required")

    results_dir = job_dir / "collection-results"
    results_dir.mkdir(parents=True, exist_ok=True)

    execution_devices: list[dict[str, Any]] = []
    planned_command_count = 0

    devices = list(plan.get("devices") or [])
    for device in devices:
        profile = select_collection_profile(device)
        profile_id = profile.get("profile_id") or "default-readonly"
        profile_valid, profile_issues = validate_profile(profile)
        device_id = str(device.get("device_id") or device.get("id") or "unknown")
        device_dir = results_dir / "devices" / device_id
        raw_dir = device_dir / "raw"
        parsed_dir = device_dir / "parsed"
        raw_dir.mkdir(parents=True, exist_ok=True)
        parsed_dir.mkdir(parents=True, exist_ok=True)
        (raw_dir / ".gitkeep").touch(exist_ok=True)
        (parsed_dir / ".gitkeep").touch(exist_ok=True)

        commands = build_read_only_commands(device)
        planned_command_count += len(commands)
        device_payload = {
            "device_id": device.get("device_id"),
            "name": device.get("name"),
            "primary_ip4": device.get("primary_ip4"),
            "platform": device.get("platform"),
            "manufacturer": device.get("manufacturer"),
            "model": device.get("model"),
            "simulation_only": simulation_only,
            "profile_id": profile_id,
            "profile_vendor": profile.get("vendor") or "generic",
            "profile_platform": profile.get("platform") or "generic",
            "profile_valid": profile_valid,
            "profile_issues": profile_issues,
            "planned_commands": commands,
            "blocked_patterns": sorted(FORBIDDEN_COMMAND_PARTS),
        }
        _dump_json(device_dir / "planned-commands.json", device_payload)
        execution_devices.append(device_payload)

    execution_payload = {
        "job_id": job_id,
        "status": SIMULATION_STATUS,
        "operator": operator,
        "simulation_only": simulation_only,
        "device_connection_started": False,
        "netbox_write": False,
        "sync_called": False,
        "approval_record_created": False,
        "apply_plan_created": False,
        "collection_started": False,
        "command_count": planned_command_count,
        "devices": execution_devices,
        "checked_at": _now(),
        "safety": get_compliance_job_safety(),
    }
    _dump_json(results_dir / "collection-execution.json", execution_payload)
    (results_dir / "COLLECTION-EXECUTION.md").write_text(
        _render_execution_markdown(job_id, operator, simulation_only, execution_devices, SIMULATION_STATUS),
        encoding="utf-8",
    )

    valid, issues = validate_collection_plan(plan)
    decision = SAFETY_VALID if valid and simulation_only and not execution_payload["device_connection_started"] else SAFETY_INVALID
    validation_payload = {
        "job_id": job_id,
        "decision": decision,
        "status": decision,
        "checked_at": _now(),
        "simulation_only": simulation_only,
        "device_connection_started": False,
        "netbox_write": False,
        "sync_called": False,
        "approval_record_created": False,
        "apply_plan_created": False,
        "issues": issues,
        "command_count": planned_command_count,
        "devices": execution_devices,
    }
    _dump_json(results_dir / "collection-safety-validation.json", validation_payload)
    (results_dir / "COLLECTION-SAFETY-VALIDATION.md").write_text(
        _render_validation_markdown(job_id, decision, issues, planned_command_count),
        encoding="utf-8",
    )

    return {
        "job_id": job_id,
        "operator": operator,
        "simulation_only": simulation_only,
        "status": SIMULATION_STATUS,
        "decision": decision,
        "results_dir": str(results_dir),
        "collection_execution": execution_payload,
        "collection_safety_validation": validation_payload,
        "files": {
            "collection_execution": str(results_dir / "collection-execution.json"),
            "collection_execution_markdown": str(results_dir / "COLLECTION-EXECUTION.md"),
            "collection_safety_validation": str(results_dir / "collection-safety-validation.json"),
            "collection_safety_validation_markdown": str(results_dir / "COLLECTION-SAFETY-VALIDATION.md"),
        },
    }
