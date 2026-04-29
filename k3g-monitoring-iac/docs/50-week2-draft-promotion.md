# FASE 2.14 — Week 2 Draft Promotion to ApprovalRecords

**Status:** COMPLETE
**Date:** 2026-04-29
**Version:** 1.0

---

## Overview

FASE 2.14 promotes approved drafts from `draft_review` status to official `proposed` ApprovalRecords.

**Critical:** Promotion requires ALL criteria satisfied AND explicit human decision in CSV.

No automatic approvals. No auto-transitions. Manual review only.

---

## Promotion Criteria (ALL Required)

```
✅ decision = "approve_for_approval_record"
✅ approval_record_allowed = true
✅ reviewer field filled
✅ reviewed_at field filled with valid ISO datetime
✅ Draft file exists and valid JSON
```

**If ANY criterion fails → Draft NOT promoted.**

---

## Execution

```bash
python3 tools/local/promote_week2_drafts_to_approvals.py \
  --device <device_name> \
  --device-id <id> \
  --decisions reports/pilot-device-compliance/week2-review/week2-review-decisions.csv \
  --drafts-dir reports/pilot-device-compliance/week2-review/week2-approval-drafts \
  --output-dir reports/pilot-device-compliance/week2-review
```

**Example:**
```bash
python3 tools/local/promote_week2_drafts_to_approvals.py \
  --device 4WNET-MNS-KTG-RX \
  --device-id 1890 \
  --decisions reports/pilot-device-compliance/week2-review/week2-review-decisions.csv \
  --drafts-dir reports/pilot-device-compliance/week2-review/week2-approval-drafts \
  --output-dir reports/pilot-device-compliance/week2-review
```

---

## Input: week2-review-decisions.csv

**Required columns filled by human reviewer:**

| Column | Value | Required |
|--------|-------|----------|
| device | 4WNET-MNS-KTG-RX | ✓ |
| device_id | 1890 | ✓ |
| object_type | subinterface | ✓ |
| object_key | Eth-Trunk0.10 | ✓ |
| reviewer | Alice Smith | **✓ MUST FILL** |
| decision | approve_for_approval_record | **✓ MUST FILL** |
| approval_record_allowed | true | **✓ MUST SET true** |
| reviewed_at | 2026-04-29T14:30:00Z | **✓ MUST FILL** |
| reason | Validated and approved | optional |
| notes | Service team confirmed | optional |

**Decision Values (only approve_for_approval_record triggers promotion):**
- `approve_for_approval_record` → **PROMOTE**
- `request_changes` → Do not promote (return to team)
- `reject` → Do not promote (not eligible)
- `defer` → Do not promote (defer to later)
- `block` → Do not promote (blocked)

---

## Promotion Logic

### For Each Decision Row:

1. **Validate decision criteria:**
   - decision = "approve_for_approval_record"? → YES: continue, NO: skip (not promoted)
   - approval_record_allowed = true? → YES: continue, NO: skip (marked as failed)
   - reviewer filled? → YES: continue, NO: skip (marked as failed)
   - reviewed_at valid ISO datetime? → YES: continue, NO: skip (marked as failed)

2. **Find draft file:**
   - Expected: week2-approval-drafts/approval-draft-{object_key}.json
   - Exists? → YES: load, NO: skip (missing draft file)
   - Valid JSON? → YES: continue, NO: skip (corrupted)

3. **Create ApprovalRecord:**
   - Generate unique approval_record_id (UUID)
   - Transform: status: draft_review → proposed
   - Copy fields: device, device_id, object_type, object_key, action, category
   - Add: reviewer, reviewed_at, promotion_timestamp
   - Add: source_draft_id (link back to draft)
   - Add: safety confirmations (no NetBox write, no ApplyPlan, manual review required)

4. **Save ApprovalRecord:**
   - Location: week2-review/promoted/approval-record-{approval_record_id}.json
   - Status: proposed (not auto-approved)
   - Immutable: written once, not updated by this script

5. **Log result:**
   - Success: added to "Promoted" list
   - Failure: added to "Not Promoted" list with reason

---

## Output Files

### 1. week2-promotion-report.md

**Location:** reports/pilot-device-compliance/week2-review/week2-promotion-report.md

**Content:**
- Summary table (promoted count, not promoted count, missing drafts)
- Promoted items table (object_key, approval_record_id, file)
- Not promoted items table (object_key, decision, reviewer, reason)
- Missing draft files table (if any)
- Promotion criteria checklist
- Safety confirmations
- Next steps

**Example Summary:**
```
| Status | Count |
|--------|-------|
| Promoted to ApprovalRecord | 5 |
| Not promoted | 2 |
| Missing draft files | 0 |
| **Total decisions processed** | **7** |
```

### 2. ApprovalRecord JSON Files

**Location:** reports/pilot-device-compliance/week2-review/promoted/

**Pattern:** approval-record-{approval_record_id}.json

**Structure:**
```json
{
  "approval_record_id": "<uuid>",
  "status": "proposed",
  "device": "4WNET-MNS-KTG-RX",
  "device_id": 1890,
  "object_type": "subinterface",
  "object_key": "Eth-Trunk0.10",
  "action": "safe_create_staged",
  "category": "service_candidate",
  "reviewer": "Alice Smith",
  "reviewed_at": "2026-04-29T14:30:00Z",
  "created_at": "2026-04-29T14:35:22.123456+00:00",
  "source_draft_id": "<draft-uuid>",
  "promotion_timestamp": "2026-04-29T14:35:22.123456+00:00",
  "safety": {
    "no_netbox_write": true,
    "no_apply_plan_created": true,
    "manual_review_required": true
  },
  "notes": [
    "Promoted from draft_review status by week2-review decision process",
    "Status: proposed (awaiting approval/rejection)",
    "Reviewer: Alice Smith",
    "Reviewed at: 2026-04-29T14:30:00Z"
  ]
}
```

**Key Fields:**
- status: `proposed` (not approved, not rejected)
- approval_record_id: Unique identifier (UUID)
- source_draft_id: Links back to original draft
- promotion_timestamp: When promoted
- reviewer: Who reviewed
- reviewed_at: When reviewed
- safety: Confirmations

---

## Workflow States

### Draft → ApprovalRecord Transition

```
DRAFT (draft_review status)
  ↓ [Human decision: approve_for_approval_record]
  ↓ [Reviewer filled, reviewed_at filled, approval_record_allowed=true]
  ↓ [Promotion script reads decisions CSV]
  ↓
APPROVAL_RECORD (proposed status)
  ↓ [Manual approval/rejection workflow]
  ↓
[Approved] or [Rejected] or [Deferred]
```

---

## Error Scenarios & Handling

### Scenario 1: Incomplete Reviewer Field

**CSV row:**
```csv
...,decision,approve_for_approval_record,reviewer,,reviewed_at,2026-04-29T14:30:00Z,approval_record_allowed,true
```

**Result:**
- Not promoted
- Reason: "reviewer field is empty"
- Logged in "Not Promoted" section of report
- Draft remains in draft_review status

### Scenario 2: Invalid reviewed_at Timestamp

**CSV row:**
```csv
...,reviewed_at,"not-a-date",approval_record_allowed,true,reviewer,Alice Smith,decision,approve_for_approval_record
```

**Result:**
- Not promoted
- Reason: "reviewed_at='not-a-date', not valid ISO datetime"
- Draft remains in draft_review status

### Scenario 3: Wrong Decision Value

**CSV row:**
```csv
...,decision,reject,approval_record_allowed,true,reviewer,Alice Smith,reviewed_at,2026-04-29T14:30:00Z
```

**Result:**
- Not promoted
- Reason: "decision=reject, expected 'approve_for_approval_record'"
- This is correct behavior (reject = no promotion)

### Scenario 4: Draft File Missing

**CSV row:**
```csv
...,object_key,Eth-Trunk0.10,decision,approve_for_approval_record,approval_record_allowed,true,reviewer,Alice Smith,reviewed_at,2026-04-29T14:30:00Z
```

**Expected draft file:** week2-approval-drafts/approval-draft-Eth-Trunk0-10.json

**If file doesn't exist:**
- Not promoted
- Logged in "Missing Draft Files" section
- Can regenerate with prepare_week2_review.py

### Scenario 5: approval_record_allowed Not Set

**CSV row:**
```csv
...,decision,approve_for_approval_record,reviewer,Alice Smith,reviewed_at,2026-04-29T14:30:00Z,approval_record_allowed,
```

**Result:**
- Not promoted
- Reason: "approval_record_allowed=, expected 'true'"
- Must explicitly set to true (or 1 or yes)

---

## Web UI Integration

**Routes:**
- `/service-engagement/{device}/week2-review` — Review board (before decisions)
- `/service-engagement/{device}/approval-drafts` — Draft list
- `/service-engagement/{device}/promotion-report` — Promotion results

**Permissions:**
- Read-only (no manual script execution via UI)
- Report download available
- Monitor ApprovalRecord creation

---

## Safety Confirmations

✅ No NetBox API calls during promotion
✅ No NetBox writes
✅ No ApplyPlan created
✅ No automatic approvals (status: proposed)
✅ No automatic transitions
✅ Manual approval/rejection required separately
✅ Drafts immutable (not modified)
✅ ApprovalRecords immutable (written once)
✅ Audit trail: source_draft_id, promotion_timestamp, reviewer, reviewed_at
✅ Promotion report generated
✅ All promotions tracked and logged

---

## Best Practices

1. **Review thoroughly before deciding**
   - Check review board for all criteria
   - Verify evidence and validation
   - Assess risk

2. **Fill CSV completely**
   - Don't leave reviewer blank
   - Use ISO datetime for reviewed_at
   - Explicitly set approval_record_allowed=true
   - Document reason and notes

3. **Monitor promotion output**
   - Check promotion report
   - Verify all intended items promoted
   - Investigate any "Not Promoted" items
   - Verify ApprovalRecords created

4. **Archive results**
   - Keep promotion report in audit trail
   - Track approval_record_ids
   - Link to original decisions CSV
   - Document timeline

---

## Post-Promotion Workflow

**After Promotion (FASE 2.14 complete):**

1. Review ApprovalRecords created
   - Check count matches decisions
   - Verify status = proposed
   - Confirm all required fields present

2. Move to Approval/Rejection Workflow
   - ApprovalRecords in proposed status
   - Separate approval workflow applies
   - Automatic → Cannot happen
   - Manual review → Required

3. Monitor State Transitions
   - proposed → approved (manual)
   - proposed → rejected (manual)
   - proposed → deferred (manual)

4. Track Audit Trail
   - Promotion timestamp
   - Reviewer information
   - Review timestamp
   - Source draft ID

---

## Compliance

✅ FASE 2.14 COMPLETE: Zero NetBox writes
✅ FASE 2.14 COMPLETE: Manual review only
✅ FASE 2.14 COMPLETE: No automatic approvals
✅ FASE 2.14 COMPLETE: Audit trail maintained
✅ FASE 2.14 COMPLETE: Drafts → ApprovalRecords (status: proposed)
✅ FASE 2.14 COMPLETE: Promotion report generated
✅ FASE 2.14 COMPLETE: Web UI read-only

---

## Troubleshooting

**Q: Why didn't my draft promote?**
A: Check promotion report for reason:
- decision != "approve_for_approval_record"
- approval_record_allowed != true
- reviewer field empty
- reviewed_at invalid ISO datetime
- Draft file missing or corrupted

**Q: Can I repromote the same draft?**
A: No. Once promoted, draft is linked to ApprovalRecord via source_draft_id.
If you need to revert, delete the ApprovalRecord and re-run promotion.

**Q: What if I change my mind after promotion?**
A: ApprovalRecords in proposed status can be rejected or deferred.
Promotion is not final — approval workflow still applies.

**Q: How do I regenerate drafts?**
A: Run prepare_week2_review.py again. Generates new draft UUIDs.

---

## See Also

- FASE 2.13 — Week 2 Review Board Preparation
- docs/49-week2-review-board-prep.md
- docs/45-service-candidate-enrichment-workflow.md
- docs/46-service-owner-engagement.md
- docs/48-week1-response-intake.md
