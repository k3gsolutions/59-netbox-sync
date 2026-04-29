# FASE 2.41.1 — Dry-Run ApplyPlan Readiness Gate Hardening

## Overview

**FASE 2.41.1** validates approved ApprovalRecords are ready for dry-run ApplyPlan.

Hardening:
- ✅ Policy baseline validation (REQUIRED)
- ✅ state_history validates approved_for_dry_run_applyplan (BLOCKER if missing)
- ✅ All safety_flags validated (5 flags, all must be true)
- ✅ Approved metadata validation (approved_by, approved_at, approval_reason)
- ✅ Secret scanning on payload

## Tool: dryrun_applyplan_readiness_gate.py

```bash
python3 tools/local/dryrun_applyplan_readiness_gate.py \
  --device "4WNET-MNS-KTG-RX" \
  --device-id 1890 \
  --approved-dir reports/pilot-device-compliance/approvals/approved \
  --policy-baseline reports/pilot-device-compliance/compliance-policy-impact-baseline.md \
  --output reports/pilot-device-compliance/approvals/DRYRUN-APPLYPLAN-READINESS-GATE.md
```

## Validation (Hardened)

### Per Approved Record
- status=approved (required)
- approved_by (required)
- approved_at (required)
- approval_reason (required)
- evidence_hash (required)
- proposed_payload (required)
- object_type, object_key (required)

### Safety Flags (ALL must be true)
- no_netbox_write = true
- no_apply_plan_created = true
- manual_review_required = true
- human_decision_required = true
- proposed_only = true

### state_history (CRITICAL HARDENING)
- MUST contain: manual_approval_reviewed
- MUST contain: approved_for_dry_run_applyplan (BLOCKER if missing)

### Policy Baseline (REQUIRED)
- File must exist
- Must contain decision marker:
  - POLICY_BASELINE_OK → BASELINE_OK
  - POLICY_BASELINE_WITH_WARNINGS → BASELINE_WITH_WARNINGS
  - POLICY_BASELINE_BLOCKED → BASELINE_BLOCKED

## Decisions

### READY_FOR_DRYRUN_APPLYPLAN
- ≥1 eligible approved records
- All records pass hardened validation
- Policy baseline = BASELINE_OK

### READY_WITH_RESTRICTIONS
- ≥1 eligible approved records
- All records pass hardened validation
- Policy baseline = BASELINE_WITH_WARNINGS

### NOT_READY_FOR_DRYRUN_APPLYPLAN
- 0 eligible approved records, OR
- Policy baseline = BASELINE_BLOCKED or missing

## Security

✓ No NetBox writes
✓ No ApplyPlan creation
✓ Read-only validation only
✓ Full audit trail maintained
✓ Policy baseline mandatory
