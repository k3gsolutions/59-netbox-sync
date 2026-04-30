#!/usr/bin/env python3
"""FASE 4.43 - Cycle-002 Approval Readiness Gate."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def safe_text(value: Any) -> str:
    return str(value or "").strip()


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def has_secret(value: str) -> bool:
    lowered = value.lower()
    blocked = ["netbox_write_token", "authorization: token", "token=", "password=", "secret=", "private key", "bearer"]
    return any(term in lowered for term in blocked)


def validate_record(record: Dict[str, Any]) -> tuple[bool, List[str]]:
    issues: List[str] = []
    if safe_text(record.get("cycle_id")) != "cycle-002":
        issues.append("cycle_id must be cycle-002")
    if safe_text(record.get("status")) != "proposed":
        issues.append("status must be proposed")
    if safe_text(record.get("state")) != "proposed":
        issues.append("state must be proposed")
    if not safe_text(record.get("object_type")):
        issues.append("object_type required")
    if not safe_text(record.get("object_key")):
        issues.append("object_key required")
    if not record.get("proposed_payload"):
        issues.append("proposed_payload required")
    review = record.get("review") or {}
    if not safe_text(review.get("reviewed_by")):
        issues.append("reviewer required")
    if not safe_text(review.get("reviewed_at")):
        issues.append("reviewed_at required")
    if not safe_text(record.get("evidence_hash")):
        issues.append("evidence_hash required")
    flags = record.get("safety_confirmations") or record.get("safety") or {}
    for key in ["no_netbox_write", "no_apply_plan_created", "manual_review_required", "human_decision_required", "proposed_only"]:
        if not flags.get(key):
            issues.append(f"safety flag missing: {key}")
    history = record.get("state_history") or []
    if not any(safe_text(item.get("event")) == "promoted_to_proposed" for item in history):
        issues.append("state_history missing promoted_to_proposed")
    text = json.dumps(record, sort_keys=True).lower()
    if any(term in text for term in ["netbox_write_token", "authorization: token", "token", "password", "secret", "private key", "bearer"]):
        issues.append("secret keyword found")
    return len(issues) == 0, issues


def main() -> int:
    parser = argparse.ArgumentParser(description="FASE 4.43 — Cycle-002 Approval Readiness Gate")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--approvals-dir", type=Path, required=True)
    parser.add_argument("--week2-review", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()

    cycle_dir = args.approvals_dir.parents[1] if len(args.approvals_dir.parents) > 1 else args.approvals_dir.parent
    scope = load_json(cycle_dir / f"{args.cycle_id.upper()}-SCOPE.json")
    review = load_json(args.week2_review)

    records = []
    issues: List[Dict[str, Any]] = []
    if args.approvals_dir.exists():
        for path in sorted(args.approvals_dir.glob("*.json")):
            record = load_json(path)
            valid, record_issues = validate_record(record)
            records.append({"file": path.name, "approval_id": record.get("approval_id", path.stem), "valid": valid, "issues": record_issues})
            if not valid:
                issues.append({"file": path.name, "issues": record_issues})

    if not args.approvals_dir.exists():
        decision = "NOT_READY_FOR_MANUAL_APPROVAL_REVIEW"
    elif not records:
        decision = "NOT_READY_FOR_MANUAL_APPROVAL_REVIEW"
    elif any(item["issues"] for item in records):
        decision = "NOT_READY_FOR_MANUAL_APPROVAL_REVIEW"
    elif not any(item["valid"] for item in records):
        decision = "NOT_READY_FOR_MANUAL_APPROVAL_REVIEW"
    elif scope and int(scope.get("max_items") or 0) > 3:
        decision = "NOT_READY_FOR_MANUAL_APPROVAL_REVIEW"
        issues.append({"scope": ["max_items must be <= 3"]})
    elif len(records) > 0 and any(item["valid"] for item in records) and len(records) == sum(1 for item in records if item["valid"]):
        decision = "READY_FOR_MANUAL_APPROVAL_REVIEW"
    elif len(records) > 0 and any(item["valid"] for item in records):
        decision = "READY_WITH_RESTRICTIONS"
    else:
        decision = "NOT_READY_FOR_MANUAL_APPROVAL_REVIEW"

    if review and not review.get("items") and not review.get("decisions"):
        decision = "NOT_READY_FOR_MANUAL_APPROVAL_REVIEW"

    report_lines = [
        f"# {args.cycle_id.upper()} — Approval Readiness Gate",
        "",
        f"## Decision: {decision}",
        "",
        f"- total records: {len(records)}",
        f"- valid: {sum(1 for item in records if item['valid'])}",
        f"- invalid: {sum(1 for item in records if not item['valid'])}",
        f"- max_items: {scope.get('max_items', 'unknown') if scope else 'unknown'}",
        "- POST-only",
        "",
        "## Records",
    ]
    report_lines.extend([f"- {item['file']}: {'valid' if item['valid'] else 'invalid'}" for item in records] or ["- none"])
    report_lines.extend(["", "## Issues"])
    if issues:
        report_lines.extend([f"- {item}" for item in issues])
    else:
        report_lines.append("- none")
    report_lines.extend([
        "",
        "## Safety",
        "- No NetBox write",
        "- No ApplyPlan",
        "- No token",
    ])
    report = "\n".join(report_lines)

    payload = {
        "cycle_id": args.cycle_id,
        "device": args.device,
        "device_id": args.device_id,
        "decision": decision,
        "validated_at": datetime.utcnow().isoformat() + "+00:00",
        "summary": {
            "total": len(records),
            "valid": sum(1 for item in records if item["valid"]),
            "invalid": sum(1 for item in records if not item["valid"]),
            "max_items": scope.get("max_items") if scope else None,
        },
        "records": records,
        "week2_review_exists": args.week2_review.exists(),
        "no_netbox_write": True,
        "no_apply_plan_created": True,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    cycle_status = cycle_dir / f"{args.cycle_id.upper()}-STATUS.md"
    cycle_status.write_text(f"# {args.cycle_id.upper()}\n\nStatus: {decision}\n", encoding="utf-8")

    print(f"✓ Approval readiness gate decision: {decision}")
    print(f"✓ Report: {args.output}")
    print(f"✓ JSON: {args.output_json}")
    return 0 if decision.startswith("READY") else 1


if __name__ == "__main__":
    raise SystemExit(main())
