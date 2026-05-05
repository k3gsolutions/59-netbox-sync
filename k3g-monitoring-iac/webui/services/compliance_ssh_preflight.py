"""SSH connectivity preflight for read-only collection."""

from __future__ import annotations

import json
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .compliance_collection import build_read_only_commands, validate_collection_plan
from .compliance_jobs import JOBS_BASE, get_compliance_job_safety, load_compliance_job
from .compliance_ssh_policy import (
    load_ssh_readonly_policy,
    sanitize_command_filename,
    validate_commands_allowed,
    validate_ssh_env,
)
from .compliance_connection_resolver import resolve_device_connection


SSH_PREFLIGHT_READY_CONFIG_ONLY = "SSH_PREFLIGHT_READY_CONFIG_ONLY"
SSH_PREFLIGHT_READY_CONNECTIVITY_CHECKED = "SSH_PREFLIGHT_READY_CONNECTIVITY_CHECKED"
SSH_PREFLIGHT_BLOCKED = "SSH_PREFLIGHT_BLOCKED"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dump_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _safe_job_dir(job_id: str, jobs_base: Optional[Path] = None) -> Path:
    return (jobs_base or JOBS_BASE) / job_id


def _extract_host(primary_ip4: Any) -> str:
    if isinstance(primary_ip4, dict):
        primary_ip4 = primary_ip4.get("address") or primary_ip4.get("value") or ""
    text = str(primary_ip4 or "").strip()
    if "/" in text:
        return text.split("/", 1)[0]
    return text


def run_ssh_preflight(job_id: str, operator: str, confirm_read_only: bool = True, jobs_base: Optional[Path] = None) -> dict:
    """Validate configs for SSH read-only collection without connecting."""
    job = load_compliance_job(job_id, jobs_base)
    job_dir = _safe_job_dir(job_id, jobs_base)
    results_dir = job_dir / "collection-results"
    results_dir.mkdir(parents=True, exist_ok=True)

    gate = job.get("collection_start_gate") or {}
    plan = job.get("collection_plan") or {}
    execution = job.get("collection_results") or {}
    safety_validation = job.get("collection_safety_validation") or {}
    env = validate_ssh_env()

    plan_devices = list(plan.get("devices") or [])
    command_issues: list[str] = []
    host_issues: list[str] = []
    planned_commands_per_device: list[dict[str, Any]] = []

    if not confirm_read_only:
        command_issues.append("confirm_read_only must be true")
    if not operator or not operator.strip():
        command_issues.append("operator required")
    if gate.get("decision") != "COLLECTION_START_GATE_READY":
        command_issues.append("collection start gate not ready")
    if plan.get("decision") != "COLLECTION_PLAN_PREPARED":
        command_issues.append("collection plan not prepared")
    if safety_validation.get("decision") != "COLLECTION_SAFETY_VALID":
        command_issues.append("collection safety validation not valid")
    if not env.get("ready"):
        command_issues.extend([f"missing env: {name}" for name in env.get("missing_env_vars") or []])

    policy = load_ssh_readonly_policy()
    for device in plan_devices:
        commands = list(device.get("planned_commands") or build_read_only_commands(device))
        ok, issues = validate_commands_allowed(commands)
        if not ok:
            command_issues.extend(issues)

        # Resolve connection with priority: override > selected > primary_ip4 > env > 22
        conn = resolve_device_connection(job_id, device, jobs_base)
        host = conn.get("host")
        port = conn.get("port", 22)

        if not host:
            host_issues.append(f"missing connection info for device {device.get('device_id')}")

        planned_commands_per_device.append(
            {
                "device_id": device.get("device_id"),
                "name": device.get("name"),
                "host": host,
                "port": port,
                "timeout": env.get("timeout", 10),
                "connection_source": conn.get("source", "default"),
                "override_applied": conn.get("override_applied", False),
                "planned_commands": commands,
                "command_files": [sanitize_command_filename(command) for command in commands],
            }
        )

    tcp_check_enabled = bool(env.get("tcp_check_enabled"))
    tcp_check_result = {"enabled": tcp_check_enabled, "attempted": False, "success": False, "issues": []}
    if tcp_check_enabled and not command_issues and not host_issues:
        tcp_check_result["attempted"] = True
        try:
            for device in planned_commands_per_device:
                with socket.create_connection((device["host"], int(device["port"])), timeout=int(device["timeout"])):
                    pass
            tcp_check_result["success"] = True
        except Exception as exc:
            tcp_check_result["issues"].append(str(exc))

    ready = not command_issues and not host_issues and env.get("ready") and confirm_read_only
    if tcp_check_enabled and tcp_check_result["attempted"] and not tcp_check_result["success"]:
        ready = False

    decision = SSH_PREFLIGHT_READY_CONFIG_ONLY
    if tcp_check_enabled and tcp_check_result["success"]:
        decision = SSH_PREFLIGHT_READY_CONNECTIVITY_CHECKED
    if not ready:
        decision = SSH_PREFLIGHT_BLOCKED

    payload = {
        "job_id": job_id,
        "operator": operator,
        "confirm_read_only": bool(confirm_read_only),
        "decision": decision,
        "status": decision,
        "checked_at": _now(),
        "env": {
            "username_present": env.get("username_present", False),
            "password_present": env.get("password_present", False),
            "port": env.get("port", 22),
            "timeout": env.get("timeout", 10),
            "tcp_check_enabled": tcp_check_enabled,
        },
        "policy": {
            "allowed_protocol": policy.get("allowed_protocol", "ssh"),
            "allowed_command_prefixes": policy.get("allowed_command_prefixes", []),
        },
        "preconditions": {
            "start_gate_ready": gate.get("decision") == "COLLECTION_START_GATE_READY",
            "plan_prepared": plan.get("decision") == "COLLECTION_PLAN_PREPARED",
            "safety_valid": safety_validation.get("decision") == "COLLECTION_SAFETY_VALID",
            "confirm_read_only": bool(confirm_read_only),
        },
        "planned_devices": planned_commands_per_device,
        "command_issues": command_issues,
        "host_issues": host_issues,
        "tcp_check": tcp_check_result,
        "safety": {
            "password_saved": False,
            "password_logged": False,
            "commands_executed": False,
            "netbox_write": False,
            "sync_called": False,
        },
    }
    _dump_json(results_dir / "ssh-preflight.json", payload)
    (results_dir / "SSH-PREFLIGHT.md").write_text(
        "\n".join(
            [
                "# SSH-PREFLIGHT",
                "",
                f"## Job ID\n`{job_id}`",
                "",
                f"## Decision\n`{decision}`",
                "",
                f"## TCP Check Enabled\n`{tcp_check_enabled}`",
                "",
                "## Preconditions",
                f"- start_gate_ready: {payload['preconditions']['start_gate_ready']}",
                f"- plan_prepared: {payload['preconditions']['plan_prepared']}",
                f"- safety_valid: {payload['preconditions']['safety_valid']}",
                f"- confirm_read_only: {payload['preconditions']['confirm_read_only']}",
                "",
                "## Issues",
                *(
                    [f"- {issue}" for issue in (command_issues + host_issues + tcp_check_result.get("issues", []))]
                    or ["- none"]
                ),
                "",
                "## Safety",
                "- password_saved=false",
                "- password_logged=false",
                "- commands_executed=false",
                "- netbox_write=false",
                "- sync_called=false",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "job_id": job_id,
        "operator": operator,
        "decision": decision,
        "status": decision,
        "files": {
            "ssh_preflight": str(results_dir / "ssh-preflight.json"),
            "ssh_preflight_markdown": str(results_dir / "SSH-PREFLIGHT.md"),
        },
        "ssh_preflight": payload,
    }
