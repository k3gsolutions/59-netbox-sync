#!/usr/bin/env python3
"""FASE 4.3 — Controlled Operation Cycle Week 1 Preparation.

Prepare Week 1 response collection structure and instructions.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def main() -> int:
    """Run FASE 4.3."""
    import argparse

    parser = argparse.ArgumentParser(description="FASE 4.3 — Controlled Operation Cycle Week 1 Prepare")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--cycle-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)

    args = parser.parse_args()

    timestamp = datetime.utcnow().isoformat() + "+00:00"

    # Create week1 directory structure
    week1_dir = args.output_dir
    week1_dir.mkdir(parents=True, exist_ok=True)

    (week1_dir / "responses").mkdir(exist_ok=True)

    # WEEK1 PLAN
    plan = f"""# {args.cycle_id.upper()} — Week 1 Response Collection

## 1. Objective

Collect operational metadata for controlled operation cycle via Web UI.

## 2. Timeline

**Start:** {timestamp}
**Target Completion:** 7 days from start
**Gate:** All responses validated and ready for Week 2 review

## 3. Teams & Fields

### Service Team
- Subinterface tenant
- Service type
- Criticality level
- Business owner
- Service notes

### Network Ops
- Interface VRF mapping
- IP address assignment
- Network role
- Backup status

### BGP Team
- BGP peer remote ASN
- Peer group
- Policy intent
- Criticality for service

## 4. Response Process

### Via Web UI (Primary)

1. Navigate to `/controlled-operation/cycle-001/week1`
2. Click "Add Response"
3. Fill fields for your team
4. Save locally (no NetBox write)
5. System generates CSV + audit JSON
6. Validation runs automatically

### Fields Per Item

```json
{{
  "item_id": "object_id",
  "object_type": "interface|ip_address|bgp_peer",
  "team": "service|network_ops|bgp",
  "response": {{}},
  "validation_status": "pending|valid|invalid",
  "validated_at": null,
  "reviewed_by": null,
  "notes": ""
}}
```

## 5. Validation Rules

- No token exposure
- No secrets in responses
- Required fields per team
- Naming convention compliance
- No duplicate responses

## 6. Restrictions

- ✓ Web UI local-only saves
- ✓ No NetBox writes during Week 1
- ✓ Manual review before any approval
- ✓ One response per item per team
- ✓ Response immutable after validation

## 7. Next Steps

1. Teams access Web UI
2. Fill responses for assigned items
3. Validation runs
4. Collect feedback
5. Gate to Week 2 when all valid

---

**Cycle ID:** {args.cycle_id}
**Device:** {args.device}
**Created:** {timestamp}
"""

    # WEEK1 CHECKLIST
    checklist = f"""# {args.cycle_id.upper()} — Week 1 Checklist

## Pre-Week 1

- [ ] Teams identified
- [ ] Assignments made
- [ ] Web UI access confirmed
- [ ] Cycle-001 visible in Web UI

## Week 1 Response Collection

### Service Team
- [ ] Subinterfaces tenant collected
- [ ] Service type filled
- [ ] Criticality assigned
- [ ] Business owner documented

### Network Ops
- [ ] Interface VRF mapping complete
- [ ] IP addresses assigned
- [ ] Network roles documented

### BGP Team
- [ ] BGP peer ASN collected
- [ ] Peer groups assigned
- [ ] Policy intent documented

## Week 1 Validation

- [ ] All responses submitted
- [ ] Validation runs without errors
- [ ] No secrets found
- [ ] Naming conventions checked
- [ ] CSV generated
- [ ] Audit JSON generated

## Week 1 Gate

- [ ] All items have valid responses
- [ ] No blocking issues
- [ ] Ready for Week 2 review
- [ ] Signed off

---

**Week 1 for:** {args.cycle_id}
**Device:** {args.device}
"""

    # WEEK1 STATUS
    status = {
        "cycle_id": args.cycle_id,
        "device": args.device,
        "device_id": args.device_id,
        "week": 1,
        "status": "WEEK1_READY_FOR_RESPONSES",
        "created_at": timestamp,
        "responses": {
            "total_needed": 0,
            "submitted": 0,
            "valid": 0,
            "invalid": 0,
        },
        "teams": {
            "service": {"status": "pending", "assigned": 0, "responses": 0},
            "network_ops": {"status": "pending", "assigned": 0, "responses": 0},
            "bgp": {"status": "pending", "assigned": 0, "responses": 0},
        },
        "gates": {
            "all_responses_submitted": False,
            "all_responses_valid": False,
            "ready_for_week2": False,
        },
        "events": [
            {
                "timestamp": timestamp,
                "event": "WEEK1_PREPARED",
                "status": "WEEK1_READY_FOR_RESPONSES",
            }
        ],
    }

    # Write files
    plan_file = week1_dir / f"{args.cycle_id.upper()}-WEEK1-PLAN.md"
    plan_file.write_text(plan, encoding="utf-8")

    checklist_file = week1_dir / f"{args.cycle_id.upper()}-WEEK1-CHECKLIST.md"
    checklist_file.write_text(checklist, encoding="utf-8")

    status_file = week1_dir / f"{args.cycle_id.upper()}-WEEK1-STATUS.json"
    with open(status_file, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2)

    print(f"✓ Week 1 prepared for {args.cycle_id}")
    print(f"✓ Plan: {plan_file}")
    print(f"✓ Checklist: {checklist_file}")
    print(f"✓ Status: {status_file}")
    print(f"✓ Responses dir: {week1_dir / 'responses'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
