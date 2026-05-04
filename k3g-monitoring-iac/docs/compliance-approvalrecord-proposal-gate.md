# Compliance ApprovalRecord Proposal Gate (FASE COMPLIANCE-APPROVAL-004)

## Overview

Validates approval candidates and gates to ApprovalRecord proposal. This gate does NOT create ApprovalRecords — it only signals readiness for the next phase.

**Regra máxima:** gate evaluation only, no NetBox writes, no SSH/SNMP/NETCONF, no ApprovalRecord or ApplyPlan creation.

## Service Function

### `evaluate_approvalrecord_proposal_gate(job_id, operator, confirm_human_reviewed=False, jobs_base=None) → dict`

Evaluate gate to ApprovalRecord proposal.

**Pre-conditions:**
1. `approval-candidates/approval-candidates.json` exists
2. `approval-candidates/approval-candidate-validation.json` exists
3. Validation decision is not `APPROVAL_CANDIDATES_UNSAFE`
4. `confirm_human_reviewed=True`

**Steps:**
1. Load approval candidates
2. Load approval candidate validation
3. Check validation decision
4. Determine gate decision based on validation result
5. Write `approval-candidates/approvalrecord-proposal-gate.json`
6. Write `approval-candidates/APPROVALRECORD-PROPOSAL-GATE.md`

```python
result = evaluate_approvalrecord_proposal_gate("job-123", "Keslley", confirm_human_reviewed=True)
```

**Returns:**
```python
{
    "job_id": "job-123",
    "status": "gate_evaluated",
    "decision": "APPROVALRECORD_PROPOSAL_READY",  # or READY_WITH_WARNINGS, or BLOCKED
    "evaluated_at": "2025-02-15T11:40:30.123456Z",
    "evaluated_by": "Keslley",
    "candidate_count": 2,
    "validation_decision": "APPROVAL_CANDIDATES_SAFE",
    "warnings": [],
    "safety": {
        "netbox_write": False,
        "device_write": False,
        "sync_called": False,
        "approval_record_created": False,
        "apply_plan_created": False
    }
}
```

## Decision Logic

```
if validation_decision == APPROVAL_CANDIDATES_UNSAFE:
    decision = APPROVALRECORD_PROPOSAL_BLOCKED
elif validation_decision == APPROVAL_CANDIDATES_SAFE:
    decision = APPROVALRECORD_PROPOSAL_READY
elif validation_decision == APPROVAL_CANDIDATES_SAFE_WITH_WARNINGS:
    decision = APPROVALRECORD_PROPOSAL_READY_WITH_WARNINGS
else:
    decision = APPROVALRECORD_PROPOSAL_BLOCKED
```

## Artifacts

### Proposal Gate Result (`approval-candidates/approvalrecord-proposal-gate.json`)

```json
{
  "job_id": "job-123",
  "status": "gate_evaluated",
  "decision": "APPROVALRECORD_PROPOSAL_READY",
  "evaluated_at": "2025-02-15T11:40:30.123456Z",
  "evaluated_by": "Keslley",
  "candidate_count": 2,
  "validation_decision": "APPROVAL_CANDIDATES_SAFE",
  "warnings": [],
  "safety": {
    "netbox_write": false,
    "device_write": false,
    "sync_called": false,
    "approval_record_created": false,
    "apply_plan_created": false
  }
}
```

### Proposal Gate Markdown (`approval-candidates/APPROVALRECORD-PROPOSAL-GATE.md`)

```markdown
# ApprovalRecord Proposal Gate

**Status:** APPROVALRECORD_PROPOSAL_READY
**Evaluated at:** 2025-02-15T11:40:30Z
**Evaluated by:** Keslley

## Summary

- Candidates: 2
- Validation decision: APPROVAL_CANDIDATES_SAFE
- Warnings: 0

## Next Step

✓ Ready for ApprovalRecord proposal

## Safety

✗ No ApprovalRecord created at this stage
✗ No ApplyPlan created
✗ No NetBox writes
✗ No device connections
```

## HTTP Endpoint

**POST /compliance/jobs/{job_id}/approval-candidates/proposal-gate**

Evaluate gate to ApprovalRecord proposal.

```bash
curl -X POST /compliance/jobs/job-123/approval-candidates/proposal-gate \
  -H "Content-Type: application/json" \
  -d '{
    "operator": "Keslley",
    "confirm_human_reviewed_candidates": true
  }'
```

**Request fields:**
- `operator` (required): Name of operator confirming human review
- `confirm_human_reviewed_candidates` (required): Must be `true` to prevent accidental gate evaluation

**Response (200 — READY):**
```json
{
  "success": true,
  "job_id": "job-123",
  "status": "gate_evaluated",
  "decision": "APPROVALRECORD_PROPOSAL_READY",
  "evaluated_at": "2025-02-15T11:40:30.123456Z",
  "evaluated_by": "Keslley",
  "candidate_count": 2,
  "validation_decision": "APPROVAL_CANDIDATES_SAFE",
  "warnings": [],
  "safety": {
    "netbox_write": false,
    ...
  }
}
```

**Response (200 — READY_WITH_WARNINGS):**
```json
{
  "success": true,
  "job_id": "job-123",
  "status": "gate_evaluated",
  "decision": "APPROVALRECORD_PROPOSAL_READY_WITH_WARNINGS",
  "evaluated_at": "2025-02-15T11:40:30.123456Z",
  "evaluated_by": "Keslley",
  "candidate_count": 2,
  "validation_decision": "APPROVAL_CANDIDATES_SAFE_WITH_WARNINGS",
  "warnings": [
    "AC-001: Minor issue found"
  ],
  "safety": {
    "netbox_write": false,
    ...
  }
}
```

**Response (409 — BLOCKED):**
```json
{
  "success": false,
  "job_id": "job-123",
  "status": "gate_evaluated",
  "decision": "APPROVALRECORD_PROPOSAL_BLOCKED",
  "evaluated_at": "2025-02-15T11:40:30.123456Z",
  "evaluated_by": "Keslley",
  "candidate_count": 2,
  "validation_decision": "APPROVAL_CANDIDATES_UNSAFE",
  "warnings": [
    "AC-001: write_allowed must be False"
  ],
  "safety": {
    "netbox_write": false,
    ...
  }
}
```

**Error codes:**
- `400` — operator missing or confirm_human_reviewed_candidates not true
- `404` — approval candidates or validation not found
- `409` — validation unsafe or gate conditions not met

## Decision States

| Decision | Meaning | Next Step |
|----------|---------|-----------|
| APPROVALRECORD_PROPOSAL_READY | Safe, no warnings, ready for ApprovalRecord proposal | Proceed to ApprovalRecord proposal phase |
| APPROVALRECORD_PROPOSAL_READY_WITH_WARNINGS | Safe with minor issues, ready for ApprovalRecord proposal | Review warnings, then proceed if acceptable |
| APPROVALRECORD_PROPOSAL_BLOCKED | Validation failed or unsafe | Fix validation issues, rebuild candidates if needed |

## Safety Guarantees

- ✗ No ApprovalRecord created at this stage
- ✗ No ApplyPlan created
- ✗ No NetBox writes
- ✗ No device connections
- ✗ No SSH/SNMP/NETCONF
- ✓ Gate decision based on validation only
- ✓ Requires human confirmation (confirm_human_reviewed=true)
- ✓ Blocks if validation=UNSAFE
- ✓ Gate is idempotent (re-evaluation doesn't change prior decisions)

## Workflow

```
Build Candidates
    ↓
Validate Candidates
    ↓
Evaluate Proposal Gate
    ↓
READY → Next phase (ApprovalRecord proposal) [Not implemented yet]
READY_WITH_WARNINGS → Review warnings, then next phase
BLOCKED → Fix validation issues, retry
```
