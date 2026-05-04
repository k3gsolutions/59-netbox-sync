"""Local remediation draft safety validation.

No NetBox writes. No device execution. No ApprovalRecord. No ApplyPlan.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .compliance_jobs import JOBS_BASE, load_compliance_job
from .compliance_remediation_drafts import load_remediation_drafts, summarize_remediation_drafts


REMEDIATION_DRAFTS_SAFE = "REMEDIATION_DRAFTS_SAFE"
REMEDIATION_DRAFTS_SAFE_WITH_WARNINGS = "REMEDIATION_DRAFTS_SAFE_WITH_WARNINGS"
REMEDIATION_DRAFTS_UNSAFE = "REMEDIATION_DRAFTS_UNSAFE"


FORBIDDEN_COMMAND_WORDS = [
    "system-view",
    "configure",
    "commit",
    "save",
    "delete",
    "undo",
    "shutdown",
    "reboot",
    "reset",
    "patch",
    "sync",
]

SECRET_WORDS = ["token", "password", "secret", "cipher"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dump_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _safe_job_dir(job_id: str, jobs_base: Optional[Path] = None) -> Path:
    return (jobs_base or JOBS_BASE) / job_id


def _remediation_drafts_dir(job_id: str, jobs_base: Optional[Path] = None) -> Path:
    return _safe_job_dir(job_id, jobs_base) / "remediation" / "drafts"


def _load_json(path: Path) -> dict[str, Any]:
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


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _contains_forbidden_command(text: str) -> list[str]:
    lower = text.lower()
    return [word for word in FORBIDDEN_COMMAND_WORDS if word in lower]


def _find_secret_markers(text: str) -> list[str]:
    lower = text.lower()
    return [word for word in SECRET_WORDS if word in lower]


def _collect_strings(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        result: list[str] = []
        for item in value.values():
            result.extend(_collect_strings(item))
        return result
    if isinstance(value, (list, tuple, set)):
        result: list[str] = []
        for item in value:
            result.extend(_collect_strings(item))
        return result
    return [str(value)]


def validate_remediation_drafts(job_id: str, jobs_base: Optional[Path] = None) -> dict[str, Any]:
    """Validate remediation draft artifacts and safety blocks."""
    job = load_compliance_job(job_id, jobs_base)
    job_dir = _safe_job_dir(job_id, jobs_base)
    drafts_dir = _remediation_drafts_dir(job_id, jobs_base)
    drafts_dir.mkdir(parents=True, exist_ok=True)
    drafts_payload = load_remediation_drafts(job_id, jobs_base)
    drafts = list(drafts_payload.get("drafts") or [])

    issues: list[str] = []
    warnings: list[str] = []
    checks = {
        "drafts_file_exists": (drafts_dir / "remediation-drafts.json").exists(),
        "no_write_allowed": all(draft.get("write_allowed") is False for draft in drafts),
        "no_execution_allowed": all(draft.get("execution_allowed") is False for draft in drafts),
        "no_requires_apply_plan": all(draft.get("requires_apply_plan") is False for draft in drafts),
        "approval_record_absent": not any(job_dir.glob("**/approval-record.json")),
        "apply_plan_absent": not any(job_dir.glob("**/apply-plan.json")),
        "safety_flags_present": all(
            isinstance(draft.get("safety"), dict)
            and {"netbox_write", "device_write", "sync_called", "approval_record_created", "apply_plan_created"}
            <= set(draft.get("safety").keys())
            for draft in drafts
        ),
    }

    if not checks["drafts_file_exists"]:
        issues.append("remediation-drafts.json missing")

    if not drafts:
        issues.append("no remediation drafts found")

    if not checks["no_write_allowed"]:
        issues.append("write_allowed=true found")
    if not checks["no_execution_allowed"]:
        issues.append("execution_allowed=true found")
    if not checks["no_requires_apply_plan"]:
        issues.append("requires_apply_plan=true found")
    if not checks["approval_record_absent"]:
        issues.append("approval record exists")
    if not checks["apply_plan_absent"]:
        issues.append("apply plan exists")
    if not checks["safety_flags_present"]:
        issues.append("safety flags missing")

    for draft in drafts:
        proposed_change = draft.get("proposed_change") or {}
        command_preview = _safe_text(proposed_change.get("command_preview")).strip()
        for word in _contains_forbidden_command(command_preview):
            issues.append(f"forbidden command keyword found in command_preview: {word}")

        combined_text = " ".join(_collect_strings(proposed_change))
        secret_markers = _find_secret_markers(combined_text)
        for marker in secret_markers:
            issues.append(f"secret marker found in proposed_change: {marker}")

        if draft.get("risk_level") == "high":
            warnings.append(f"{draft.get('draft_id')} high risk")

    decision = REMEDIATION_DRAFTS_SAFE
    if issues:
        decision = REMEDIATION_DRAFTS_UNSAFE
    elif warnings:
        decision = REMEDIATION_DRAFTS_SAFE_WITH_WARNINGS

    summary = summarize_remediation_drafts(job_id, jobs_base)
    payload = {
        "job_id": job_id,
        "checked_at": _now(),
        "decision": decision,
        "status": decision,
        "draft_count": len(drafts),
        "checks": checks,
        "warnings": warnings,
        "issues": issues,
        "summary": summary,
        "safety": {
            "netbox_write": False,
            "device_write": False,
            "sync_called": False,
            "approval_record_created": False,
            "apply_plan_created": False,
        },
    }

    validation_json = drafts_dir / "remediation-draft-validation.json"
    validation_md = drafts_dir / "REMEDIATION-DRAFT-VALIDATION.md"
    _dump_json(validation_json, payload)
    validation_md.write_text(
        "\n".join(
            [
                "# REMEDIATION-DRAFT-VALIDATION",
                "",
                f"## Job ID\n`{job_id}`",
                "",
                f"## Decision\n`{decision}`",
                "",
                "## Checks",
                *[f"- {key}: {value}" for key, value in checks.items()],
                "",
                "## Warnings",
                *([f"- {warning}" for warning in warnings] or ["- none"]),
                "",
                "## Issues",
                *([f"- {issue}" for issue in issues] or ["- none"]),
                "",
                "## Safety",
                "- no NetBox write",
                "- no device write",
                "- no /sync",
                "- no ApprovalRecord",
                "- no ApplyPlan",
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
            "remediation_draft_validation": str(validation_json),
            "remediation_draft_validation_markdown": str(validation_md),
        },
        "remediation_draft_validation": payload,
    }
