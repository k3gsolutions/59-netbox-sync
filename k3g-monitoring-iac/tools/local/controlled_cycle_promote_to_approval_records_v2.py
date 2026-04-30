#!/usr/bin/env python3
"""FASE 4.42 - Cycle-002 Promote Drafts to Proposed ApprovalRecords."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def safe_text(value: Any) -> str:
    return str(value or "").strip()


def truthy(value: Any) -> bool:
    return safe_text(value).lower() in {"true", "1", "yes", "y"}


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def sanitize_item_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", safe_text(value))


def draft_path(drafts_dir: Path, item_id: str) -> Path:
    return drafts_dir / f"approval-draft-{sanitize_item_id(item_id)}.json"


def sha256_dict(payload: Dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def build_record(cycle_id: str, device: str, device_id: str, row: Dict[str, str], draft: Dict[str, Any], week2_review: Dict[str, Any], decisions_csv_name: str) -> Dict[str, Any]:
    now = datetime.utcnow().isoformat() + "+00:00"
    item_id = safe_text(row.get("item_id") or row.get("object_key"))
    approval_id = f"{cycle_id}-{sanitize_item_id(item_id)}-{uuid.uuid4().hex[:8]}"
    reviewer = safe_text(row.get("reviewer"))
    reviewed_at = safe_text(row.get("reviewed_at"))
    proposed_payload = {
        "cycle_id": cycle_id,
        "device": device,
        "device_id": device_id,
        "team": safe_text(row.get("responsible_team")),
        "object_type": safe_text(row.get("object_type")),
        "object_key": safe_text(row.get("object_key")),
        "action": draft.get("action", "safe_create_staged"),
        "category": draft.get("category", safe_text(row.get("responsible_team"))),
    }
    draft_hash = sha256_dict(draft)
    return {
        "approval_id": approval_id,
        "approval_record_id": approval_id,
        "cycle_id": cycle_id,
        "device": device,
        "device_id": device_id,
        "object_type": safe_text(row.get("object_type")),
        "object_key": safe_text(row.get("object_key")),
        "object_id": item_id,
        "status": "proposed",
        "state": "proposed",
        "created_at": now,
        "source_week2_review": str(week2_review.get("path") or week2_review.get("file") or "cycle-002-week2-human-review.json"),
        "source_draft": draft.get("draft_id") or draft.get("approval_id") or "",
        "source_decision_csv": decisions_csv_name,
        "proposal": {
            "object_key": safe_text(row.get("object_key")),
            "object_type": safe_text(row.get("object_type")),
            "category": draft.get("category", safe_text(row.get("responsible_team"))),
            "preferred_next_step": "Revisar manualmente",
        },
        "proposed_payload": proposed_payload,
        "evidence_hash": draft_hash,
        "review": {
            "status": "proposed",
            "reviewed_by": reviewer,
            "reviewed_at": reviewed_at,
            "decision": "approve_for_approval_record",
            "comment": safe_text(row.get("notes") or row.get("reason")),
            "changes_requested": [],
        },
        "audit": {
            "created_at": now,
            "updated_at": now,
            "created_by": reviewer,
            "source_week2_review": str(week2_review.get("path") or week2_review.get("file") or "cycle-002-week2-human-review.json"),
            "source_draft": draft.get("draft_id") or draft.get("approval_id") or "",
            "source_decision_csv": decisions_csv_name,
            "evidence_hash": draft_hash,
        },
        "safety_confirmations": {
            "no_netbox_write": True,
            "no_apply_plan_created": True,
            "manual_review_required": True,
            "human_decision_required": True,
            "proposed_only": True,
        },
        "state_history": [
            {
                "status": "draft_review",
                "timestamp": draft.get("created_at", now),
                "event": "cycle_week2_reviewed",
            },
            {
                "status": "proposed",
                "timestamp": now,
                "event": "promoted_to_proposed",
                "by": reviewer,
            },
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="FASE 4.42 — Promote Cycle-002 Drafts to Proposed ApprovalRecords")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--week2-review", type=Path, required=True)
    parser.add_argument("--drafts-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()

    review = load_json(args.week2_review)
    rows = review.get("items") or review.get("decisions") or []
    decisions_csv_name = Path(review.get("source_decisions_csv") or f"{args.cycle_id.upper()}-WEEK2-DECISIONS.csv").name

    promoted: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    args.output_dir.mkdir(parents=True, exist_ok=True)

    for row in rows:
        decision = safe_text(row.get("decision")).lower()
        item_id = safe_text(row.get("item_id") or row.get("object_key"))
        allowed = truthy(row.get("approval_record_allowed"))
        reviewer = safe_text(row.get("reviewer"))
        reviewed_at = safe_text(row.get("reviewed_at"))
        notes = safe_text(row.get("notes"))
        reason = safe_text(row.get("reason"))
        draft_file = draft_path(args.drafts_dir, item_id)

        if decision != "approve_for_approval_record" or not allowed or not reviewer or not reviewed_at or not (notes or reason):
            skipped.append({"item_id": item_id, "status": "not_promoted", "reason": "decision/reviewer/timestamp/allowance missing"})
            continue
        if not draft_file.exists():
            skipped.append({"item_id": item_id, "status": "not_promoted", "reason": f"draft missing: {draft_file.name}"})
            continue

        draft = load_json(draft_file)
        if not draft or safe_text(draft.get("status")) != "draft_review":
            skipped.append({"item_id": item_id, "status": "not_promoted", "reason": f"invalid draft: {draft_file.name}"})
            continue

        record = build_record(args.cycle_id, args.device, args.device_id, row, draft, review, decisions_csv_name)
        record_file = args.output_dir / f"approval-{sanitize_item_id(item_id)}.json"
        record_file.write_text(json.dumps(record, indent=2), encoding="utf-8")
        promoted.append({"item_id": item_id, "approval_id": record["approval_id"], "file": record_file.name})

    summary = {
        "cycle_id": args.cycle_id,
        "device": args.device,
        "device_id": args.device_id,
        "decision": "PROPOSED_APPROVALS_CREATED"
        if promoted and not skipped
        else "PROPOSED_APPROVALS_CREATED_WITH_RESTRICTIONS"
        if promoted
        else "NO_PROPOSED_APPROVALS_CREATED",
        "created_at": datetime.utcnow().isoformat() + "+00:00",
        "promoted": promoted,
        "skipped": skipped,
        "no_netbox_write": True,
        "no_apply_plan_created": True,
        "manual_review_required": True,
    }

    report_lines = [
        f"# {args.cycle_id.upper()} — Proposed ApprovalRecords",
        "",
        "## Resumo",
        f"- promovidos: {len(promoted)}",
        f"- não promovidos: {len(skipped)}",
        "- status: proposed/pending only",
        "",
        "## Promovidos",
    ]
    if promoted:
        for item in promoted:
            report_lines.append(f"- {item['item_id']} → {item['approval_id']} ({item['file']})")
    else:
        report_lines.append("- nenhum")
    report_lines += ["", "## Não promovidos"]
    if skipped:
        for item in skipped:
            report_lines.append(f"- {item['item_id']}: {item['reason']}")
    else:
        report_lines.append("- nenhum")
    report_lines += [
        "",
        "## Segurança",
        "- Nenhuma escrita NetBox",
        "- Nenhum ApplyPlan",
        "- Nenhum ApprovalRecord aprovado",
        "- Revisão humana obrigatória",
    ]

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(report_lines), encoding="utf-8")
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"✓ Proposed approvals created: {len(promoted)}")
    print(f"✓ Report: {args.report}")
    print(f"✓ JSON: {args.output_json}")
    return 0 if promoted else 1


if __name__ == "__main__":
    raise SystemExit(main())
