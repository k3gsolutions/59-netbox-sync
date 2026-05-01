# Compliance Review Audit Trail (FASES REVIEW-003)

## Overview

Every decision recorded during findings review generates an immutable audit entry. This enables traceability, dispute resolution, and compliance documentation.

**Regra máxima:** audit files are write-once (no updates or deletes), no NetBox writes, local storage only.

## Audit File Structure

Each decision creates one immutable file in `review/audit/`:

**Path pattern:** `review/audit/{finding_id}-{ISO-timestamp}.json`

**Example:** `review/audit/CMP-0001-2025-02-15T10:30:45.123456Z.json`

```json
{
  "event_id": "CMP-0001-2025-02-15T10:30:45.123456Z",
  "finding_id": "CMP-0001",
  "reviewer": "Keslley",
  "reason": "Descrição ausente precisa ser padronizada",
  "decision": "needs_remediation",
  "decided_at": "2025-02-15T10:30:45.123456Z",
  "status": "remediation_candidate",
  "severity_override": null
}
```

## Properties

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| event_id | string | yes | Unique identifier: `{finding_id}-{timestamp}` |
| finding_id | string | yes | Reference to original finding (e.g., CMP-0001) |
| reviewer | string | yes | Name of operator making decision |
| reason | string | yes | Explanation for decision |
| decision | enum | yes | One of: accepted, false_positive, ignored_temporarily, needs_remediation, needs_more_evidence, blocked |
| decided_at | ISO-8601 | yes | Timestamp with microseconds and Z suffix |
| status | string | yes | Logical status mapped from decision |
| severity_override | string \| null | no | Optional severity adjustment (reserved for future use) |

## Audit Trail Query

**List all decisions for a finding:**

```bash
find reports/compliance/jobs/job-123/review/audit/ \
  -name "CMP-0001-*.json" \
  -type f \
  -exec cat {} \;
```

**Timeline:** Files are sorted by ISO-timestamp embedded in filename.

## Integrity

- **Write-once:** Audit files are never modified or deleted after creation
- **Atomic:** Each POST /findings/{finding_id}/decision creates exactly one file
- **Searchable:** Filename convention enables grep and find patterns
- **Portable:** JSON format, no binary encoding, human-readable

## HTTP Endpoint

**GET /compliance/jobs/{job_id}/findings/review-summary**

Aggregates audit trail and decision state for dashboard display.

```bash
curl /compliance/jobs/job-123/findings/review-summary
```

**Response (200):**
```json
{
  "success": true,
  "job_id": "job-123",
  "total_findings": 5,
  "reviewed": 2,
  "needs_remediation": 1,
  "blocked": 0,
  "pending": 3,
  "draft_eligible": false,
  "safety": {
    "netbox_write": false,
    "device_connection": false,
    "sync_called": false,
    "approval_record_created": false,
    "apply_plan_created": false
  }
}
```

## Service Function

### `summarize_review(job_id, jobs_base=None) -> dict`

Aggregates all audit records and decision state.

```python
summary = summarize_review("job-123")
```

**Returns:**
```python
{
    "job_id": "job-123",
    "total_findings": 5,
    "reviewed": 2,           # any decision recorded
    "needs_remediation": 1,  # decision == "needs_remediation"
    "blocked": 0,            # decision == "blocked"
    "pending": 3,            # no decision recorded
    "draft_eligible": False,  # draft eligibility gate result (see next doc)
    "safety": {
        "netbox_write": False,
        "device_connection": False,
        "sync_called": False,
        "approval_record_created": False,
        "apply_plan_created": False
    }
}
```

## Timeline Example

Job created → findings generated → operators review → audit files created:

```
reports/compliance/jobs/job-123/review/audit/
├── CMP-0001-2025-02-15T10:30:45.123456Z.json  (reviewer: Keslley, decision: needs_remediation)
├── CMP-0001-2025-02-15T10:35:12.654321Z.json  (reviewer: Admin, decision: accepted) [overrides first]
├── CMP-0002-2025-02-15T10:31:05.234567Z.json  (reviewer: Keslley, decision: false_positive)
└── CMP-0003-2025-02-15T11:00:20.345678Z.json  (reviewer: Junior, decision: needs_more_evidence)
```

**Current state at end:**
- CMP-0001: decision=accepted (latest audit entry)
- CMP-0002: decision=false_positive
- CMP-0003: decision=needs_more_evidence
- CMP-0004, CMP-0005: pending (no audit entry)

## Use Cases

### Dispute Resolution

Engineer questions why CMP-0001 was accepted. Retrieve audit trail:

```bash
cat reports/compliance/jobs/job-123/review/audit/CMP-0001-*.json
```

Shows decision history and reviewer comments.

### Compliance Report

Export all decisions for a time period or job:

```bash
grep -r "decided_at" reports/compliance/jobs/job-123/review/audit/*.json | \
  jq -r '[.finding_id, .reviewer, .decision, .decided_at]'
```

### Decision Statistics

Count decisions by type:

```bash
jq -r '.decision' reports/compliance/jobs/job-123/review/audit/*.json | \
  sort | uniq -c
```

## Safety Guarantees

- ✗ Audit files cannot be updated (write-once)
- ✗ Audit files cannot be deleted by application (only filesystem)
- ✗ No NetBox writes from audit creation
- ✓ Reviewer name and reason stored as-is (no sanitization that loses data)
- ✓ Timestamps immutable after file creation
- ✓ All audit entries read-only to comparison/findings
