#!/usr/bin/env python3
"""
Prepare Week 2 Review board and approval drafts.

Generate review board, decisions CSV, and draft ApprovalRecords.
Drafts remain in draft_review status until explicit promotion.

Zero NetBox writes, zero tokens.

Usage:
    python3 prepare_week2_review.py \
        --device <device_name> \
        --device-id <id> \
        --validation <path/to/validation.md> \
        --candidates <path/to/candidates.md> \
        --responses-dir <path/to/week1-responses> \
        --output-dir <path/to/week2-review>
"""

import argparse
import csv
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List


def parse_args():
    parser = argparse.ArgumentParser(
        description="Prepare Week 2 review and approval drafts"
    )
    parser.add_argument("--device", required=True, help="Device name")
    parser.add_argument("--device-id", required=True, type=int, help="Device ID")
    parser.add_argument("--validation", required=True, help="Validation MD file")
    parser.add_argument("--candidates", required=True, help="Candidates MD file")
    parser.add_argument("--responses-dir", required=True, help="Responses directory")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    return parser.parse_args()


def extract_items_from_validation(validation_file: str) -> Dict[str, List[Dict]]:
    """Extract validated items from validation MD file."""
    items = {
        "validated": [],
        "needs_clarification": [],
        "still_pending": [],
        "blocked": [],
    }

    with open(validation_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Parse sections
    sections = content.split("##")
    for section in sections:
        lines = section.split("\n")
        if not lines:
            continue

        section_title = lines[0].strip().lower()

        # Parse table rows
        in_table = False
        for line in lines[1:]:
            if "|" in line and "---" not in line:
                in_table = True
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 3 and parts[1]:
                    item = {
                        "object_key": parts[1] if len(parts) > 1 else "",
                        "type": parts[2] if len(parts) > 2 else "",
                        "team": parts[3] if len(parts) > 3 else "",
                    }
                    if item["object_key"]:
                        if "validated" in section_title:
                            items["validated"].append(item)
                        elif "clarif" in section_title:
                            items["needs_clarification"].append(item)
                        elif "pending" in section_title:
                            items["still_pending"].append(item)
                        elif "blocked" in section_title:
                            items["blocked"].append(item)

    return items


def create_review_board(device: str, items: Dict) -> str:
    """Generate Week 2 review board markdown."""
    timestamp = datetime.utcnow().isoformat() + "+00:00"

    board = f"""# Week 2 Review Board — {device}

**Generated:** {timestamp}
**Status:** Ready for human review

---

## 1. Summary

| Category | Count |
|----------|-------|
| Ready for review | {len(items['validated'])} |
| Needs clarification | {len(items['needs_clarification'])} |
| Still pending | {len(items['still_pending'])} |
| Blocked | {len(items['blocked'])} |
| **Total candidates** | **{len(items['validated']) + len(items['needs_clarification']) + len(items['still_pending']) + len(items['blocked'])}** |

---

## 2. Items Ready for Review

| Object Key | Type | Team | Draft | Status |
|------------|------|------|-------|--------|
"""

    for item in items["validated"]:
        board += f"| {item['object_key']} | {item['type']} | {item['team']} | approval-draft-{item['object_key'].replace('.', '-').replace('/', '-')}.json | draft_review |\n"

    board += f"""
---

## 3. Not Eligible for Review

| Object Key | Reason | Action |
|------------|--------|--------|
"""

    for item in items["needs_clarification"]:
        board += f"| {item['object_key']} | Missing fields | Return to team for clarification |\n"

    for item in items["still_pending"]:
        board += f"| {item['object_key']} | No response | Follow up with team |\n"

    for item in items["blocked"]:
        board += f"| {item['object_key']} | Blocked | Escalate |\n"

    board += """
---

## 4. Review Checklist

For each validated item, reviewer must verify:

- [x] Naming valid (no conflicts)
- [x] Tenant confirmed (known domain)
- [x] Service type valid (approved list)
- [x] Criticality defined (high/medium/low)
- [x] Owner identified
- [x] Evidence sufficient
- [x] Parent/interface/VRF coheent
- [x] Risk assessed (BAIXO/MÉDIO/ALTO)
- [x] Reviewer identified

---

## 5. Allowed Decisions

Fill week2-review-decisions.csv with decisions:

- **approve_for_approval_record** → Promote to ApprovalRecord (pending status)
- **request_changes** → Return for clarification
- **reject** → Not eligible for approval
- **defer** → Defer to later phase
- **block** → Blocked (cannot proceed)

---

## Next Steps

1. Review each item in section 2
2. Fill week2-review-decisions.csv with decision
3. Run promotion script to create ApprovalRecords
4. Verify promoted ApprovalRecords in approvals/pending

---

**Safety Confirmations:**

✅ No NetBox writes
✅ No ApplyPlan
✅ No apply execution
✅ No tokens
✅ Drafts remain draft_review status
✅ Manual review required

---

**Status:** Awaiting human review decisions
**Next:** Run promote_week2_drafts_to_approvals.py after decisions are complete
"""

    return board


def create_decisions_csv(device: str, device_id: int, items: Dict) -> str:
    """Generate decisions CSV template."""
    csv_content = "device,device_id,object_type,object_key,responsible_team,tenant,service_type,criticality,owner,reviewer,decision,reason,notes,reviewed_at,approval_record_allowed\n"

    for item in items["validated"]:
        csv_content += f'{device},{device_id},{item["type"]},{item["object_key"]},{item["team"]},,,,,,[DECISION],[reason],[notes],[datetime],\n'

    return csv_content


def create_approval_draft(device: str, device_id: int, object_key: str, object_type: str) -> Dict:
    """Create approval draft (not official ApprovalRecord yet)."""
    draft_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat() + "+00:00"

    draft = {
        "draft_id": draft_id,
        "status": "draft_review",
        "device": device,
        "device_id": device_id,
        "object_type": object_type,
        "object_key": object_key,
        "action": "safe_create_staged",
        "category": "service_candidate",
        "created_at": timestamp,
        "allowed_to_promote": False,
        "promotion_requirements": {
            "reviewer_required": True,
            "decision_required": True,
            "approval_record_allowed_required": True,
            "reviewed_at_required": True,
        },
        "warnings": [
            "This is a draft. Not an official ApprovalRecord.",
            "Can only be promoted with explicit human decision.",
            "Must complete: reviewer, decision, reviewed_at, approval_record_allowed=true",
        ],
        "safety": {
            "no_netbox_write": True,
            "no_apply_plan_created": True,
            "manual_review_required": True,
        },
    }

    return draft


def main():
    args = parse_args()

    # Extract items from validation
    items = extract_items_from_validation(args.validation)
    print(f"✓ Extracted items from validation")
    print(f"  Validated: {len(items['validated'])}")
    print(f"  Needs clarification: {len(items['needs_clarification'])}")
    print(f"  Still pending: {len(items['still_pending'])}")
    print(f"  Blocked: {len(items['blocked'])}")

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    drafts_dir = output_dir / "week2-approval-drafts"
    drafts_dir.mkdir(exist_ok=True)

    # Generate review board
    board = create_review_board(args.device, items)
    board_file = output_dir / "week2-review-board.md"
    with open(board_file, "w", encoding="utf-8") as f:
        f.write(board)
    print(f"✓ Review board saved: {board_file}")

    # Generate decisions CSV
    csv_content = create_decisions_csv(args.device, args.device_id, items)
    decisions_file = output_dir / "week2-review-decisions.csv"
    with open(decisions_file, "w", encoding="utf-8") as f:
        f.write(csv_content)
    print(f"✓ Decisions CSV saved: {decisions_file}")

    # Create approval drafts
    draft_count = 0
    for item in items["validated"]:
        draft = create_approval_draft(args.device, args.device_id, item["object_key"], item["type"])
        draft_file = drafts_dir / f"approval-draft-{item['object_key'].replace('.', '-').replace('/', '-')}.json"
        with open(draft_file, "w", encoding="utf-8") as f:
            json.dump(draft, f, indent=2)
        draft_count += 1

    print(f"✓ {draft_count} approval drafts created in {drafts_dir}")
    print(f"\n✅ Week 2 review preparation complete")
    print(f"\nNext steps:")
    print(f"  1. Review items in {board_file}")
    print(f"  2. Fill decisions in {decisions_file}")
    print(f"  3. Run: python3 promote_week2_drafts_to_approvals.py")


if __name__ == "__main__":
    main()
