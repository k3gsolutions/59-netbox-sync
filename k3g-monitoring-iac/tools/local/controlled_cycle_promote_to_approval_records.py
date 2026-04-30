#!/usr/bin/env python3
"""FASE 4.9 — Controlled Operation Cycle Promote Drafts to Proposed ApprovalRecords.

Promote Week 2 approved drafts to official proposed/pending ApprovalRecords.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def load_json_safe(file_path: Path) -> Dict[str, Any]:
    """Load JSON file safely."""
    if not file_path.exists():
        return {}

    try:
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def compute_sha256(data: str) -> str:
    """Compute SHA256 hash."""
    return hashlib.sha256(data.encode()).hexdigest()


def promote_draft(
    cycle_id: str,
    draft: Dict[str, Any],
    decision: Dict[str, str],
) -> Dict[str, Any]:
    """Create proposed ApprovalRecord from draft."""
    timestamp = datetime.utcnow().isoformat() + "+00:00"

    approval_record = {
        "approval_id": f"{cycle_id}-{decision.get('item_id', 'unknown')}".replace(" ", "_").lower(),
        "cycle_id": cycle_id,
        "object_type": decision.get("object_type", "unknown"),
        "object_id": decision.get("item_id", "unknown"),
        "status": "proposed",
        "state": "proposed",
        "created_at": timestamp,
        "review": {
            "status": "proposed",
            "reviewed_by": decision.get("reviewed_by"),
            "reviewed_at": decision.get("reviewed_at"),
            "evidence_reference": decision.get("evidence_reference", ""),
            "notes": decision.get("notes", ""),
        },
        "source": {
            "week2_review": True,
            "source_draft": draft.get("approval_id", ""),
            "source_decision_csv": True,
        },
        "evidence_hash": compute_sha256(json.dumps(draft, sort_keys=True)),
        "safety_confirmations": {
            "no_netbox_write": True,
            "no_apply_plan_created": True,
            "manual_review_required": True,
            "human_decision_required": True,
            "proposed_only": True,
            "no_automatic_approval": True,
        },
        "state_history": [
            {
                "status": "proposed",
                "timestamp": timestamp,
                "event": "cycle_week2_reviewed",
            },
            {
                "status": "proposed",
                "timestamp": timestamp,
                "event": "promoted_to_proposed",
                "by": decision.get("reviewed_by"),
            },
        ],
    }

    return approval_record


def main() -> int:
    """Run FASE 4.9."""
    parser = argparse.ArgumentParser(description="FASE 4.9 — Promote Drafts to Proposed ApprovalRecords")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--week2-review", type=Path, required=True)
    parser.add_argument("--drafts-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)

    args = parser.parse_args()

    # Load review
    review_data = load_json_safe(args.week2_review)
    decisions = review_data.get("decisions", [])

    # Promote approved decisions
    promoted_count = 0
    promotion_details = []

    args.output_dir.mkdir(parents=True, exist_ok=True)

    for decision in decisions:
        if decision.get("decision") != "approve_for_approval_record":
            continue

        if not decision.get("reviewed_by"):
            continue

        if decision.get("approval_record_allowed", "").lower() != "true":
            continue

        # Find corresponding draft
        item_id = decision.get("item_id", "unknown")
        draft_file = args.drafts_dir / f"draft-{item_id}.json"

        if not draft_file.exists():
            draft_file = list(args.drafts_dir.glob("*.json"))[0] if args.drafts_dir.glob("*.json") else None

        if not draft_file:
            promotion_details.append({
                "item_id": item_id,
                "status": "error",
                "reason": "draft not found",
            })
            continue

        draft = load_json_safe(draft_file)

        # Create proposed ApprovalRecord
        approval_record = promote_draft(args.cycle_id, draft, decision)

        # Write approval record
        approval_file = args.output_dir / f"{approval_record['approval_id']}.json"
        with open(approval_file, "w", encoding="utf-8") as f:
            json.dump(approval_record, f, indent=2)

        promoted_count += 1
        promotion_details.append({
            "item_id": item_id,
            "approval_id": approval_record["approval_id"],
            "status": "promoted",
            "file": approval_file.name,
        })

    # Generate report
    timestamp = datetime.utcnow().isoformat() + "+00:00"

    report_md = f"""# {args.cycle_id} — Proposed ApprovalRecords Promotion

## 1. Summary

- **Total Approved:** {promoted_count}
- **All Proposed Status:** proposed
- **All State:** proposed
- **No Automatic Approval:** true
- **Manual Review Required:** true

## 2. Promoted Records

"""
    for detail in promotion_details:
        if detail["status"] == "promoted":
            report_md += f"- **{detail['item_id']}** → {detail['approval_id']} (proposed)\n"
        else:
            report_md += f"- **{detail['item_id']}** → ERROR: {detail['reason']}\n"

    report_md += f"""

## 3. Safety Confirmations

- ✓ No NetBox writes
- ✓ No ApplyPlan created
- ✓ Manual review required
- ✓ Human decision required
- ✓ Proposed status only (not approved)
- ✓ No automatic approval

## 4. Next Steps

1. Review proposed ApprovalRecords in Web UI
2. Manual approval gate will validate
3. No automatic progression to approved state

---

**Cycle ID:** {args.cycle_id}
**Device:** {args.device}
**Promoted At:** {timestamp}
"""

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report_md, encoding="utf-8")

    print(f"✓ Promoted {promoted_count} drafts to proposed ApprovalRecords")
    print(f"✓ Location: {args.output_dir}")
    print(f"✓ Report: {args.report}")

    return 0 if promoted_count > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
