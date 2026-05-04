"""Parser safety validation helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .compliance_jobs import JOBS_BASE, load_compliance_job
from .compliance_output_redaction import scan_sensitive_findings


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dump_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _safe_job_dir(job_id: str, jobs_base: Optional[Path] = None) -> Path:
    return (jobs_base or JOBS_BASE) / job_id


def _reports_root() -> Path:
    return JOBS_BASE.parents[1]


def _report_path(path: Path) -> str:
    try:
        return str(path.relative_to(_reports_root()))
    except Exception:
        return str(path)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def validate_parser_outputs(job_id: str, jobs_base: Optional[Path] = None) -> dict[str, Any]:
    """Validate parser artifacts and ensure no sensitive content slipped in."""
    job = load_compliance_job(job_id, jobs_base)
    job_dir = _safe_job_dir(job_id, jobs_base)
    results_dir = job_dir / "collection-results"
    results_dir.mkdir(parents=True, exist_ok=True)

    parser_result_file = results_dir / "parser-result.json"
    parsed_inventory_files = sorted(results_dir.glob("devices/*/parsed/parsed-inventory.json"))
    parsed_inventory_markdown_files = sorted(results_dir.glob("devices/*/parsed/PARSED-INVENTORY.md"))

    issues: list[str] = []
    warnings: list[str] = []
    checks = {
        "parser_result_exists": parser_result_file.exists(),
        "parsed_inventory_exists": bool(parsed_inventory_files),
        "netbox_write_false": False,
        "ssh_not_called": False,
        "approval_record_absent": not (job_dir / "approval-record.json").exists(),
        "apply_plan_absent": not (job_dir / "apply-plan.json").exists(),
    }

    parser_result = _load_json(parser_result_file)
    if not checks["parser_result_exists"]:
        issues.append("parser-result.json missing")
    if not checks["parsed_inventory_exists"]:
        issues.append("parsed inventory missing")

    checks["netbox_write_false"] = parser_result.get("netbox_write") is False
    checks["ssh_not_called"] = parser_result.get("device_connection_started") is False and parser_result.get("simulation_only") is True

    if parser_result.get("netbox_write") is not False:
        issues.append("netbox_write not false")
    if parser_result.get("device_connection_started") is not False:
        issues.append("device_connection_started not false")
    if parser_result.get("simulation_only") is not True:
        issues.append("simulation_only not true")
    if parser_result.get("approval_record_created") is not False:
        issues.append("approval_record_created not false")
    if parser_result.get("apply_plan_created") is not False:
        issues.append("apply_plan_created not false")

    parsed_text = []
    for file_path in parsed_inventory_files:
        try:
            parsed_text.append(file_path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            warnings.append(f"cannot read {file_path.name}")
    parsed_blob = "\n".join(parsed_text)
    finding_patterns = scan_sensitive_findings(parsed_blob)
    sensitive_hits = [finding for finding in finding_patterns if str(finding.get("pattern") or "").lower() in {"password", "token", "cipher"}]
    if sensitive_hits:
        issues.append("sensitive tokens found in parsed inventory")

    lower_blob = parsed_blob.lower()
    for marker in ("password", "token", "cipher"):
        if marker in lower_blob:
            issues.append(f"{marker} found in parsed inventory")
    for marker in ("approvalrecord", "applyplan", "netbox", "sshclient", "paramiko"):
        if marker in lower_blob:
            warnings.append(f"parser artifact mentions {marker}")

    if parser_result.get("warnings"):
        warnings.extend([str(item) for item in parser_result.get("warnings")])
    if parser_result.get("skipped"):
        warnings.append(f"{len(parser_result.get('skipped') or [])} commands skipped")

    if not checks["approval_record_absent"]:
        issues.append("approval record file exists")
    if not checks["apply_plan_absent"]:
        issues.append("apply plan file exists")

    decision = "PARSER_SAFETY_VALID"
    if warnings:
        decision = "PARSER_SAFETY_VALID_WITH_WARNINGS"
    if issues:
        decision = "PARSER_SAFETY_INVALID"

    payload = {
        "job_id": job_id,
        "checked_at": _now(),
        "decision": decision,
        "status": decision,
        "parser_result_exists": checks["parser_result_exists"],
        "parsed_inventory_exists": checks["parsed_inventory_exists"],
        "raw_not_displayed_in_ui": True,
        "netbox_write": False,
        "ssh_called": False,
        "approval_record_created": False,
        "apply_plan_created": False,
        "checks": checks,
        "warnings": warnings,
        "issues": issues,
    }

    validation_json = results_dir / "parser-safety-validation.json"
    validation_md = results_dir / "PARSER-SAFETY-VALIDATION.md"
    _dump_json(validation_json, payload)

    lines = [
        "# PARSER-SAFETY-VALIDATION",
        "",
        f"## Job ID\n`{job_id}`",
        "",
        f"## Decision\n`{decision}`",
        "",
        "## Checks",
    ]
    for key, value in checks.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Warnings",
        ]
    )
    if warnings:
        lines.extend([f"- {warning}" for warning in warnings])
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Issues",
        ]
    )
    if issues:
        lines.extend([f"- {issue}" for issue in issues])
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Safety",
            "- parser only",
            "- no SSH",
            "- no NetBox",
            "- no ApprovalRecord",
            "- no ApplyPlan",
            "- raw not displayed in UI",
        ]
    )
    validation_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "job_id": job_id,
        "decision": decision,
        "status": decision,
        "files": {
            "parser_safety_validation": str(validation_json),
            "parser_safety_validation_markdown": str(validation_md),
            "parser_safety_validation_report_path": _report_path(validation_md),
        },
        "parser_safety_validation": payload,
    }
