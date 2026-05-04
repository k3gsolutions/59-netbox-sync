# Compliance Approval Candidates (FASE COMPLIANCE-APPROVAL-001)

## Overview

Builds approval candidates from safe remediation drafts. Each candidate represents a proposed change ready for human approval.

**Regra máxima:** local candidates only, no NetBox writes, no SSH/SNMP/NETCONF, no ApprovalRecord creation, no ApplyPlan creation.

## Service Functions

### `load_remediation_promotion_gate(job_id, jobs_base=None) → dict`

Load remediation promotion gate result.

```python
gate = load_remediation_promotion_gate("job-123")
```

### `load_safe_remediation_drafts(job_id, jobs_base=None) → list[dict]`

Load remediation drafts from drafts directory (only safe drafts with `write_allowed=false` and `execution_allowed=false`).

```python
drafts = load_safe_remediation_drafts("job-123")
```

### `load_remediation_draft_validation(job_id, jobs_base=None) → dict`

Load remediation draft validation result.

```python
validation = load_remediation_draft_validation("job-123")
```

### `build_approval_candidate_for_draft(job_id, draft) → dict`

Build a single approval candidate from a draft.

```python
candidate = build_approval_candidate_for_draft("job-123", draft)
```

**Returns:**
```python
{
    "candidate_id": "AC-XXXXXXXX",
    "draft_id": "RD-001",
    "finding_id": "CMP-001",
    "device_id": 1890,
    "device_name": "4WNET-MNS-KTG-RX",
    "scope": "interface",
    "object_type": "interface",
    "object_name": "Eth-Trunk0/1",
    "rule_id": "RULE-001",
    "severity": "warning",
    "risk_level": "low",
    "proposed_action_type": "documentation_update",
    "proposed_change": {...},
    "approval_intent": {
        "approval_type": "manual_review_required",
        "approval_required": True,
        "reason": "Draft requires human approval before any proposed record."
    },
    "status": "candidate",
    "write_allowed": False,
    "execution_allowed": False,
    "approval_record_created": False,
    "apply_plan_created": False,
    "safety": {
        "netbox_write": False,
        "device_write": False,
        "sync_called": False,
        "approval_record_created": False,
        "apply_plan_created": False
    }
}
```

### `build_approval_candidates(job_id, operator, jobs_base=None) → dict`

Build approval candidates from safe remediation drafts.

**Pre-conditions:**
1. `remediation-promotion-gate.json` exists
2. Gate decision is `REMEDIATION_PROMOTION_CANDIDATE_READY` or `REMEDIATION_PROMOTION_CANDIDATE_READY_WITH_WARNINGS`
3. `remediation-draft-validation.json` exists and is not `REMEDIATION_DRAFT_VALIDATION_UNSAFE`
4. At least 1 safe remediation draft exists

**Steps:**
1. Load promotion gate
2. Load draft validation
3. Load all safe remediation drafts from `remediation/drafts/`
4. Build candidate for each draft
5. Write `approval-candidates/approval-candidates.json`
6. Write `approval-candidates/APPROVAL-CANDIDATES.md`

```python
result = build_approval_candidates("job-123", "Keslley")
```

**Returns:**
```python
{
    "job_id": "job-123",
    "status": "APPROVAL_CANDIDATES_BUILT",
    "generated_at": "2025-02-15T11:30:45.123456Z",
    "generated_by": "Keslley",
    "candidates": [
        {
            "candidate_id": "AC-...",
            "draft_id": "RD-...",
            "finding_id": "CMP-...",
            ...
        }
    ],
    "candidate_count": 2,
    "safety": {
        "netbox_write": False,
        "device_write": False,
        "sync_called": False,
        "approval_record_created": False,
        "apply_plan_created": False
    }
}
```

### `load_approval_candidates(job_id, jobs_base=None) → dict`

Load existing approval candidates.

```python
candidates = load_approval_candidates("job-123")
```

### `summarize_approval_candidates(job_id, jobs_base=None) → dict`

Summarize approval candidates without loading all details.

```python
summary = summarize_approval_candidates("job-123")
```

**Returns:**
```python
{
    "job_id": "job-123",
    "status": "APPROVAL_CANDIDATES_BUILT",
    "generated_at": "2025-02-15T11:30:45.123456Z",
    "generated_by": "Keslley",
    "candidate_count": 2,
    "safety": {
        "netbox_write": False,
        "device_write": False,
        "sync_called": False,
        "approval_record_created": False,
        "apply_plan_created": False
    }
}
```

## Artifacts

### Candidates (`approval-candidates/approval-candidates.json`)

```json
{
  "job_id": "job-123",
  "status": "APPROVAL_CANDIDATES_BUILT",
  "generated_at": "2025-02-15T11:30:45.123456Z",
  "generated_by": "Keslley",
  "candidates": [
    {
      "candidate_id": "AC-...",
      "draft_id": "RD-...",
      "finding_id": "CMP-...",
      "device_id": 1890,
      "device_name": "4WNET-MNS-KTG-RX",
      "scope": "interface",
      "object_type": "interface",
      "object_name": "Eth-Trunk0/1",
      "rule_id": "RULE-001",
      "severity": "warning",
      "risk_level": "low",
      "proposed_action_type": "documentation_update",
      "proposed_change": {...},
      "approval_intent": {
        "approval_type": "manual_review_required",
        "approval_required": true,
        "reason": "Draft requires human approval before any proposed record."
      },
      "status": "candidate",
      "write_allowed": false,
      "execution_allowed": false,
      "approval_record_created": false,
      "apply_plan_created": false,
      "safety": {
        "netbox_write": false,
        "device_write": false,
        "sync_called": false,
        "approval_record_created": false,
        "apply_plan_created": false
      }
    }
  ],
  "candidate_count": 1
}
```

### Candidates Markdown (`approval-candidates/APPROVAL-CANDIDATES.md`)

```markdown
# Approval Candidates

**Status:** APPROVAL_CANDIDATES_BUILT
**Generated at:** 2025-02-15T11:30:45Z
**Generated by:** Keslley
**Total candidates:** 1

## Candidates

### AC-XXXXXXXX

- **Draft ID:** RD-001
- **Finding ID:** CMP-001
- **Device:** 4WNET-MNS-KTG-RX (1890)
- **Severity:** warning
- **Risk Level:** low
- **Scope:** interface
- **Object:** interface — Eth-Trunk0/1
- **Action Type:** documentation_update
- **Status:** candidate

## Safety

✗ NetBox writes disabled
✗ Device writes disabled
✗ Sync disabled
✗ ApprovalRecord creation disabled
✗ ApplyPlan creation disabled
```

## HTTP Endpoint

**POST /compliance/jobs/{job_id}/approval-candidates**

Build approval candidates from safe remediation drafts.

```bash
curl -X POST /compliance/jobs/job-123/approval-candidates \
  -H "Content-Type: application/json" \
  -d '{
    "operator": "Keslley",
    "confirm_build_candidates": true
  }'
```

**Request fields:**
- `operator` (required): Name of operator building candidates
- `confirm_build_candidates` (required): Must be `true`

**Response (200 — SUCCESS):**
```json
{
  "success": true,
  "status": "APPROVAL_CANDIDATES_BUILT",
  "generated_at": "2025-02-15T11:30:45.123456Z",
  "generated_by": "Keslley",
  "candidate_count": 2,
  "candidates": [...],
  "safety": {
    "netbox_write": false,
    ...
  }
}
```

**Error codes:**
- `400` — operator missing or confirm_build_candidates not true
- `404` — promotion gate not found
- `409` — gate not ready, validation unsafe, or no safe drafts

## Safety Guarantees

- ✗ No NetBox writes during candidate building
- ✗ No device connections
- ✗ No ApprovalRecord creation
- ✗ No ApplyPlan creation
- ✓ Each candidate has write_allowed=false
- ✓ Each candidate has execution_allowed=false
- ✓ Candidates are local-only assessments
- ✓ Requires gate decision=READY
- ✓ Blocks if validation=UNSAFE
