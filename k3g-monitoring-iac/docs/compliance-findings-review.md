# Compliance Findings Review Workflow (FASES REVIEW-001–004)

## Overview

After findings are generated via comparison, operators review each finding and record a decision. Decisions are stored locally in JSON format; no NetBox writes occur.

**Regra máxima:** local decisions only, no device connections, no ApprovalRecord creation.

## Service Module

`webui/services/compliance_findings_review.py`

### Allowed Decisions

```python
ALLOWED_DECISIONS = {
    "accepted",              # Finding acknowledged, no action needed
    "false_positive",        # Mismatch between policy and actual state is not a real issue
    "ignored_temporarily",   # Known issue, will be addressed later
    "needs_remediation",     # Issue must be fixed
    "needs_more_evidence",   # Cannot confirm finding yet, needs more data
    "blocked",               # Review is blocked (escalation, missing context, etc.)
}
```

### Decision Status Mapping

Each decision maps to a logical status:

| Decision | Status | Meaning |
|----------|--------|---------|
| accepted | reviewed | Finding confirmed and acceptable |
| false_positive | dismissed | Finding is not a real issue |
| ignored_temporarily | deferred | Known issue, deferred |
| needs_remediation | remediation_candidate | Requires fix |
| needs_more_evidence | pending_evidence | Awaiting additional data |
| blocked | blocked | Review blocked |

## Functions

### `load_findings(job_id, jobs_base=None) -> list[dict]`

Loads all findings from a completed comparison run.

- Globs `comparison/devices/*/compliance-findings.json`
- Returns flat list of findings across all devices
- Returns `[]` if no comparison run exists

### `load_review_decisions(job_id, jobs_base=None) -> dict`

Loads all recorded decisions for a job.

- Returns `{"decisions": {...}}` where decisions is a dict keyed by finding_id
- Returns `{"decisions": {}}` if no decisions recorded yet

### `validate_finding_decision(decision_payload) -> (bool, str)`

Validates a decision payload before saving.

```python
payload = {
    "reviewer": "Keslley",
    "reason": "Descrição ausente precisa ser padronizada",
    "decision": "needs_remediation"
}
valid, error = validate_finding_decision(payload)
```

**Checks:**
- `reviewer` must be non-empty
- `reason` must be non-empty
- `decision` must be in ALLOWED_DECISIONS

**Returns:** `(True, "")` or `(False, "error message")`

### `save_finding_decision(job_id, finding_id, decision_payload, jobs_base=None) -> dict`

Validates, saves, and audits a decision.

```python
payload = {
    "reviewer": "Keslley",
    "reason": "Descrição ausente precisa ser padronizada",
    "decision": "needs_remediation"
}
result = save_finding_decision(job_id, "CMP-0001", payload)
```

**Steps:**
1. Validate payload with `validate_finding_decision()`
2. Load all findings and locate by finding_id
3. Load existing decisions
4. Build decision entry with timestamp and status mapping
5. Upsert into `review/finding-decisions.json`
6. Write immutable audit file: `review/audit/{finding_id}-{ISO-timestamp}.json`
7. Rewrite `review/FINDING-DECISIONS.md` (human-readable summary)

**Returns:**
```json
{
  "success": true,
  "finding_id": "CMP-0001",
  "decision": "needs_remediation",
  "status": "remediation_candidate",
  "audit_path": "review/audit/CMP-0001-2025-02-15T10:30:45.123456Z.json",
  "safety": {
    "netbox_write": false,
    "device_connection": false,
    "sync_called": false,
    "approval_record_created": false,
    "apply_plan_created": false
  }
}
```

## Artifacts

### Finding Decisions (`review/finding-decisions.json`)

Keyed index of all decisions.

```json
{
  "decisions": {
    "CMP-0001": {
      "finding_id": "CMP-0001",
      "reviewer": "Keslley",
      "reason": "Descrição ausente precisa ser padronizada",
      "decision": "needs_remediation",
      "status": "remediation_candidate",
      "severity_override": null,
      "decided_at": "2025-02-15T10:30:45.123456Z"
    },
    "CMP-0002": {
      "finding_id": "CMP-0002",
      "reviewer": "Keslley",
      "reason": "FP - regra não se aplica",
      "decision": "false_positive",
      "status": "dismissed",
      "severity_override": null,
      "decided_at": "2025-02-15T10:31:12.654321Z"
    }
  }
}
```

### Finding Decisions Markdown (`review/FINDING-DECISIONS.md`)

Human-readable summary, regenerated after each decision.

```markdown
# Findings Review Summary

Reviewed: 2 / 5
Pending: 3

## Decisions

### CMP-0001 (remediation_candidate)
- Decision: needs_remediation
- Reviewer: Keslley
- Reason: Descrição ausente precisa ser padronizada
- Decided at: 2025-02-15T10:30:45Z

### CMP-0002 (dismissed)
- Decision: false_positive
- Reviewer: Keslley
- Reason: FP - regra não se aplica
- Decided at: 2025-02-15T10:31:12Z

## Pending (3)

- CMP-0003
- CMP-0004
- CMP-0005
```

### Audit Trail (`review/audit/{finding_id}-{ISO-timestamp}.json`)

Immutable record of each decision event.

```json
{
  "event_id": "CMP-0001-2025-02-15T10:30:45.123456Z",
  "finding_id": "CMP-0001",
  "reviewer": "Keslley",
  "reason": "Descrição ausente precisa ser padronizada",
  "decision": "needs_remediation",
  "decided_at": "2025-02-15T10:30:45.123456Z",
  "status": "remediation_candidate"
}
```

## UI Integration

### Web UI (compliance_job_detail.html)

After findings are generated:

1. **Review Summary Cards:** Show total, pending, needs_remediation, blocked counts
2. **Findings Table:** Per-finding row with action buttons (✓ Aceitar, FP, ↷ Ignorar, ⚡ Correção, ? Evidência, ⊗ Bloquear)
3. **Decision Column:** Show current status (reviewed, dismissed, deferred, remediation_candidate, pending_evidence, blocked)
4. **JavaScript Handlers:** On button click, prompt for reviewer name and reason, POST decision payload

### HTTP Endpoints

**POST /compliance/jobs/{job_id}/findings/{finding_id}/decision**

Record a decision for a single finding.

```bash
curl -X POST /compliance/jobs/job-123/findings/CMP-0001/decision \
  -H "Content-Type: application/json" \
  -d '{
    "reviewer": "Keslley",
    "reason": "Descrição ausente precisa ser padronizada",
    "decision": "needs_remediation"
  }'
```

**Response (200):**
```json
{
  "success": true,
  "finding_id": "CMP-0001",
  "decision": "needs_remediation",
  "status": "remediation_candidate",
  "safety": { "netbox_write": false, ... }
}
```

**Errors:**
- `400` — validation failed (missing reviewer/reason, invalid decision)
- `404` — finding not found
- `409` — no comparison run (findings missing)

## Safety Guarantees

- ✗ No NetBox writes
- ✗ No device SSH/SNMP/NETCONF connections
- ✗ No ApprovalRecord creation
- ✗ No ApplyPlan creation
- ✓ Decisions stored locally only
- ✓ Audit trail immutable (no update/delete of audit files)
- ✓ All operations read-only on state outside review/

## Next Local Steps

- `POST /compliance/jobs/{job_id}/remediation/drafts` creates draft artifacts after eligibility exists.
- `GET /compliance/jobs/{job_id}/remediation/drafts/validation` validates draft safety only.
- `POST /compliance/jobs/{job_id}/remediation/promotion-gate` evaluates readiness for the next flow and does not promote anything.
