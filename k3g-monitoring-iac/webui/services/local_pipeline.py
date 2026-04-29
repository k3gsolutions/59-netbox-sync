"""Local-safe pipeline helpers for Week 1 response intake."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional


ROOT = Path(__file__).resolve().parents[2]
REPORTS_ROOT = ROOT / "reports" / "pilot-device-compliance"
RESPONSES_DIR = REPORTS_ROOT / "week1-responses"
OUTREACH_DIR = REPORTS_ROOT / "outreach"
WEEK2_REVIEW_DIR = REPORTS_ROOT / "week2-review"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _run_script(args: list[str]) -> Dict[str, object]:
    proc = subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "success": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def _summary_paths() -> Dict[str, Path]:
    return {
        "validation": REPORTS_ROOT / "week1-response-validation.md",
        "snapshot": OUTREACH_DIR / "execution" / "outreach-status-snapshot.md",
        "intake": REPORTS_ROOT / "week1-response-intake-report.md",
        "gate": REPORTS_ROOT / "week2-activation-gate.md",
        "week2_review": WEEK2_REVIEW_DIR / "week2-review-board.md",
    }


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def parse_week1_validation_summary(report_path: Optional[Path] = None) -> Dict[str, int | str]:
    path = report_path or _summary_paths()["validation"]
    summary = {
        "total": 0,
        "validated": 0,
        "ready_for_review": 0,
        "still_pending": 0,
        "needs_clarification": 0,
        "blocked": 0,
        "rejected": 0,
    }

    if not path.exists():
        return summary

    content = path.read_text(encoding="utf-8")
    patterns = {
        "validated": r"\|\s*Validated\s*\|\s*(\d+)\s*\|",
        "ready_for_review": r"\|\s*Ready for Review\s*\|\s*(\d+)\s*\|",
        "still_pending": r"\|\s*Still Pending\s*\|\s*(\d+)\s*\|",
        "needs_clarification": r"\|\s*Needs Clarification\s*\|\s*(\d+)\s*\|",
        "blocked": r"\|\s*Blocked\s*\|\s*(\d+)\s*\|",
        "rejected": r"\|\s*Rejected\s*\|\s*(\d+)\s*\|",
        "total": r"\|\s*\*\*TOTAL\*\*\s*\|\s*\*\*(\d+)\*\*\s*\|",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            summary[key] = int(match.group(1))

    if summary["ready_for_review"] == 0:
        summary["ready_for_review"] = int(summary["validated"])
    if summary["total"] == 0:
        summary["total"] = int(
            summary["validated"]
            + summary["still_pending"]
            + summary["needs_clarification"]
            + summary["blocked"]
            + summary["rejected"]
        )
    return summary


def run_week1_validation(device: str) -> Dict[str, object]:
    paths = _summary_paths()
    _ensure_parent(paths["validation"])
    result = _run_script(
        [
            "tools/local/validate_week1_responses.py",
            "--template",
            str(REPORTS_ROOT / "week1-metadata-collection-template.csv"),
            "--responses-dir",
            str(RESPONSES_DIR),
            "--output",
            str(paths["validation"]),
            "--device",
            device,
        ]
    )
    result["report_path"] = str(paths["validation"])
    result["summary"] = parse_week1_validation_summary(paths["validation"])
    return result


def run_outreach_snapshot(device: str) -> Dict[str, object]:
    paths = _summary_paths()
    _ensure_parent(paths["snapshot"])
    result = _run_script(
        [
            "tools/local/track_week1_outreach_execution.py",
            "--device",
            device,
            "--outreach-dir",
            str(OUTREACH_DIR),
            "--responses-dir",
            str(RESPONSES_DIR),
            "--output",
            str(paths["snapshot"]),
            "--deadline",
            "2026-05-08",
            "--reminder-date",
            "2026-05-06",
        ]
    )
    result["report_path"] = str(paths["snapshot"])
    return result


def should_activate_week2(summary: Dict[str, int | str]) -> bool:
    return (
        int(summary.get("still_pending", 0)) == 0
        and int(summary.get("needs_clarification", 0)) == 0
        and int(summary.get("blocked", 0)) == 0
        and int(summary.get("rejected", 0)) == 0
        and (int(summary.get("validated", 0)) > 0 or int(summary.get("ready_for_review", 0)) > 0)
    )


def generate_intake_report(device: str, summary: Dict[str, int | str], gate: str, week2_prepared: bool, next_action: str) -> Path:
    path = REPORTS_ROOT / "week1-response-intake-report.md"
    _ensure_parent(path)
    content = f"""# Week 1 Response Intake Report — {device}

**Generated:** {_utc_now()}

## Summary

- Validated: {summary.get("validated", 0)}
- Ready for Review: {summary.get("ready_for_review", 0)}
- Still Pending: {summary.get("still_pending", 0)}
- Needs Clarification: {summary.get("needs_clarification", 0)}
- Blocked: {summary.get("blocked", 0)}
- Rejected: {summary.get("rejected", 0)}

## Gate

- Decision: {gate}
- Week 2 prepared: {'yes' if week2_prepared else 'no'}

## Next Action

{next_action}

## Safety

- No NetBox write
- No apply
- No /sync
- No ApprovalRecord auto-create
- No ApplyPlan auto-create
"""
    path.write_text(content, encoding="utf-8")
    return path


def generate_activation_gate(device: str, summary: Dict[str, int | str]) -> Dict[str, object]:
    path = _summary_paths()["gate"]
    _ensure_parent(path)
    if should_activate_week2(summary):
        gate = "GO_WEEK2_REVIEW"
        reason = "All required responses complete."
    elif int(summary.get("validated", 0)) > 0 or int(summary.get("ready_for_review", 0)) > 0:
        gate = "GO_WITH_RESTRICTIONS"
        reason = "Some responses are ready, but the set is not complete."
    else:
        gate = "NO_GO"
        reason = "No validated response ready."

    content = f"""# Week 2 Activation Gate — {device}

**Generated:** {_utc_now()}
**Decision:** {gate}

## Summary

- Validated: {summary.get("validated", 0)}
- Ready for Review: {summary.get("ready_for_review", 0)}
- Still Pending: {summary.get("still_pending", 0)}
- Needs Clarification: {summary.get("needs_clarification", 0)}
- Blocked: {summary.get("blocked", 0)}
- Rejected: {summary.get("rejected", 0)}

## Reason

{reason}

## Safety

- Local only
- No ApprovalRecord auto-create
- No ApplyPlan
- No NetBox writes
"""
    path.write_text(content, encoding="utf-8")
    return {"success": True, "gate": gate, "reason": reason, "path": str(path.relative_to(ROOT))}


def prepare_week2_if_ready(device: str, summary: Optional[Dict[str, int | str]] = None) -> Dict[str, object]:
    summary = summary or parse_week1_validation_summary()
    if not should_activate_week2(summary):
        return {
            "success": True,
            "week2_prepared": False,
            "next_action": f"Ainda existem {int(summary.get('still_pending', 0))} pendências. Continue preenchendo os itens restantes.",
        }

    _ensure_parent(WEEK2_REVIEW_DIR / "week2-review-board.md")
    result = _run_script(
        [
            "tools/local/prepare_week2_review.py",
            "--device",
            device,
            "--device-id",
            "1890",
            "--validation",
            str(_summary_paths()["validation"]),
            "--candidates",
            str(REPORTS_ROOT / "week2-review-candidates.md"),
            "--responses-dir",
            str(RESPONSES_DIR),
            "--output-dir",
            str(WEEK2_REVIEW_DIR),
        ]
    )
    result["week2_prepared"] = result["success"]
    result["next_action"] = "Week 2 review board gerado. Próximo passo: revisão humana." if result["success"] else "Falha ao preparar Week 2."
    return result


def run_safe_local_pipeline_after_response(device: str) -> Dict[str, object]:
    validation = run_week1_validation(device)
    snapshot = run_outreach_snapshot(device)
    summary = validation.get("summary", parse_week1_validation_summary())
    gate_info = generate_activation_gate(device, summary)
    week2 = prepare_week2_if_ready(device, summary)
    next_action = (
        week2.get("next_action")
        if week2.get("week2_prepared")
        else f"Ainda existem {int(summary.get('still_pending', 0))} pendências. Continue preenchendo os itens restantes."
    )
    intake_report = generate_intake_report(device, summary, gate_info["gate"], bool(week2.get("week2_prepared")), str(next_action))

    return {
        "success": bool(validation.get("success")) and bool(snapshot.get("success")),
        "validation": summary,
        "week2_gate": gate_info["gate"],
        "week2_prepared": bool(week2.get("week2_prepared")),
        "next_action": next_action,
        "validation_report": validation.get("report_path"),
        "snapshot_report": snapshot.get("report_path"),
        "activation_gate": gate_info.get("path"),
        "intake_report": str(intake_report.relative_to(ROOT)),
    }
