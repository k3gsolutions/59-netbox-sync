# FASE 2.40.1 — Manual Approval Review Hardening

## Overview

**FASE 2.40.1** implements hardened manual review of proposed ApprovalRecords.

Hardening:
- ✅ All required safety_flags validated (5 flags, all must be true)
- ✅ state_history explicitly tracks manual_approval_reviewed + approved_for_dry_run_applyplan
- ✅ Secret scanning on payload (7 keywords)
- ✅ Evidence integrity (evidence_hash, proposed_payload)
- ✅ Metadata validation (object_type, object_key)

## Tool: review_proposed_approval_record.py

```bash
python3 tools/local/review_proposed_approval_record.py \
  --approval-record path/to/approval-record-uuid.json \
  --decision approve|reject|request_changes|defer|block \
  --reviewer "Name" \
  --reason "Justification" \
  --output-dir reports/pilot-device-compliance/approvals
```

## Validation (Hardened)

### Required safety_flags (ALL must be true)
- no_netbox_write = true
- no_apply_plan_created = true
- manual_review_required = true
- human_decision_required = true
- proposed_only = true

### Secret Keywords Blocked
- token, password, secret, api_key
- private key, bearer, authorization

### Required Fields
- reviewer (populated)
- object_type (populated)
- object_key (populated)
- evidence_hash (populated)
- proposed_payload (populated)

## Decisions

### Approve
- status=approved, state=approved
- approved_by, approved_at, approval_reason recorded
- state_history adds:
  1. manual_approval_reviewed
  2. approved_for_dry_run_applyplan

### Reject
- status=rejected, state=rejected
- state_history adds: rejected_by_manual_review

### Request Changes
- status=request_changes, state=changes_requested
- state_history adds: changes_requested_by_manual_review

### Defer
- status=deferred, state=deferred
- state_history adds: deferred_by_manual_review

### Block
- status=blocked, state=blocked
- state_history adds: blocked_by_manual_review

## Security

✓ No NetBox writes
✓ No ApplyPlan creation
✓ No automatic progression
✓ Full audit trail maintained
✓ All decisions local only
