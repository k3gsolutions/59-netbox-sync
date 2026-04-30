#!/usr/bin/env python3
"""FASE 4.31 — Controlled Cycle Start Gate."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from webui.services.controlled_operation import load_json_safe, scan_sensitive_terms


def main() -> int:
    parser = argparse.ArgumentParser(description="FASE 4.31 — Cycle Start Gate")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--previous-cycle", required=True)
    parser.add_argument("--cycle-dir", type=Path, required=True)
    parser.add_argument("--previous-handoff", type=Path, required=True)
    parser.add_argument("--operation-index", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()

    decision = "CYCLE_START_BLOCKED"
    reason = "Unprocessed"
    blockers: list[str] = []
    previous_decision = ""

    if not args.previous_handoff.exists():
        blockers.append("previous handoff missing")
    else:
        previous = load_json_safe(args.previous_handoff)
        previous_decision = str(previous.get("decision") or "").strip()
        if not previous_decision:
            blockers.append("previous handoff decision missing")
        elif "ACTION_REQUIRED" in previous_decision:
            blockers.append("previous cycle action required")
        elif "READY" in previous_decision:
            if "WITH_RESTRICTIONS" in previous_decision:
                decision = "CYCLE_START_READY_WITH_RESTRICTIONS"
                reason = "previous cycle completed with restrictions"
            else:
                decision = "CYCLE_START_READY"
                reason = "previous cycle ready for next operation"
        else:
            blockers.append(f"unsupported previous decision: {previous_decision}")

    if not args.operation_index.exists():
        blockers.append("operation index missing")

    if not args.cycle_dir.exists():
        blockers.append("cycle directory missing")

    scope_file = args.cycle_dir / f"{args.cycle_id.upper()}-SCOPE.json"
    status_file = args.cycle_dir / f"{args.cycle_id.upper()}-STATUS.md"
    if not scope_file.exists():
        blockers.append("scope file missing")
    if not status_file.exists():
        blockers.append("status file missing")

    scope = load_json_safe(scope_file) if scope_file.exists() else {}
    if scope:
        if str(scope.get("status") or "").strip() != "PLANNED_NOT_STARTED":
            blockers.append("status is not PLANNED_NOT_STARTED")
        if int(scope.get("max_items") or 0) > 3:
            blockers.append("max_items > 3")
        allowed_methods = [str(value).upper() for value in scope.get("allowed_methods", [])]
        forbidden_methods = [str(value).upper() for value in scope.get("forbidden_methods", [])]
        forbidden_targets = [str(value).lower() for value in scope.get("forbidden_targets", [])]
        if "POST" not in allowed_methods:
            blockers.append("POST not allowed")
        if "PATCH" not in forbidden_methods:
            blockers.append("PATCH not forbidden")
        if "DELETE" not in forbidden_methods:
            blockers.append("DELETE not forbidden")
        for target in ["/sync", "equipment", "ssh", "netconf"]:
            if target not in forbidden_targets:
                blockers.append(f"{target} not forbidden")
        for flag in [
            "requires_week1",
            "requires_week2",
            "requires_approval_records",
            "requires_applyplan_dryrun",
            "requires_real_write_authorization",
            "requires_post_write_verification",
        ]:
            if not scope.get(flag):
                blockers.append(f"{flag} false or missing")
    else:
        blockers.append("scope unreadable")

    sensitive_hits = scan_sensitive_terms(args.cycle_dir)
    if sensitive_hits:
        blockers.append(f"sensitive content found: {', '.join(sensitive_hits[:3])}")

    if blockers:
        decision = "CYCLE_START_BLOCKED"
        reason = "; ".join(blockers)

    now = datetime.now(timezone.utc).isoformat()
    result = {
        "cycle_id": args.cycle_id,
        "previous_cycle": args.previous_cycle,
        "decision": decision,
        "reason": reason,
        "decided_at": now,
        "checked_previous_handoff": str(args.previous_handoff),
        "checked_operation_index": str(args.operation_index),
        "checked_scope": str(scope_file),
        "checked_status": str(status_file),
        "sensitive_hits": sensitive_hits,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, indent=2), encoding="utf-8")

    status_markdown = [
        f"# {args.cycle_id.upper()} — Status do Ciclo",
        "",
        "## Status Atual",
        "START_READY" if decision.startswith("CYCLE_START_READY") else "START_BLOCKED",
        "",
        "## Gate",
        f"- Decision: {decision}",
        f"- Reason: {reason}",
        f"- Previous cycle: {args.previous_cycle}",
        f"- Checked at: {now}",
        "",
        "## Guardrails",
        f"- Previous handoff: {'present' if args.previous_handoff.exists() else 'missing'}",
        f"- Operation index: {'present' if args.operation_index.exists() else 'missing'}",
        f"- Scope: {'present' if scope_file.exists() else 'missing'}",
        f"- Status template: {'present' if status_file.exists() else 'missing'}",
        f"- Sensitive hits: {len(sensitive_hits)}",
        "",
    ]
    status_file.write_text("\n".join(status_markdown), encoding="utf-8")

    markdown = [
        f"# Cycle Start Gate — {args.cycle_id}",
        "",
        "## 1. Decision",
        f"**{decision}**",
        "",
        "## 2. Validations",
        f"- Previous cycle: {args.previous_cycle}",
        f"- Reason: {reason}",
        f"- Sensitive hits: {len(sensitive_hits)}",
        "",
        "## 3. Recommendation",
    ]
    if decision == "CYCLE_START_READY":
        markdown.append(f"Ready to start {args.cycle_id}.")
    elif decision == "CYCLE_START_READY_WITH_RESTRICTIONS":
        markdown.append(f"Ready to start {args.cycle_id} with restrictions from {args.previous_cycle}.")
    else:
        markdown.append(f"Blocked. Resolve issues before starting {args.cycle_id}.")
    markdown.extend(["", f"---", f"Decided at {now}", ""])
    args.output.write_text("\n".join(markdown), encoding="utf-8")

    print(f"✓ Start gate decision: {decision}")
    print(f"✓ Report: {args.output}")
    return 0 if decision != "CYCLE_START_BLOCKED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
