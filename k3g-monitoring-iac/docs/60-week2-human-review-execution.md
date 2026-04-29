# FASE 2.23 — Week 2 Human Review Execution

**Objective:** Execute human review, validate decisions, promote valid drafts.

**Timeline:** 2026-05-09 onwards

**Constraints:**
- No automatic approvals
- No automatic promotion
- No ApplyPlan creation
- Manual decision gate
- All approvals remain proposed/pending

---

## Overview

Week 2 human review is a structured decision process:

1. Reviewer examines draft ApprovalRecords
2. Reviewer records decision in CSV
3. Decisions validated
4. Valid approvals promoted to ApprovalRecord (proposed status)
5. System stops — no execution without further approval

**Decision Types:**
- `approve_for_approval_record` — Approve for creation (proposed status)
- `request_changes` — Ask team for changes
- `reject` — Do not proceed
- `defer` — Review later
- `block` — Explicitly prevent

---

## Process

### Step 1 — Review Week 2 Board

Open Web UI:

```
http://127.0.0.1:8890/service-engagement/4WNET-MNS-KTG-RX/week2-review
```

Or read file:

```bash
cat reports/pilot-device-compliance/week2-review/week2-review-board.md
```

Shows:
- 9-item review checklist
- Draft candidates
- Evidence references
- Verification criteria

### Step 2 — Fill Decision CSV

Edit: `reports/pilot-device-compliance/week2-review/week2-review-decisions.csv`

Template columns:
- `draft_id` (auto-filled)
- `object_key` (auto-filled)
- `object_type` (auto-filled)
- `decision` (reviewer fills: approve_for_approval_record / request_changes / reject / defer / block)
- `reviewer` (reviewer name)
- `reviewed_at` (ISO datetime)
- `approval_record_allowed` (true/false)
- `reason` (notes)
- `evidence` (reference to evidence file)

**For approval decisions, must fill:**
- `decision = approve_for_approval_record`
- `reviewer = [name]`
- `reviewed_at = [ISO datetime, e.g., 2026-05-10T14:30:00Z]`
- `approval_record_allowed = true`

Example:

```csv
draft_id,object_key,object_type,decision,reviewer,reviewed_at,approval_record_allowed,reason,evidence
approval-draft-001,Eth-Trunk0.10,subinterface,approve_for_approval_record,Alice Chen,2026-05-10T14:30:00Z,true,Verified with service owner,review-evidence/eth-trunk-evidence-001.md
approval-draft-002,Eth-Trunk0.147,subinterface,request_changes,Alice Chen,2026-05-10T14:35:00Z,false,Need service type clarification,review-evidence/eth-trunk-evidence-002.md
```

### Step 3 — Validate Decisions (No Promotion Yet)

```bash
python3 tools/local/validate_week2_review_decisions.py \
  --decisions reports/pilot-device-compliance/week2-review/week2-review-decisions.csv \
  --drafts-dir reports/pilot-device-compliance/week2-review/week2-approval-drafts \
  --output reports/pilot-device-compliance/week2-review/week2-review-decision-validation.md
```

**Output:** `week2-review-decision-validation.md`

Validates:
- All decisions are allowed values
- Approval decisions have required fields (reviewer, reviewed_at, approval_record_allowed=true)
- Draft files exist
- ISO datetimes are valid
- No automatic promotions yet

### Step 4 — Generate Human Review Report

Create: `reports/pilot-device-compliance/week2-review/week2-human-review-report.md`

```markdown
# Week 2 Human Review Report — 4WNET-MNS-KTG-RX

## Summary

| Decision | Count |
|---|---:|
| Approved for ApprovalRecord | 5 |
| Request Changes | 1 |
| Rejected | 0 |
| Deferred | 1 |
| Blocked | 0 |
| **Total Reviewed** | 7 |

## Approved for ApprovalRecord (Pending Promotion)

Items approved by human review, ready for creation as ApprovalRecord (proposed status):

| Object Key | Object Type | Reviewer | Reviewed At |
|---|---|---|---|
| Eth-Trunk0.10 | subinterface | Alice Chen | 2026-05-10T14:30:00Z |
| Eth-Trunk0.147 | subinterface | Alice Chen | 2026-05-10T14:35:00Z |
| ... | ... | ... | ... |

## Request Changes

Items requiring modifications before approval:

| Object Key | Issue | Reviewer | Feedback |
|---|---|---|---|
| [key] | Missing service_type | Alice Chen | Need clarification from team |

## Rejected

(None)

## Deferred

Items deferred for later review:

| Object Key | Reason | Reviewer |
|---|---|---|
| [key] | Pending infrastructure work | Alice Chen |

## Blocked

(None)

## Next Steps

- Approved items: Ready for promotion to ApprovalRecord (proposed)
- Changed items: Send feedback to team
- Deferred items: Reschedule review
```

### Step 5 — Promote Valid Approvals to ApprovalRecord (Optional)

Only if valid approval decisions exist in CSV:

```bash
python3 tools/local/promote_week2_drafts_to_approvals.py \
  --device 4WNET-MNS-KTG-RX \
  --device-id 1890 \
  --drafts-dir reports/pilot-device-compliance/week2-review/week2-approval-drafts \
  --decisions reports/pilot-device-compliance/week2-review/week2-review-decisions.csv \
  --output-dir reports/pilot-device-compliance/approvals/pending \
  --report reports/pilot-device-compliance/week2-review/week2-promotion-report.md
```

**Output:**
- `approvals/pending/approval-record-*.json` (proposed status)
- `week2-promotion-report.md` (promotion audit trail)

**Constraints:**
- Creates ApprovalRecords with status `proposed`
- Never creates ApplyPlan
- Never automatically approves
- Never executes changes
- Respects all decisions in CSV (approve only)

If no valid approvals in CSV:
- Report generated with promoted_count=0
- No error
- Process continues

### Step 6 — Update Web UI

Ensure routes show results:

```
GET /service-engagement/4WNET-MNS-KTG-RX/week2-review
GET /service-engagement/4WNET-MNS-KTG-RX/approval-drafts
GET /service-engagement/4WNET-MNS-KTG-RX/promotion-report
GET /approval-queue
```

Display:
- `week2-review-decision-validation.md`
- `week2-human-review-report.md`
- `week2-promotion-report.md`

---

## Decision Guide

### Approve for ApprovalRecord

**When to use:** Item passes all review criteria, no concerns.

**Effect:**
- ApprovalRecord created in `proposed` status
- Will be available for operational approval
- No immediate execution

**Requirement:** Fill all fields in CSV for approval decisions.

### Request Changes

**When to use:** Item mostly valid but needs clarification/modification.

**Effect:**
- Item blocked from promotion
- Send feedback to responsible team
- Will re-validate when updated response received

**Process:**
- Record reason in CSV
- Reach out to team
- Update response file when received
- Re-validate and re-review

### Reject

**When to use:** Item invalid or should not proceed.

**Effect:**
- Item permanently blocked
- Will not be promoted
- Not advanced to ApprovalRecord

**Reason:** Security issue, incorrect data, team decision, etc.

### Defer

**When to use:** Item valid but review should happen later.

**Effect:**
- Item held pending further review
- Not promoted now
- Will be queued for re-review at scheduled date

**Reason:** Awaiting prerequisite, scheduled maintenance window, etc.

### Block

**When to use:** Item cannot proceed due to external blocker.

**Effect:**
- Item explicitly prevented from execution
- Blocks any attempts at automation
- Requires explicit unblock decision

**Reason:** Dependency issue, incident, security hold, etc.

---

## Safety Gates

### Before Approval

- All response data validated
- No tokens/secrets in CSVs
- Reviewer identified
- Evidence documented
- Related items reviewed

### During Promotion

- No automatic approval
- No ApplyPlan created
- No field configuration
- ApprovalRecord stays proposed
- Promotion report audit trail

### After Promotion

- ApprovalRecords awaiting operational approval
- No further action without explicit approval
- Manual deployment required
- Change control maintained

---

## Timeline

| Date | Action | Owner |
|---|---|---|
| 2026-05-09 | Week 2 board published | System |
| 2026-05-10–15 | Human review window | Reviewer |
| 2026-05-16 | Decisions finalized | Reviewer |
| 2026-05-17 | Validate + promote | System |
| 2026-05-18+ | ApprovalRecords awaiting execution | Operator |

---

## Constraints

- ✅ Manual review required
- ✅ No automatic approvals
- ✅ No ApplyPlan creation
- ✅ ApprovalRecords remain proposed
- ✅ Audit trail complete
- ✅ No NetBox writes during review
- ✅ No secrets in decision data

---

**Document Version:** 1.0
**Last Updated:** 2026-04-29
