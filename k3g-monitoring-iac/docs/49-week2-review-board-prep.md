# FASE 2.13 — Week 2 Review Board Preparation

**Status:** COMPLETE
**Date:** 2026-04-29
**Version:** 1.0

---

## Overview

FASE 2.13 prepares the Week 2 review board from Week 1 validated responses.

Generates:
- week2-review-board.md (human review checklist)
- week2-review-decisions.csv (decision template)
- approval drafts in draft_review status (NOT official ApprovalRecords)

Key principle: **Zero automation, zero approvals. All drafts remain draft_review status until explicit human promotion.**

---

## Inputs

**From FASE 2.12 (Week 1 Response Intake):**
- reports/pilot-device-compliance/week1-response-validation.md (validation results)
- reports/pilot-device-compliance/week2-review-candidates.md (validated items list)
- reports/pilot-device-compliance/week1-responses/ (response directory)

**Format:**
- Validated items extracted from validation report
- Classified into: validated, needs_clarification, still_pending, blocked
- Only "validated" items proceed to review board

---

## Execution

```bash
python3 tools/local/prepare_week2_review.py \
  --device <device_name> \
  --device-id <id> \
  --validation reports/pilot-device-compliance/week1-response-validation.md \
  --candidates reports/pilot-device-compliance/week2-review-candidates.md \
  --responses-dir reports/pilot-device-compliance/week1-responses \
  --output-dir reports/pilot-device-compliance/week2-review
```

**Example:**
```bash
python3 tools/local/prepare_week2_review.py \
  --device 4WNET-MNS-KTG-RX \
  --device-id 1890 \
  --validation reports/pilot-device-compliance/week1-response-validation.md \
  --candidates reports/pilot-device-compliance/week2-review-candidates.md \
  --responses-dir reports/pilot-device-compliance/week1-responses \
  --output-dir reports/pilot-device-compliance/week2-review
```

---

## Outputs

### 1. week2-review-board.md

**Location:** reports/pilot-device-compliance/week2-review/week2-review-board.md

**Sections:**
1. Summary (count by category)
2. Items Ready for Review (validated items in table)
3. Not Eligible for Review (needs_clarification, still_pending, blocked)
4. Review Checklist (verification criteria)
5. Allowed Decisions (decision options)
6. Next Steps

**Content:**
- Timestamp of generation
- Status: Ready for human review
- Tables with object keys, types, teams
- Review criteria checklist
- Allowed decision options

**Decision Options:**
- `approve_for_approval_record` → Promote to ApprovalRecord (pending status)
- `request_changes` → Return for clarification
- `reject` → Not eligible for approval
- `defer` → Defer to later phase
- `block` → Blocked (cannot proceed)

### 2. week2-review-decisions.csv

**Location:** reports/pilot-device-compliance/week2-review/week2-review-decisions.csv

**Columns:**
- device (device name)
- device_id (numeric ID)
- object_type (interface, ip_address, bgp_peer, etc.)
- object_key (what we're enriching)
- responsible_team (which team provided response)
- tenant (enriched value)
- service_type (enriched value)
- criticality (enriched value)
- owner (enriched value)
- reviewer (human reviewer name) — **MUST FILL**
- decision (approval option) — **MUST FILL**
- reason (why this decision) — optional
- notes (additional context) — optional
- reviewed_at (ISO datetime) — **MUST FILL** (e.g., 2026-04-29T14:30:00Z)
- approval_record_allowed (true/false) — **MUST SET TO true FOR PROMOTION**

**User Tasks:**
1. Fill in decision for each row
2. Fill in reviewer name
3. Fill in reviewed_at timestamp (ISO format)
4. Set approval_record_allowed=true for items to promote
5. Set approval_record_allowed=false (or empty) for items NOT to promote

### 3. Approval Drafts (draft_review status)

**Location:** reports/pilot-device-compliance/week2-review/week2-approval-drafts/

**Pattern:** approval-draft-{object_key}.json

**Structure:**
```json
{
  "draft_id": "<uuid>",
  "status": "draft_review",
  "device": "<device>",
  "device_id": <id>,
  "object_type": "<type>",
  "object_key": "<key>",
  "action": "safe_create_staged",
  "category": "service_candidate",
  "created_at": "<iso-timestamp>",
  "allowed_to_promote": false,
  "promotion_requirements": {
    "reviewer_required": true,
    "decision_required": true,
    "approval_record_allowed_required": true,
    "reviewed_at_required": true
  },
  "warnings": [
    "This is a draft. Not an official ApprovalRecord.",
    "Can only be promoted with explicit human decision.",
    "Must complete: reviewer, decision, reviewed_at, approval_record_allowed=true"
  ],
  "safety": {
    "no_netbox_write": true,
    "no_apply_plan_created": true,
    "manual_review_required": true
  }
}
```

**Key Points:**
- status: `draft_review` (not official)
- allowed_to_promote: false initially
- Promotion requirements listed explicitly
- Safety confirmations included
- No NetBox writes
- No automatic transitions

---

## Safety Confirmations

✅ No NetBox writes during board preparation
✅ No ApplyPlan created
✅ No apply execution
✅ No tokens used
✅ Drafts remain draft_review status
✅ Manual review required for all items
✅ Audit trail maintained
✅ Zero automation

---

## Validation Example

**Scenario:** 7 items in Week 1 responses, all still_pending (no responses yet)

**Output:**
- Summary: 0 validated, 0 needs_clarification, 7 still_pending, 0 blocked
- Review Board: Section 2 empty (no items ready)
- Section 3: All 7 items listed as "No response — Follow up with team"
- Approval Drafts: 0 created (only validated items get drafts)
- decisions.csv: Created but empty (no rows for still_pending items)

**Action:** Follow up with teams on pending items

**Next Phase (FASE 2.14):** Once responses received, re-run FASE 2.12, then FASE 2.13

---

## Web UI Integration

**Routes:**
- `/service-engagement/{device}/week2-review` — View review board
- `/service-engagement/{device}/approval-drafts` — List drafts
- `/service-engagement/{device}/promotion-report` — View promotion result (FASE 2.14)

**Permissions:**
- Read-only (no writes)
- Download links for board and CSV
- Filter support for device

---

## Next Steps

**FASE 2.14 — Week 2 Draft Promotion:**
1. Human reviews items in week2-review-board.md
2. Human fills decisions in week2-review-decisions.csv
3. Human fills reviewer, reviewed_at, approval_record_allowed
4. Run promote_week2_drafts_to_approvals.py
5. Drafts promoted → ApprovalRecords (status: proposed)
6. Monitor promotion report

---

## Workflow Timeline

```
FASE 2.11: Week 1 Metadata Collection (engagement package distributed)
    ↓
Week 1 (2026-05-02 to 2026-05-08): Teams collect metadata
    ↓
FASE 2.12: Week 1 Response Intake & Validation (responses reviewed)
    ↓
FASE 2.13: Week 2 Review Board Prep (review board + decisions CSV)
    ↓
FASE 2.14: Week 2 Draft Promotion (decisions processed → ApprovalRecords)
    ↓
Week 3+: Approval/rejection workflow
```

---

## Error Handling

**If validation file missing:**
- Check FASE 2.12 completion
- Verify week1-response-validation.md exists and is valid
- Re-run validation if needed

**If all items still_pending:**
- Expected if Week 1 deadline hasn't passed
- Board will be generated with empty review section
- drafts.csv will have 0 rows
- No promotion needed yet

**If draft files corrupted:**
- Promotion script will skip with warning
- See promotion report for details
- Can re-run prepare_week2_review.py to regenerate

---

## Compliance

- ✅ Zero NetBox API calls
- ✅ Zero writes
- ✅ Manual review only
- ✅ Audit trail maintained
- ✅ Drafts immutable (JSON format, read-only)
- ✅ Decisions logged in CSV
- ✅ Promotion requires explicit approval

---

## See Also

- FASE 2.11 — Week 1 Metadata Collection Workflow
- FASE 2.12 — Week 1 Response Intake
- FASE 2.14 — Week 2 Draft Promotion
- docs/45-service-candidate-enrichment-workflow.md
- docs/46-service-owner-engagement.md
- docs/48-week1-response-intake.md
- docs/50-week2-draft-promotion.md
