# Compliance Proposed ApprovalRecords (FASES COMPLIANCE-APPROVALRECORD-001–003)

## Overview

Builds proposed ApprovalRecords from approval candidates, validates them for safety, and gates to ApplyPlan candidate builder.

**Regra máxima:** local proposed records only, no NetBox writes, no SSH/SNMP/NETCONF, no actual ApprovalRecord creation.

## Service Functions

### BLOCO 1 — Proposed ApprovalRecord Builder

#### `load_applyplan_candidate_gate(job_id, jobs_base=None) → dict`

Load ApprovalRecord proposal gate result.

#### `load_safe_approval_candidates(job_id, jobs_base=None) → list[dict]`

Load approval candidates.

#### `build_proposed_approval_record_for_candidate(candidate) → dict`

Build a single proposed ApprovalRecord from a candidate.

```python
{
    "approval_record_id": "PAR-XXXXXXXX",
    "candidate_id": "AC-001",
    "finding_id": "CMP-001",
    "device_id": 1890,
    "device_name": "Device",
    "scope": "interface",
    "object_type": "interface",
    "object_name": "Eth-Trunk0/1",
    "status": "proposed",
    "approved": False,
    "approved_by": None,
    "approved_at": None,
    "write_allowed": False,
    "execution_allowed": False,
    "apply_plan_created": False,
    "manual_approval_required": True,
    "state_history": [
        {
            "status": "proposed",
            "created_at": "2025-02-15T12:00:00Z",
            "created_by": None,
            "reason": "Proposed from candidate"
        }
    ],
    "safety": {
        "netbox_write": False,
        "device_write": False,
        "sync_called": False,
        "approval_record_created": False,
        "apply_plan_created": False
    }
}
```

#### `build_proposed_approval_records(job_id, operator, jobs_base=None) → dict`

Build proposed ApprovalRecords from safe approval candidates.

**Pre-conditions:**
1. `approvalrecord-proposal-gate.json` exists
2. Gate decision is `APPROVALRECORD_PROPOSAL_READY` or `APPROVALRECORD_PROPOSAL_READY_WITH_WARNINGS`
3. Approval validation is not UNSAFE
4. At least 1 approval candidate exists

**Artifacts:**
- `approval-records/proposed/proposed-approval-records.json`
- `approval-records/proposed/PROPOSED-APPROVAL-RECORDS.md`

### BLOCO 2 — Proposed ApprovalRecord Validation

#### `validate_proposed_approval_records(job_id, jobs_base=None) → dict`

Validate all proposed ApprovalRecords.

**Validation rules — UNSAFE if any record has:**
1. `status != "proposed"`
2. `approved != False`
3. `approved_by != None`
4. `approved_at != None`
5. `write_allowed != False`
6. `execution_allowed != False`
7. `apply_plan_created != False`
8. `manual_approval_required != True`
9. Missing `state_history`
10. Secret keyword in `proposed_change`
11. Any safety flag != False

**Decision:**
- `PROPOSED_APPROVAL_RECORDS_SAFE`
- `PROPOSED_APPROVAL_RECORDS_SAFE_WITH_WARNINGS`
- `PROPOSED_APPROVAL_RECORDS_UNSAFE`

**Artifacts:**
- `approval-records/proposed/proposed-approval-record-validation.json`
- `approval-records/proposed/PROPOSED-APPROVAL-RECORD-VALIDATION.md`

### BLOCO 3 — ApplyPlan Candidate Gate

Evaluates readiness to proceed to ApplyPlan candidate builder.

**Decision logic:**
```
if validation decision == UNSAFE:
    decision = APPLYPLAN_CANDIDATE_BLOCKED
elif validation decision == SAFE:
    decision = APPLYPLAN_CANDIDATE_READY
else:
    decision = APPLYPLAN_CANDIDATE_READY_WITH_WARNINGS
```

## HTTP Endpoints

### POST /compliance/jobs/{job_id}/approval-records/proposed

Build proposed ApprovalRecords.

```bash
curl -X POST /compliance/jobs/job-123/approval-records/proposed \
  -H "Content-Type: application/json" \
  -d '{
    "operator": "Keslley",
    "confirm_create_proposed_records": true
  }'
```

**Response (200 — SUCCESS):**
```json
{
  "success": true,
  "status": "PROPOSED_APPROVAL_RECORDS_BUILT",
  "created_at": "2025-02-15T12:00:00Z",
  "created_by": "Keslley",
  "record_count": 2,
  "records": [...],
  "safety": {
    "netbox_write": false,
    ...
  }
}
```

**Error codes:**
- `400` — operator missing or confirm not true
- `404` — proposal gate not found
- `409` — gate not ready, validation unsafe, or no candidates

### GET /compliance/jobs/{job_id}/approval-records/proposed/validation

Validate proposed ApprovalRecords.

```bash
curl -X GET /compliance/jobs/job-123/approval-records/proposed/validation
```

**Response (200 — SAFE):**
```json
{
  "success": true,
  "decision": "PROPOSED_APPROVAL_RECORDS_SAFE",
  "validated_at": "2025-02-15T12:05:00Z",
  "record_count": 2,
  "valid_count": 2,
  "issues": [],
  "issue_count": 0,
  "safety": {
    "netbox_write": false,
    ...
  }
}
```

**Error codes:**
- `404` — proposed records not found
- `409` — validation failed (UNSAFE)

### POST /compliance/jobs/{job_id}/approval-records/applyplan-candidate-gate

Gate to ApplyPlan candidate builder.

```bash
curl -X POST /compliance/jobs/job-123/approval-records/applyplan-candidate-gate \
  -H "Content-Type: application/json" \
  -d '{
    "operator": "Keslley",
    "confirm_human_reviewed_proposed_records": true
  }'
```

**Response (200 — READY):**
```json
{
  "success": true,
  "decision": "APPLYPLAN_CANDIDATE_READY",
  "evaluated_at": "2025-02-15T12:10:00Z",
  "evaluated_by": "Keslley",
  "validation_decision": "PROPOSED_APPROVAL_RECORDS_SAFE",
  "safety": {
    "netbox_write": false,
    ...
  }
}
```

**Error codes:**
- `400` — operator missing or confirm not true
- `409` — validation unsafe or failed

## Safety Guarantees

- ✗ No NetBox writes during record building or validation
- ✗ No device connections
- ✗ No SSH/SNMP/NETCONF
- ✗ No actual ApprovalRecord creation
- ✗ No ApplyPlan creation
- ✓ All records have `approved=false`, `write_allowed=false`, `execution_allowed=false`
- ✓ All records have `manual_approval_required=true`
- ✓ State history preserved
- ✓ Validation blocks secrets and safety violations
- ✓ Gate blocks if validation unsafe

## Artifacts

```
reports/compliance/jobs/<job_id>/approval-records/proposed/
├── proposed-approval-records.json
├── PROPOSED-APPROVAL-RECORDS.md
├── proposed-approval-record-validation.json
└── PROPOSED-APPROVAL-RECORD-VALIDATION.md
```

## Next Step

If gate READY or READY_WITH_WARNINGS → proceed to ApplyPlan candidate builder.
If gate BLOCKED → review validation issues and rebuild candidates if needed.
