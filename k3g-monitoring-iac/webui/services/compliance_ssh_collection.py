"""Controlled SSH read-only collection executor."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

try:  # pragma: no cover - optional dependency
    import paramiko  # type: ignore
except Exception:  # pragma: no cover
    class _MissingParamiko:
        class SSHClient:  # type: ignore
            pass

        class AutoAddPolicy:  # type: ignore
            pass

    paramiko = _MissingParamiko()  # type: ignore

from .compliance_collection import build_read_only_commands
from .compliance_jobs import JOBS_BASE, load_compliance_job
from .compliance_output_redaction import redact_file, scan_sensitive_findings
from .compliance_parser_staging import create_parser_staging
from .compliance_ssh_policy import (
    sanitize_command_filename,
    validate_command_allowed,
    validate_commands_allowed,
    validate_ssh_env,
)
from .compliance_connection_resolver import resolve_device_connection


SSH_COLLECTION_COMPLETED = "SSH_COLLECTION_COMPLETED"
SSH_COLLECTION_COMPLETED_WITH_ERRORS = "SSH_COLLECTION_COMPLETED_WITH_ERRORS"
SSH_COLLECTION_BLOCKED = "SSH_COLLECTION_BLOCKED"
SSH_COLLECTION_FAILED = "SSH_COLLECTION_FAILED"


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


def _load_ssh_preflight(results_dir: Path) -> dict:
    path = results_dir / "ssh-preflight.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _drain_shell_output(channel: Any, timeout: int) -> str:
    """Read shell output until it goes quiet or timeout expires."""
    deadline = time.monotonic() + max(timeout, 1)
    quiet_since: float | None = None
    chunks: list[str] = []

    while time.monotonic() < deadline:
        if hasattr(channel, "recv_ready") and channel.recv_ready():
            try:
                raw = channel.recv(65535)
            except Exception:
                break
            text = raw.decode("utf-8", errors="ignore") if raw else ""
            if text:
                chunks.append(text)
                quiet_since = None
            continue

        if quiet_since is None:
            quiet_since = time.monotonic()
        elif time.monotonic() - quiet_since >= 0.4:
            break
        time.sleep(0.05)

    return "".join(chunks)


def _read_shell_prompt(channel: Any, timeout: int) -> str:
    """Drain initial banner/prompt output from an interactive shell."""
    return _drain_shell_output(channel, timeout)


def _run_shell_command(channel: Any, command: str, timeout: int) -> str:
    """Send a command over an interactive shell and collect its output."""
    channel.send(f"{command}\n")
    return _drain_shell_output(channel, timeout)


def _normalize_exception(exc: Exception) -> str:
    text = str(exc).strip()
    if text:
        return text
    return exc.__class__.__name__


def execute_ssh_readonly_collection(job_id: str, operator: str, confirm_execute_read_only: bool = True, jobs_base: Optional[Path] = None) -> dict:
    """Execute SSH read-only collection with one attempt per device."""
    job = load_compliance_job(job_id, jobs_base)
    job_dir = _safe_job_dir(job_id, jobs_base)
    results_dir = job_dir / "collection-results"
    results_dir.mkdir(parents=True, exist_ok=True)

    preflight = _load_ssh_preflight(results_dir)
    if preflight.get("decision") not in {"SSH_PREFLIGHT_READY_CONFIG_ONLY", "SSH_PREFLIGHT_READY_CONNECTIVITY_CHECKED"}:
        return {
            "job_id": job_id,
            "status": SSH_COLLECTION_BLOCKED,
            "decision": SSH_COLLECTION_BLOCKED,
            "reason": "ssh preflight not ready",
            "files": {
                "ssh_collection_result": str(results_dir / "ssh-collection-result.json"),
                "ssh_collection_result_markdown": str(results_dir / "SSH-COLLECTION-RESULT.md"),
            },
        }

    if not confirm_execute_read_only:
        return {
            "job_id": job_id,
            "status": SSH_COLLECTION_BLOCKED,
            "decision": SSH_COLLECTION_BLOCKED,
            "reason": "confirm_execute_read_only must be true",
        }

    env = validate_ssh_env()
    if not env.get("ready"):
        return {
            "job_id": job_id,
            "status": SSH_COLLECTION_BLOCKED,
            "decision": SSH_COLLECTION_BLOCKED,
            "reason": "ssh env not ready",
        }

    plan = job.get("collection_plan") or {}
    devices = list(plan.get("devices") or [])
    if not devices:
        return {
            "job_id": job_id,
            "status": SSH_COLLECTION_BLOCKED,
            "decision": SSH_COLLECTION_BLOCKED,
            "reason": "no devices in plan",
        }

    all_commands_allowed = True
    command_issues: list[str] = []
    for device in devices:
        commands = list(device.get("planned_commands") or build_read_only_commands(device))
        ok, issues = validate_commands_allowed(commands)
        if not ok:
            all_commands_allowed = False
            command_issues.extend(issues)
        for command in commands:
            allowed, reason = validate_command_allowed(command)
            if not allowed:
                all_commands_allowed = False
                command_issues.append(f"{device.get('device_id')}: {command}: {reason}")

    if not all_commands_allowed:
        result = {
            "job_id": job_id,
            "status": SSH_COLLECTION_BLOCKED,
            "decision": SSH_COLLECTION_BLOCKED,
            "operator": operator,
            "simulation_only": False,
            "device_connection_started": False,
            "netbox_write": False,
            "sync_called": False,
            "approval_record_created": False,
            "apply_plan_created": False,
            "commands_executed_count": 0,
            "forbidden_commands_executed": False,
            "config_mode_entered": False,
            "password_logged": False,
            "password_saved": False,
            "issues": command_issues,
            "devices": [],
            "checked_at": _now(),
        }
        _dump_json(results_dir / "ssh-collection-result.json", result)
        (results_dir / "SSH-COLLECTION-RESULT.md").write_text(
            "# SSH-COLLECTION-RESULT\n\nCollection blocked before connection.\n",
            encoding="utf-8",
        )
        return {
            "job_id": job_id,
            "status": SSH_COLLECTION_BLOCKED,
            "decision": SSH_COLLECTION_BLOCKED,
            "files": {
                "ssh_collection_result": str(results_dir / "ssh-collection-result.json"),
                "ssh_collection_result_markdown": str(results_dir / "SSH-COLLECTION-RESULT.md"),
            },
            "ssh_collection_result": result,
        }

    ssh_client_class = getattr(paramiko, "SSHClient", None)
    if ssh_client_class is None:
        raise RuntimeError("paramiko unavailable")

    all_device_results: list[dict[str, Any]] = []
    commands_executed_count = 0
    any_errors = False
    completed_devices = 0

    for device in devices:
        device_id = str(device.get("device_id") or device.get("id") or "unknown")

        # Resolve connection with priority: override > selected > primary_ip4 > env > 22
        conn = resolve_device_connection(job_id, device, jobs_base)
        host = conn.get("host")
        port = conn.get("port", 22)

        device_dir = results_dir / "devices" / device_id
        raw_dir = device_dir / "raw"
        redacted_dir = device_dir / "redacted"
        parsed_dir = device_dir / "parsed"
        raw_dir.mkdir(parents=True, exist_ok=True)
        redacted_dir.mkdir(parents=True, exist_ok=True)
        parsed_dir.mkdir(parents=True, exist_ok=True)
        (raw_dir / ".gitkeep").touch(exist_ok=True)
        (redacted_dir / ".gitkeep").touch(exist_ok=True)
        (parsed_dir / ".gitkeep").touch(exist_ok=True)

        commands = list(device.get("planned_commands") or build_read_only_commands(device))
        device_result = {
            "device_id": device.get("device_id"),
            "name": device.get("name"),
            "host": host,
            "port": port,
            "connection_source": conn.get("source", "default"),
            "override_applied": conn.get("override_applied", False),
            "status": "pending",
            "commands_executed_count": 0,
            "redaction_applied": False,
            "sensitive_findings_count": 0,
            "errors": [],
        }

        try:
            ssh = ssh_client_class()
            if hasattr(ssh, "set_missing_host_key_policy"):
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            username = os.getenv("COMPLIANCE_SSH_USERNAME")
            password = os.getenv("COMPLIANCE_SSH_PASSWORD")
            ssh.connect(
                hostname=host,
                port=int(port),
                username=username,
                password=password,
                timeout=int(env.get("timeout", 10)),
                banner_timeout=int(env.get("timeout", 10)),
                auth_timeout=int(env.get("timeout", 10)),
                look_for_keys=False,
                allow_agent=False,
            )
            if username or password:
                device_result["password_logged"] = False
                device_result["password_saved"] = False
            shell = ssh.invoke_shell()
            if hasattr(shell, "settimeout"):
                shell.settimeout(int(env.get("timeout", 10)))
            _read_shell_prompt(shell, int(env.get("timeout", 10)))
            _run_shell_command(shell, "screen-length 0 temporary", int(env.get("timeout", 10)))
            for command in commands:
                safe_name = sanitize_command_filename(command)
                raw_text = _run_shell_command(shell, command, int(env.get("timeout", 10)))
                raw_file = raw_dir / f"{safe_name}.txt"
                raw_file.write_text(raw_text, encoding="utf-8")
                redaction_result = redact_file(raw_file, redacted_dir / f"{safe_name}.txt")
                findings = scan_sensitive_findings(raw_text)
                _dump_json(
                    raw_dir / f"{safe_name}.meta.json",
                    {
                        "command": command,
                        "device_id": device.get("device_id"),
                        "host": host,
                        "executed_at": _now(),
                        "stdout_bytes": len(raw_text.encode("utf-8")),
                        "stderr_bytes": 0,
                        "redaction_applied": True,
                        "sensitive_findings_count": len(findings),
                        "redacted_file": str(redacted_dir / f"{safe_name}.txt"),
                    },
                )
                _dump_json(
                    redacted_dir / f"{safe_name}.meta.json",
                    {
                        "command": command,
                        "device_id": device.get("device_id"),
                        "host": host,
                        "executed_at": _now(),
                        "redaction_applied": True,
                        "sensitive_findings_count": redaction_result["sensitive_findings_count"],
                        "raw_file": str(raw_file),
                    },
                )
                commands_executed_count += 1
                device_result["commands_executed_count"] += 1
                device_result["redaction_applied"] = True
                device_result["sensitive_findings_count"] += int(redaction_result["sensitive_findings_count"])
            if hasattr(shell, "close"):
                shell.close()
            if hasattr(ssh, "close"):
                ssh.close()
            device_result["status"] = "completed"
            completed_devices += 1
        except Exception as exc:
            any_errors = True
            device_result["status"] = "failed"
            device_result["errors"].append(_normalize_exception(exc))
            try:
                if "shell" in locals() and hasattr(shell, "close"):
                    shell.close()
                if "ssh" in locals() and hasattr(ssh, "close"):
                    ssh.close()
            except Exception:
                pass

        all_device_results.append(device_result)

    if any_errors:
        status = SSH_COLLECTION_COMPLETED_WITH_ERRORS if completed_devices > 0 else SSH_COLLECTION_FAILED
    else:
        status = SSH_COLLECTION_COMPLETED
    result_payload = {
        "job_id": job_id,
        "status": status,
        "decision": status,
        "operator": operator,
        "simulation_only": False,
        "device_connection_started": True,
        "netbox_write": False,
        "sync_called": False,
        "approval_record_created": False,
        "apply_plan_created": False,
        "commands_executed_count": commands_executed_count,
        "forbidden_commands_executed": False,
        "config_mode_entered": False,
        "password_logged": False,
        "password_saved": False,
        "redaction_applied": True,
        "devices": all_device_results,
        "checked_at": _now(),
        "issues": command_issues,
    }
    _dump_json(results_dir / "ssh-collection-result.json", result_payload)
    (results_dir / "SSH-COLLECTION-RESULT.md").write_text(
        "\n".join(
            [
                "# SSH-COLLECTION-RESULT",
                "",
                f"## Job ID\n`{job_id}`",
                "",
                f"## Status\n`{status}`",
                "",
                f"## Commands Executed\n{commands_executed_count}",
                "",
                "## Safety",
                "- forbidden_commands_executed=false",
                "- config_mode_entered=false",
                "- netbox_write=false",
                "- sync_called=false",
                "- password_logged=false",
                "- password_saved=false",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    try:
        create_parser_staging(job_id, jobs_base)
    except Exception:
        pass

    manifest_path = results_dir / "parser-manifest.json"
    markdown_path = results_dir / "PARSER-STAGING.md"
    if not manifest_path.exists():
        parser_devices: list[dict[str, Any]] = []
        for device in devices:
            device_id = str(device.get("device_id") or device.get("id") or "unknown")
            device_dir = results_dir / "devices" / device_id
            raw_dir = device_dir / "raw"
            redacted_dir = device_dir / "redacted"
            parsed_dir = device_dir / "parsed"
            parser_devices.append(
                {
                    "device_id": device.get("device_id"),
                    "name": device.get("name"),
                    "profile": (device.get("collection_profile") or {}).get("profile_id") or device.get("profile_id") or "default-readonly",
                    "raw_files": sorted(str(path) for path in raw_dir.glob("*") if path.is_file() and path.name != ".gitkeep"),
                    "redacted_files": sorted(str(path) for path in redacted_dir.glob("*") if path.is_file() and path.name != ".gitkeep"),
                    "parsed_files": sorted(str(path) for path in parsed_dir.glob("*") if path.is_file() and path.name != ".gitkeep"),
                    "parsed_dir": str(parsed_dir),
                    "ready_for_parsing": any(path.is_file() and path.name != ".gitkeep" for path in redacted_dir.glob("*")),
                }
            )
        fallback_manifest = {
            "job_id": job_id,
            "generated_at": _now(),
            "devices": parser_devices,
            "safety": {
                "raw_not_displayed_in_ui": True,
                "redaction_available": True,
                "netbox_write": False,
            },
        }
        _dump_json(manifest_path, fallback_manifest)
        markdown_lines = [
            "# PARSER-STAGING",
            "",
            f"## Job ID\n`{job_id}`",
            "",
            "## Devices",
        ]
        if not parser_devices:
            markdown_lines.append("- none")
        for device in parser_devices:
            markdown_lines.extend(
                [
                    "",
                    f"### {device.get('name')}",
                    f"- device_id: {device.get('device_id')}",
                    f"- profile: {device.get('profile')}",
                    f"- ready_for_parsing: {device.get('ready_for_parsing')}",
                    f"- raw_files: {len(device.get('raw_files') or [])}",
                    f"- redacted_files: {len(device.get('redacted_files') or [])}",
                    f"- parsed_files: {len(device.get('parsed_files') or [])}",
                ]
            )
        markdown_lines.extend(
            [
                "",
                "## Safety",
                "- raw_not_displayed_in_ui=true",
                "- redaction_available=true",
                "- netbox_write=false",
            ]
        )
        markdown_path.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")

    return {
        "job_id": job_id,
        "status": status,
        "decision": status,
        "files": {
            "ssh_collection_result": str(results_dir / "ssh-collection-result.json"),
            "ssh_collection_result_markdown": str(results_dir / "SSH-COLLECTION-RESULT.md"),
        },
        "ssh_collection_result": result_payload,
    }
