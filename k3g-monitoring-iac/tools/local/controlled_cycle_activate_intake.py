#!/usr/bin/env python3
"""FASE 4.34 — Controlled Operation Cycle Intake Activation."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from webui.services.controlled_operation import load_json_safe, scan_sensitive_terms


def _read_status_text(status_path: Path) -> str:
    if not status_path.exists():
        return ""
    try:
        return status_path.read_text(encoding="utf-8")
    except Exception:
        return ""


def main() -> int:
    parser = argparse.ArgumentParser(description="FASE 4.34 — Cycle Intake Activation")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--cycle-dir", type=Path, required=True)
    parser.add_argument("--start-gate", type=Path, required=True)
    parser.add_argument("--operation-index", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()

    scope_file = args.cycle_dir / f"{args.cycle_id.upper()}-SCOPE.json"
    status_file = args.cycle_dir / f"{args.cycle_id.upper()}-STATUS.md"
    blockers: list[str] = []

    start_gate = load_json_safe(args.start_gate) if args.start_gate.exists() else {}
    if not start_gate:
        blockers.append("start gate missing or unreadable")
    else:
        start_decision = str(start_gate.get("decision") or "").strip()
        if start_decision == "CYCLE_START_BLOCKED":
            blockers.append("start gate blocked")
        elif start_decision not in {"CYCLE_START_READY", "CYCLE_START_READY_WITH_RESTRICTIONS"}:
            blockers.append(f"unexpected start gate decision: {start_decision}")

    if not args.operation_index.exists():
        blockers.append("operation index missing")
    if not args.cycle_dir.exists():
        blockers.append("cycle directory missing")
    if not scope_file.exists():
        blockers.append("scope file missing")
    if not status_file.exists():
        blockers.append("status file missing")

    scope = load_json_safe(scope_file) if scope_file.exists() else {}
    if scope:
        if str(scope.get("status") or "").strip() not in {"PLANNED_NOT_STARTED", "START_READY"}:
            blockers.append(f"status must be PLANNED_NOT_STARTED or START_READY, got {scope.get('status')}")
        if int(scope.get("max_items") or 0) > 3:
            blockers.append("max_items > 3")
        if [str(v).upper() for v in scope.get("allowed_methods", [])] != ["POST"]:
            blockers.append("allowed_methods must be POST only")
        forbidden_methods = {str(v).upper() for v in scope.get("forbidden_methods", [])}
        for method in ("PATCH", "DELETE"):
            if method not in forbidden_methods:
                blockers.append(f"{method} not forbidden")
        forbidden_targets = {str(v).lower() for v in scope.get("forbidden_targets", [])}
        for target in ("/sync", "equipment", "ssh", "netconf"):
            if target not in forbidden_targets:
                blockers.append(f"{target} not forbidden")
        for flag in (
            "requires_week1",
            "requires_week2",
            "requires_approval_records",
            "requires_applyplan_dryrun",
            "requires_real_write_authorization",
            "requires_post_write_verification",
        ):
            if not scope.get(flag):
                blockers.append(f"{flag} missing or false")
    else:
        blockers.append("scope unreadable")

    sensitive_hits = scan_sensitive_terms(args.cycle_dir)
    if sensitive_hits:
        blockers.append(f"sensitive content found: {', '.join(sensitive_hits[:3])}")

    start_decision = str(start_gate.get("decision") or "").strip()
    if blockers:
        decision = "CYCLE_INTAKE_ACTIVATION_BLOCKED"
        status_value = "INTAKE_BLOCKED"
        reason = "; ".join(blockers)
    elif start_decision == "CYCLE_START_READY_WITH_RESTRICTIONS":
        decision = "CYCLE_INTAKE_ACTIVATED_WITH_RESTRICTIONS"
        status_value = "INTAKE_ACTIVATED_WITH_RESTRICTIONS"
        reason = "start gate ready with restrictions"
    else:
        decision = "CYCLE_INTAKE_ACTIVATED"
        status_value = "INTAKE_ACTIVATED"
        reason = "start gate ready"

    now = datetime.now(timezone.utc).isoformat()
    report = f"""# {args.cycle_id.upper()} — Intake Activation

## 1. Decision

**{decision}**

## 2. Summary

- Cycle: {args.cycle_id}
- Device: {args.device}
- Device ID: {args.device_id}
- Status: {status_value}
- Reason: {reason}

## 3. Guardrails

- Start gate: {'present' if args.start_gate.exists() else 'missing'}
- Operation index: {'present' if args.operation_index.exists() else 'missing'}
- Scope: {'present' if scope_file.exists() else 'missing'}
- Max items: {scope.get('max_items', '?')}
- Allowed methods: {', '.join(scope.get('allowed_methods', []))}
- Forbidden methods: {', '.join(scope.get('forbidden_methods', []))}
- Forbidden targets: {', '.join(scope.get('forbidden_targets', []))}
- Sensitive hits: {len(sensitive_hits)}

## 4. Next Step

{('Proceed to Week 1 preparation.' if decision.startswith('CYCLE_INTAKE_ACTIVATED') else 'Resolve blockers before Week 1 preparation.')}

---

**Decision at:** {now}
"""

    output_json = {
        "cycle_id": args.cycle_id,
        "device": args.device,
        "device_id": args.device_id,
        "decision": decision,
        "status": status_value,
        "reason": reason,
        "decided_at": now,
        "start_gate": str(args.start_gate),
        "operation_index": str(args.operation_index),
        "scope": str(scope_file),
        "status_file": str(status_file),
        "sensitive_hits": sensitive_hits,
        "guardrails": {
            "max_items": int(scope.get("max_items") or 0),
            "allowed_methods": scope.get("allowed_methods", []),
            "forbidden_methods": scope.get("forbidden_methods", []),
            "forbidden_targets": scope.get("forbidden_targets", []),
            "requires_week1": bool(scope.get("requires_week1", False)),
            "requires_week2": bool(scope.get("requires_week2", False)),
            "requires_approval_records": bool(scope.get("requires_approval_records", False)),
            "requires_applyplan_dryrun": bool(scope.get("requires_applyplan_dryrun", False)),
            "requires_real_write_authorization": bool(scope.get("requires_real_write_authorization", False)),
            "requires_post_write_verification": bool(scope.get("requires_post_write_verification", False)),
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(output_json, indent=2), encoding="utf-8")

    status_markdown = [
        f"# {args.cycle_id.upper()} — Status do Ciclo",
        "",
        "## Status Atual",
        status_value,
        "",
        "## Gate",
        f"- Decision: {decision}",
        f"- Reason: {reason}",
        f"- Previous cycle: cycle-001",
        f"- Checked at: {now}",
        "",
        "## Guardrails",
        f"- Start gate: {'present' if args.start_gate.exists() else 'missing'}",
        f"- Operation index: {'present' if args.operation_index.exists() else 'missing'}",
        f"- Scope: {'present' if scope_file.exists() else 'missing'}",
        f"- Status template: {'present' if status_file.exists() else 'missing'}",
        f"- Sensitive hits: {len(sensitive_hits)}",
        "",
    ]
    status_file.write_text("\n".join(status_markdown), encoding="utf-8")

    print(f"✓ Intake activation decision: {decision}")
    print(f"✓ Report: {args.output}")
    print(f"✓ JSON: {args.output_json}")
    return 0 if decision != "CYCLE_INTAKE_ACTIVATION_BLOCKED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
