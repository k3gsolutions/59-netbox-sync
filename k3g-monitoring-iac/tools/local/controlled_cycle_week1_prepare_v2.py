#!/usr/bin/env python3
"""FASE 4.35 — Controlled Operation Cycle Week 1 Preparation (v2)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from webui.services.controlled_operation import load_json_safe, scan_sensitive_terms


def main() -> int:
    parser = argparse.ArgumentParser(description="FASE 4.35 — Cycle Week 1 Preparation")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--cycle-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    scope_file = args.cycle_dir / f"{args.cycle_id.upper()}-SCOPE.json"
    status_file = args.cycle_dir / f"{args.cycle_id.upper()}-STATUS.md"
    week1_dir = args.output_dir
    week1_dir.mkdir(parents=True, exist_ok=True)
    responses_dir = week1_dir / "responses"
    audit_dir = week1_dir / "audit"
    responses_dir.mkdir(exist_ok=True)
    audit_dir.mkdir(exist_ok=True)

    scope = load_json_safe(scope_file) if scope_file.exists() else {}
    blockers: list[str] = []
    if not scope_file.exists():
        blockers.append("scope file missing")
    if not status_file.exists():
        blockers.append("status file missing")
    status_text = status_file.read_text(encoding="utf-8") if status_file.exists() else ""
    if "INTAKE_ACTIVATED" not in status_text and "START_READY" not in status_text:
        blockers.append("cycle not activated")
    if scan_sensitive_terms(args.cycle_dir):
        blockers.append("sensitive content found in cycle directory")

    now = datetime.now(timezone.utc).isoformat()
    if blockers:
        decision = "WEEK1_PREPARATION_BLOCKED"
        status_value = "WEEK1_PREPARATION_BLOCKED"
        reason = "; ".join(blockers)
    else:
        decision = "WEEK1_READY_FOR_RESPONSES"
        status_value = "WEEK1_READY_FOR_RESPONSES"
        reason = "week1 structure ready"

    plan = f"""# {args.cycle_id.upper()} — Week 1 Plan

## 1. Objective
Collect responses locally for Cycle 002 Week 1.

## 2. Scope

- Device: {args.device}
- Device ID: {args.device_id}
- Max items: {scope.get('max_items', 3)}
- Allowed methods: {', '.join(scope.get('allowed_methods', []))}
- Forbidden methods: {', '.join(scope.get('forbidden_methods', []))}
- Forbidden targets: {', '.join(scope.get('forbidden_targets', []))}

## 3. Teams

- Service: subinterface response
- Network Ops: IP mapping response
- BGP: peer response

## 4. Response Rules

- Save locally only
- No NetBox write
- No apply
- No sync
- No retry automation
- No rollback automation

## 5. How to Respond

1. Open the Web UI or write a local response file.
2. Fill only the fields for your team.
3. Save response in `responses/`.
4. Validate locally.

## 6. Guardrails

- POST only
- PATCH forbidden
- DELETE forbidden
- /sync forbidden
- equipment forbidden
- ssh forbidden
- netconf forbidden

## 7. Next Step

{('Collect responses.' if not blockers else 'Fix blockers before collecting responses.')}

---

**Prepared at:** {now}
"""

    status_md = f"""# {args.cycle_id.upper()} — Week 1 Status

## Status Atual
{status_value}

## Summary

- Decision: {decision}
- Device: {args.device}
- Device ID: {args.device_id}
- Responses dir: present
- Audit dir: present
- Sensitive hits: {len(scan_sensitive_terms(args.cycle_dir))}

## Next Step

{('Pending responses.' if decision == 'WEEK1_READY_FOR_RESPONSES' else 'Resolve blockers first.')}
"""

    (week1_dir / f"{args.cycle_id.upper()}-WEEK1-PLAN.md").write_text(plan, encoding="utf-8")
    (week1_dir / f"{args.cycle_id.upper()}-WEEK1-STATUS.md").write_text(status_md, encoding="utf-8")

    status_file.write_text(
        "\n".join(
            [
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
                f"- Scope: {'present' if scope_file.exists() else 'missing'}",
                f"- Week 1 dir: present",
                f"- Responses dir: present",
                f"- Audit dir: present",
                "",
            ]
        ),
        encoding="utf-8",
    )

    print(f"✓ Week 1 preparation decision: {decision}")
    print(f"✓ Plan: {week1_dir / f'{args.cycle_id.upper()}-WEEK1-PLAN.md'}")
    print(f"✓ Status: {week1_dir / f'{args.cycle_id.upper()}-WEEK1-STATUS.md'}")
    return 0 if decision == "WEEK1_READY_FOR_RESPONSES" else 1


if __name__ == "__main__":
    raise SystemExit(main())
