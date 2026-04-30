#!/usr/bin/env python3
"""FASE 4.40 — Cycle-002 Week 2 Preparation (v2)."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tools.local.controlled_cycle_week1_common import classify_record, detect_secret_hits
from webui.services.controlled_operation import load_json_safe


def _safe_item_id(object_key: str) -> str:
    base = re.sub(r"[^A-Za-z0-9]+", "-", object_key).strip("-")
    return base or "item"


def _load_validation(validation_file: Path) -> Dict[str, Any]:
    if not validation_file.exists():
        return {}
    return load_json_safe(validation_file)


def _select_review_items(validation: Dict[str, Any]) -> List[Dict[str, Any]]:
    items = []
    for row in validation.get("ready_for_week2_review", []):
        items.append({
            "object_type": row.get("object_type", ""),
            "object_key": row.get("object_key", ""),
            "team": row.get("team", ""),
            "updated_by": row.get("updated_by", ""),
            "updated_at": row.get("updated_at", ""),
            "evidence": row.get("evidence", ""),
            "notes": row.get("notes", ""),
        })
    for row in validation.get("validated", []):
        items.append({
            "object_type": row.get("object_type", ""),
            "object_key": row.get("object_key", ""),
            "team": row.get("team", ""),
            "updated_by": row.get("updated_by", ""),
            "updated_at": row.get("updated_at", ""),
            "evidence": row.get("evidence", ""),
            "notes": row.get("notes", ""),
        })
    return items


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="FASE 4.40 — Cycle-002 Week 2 Preparation v2")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--cycle-dir", type=Path, required=True)
    parser.add_argument("--week1-validation", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    scope_file = args.cycle_dir / "CYCLE-002-SCOPE.json"
    status_file = args.cycle_dir / "CYCLE-002-STATUS.md"
    week1_status_file = args.cycle_dir / "week1" / "CYCLE-002-WEEK1-STATUS.md"
    week2_dir = args.output_dir
    validation = _load_validation(args.week1_validation)
    ready_items = _select_review_items(validation)
    validation_summary = validation.get("summary", {})

    blockers: List[str] = []
    if not scope_file.exists():
        blockers.append("scope missing")
    if not args.week1_validation.exists():
        blockers.append("week1 validation missing")
    if validation and validation.get("decision") == "WEEK1_VALIDATION_BLOCKED":
        blockers.append("week1 validation blocked")
    if not ready_items:
        blockers.append("no ready items")
    if detect_secret_hits(args.cycle_dir):
        blockers.append("sensitive content found")

    if blockers:
        decision = "WEEK2_PREPARATION_BLOCKED"
        status_value = "WEEK2_PREPARATION_BLOCKED"
    else:
        if any(int(validation_summary.get(key, 0)) > 0 for key in ("still_pending", "needs_clarification", "blocked", "rejected")):
            decision = "WEEK2_PREPARATION_READY_WITH_RESTRICTIONS"
        else:
            decision = "WEEK2_PREPARATION_READY"
        status_value = decision

    week2_dir.mkdir(parents=True, exist_ok=True)
    drafts_dir = week2_dir / "approval-drafts"
    drafts_dir.mkdir(exist_ok=True)

    timestamp = datetime.now(timezone.utc).isoformat()
    plan_md = f"""# {args.cycle_id.upper()} — Week 2 Plan

## 1. Objective
Prepare human review for items validated in Week 1.

## 2. Scope
- Device: {args.device}
- Device ID: {args.device_id}
- Ready items: {len(ready_items)}
- Max items: {load_json_safe(scope_file).get('max_items', 3) if scope_file.exists() else 3}

## 3. Guardrails
- No NetBox write
- No ApplyPlan
- No ApprovalRecord official
- Manual review required

## 4. Next Step
{"Open review board." if not blockers else "Resolve blockers before review."}
"""
    board_lines = [
        f"# {args.cycle_id.upper()} — Week 2 Review Board",
        "",
        "## 1. Summary",
        f"- Ready items: {len(ready_items)}",
        f"- Validated: {int(validation_summary.get('validated', 0))}",
        f"- Pending: {int(validation_summary.get('still_pending', 0))}",
        f"- Needs clarification: {int(validation_summary.get('needs_clarification', 0))}",
        f"- Blocked: {int(validation_summary.get('blocked', 0))}",
        f"- Rejected: {int(validation_summary.get('rejected', 0))}",
        "",
        "## 2. Ready for Review",
        "",
        "| Object Type | Object Key | Team | Status | Draft |",
        "|---|---|---|---|---|",
    ]
    decisions_rows = [
        ["item_id", "device", "device_id", "object_type", "object_key", "responsible_team", "decision", "reviewer", "reviewed_at", "approval_record_allowed", "reason", "notes", "restriction"],
    ]
    for item in ready_items:
        safe_id = _safe_item_id(item["object_key"])
        draft_file = drafts_dir / f"approval-draft-{safe_id}.json"
        draft = {
            "draft_id": f"approval-draft-{safe_id}",
            "status": "draft_review",
            "device": args.device,
            "device_id": args.device_id,
            "object_type": item["object_type"],
            "object_key": item["object_key"],
            "responsible_team": item["team"],
            "action": "safe_create_staged",
            "category": item["team"] or item["object_type"],
            "created_at": timestamp,
            "allowed_to_promote": False,
            "restriction": "none",
            "evidence": item["evidence"],
            "owner": item["updated_by"],
            "notes": item["notes"],
            "safety": {
                "no_netbox_write": True,
                "no_apply_plan_created": True,
                "manual_review_required": True,
            },
        }
        _write_json(draft_file, draft)
        board_lines.append(
            f"| {item['object_type']} | {item['object_key']} | {item['team']} | ready_for_week2_review | {draft_file.name} |"
        )
        decisions_rows.append([
            safe_id,
            args.device,
            args.device_id,
            item["object_type"],
            item["object_key"],
            item["team"],
            "pending",
            "",
            "",
            "false",
            "",
            "",
            "none",
        ])

    if not ready_items:
        board_lines.append("| - | - | - | - | - |")

    board_lines.extend([
        "",
        "## 3. Not Eligible",
        "",
        "| Motivo | Próxima ação |",
        "|---|---|",
    ])
    if validation_summary.get("still_pending", 0):
        board_lines.append("| Still pending | Responder pendências restantes |")
    if validation_summary.get("needs_clarification", 0):
        board_lines.append("| Needs clarification | Pedir esclarecimento |")
    if validation_summary.get("blocked", 0):
        board_lines.append("| Blocked | Resolver bloqueio |")
    if validation_summary.get("rejected", 0):
        board_lines.append("| Rejected | Revisar e decidir |")
    if not any(validation_summary.get(key, 0) for key in ("still_pending", "needs_clarification", "blocked", "rejected")):
        board_lines.append("| - | - |")

    board_lines.extend([
        "",
        "## 4. Safety",
        "- No NetBox write",
        "- No ApplyPlan",
        "- No official ApprovalRecord",
        "- Manual review required",
    ])

    status_json = {
        "cycle_id": args.cycle_id,
        "device": args.device,
        "device_id": args.device_id,
        "status": status_value,
        "decision": decision,
        "generated_at": timestamp,
        "ready_items": ready_items,
        "summary": {
            "ready_items": len(ready_items),
            "validated": int(validation_summary.get("validated", 0)),
            "still_pending": int(validation_summary.get("still_pending", 0)),
            "needs_clarification": int(validation_summary.get("needs_clarification", 0)),
            "blocked": int(validation_summary.get("blocked", 0)),
            "rejected": int(validation_summary.get("rejected", 0)),
        },
        "blockers": blockers,
        "no_netbox_write": True,
        "no_apply_plan_created": True,
        "manual_review_required": True,
        "source_validation": str(args.week1_validation),
        "source_cycle_dir": str(args.cycle_dir),
    }

    _write_text(week2_dir / "CYCLE-002-WEEK2-PLAN.md", plan_md)
    _write_text(week2_dir / "CYCLE-002-WEEK2-REVIEW-BOARD.md", "\n".join(board_lines))
    with (week2_dir / "CYCLE-002-WEEK2-DECISIONS.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerows(decisions_rows)
    _write_text(week2_dir / "CYCLE-002-WEEK2-STATUS.md", "\n".join([
        f"# {args.cycle_id.upper()} — Week 2 Status",
        "",
        "## Status Atual",
        status_value,
        "",
        "## Summary",
        f"- Ready items: {len(ready_items)}",
        f"- Validated: {int(validation_summary.get('validated', 0))}",
        f"- Pending: {int(validation_summary.get('still_pending', 0))}",
        f"- Needs clarification: {int(validation_summary.get('needs_clarification', 0))}",
        f"- Blocked: {int(validation_summary.get('blocked', 0))}",
        f"- Rejected: {int(validation_summary.get('rejected', 0))}",
        "",
        "## Next Step",
        "Manual Week 2 review." if not blockers else "Resolve blockers first.",
    ]))
    _write_json(week2_dir / "CYCLE-002-WEEK2-STATUS.json", status_json)

    status_file.write_text(
        "\n".join([
            f"# {args.cycle_id.upper()} — Status do Ciclo",
            "",
            "## Status Atual",
            status_value,
            "",
            "## Gate",
            f"- Decision: {decision}",
            f"- Reason: Week 2 preparation evaluated",
            f"- Previous cycle: cycle-001",
            f"- Checked at: {timestamp}",
            "",
            "## Guardrails",
            f"- Validation: {'present' if args.week1_validation.exists() else 'missing'}",
            f"- Week 2 dir: present",
            f"- Drafts dir: present",
        ]),
        encoding="utf-8",
    )
    if week1_status_file.exists():
        week1_status_file.write_text(
            "\n".join([
                f"# {args.cycle_id.upper()} — Week 1 Status",
                "",
                "## Status Atual",
                "WEEK1_VALIDATION_PASSED_WITH_RESTRICTIONS" if int(validation_summary.get("still_pending", 0)) or int(validation_summary.get("needs_clarification", 0)) or int(validation_summary.get("blocked", 0)) or int(validation_summary.get("rejected", 0)) else "WEEK1_VALIDATION_PASSED",
                "",
                "## Summary",
                f"- Validated: {int(validation_summary.get('validated', 0))}",
                f"- Ready for Week 2 review: {len(ready_items)}",
                f"- Still pending: {int(validation_summary.get('still_pending', 0))}",
                f"- Needs clarification: {int(validation_summary.get('needs_clarification', 0))}",
                f"- Blocked: {int(validation_summary.get('blocked', 0))}",
                f"- Rejected: {int(validation_summary.get('rejected', 0))}",
            ]),
            encoding="utf-8",
        )

    print(f"✓ Week 2 preparation decision: {decision}")
    print(f"✓ Review board: {week2_dir / 'CYCLE-002-WEEK2-REVIEW-BOARD.md'}")
    print(f"✓ Decisions CSV: {week2_dir / 'CYCLE-002-WEEK2-DECISIONS.csv'}")
    print(f"✓ Drafts dir: {drafts_dir}")
    return 0 if decision != "WEEK2_PREPARATION_BLOCKED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
