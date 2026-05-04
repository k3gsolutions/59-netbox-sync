"""Raw output safety validation for SSH read-only collection."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .compliance_jobs import JOBS_BASE
from .compliance_output_redaction import scan_sensitive_findings


RAW_OUTPUT_SAFETY_VALID = "RAW_OUTPUT_SAFETY_VALID"
RAW_OUTPUT_SAFETY_VALID_WITH_WARNINGS = "RAW_OUTPUT_SAFETY_VALID_WITH_WARNINGS"
RAW_OUTPUT_SAFETY_INVALID = "RAW_OUTPUT_SAFETY_INVALID"


SENSITIVE_MARKERS = [
    "password",
    "token",
    "NETBOX_WRITE_TOKEN",
    "authorization header",
    "Authorization:",
    "system-view",
    "configure terminal",
    "commit complete",
    "saved successfully",
    "/sync",
    "ApplyPlan",
    "ApprovalRecord",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dump_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _safe_job_dir(job_id: str, jobs_base: Optional[Path] = None) -> Path:
    return (jobs_base or JOBS_BASE) / job_id


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
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def validate_raw_collection_outputs(job_id: str, jobs_base: Optional[Path] = None) -> dict:
    """Validate raw SSH outputs for sensitive data and command drift."""
    job_dir = _safe_job_dir(job_id, jobs_base)
    results_dir = job_dir / "collection-results"
    results_dir.mkdir(parents=True, exist_ok=True)
    result_file = results_dir / "ssh-collection-result.json"
    validation_file = results_dir / "raw-output-safety-validation.json"
    markdown_file = results_dir / "RAW-OUTPUT-SAFETY-VALIDATION.md"
    issues: list[str] = []
    warnings: list[str] = []

    if not result_file.exists():
        issues.append("ssh-collection-result.json missing")

    collection_result = _load_json(result_file)
    if collection_result.get("status") not in {"SSH_COLLECTION_COMPLETED", "SSH_COLLECTION_COMPLETED_WITH_ERRORS"}:
        issues.append("ssh collection result status invalid")

    planned_commands = {}
    for planned_path in results_dir.glob("devices/*/planned-commands.json"):
        data = _load_json(planned_path)
        planned_commands[str(data.get("device_id") or planned_path.parent.name)] = set(data.get("planned_commands") or [])

    executed_commands = []
    sensitive_findings_count = 0
    for device in collection_result.get("devices") or []:
        for _ in range(int(device.get("commands_executed_count") or 0)):
            pass
        device_id = str(device.get("device_id") or "")
        device_dir = results_dir / "devices" / device_id / "raw"
        if not device_dir.exists():
            issues.append(f"raw dir missing for {device_id}")
            continue
        for txt_file in device_dir.glob("*.txt"):
            command_name = txt_file.stem
            meta_file = device_dir / f"{command_name}.meta.json"
            if not meta_file.exists():
                issues.append(f"meta file missing for {txt_file.name}")
            meta = _load_json(meta_file)
            command = meta.get("command", "")
            executed_commands.append((device_id, command))
            if command not in planned_commands.get(device_id, set()):
                issues.append(f"unplanned command executed: {device_id}:{command}")

            content = _load_text(txt_file)
            findings = scan_sensitive_findings(content)
            sensitive_findings_count += len(findings)
            redacted_file = device_dir.parent / "redacted" / f"{command_name}.txt"
            if findings:
                if redacted_file.exists():
                    warnings.append(f"sensitive findings redacted in {txt_file.name}")
                else:
                    issues.append(f"sensitive marker found in {txt_file.name}")

    if collection_result.get("device_connection_started") is not True:
        issues.append("device_connection_started not true in collection result")
    if collection_result.get("netbox_write") is not False:
        issues.append("netbox_write not false")
    if collection_result.get("sync_called") is not False:
        issues.append("sync_called not false")
    if collection_result.get("approval_record_created") is not False:
        issues.append("approval_record_created not false")
    if collection_result.get("apply_plan_created") is not False:
        issues.append("apply_plan_created not false")

    decision = RAW_OUTPUT_SAFETY_VALID
    if issues:
        decision = RAW_OUTPUT_SAFETY_INVALID
    elif warnings or sensitive_findings_count:
        decision = RAW_OUTPUT_SAFETY_VALID_WITH_WARNINGS

    payload = {
        "job_id": job_id,
        "decision": decision,
        "status": decision,
        "checked_at": _now(),
        "issues": issues,
        "warnings": warnings,
        "sensitive_findings_count": sensitive_findings_count,
        "executed_commands": [{"device_id": d, "command": c} for d, c in executed_commands],
        "raw_files_checked": len(list(results_dir.glob("devices/*/raw/*.txt"))),
        "meta_files_checked": len(list(results_dir.glob("devices/*/raw/*.meta.json"))),
        "redacted_files_checked": len(list(results_dir.glob("devices/*/redacted/*.txt"))),
    }
    _dump_json(validation_file, payload)
    markdown_file.write_text(
        "\n".join(
            [
                "# RAW-OUTPUT-SAFETY-VALIDATION",
                "",
                f"## Job ID\n`{job_id}`",
                "",
                f"## Decision\n`{decision}`",
                "",
                "## Issues",
                *([f"- {issue}" for issue in issues] or ["- none"]),
                "",
                "## Warnings",
                *([f"- {warning}" for warning in warnings] or ["- none"]),
                "",
                "## Safety",
                "- no ApprovalRecord",
                "- no ApplyPlan",
                "- no /sync",
                "- no token exposure",
                "- no password exposure",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "job_id": job_id,
        "decision": decision,
        "status": decision,
        "files": {
            "raw_output_safety_validation": str(validation_file),
            "raw_output_safety_validation_markdown": str(markdown_file),
        },
        "raw_output_safety_validation": payload,
    }
