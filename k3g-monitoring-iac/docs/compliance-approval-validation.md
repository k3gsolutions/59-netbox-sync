# Compliance Approval Candidate Validation (FASE COMPLIANCE-APPROVAL-003)

## Overview

Validates approval candidates for safety and security before they proceed to ApprovalRecord proposal.

**Regra máxima:** validation only, no NetBox writes, no SSH/SNMP/NETCONF, no state changes.

## Validation Rules

Approval candidates are marked **UNSAFE** if:

1. Any candidate has `write_allowed=true`
2. Any candidate has `execution_allowed=true`
3. Any candidate has `approval_record_created=true`
4. Any candidate has `apply_plan_created=true`
5. Any proposed_change contains forbidden commands:
   - system-view, configure, commit, save, delete, undo, shutdown, reboot, reset, patch, sync
6. Any proposed_change contains secret keywords:
   - token, password, secret, cipher, private_key, api_key, access_key
7. Any candidate has `approval_required=false`
8. Any safety flag is `true`

## Service Function

### `validate_approval_candidates(job_id, jobs_base=None) → dict`

Validate all approval candidates.

**Pre-conditions:**
1. `approval-candidates/approval-candidates.json` exists
2. Candidates list is not empty

**Steps:**
1. Load approval candidates
2. Check each candidate against validation rules
3. Determine decision (SAFE, SAFE_WITH_WARNINGS, or UNSAFE)
4. Write `approval-candidates/approval-candidate-validation.json`
5. Write `approval-candidates/APPROVAL-CANDIDATE-VALIDATION.md`

```python
result = validate_approval_candidates("job-123")
```

**Returns:**
```python
{
    "job_id": "job-123",
    "status": "validation_completed",
    "decision": "APPROVAL_CANDIDATES_SAFE",  # or SAFE_WITH_WARNINGS, or UNSAFE
    "validated_at": "2025-02-15T11:35:20.123456Z",
    "candidate_count": 2,
    "valid_count": 2,
    "issues": [],
    "issue_count": 0,
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
if any issue found:
    if issues > 25% of candidates:
        decision = APPROVAL_CANDIDATES_UNSAFE
    else:
        decision = APPROVAL_CANDIDATES_SAFE_WITH_WARNINGS
else:
    decision = APPROVAL_CANDIDATES_SAFE
```

## Artifacts

### Validation Result (`approval-candidates/approval-candidate-validation.json`)

```json
{
  "job_id": "job-123",
  "status": "validation_completed",
  "decision": "APPROVAL_CANDIDATES_SAFE",
  "validated_at": "2025-02-15T11:35:20.123456Z",
  "candidate_count": 2,
  "valid_count": 2,
  "issues": [],
  "issue_count": 0,
  "safety": {
    "netbox_write": false,
    "device_write": false,
    "sync_called": false,
    "approval_record_created": false,
    "apply_plan_created": false
  }
}
```

### Validation Markdown (`approval-candidates/APPROVAL-CANDIDATE-VALIDATION.md`)

```markdown
# Approval Candidate Validation

**Status:** APPROVAL_CANDIDATES_SAFE
**Validated at:** 2025-02-15T11:35:20Z

## Summary

- Total candidates: 2
- Valid: 2
- Issues: 0

## Issues

(None)

## Safety

✗ NetBox writes blocked
✗ Device writes blocked
✗ Sync blocked
✗ ApprovalRecord creation blocked
✗ ApplyPlan creation blocked
```

## HTTP Endpoint

**POST /compliance/jobs/{job_id}/approval-candidates/proposal-gate**

Validate candidates and gate to ApprovalRecord proposal.

```bash
curl -X POST /compliance/jobs/job-123/approval-candidates/proposal-gate \
  -H "Content-Type: application/json" \
  -d '{
    "operator": "Keslley",
    "confirm_human_reviewed_candidates": true
  }'
```

**Request fields:**
- `operator` (required): Name of operator confirming review
- `confirm_human_reviewed_candidates` (required): Must be `true`

**Response (200 — VALIDATION PASSED):**
```json
{
  "success": true,
  "job_id": "job-123",
  "status": "validation_completed",
  "decision": "APPROVAL_CANDIDATES_SAFE",
  "candidate_count": 2,
  "valid_count": 2,
  "issues": [],
  "safety": {
    "netbox_write": false,
    ...
  }
}
```

**Response (409 — VALIDATION FAILED):**
```json
{
  "success": false,
  "validation_decision": "APPROVAL_CANDIDATES_UNSAFE",
  "job_id": "job-123",
  "status": "validation_completed",
  "decision": "APPROVAL_CANDIDATES_UNSAFE",
  "candidate_count": 2,
  "valid_count": 1,
  "issues": [
    "AC-001: write_allowed must be False"
  ],
  "issue_count": 1,
  "safety": {
    "netbox_write": false,
    ...
  }
}
```

**Error codes:**
- `400` — operator missing or confirm_human_reviewed_candidates not true
- `404` — approval candidates not found
- `409` — validation failed (UNSAFE)

## Forbidden Commands

```
system-view, configure, commit, save, delete, undo, shutdown, reboot, reset, patch, sync
```

## Forbidden Keywords

```
token, password, secret, cipher, private_key, api_key, access_key
```

## Safety Guarantees

- ✗ No NetBox writes during validation
- ✗ No device connections
- ✗ No ApprovalRecord creation
- ✗ No ApplyPlan creation
- ✗ No state changes
- ✓ All candidates checked for write_allowed=false
- ✓ All candidates checked for execution_allowed=false
- ✓ All candidates checked for secret keywords
- ✓ All candidates checked for forbidden commands
- ✓ Validation is deterministic (same input = same decision)

## Example Issues

```
AC-001: write_allowed must be False
AC-001: forbidden command 'system-view' in proposed_change
AC-002: secret keyword 'password' in proposed_change
AC-003: safety.netbox_write must be False
```
