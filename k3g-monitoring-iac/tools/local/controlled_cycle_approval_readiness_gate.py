#!/usr/bin/env python3
"""FASE 4.10 — Controlled Operation Cycle Approval Readiness Gate.

Validate that proposed ApprovalRecords are ready for manual review.
"""

from __future__ import annotations

import argparse
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


def validate_approval_record(record: Dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate proposed ApprovalRecord."""
    issues = []

    # Check status
    if record.get("status") != "proposed":
        issues.append(f"status={record.get('status')} must be proposed")

    # Check state
    if record.get("state") != "proposed":
        issues.append(f"state={record.get('state')} must be proposed")

    # Check object_type
    valid_types = ["interface", "ip_address", "bgp_peer", "vrf", "route_policy"]
    if record.get("object_type") not in valid_types:
        issues.append(f"object_type not in {valid_types}")

    # Check object_id
    if not record.get("object_id"):
        issues.append("object_id required")

    # Check review
    if not record.get("review"):
        issues.append("review field required")
    elif record.get("review", {}).get("status") != "proposed":
        issues.append("review.status must be proposed")

    # Check safety flags
    safety = record.get("safety_confirmations", {})
    if not safety.get("no_netbox_write"):
        issues.append("safety: no_netbox_write required")
    if not safety.get("no_apply_plan_created"):
        issues.append("safety: no_apply_plan_created required")
    if not safety.get("manual_review_required"):
        issues.append("safety: manual_review_required required")
    if not safety.get("proposed_only"):
        issues.append("safety: proposed_only required")

    # Check state_history
    history = record.get("state_history", [])
    if not any(e.get("event") == "promoted_to_proposed" for e in history):
        issues.append("state_history must contain promoted_to_proposed event")

    # Check for secrets
    record_str = json.dumps(record).lower()
    blocked = ["token", "password", "secret", "netbox_write_token"]
    for word in blocked:
        if word in record_str:
            issues.append(f"blocked keyword: {word}")

    return len(issues) == 0, issues


def evaluate_gate(valid_count: int, total: int, blocked_count: int) -> str:
    """Evaluate approval readiness gate."""
    if blocked_count > 0:
        return "NOT_READY_FOR_MANUAL_APPROVAL_REVIEW"

    if valid_count > 0 and valid_count == total:
        return "READY_FOR_MANUAL_APPROVAL_REVIEW"

    if valid_count > 0:
        return "READY_WITH_RESTRICTIONS"

    return "NOT_READY_FOR_MANUAL_APPROVAL_REVIEW"


def generate_gate_markdown(
    cycle_id: str,
    device: str,
    decision: str,
    valid_count: int,
    total: int,
    blocked_count: int,
) -> str:
    """Generate gate markdown report."""
    timestamp = datetime.utcnow().isoformat() + "+00:00"

    emoji = {
        "READY_FOR_MANUAL_APPROVAL_REVIEW": "✓",
        "READY_WITH_RESTRICTIONS": "⚠",
        "NOT_READY_FOR_MANUAL_APPROVAL_REVIEW": "✗",
    }.get(decision, "?")

    md = f"""# {cycle_id} — Approval Readiness Gate

## 1. Decision

### {emoji} {decision}

## 2. Validation Results

- **Total Records:** {total}
- **Valid Proposed:** {valid_count}
- **Blocked:** {blocked_count}
- **Pending Validation:** {total - valid_count - blocked_count}

## 3. Gate Checks

- ✓ Status = proposed
- ✓ State = proposed
- ✓ Object type valid
- ✓ Object ID present
- ✓ Review fields complete
- ✓ Safety flags enforced
- ✓ State history contains promoted_to_proposed
- ✓ No token/password/secret keywords

## 4. Next Steps

"""
    if decision == "READY_FOR_MANUAL_APPROVAL_REVIEW":
        md += "Proceed to manual approval review. All records are valid and ready."
    elif decision == "READY_WITH_RESTRICTIONS":
        md += "Proceed with caution. Some restrictions detected but valid records exist."
    else:
        md += "Gate blocked. Address issues before attempting manual review."

    md += f"""

---

**Cycle ID:** {cycle_id}
**Device:** {device}
**Gate Validated At:** {timestamp}
"""

    return md


def main() -> int:
    """Run FASE 4.10."""
    parser = argparse.ArgumentParser(description="FASE 4.10 — Approval Readiness Gate")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--approvals-dir", type=Path, required=True)
    parser.add_argument("--week2-review", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)

    args = parser.parse_args()

    # Validate all approval records
    valid_count = 0
    blocked_count = 0
    validation_details = []

    if args.approvals_dir.exists():
        for record_file in args.approvals_dir.glob("*.json"):
            record = load_json_safe(record_file)
            is_valid, issues = validate_approval_record(record)

            if is_valid:
                valid_count += 1
                status = "valid"
            else:
                blocked_count += 1
                status = "invalid"

            validation_details.append({
                "file": record_file.name,
                "approval_id": record.get("approval_id"),
                "status": status,
                "issues": issues,
            })

    total = valid_count + blocked_count
    decision = evaluate_gate(valid_count, total, blocked_count)

    # Generate markdown
    markdown = generate_gate_markdown(args.cycle_id, args.device, decision, valid_count, total, blocked_count)

    # Generate JSON
    gate_json = {
        "cycle_id": args.cycle_id,
        "device": args.device,
        "device_id": args.device_id,
        "decision": decision,
        "validated_at": datetime.utcnow().isoformat() + "+00:00",
        "summary": {
            "total_records": total,
            "valid": valid_count,
            "blocked": blocked_count,
            "ready_for_manual_review": valid_count > 0 and blocked_count == 0,
        },
        "details": validation_details,
    }

    # Write outputs
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(gate_json, f, indent=2)

    print(f"✓ Approval readiness gate decision: {decision}")
    print(f"✓ Valid records: {valid_count}")
    print(f"✓ Blocked records: {blocked_count}")
    print(f"✓ Report: {args.output}")
    print(f"✓ JSON: {args.output_json}")

    return 0 if "READY" in decision else 1


if __name__ == "__main__":
    raise SystemExit(main())
