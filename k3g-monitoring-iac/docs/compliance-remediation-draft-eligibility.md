# Compliance Remediation Draft Eligibility Gate (FASES REVIEW-004)

## Overview

After findings are reviewed and decisions recorded, the eligibility gate evaluates whether a remediation draft can be created. The gate enforces safety requirements and ensures sufficient review progress before proceeding.

**Regra máxima:** local evaluation only, no NetBox writes, no draft creation during gate check.

## Gate Logic

The gate checks four independent conditions:

| Gate | Check | Fails If | Impact |
|------|-------|----------|--------|
| `has_findings` | At least 1 finding exists | 0 findings | BLOCKED |
| `critical_reviewed` | All blocker/error findings have a decision | Any blocker/error pending | BLOCKED |
| `no_blocked_findings` | No finding has decision="blocked" | Any decision="blocked" | BLOCKED |
| `has_remediation_candidates` | At least 1 finding has decision="needs_remediation" | 0 remediation candidates | BLOCKED |

**Decision Logic:**

```
if NOT has_findings OR NOT critical_reviewed OR NOT no_blocked_findings:
    decision = REMEDIATION_DRAFT_BLOCKED
elif NOT has_remediation_candidates:
    decision = REMEDIATION_DRAFT_BLOCKED
else:
    decision = REMEDIATION_DRAFT_ELIGIBLE
```

If `has_remediation_candidates` but some info/warning findings are unreviewed → decision=REMEDIATION_DRAFT_ELIGIBLE_WITH_WARNINGS.

## Service Function

### `evaluate_remediation_draft_eligibility(job_id, jobs_base=None) -> dict`

Evaluates gate and records result.

```python
result = evaluate_remediation_draft_eligibility("job-123")
```

**Steps:**
1. Load all findings
2. Load all decisions
3. Check each gate condition
4. Determine decision and warnings
5. Write `review/remediation-draft-eligibility.json` (idempotent)
6. Rewrite `review/REMEDIATION-DRAFT-ELIGIBILITY.md`

**Returns:**
```python
{
    "job_id": "job-123",
    "status": "completed",
    "decision": "REMEDIATION_DRAFT_ELIGIBLE",  # or BLOCKED, or ELIGIBLE_WITH_WARNINGS
    "gates": {
        "has_findings": True,
        "critical_reviewed": True,
        "no_blocked_findings": True,
        "has_remediation_candidates": True
    },
    "summary": {
        "job_id": "job-123",
        "total_findings": 5,
        "reviewed": 4,
        "needs_remediation": 2,
        "blocked": 0,
        "pending": 1,
        "draft_eligible": True
    },
    "warnings": [],  # list of warning messages if ELIGIBLE_WITH_WARNINGS
    "safety": {
        "netbox_write": False,
        "device_connection": False,
        "sync_called": False,
        "approval_record_created": False,
        "apply_plan_created": False
    }
}
```

## Artifacts

### Eligibility Result (`review/remediation-draft-eligibility.json`)

```json
{
  "job_id": "job-123",
  "status": "completed",
  "decision": "REMEDIATION_DRAFT_ELIGIBLE",
  "evaluated_at": "2025-02-15T11:15:30.123456Z",
  "gates": {
    "has_findings": true,
    "critical_reviewed": true,
    "no_blocked_findings": true,
    "has_remediation_candidates": true
  },
  "summary": {
    "job_id": "job-123",
    "total_findings": 5,
    "reviewed": 4,
    "needs_remediation": 2,
    "blocked": 0,
    "pending": 1,
    "draft_eligible": true
  },
  "warnings": [],
  "safety": {
    "netbox_write": false,
    "device_connection": false,
    "sync_called": false,
    "approval_record_created": false,
    "apply_plan_created": false
  }
}
```

### Eligibility Markdown (`review/REMEDIATION-DRAFT-ELIGIBILITY.md`)

```markdown
# Remediation Draft Eligibility

**Status:** Completed
**Decision:** REMEDIATION_DRAFT_ELIGIBLE
**Evaluated at:** 2025-02-15T11:15:30Z

## Gates

| Gate | Status | Details |
|------|--------|---------|
| has_findings | ✓ PASS | 5 findings exist |
| critical_reviewed | ✓ PASS | All 2 blocker/error findings reviewed |
| no_blocked_findings | ✓ PASS | No findings blocked |
| has_remediation_candidates | ✓ PASS | 2 findings marked for remediation |

## Summary

- Total findings: 5
- Reviewed: 4
- Pending review: 1
- Marked for remediation: 2
- Blocked: 0

## Warnings

None.

## Next Step

Draft remediation script is eligible for creation. Proceed to apply planning (not yet implemented).
```

## HTTP Endpoint

**POST /compliance/jobs/{job_id}/remediation/draft-eligibility**

Evaluate gate and record result.

```bash
curl -X POST /compliance/jobs/job-123/remediation/draft-eligibility \
  -H "Content-Type: application/json" \
  -d '{
    "confirm_review_complete": true
  }'
```

**Request fields:**
- `confirm_review_complete` (required): Must be `true`. Prevents accidental re-evaluation during incomplete review.

**Response (200 — ELIGIBLE):**
```json
{
  "success": true,
  "status": "completed",
  "decision": "REMEDIATION_DRAFT_ELIGIBLE",
  "gates": {
    "has_findings": true,
    "critical_reviewed": true,
    "no_blocked_findings": true,
    "has_remediation_candidates": true
  },
  "summary": {
    "total_findings": 5,
    "reviewed": 4,
    "needs_remediation": 2,
    "blocked": 0,
    "pending": 1,
    "draft_eligible": true
  },
  "safety": { "netbox_write": false, ... }
}
```

**Response (409 — BLOCKED):**
```json
{
  "success": true,
  "status": "completed",
  "decision": "REMEDIATION_DRAFT_BLOCKED",
  "gates": {
    "has_findings": true,
    "critical_reviewed": false,
    "no_blocked_findings": false,
    "has_remediation_candidates": true
  },
  "summary": {
    "total_findings": 5,
    "reviewed": 3,
    "needs_remediation": 1,
    "blocked": 1,
    "pending": 2,
    "draft_eligible": false
  },
  "safety": { "netbox_write": false, ... }
}
```

**Error codes:**
- `400` — `confirm_review_complete` not true
- `409` — gate conditions not met (use response body for details)

## UI Integration

### Web UI (compliance_job_detail.html)

After findings review:

1. **Summary Grid:** Total, pending, needs_remediation, blocked counts
2. **Review Table:** Per-finding rows with decision column and action buttons
3. **Eligibility Section:** Button to evaluate gate; display result if evaluated

```html
<button id="eligibility-btn">Avaliar elegibilidade para rascunho</button>

{% if job.remediation_draft_eligibility %}
  <pre>{{ job.remediation_draft_eligibility_markdown }}</pre>
{% endif %}
```

### Decision Flow

```
Findings generated
    ↓
Review findings (record decisions) ← Review Summary shows pending/remediation/blocked
    ↓
Click "Avaliar elegibilidade"
    ↓
Gate evaluation (local only)
    ↓
ELIGIBLE → Next phase (apply planning, not yet implemented)
BLOCKED → Fix issues, re-click button
```

## Example Scenarios

### Scenario 1: Fully Eligible

- Total findings: 5
- Blocker findings: 2 (both reviewed)
- Remediation decisions: 2
- Blocked findings: 0
- Pending findings: 0 or only info/warning

**Result:** REMEDIATION_DRAFT_ELIGIBLE

### Scenario 2: Unreviewed Criticials

- Total findings: 5
- Blocker findings: 2 (1 reviewed, 1 pending)
- Remediation decisions: 1
- Blocked findings: 0

**Result:** REMEDIATION_DRAFT_BLOCKED (gate: critical_reviewed = false)

### Scenario 3: Has Blocked Finding

- Total findings: 5
- Blocker findings: 2 (both reviewed)
- Remediation decisions: 2
- Blocked findings: 1

**Result:** REMEDIATION_DRAFT_BLOCKED (gate: no_blocked_findings = false)

### Scenario 4: No Remediation Candidates

- Total findings: 5
- Blocker findings: 2 (both reviewed)
- All decisions: accepted, false_positive (no needs_remediation)

**Result:** REMEDIATION_DRAFT_BLOCKED (gate: has_remediation_candidates = false)

## Safety Guarantees

- ✗ No NetBox writes during evaluation
- ✗ No device connections
- ✗ No ApprovalRecord creation
- ✗ No ApplyPlan creation
- ✓ Gate is idempotent (re-evaluation doesn't change prior decisions)
- ✓ Result is read-only assessment (no state change before draft creation)
- ✓ Eligible result does NOT auto-create remediation (manual next step)
