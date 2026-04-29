# FASE 2.22 — Week 1 Final Validation / Week 2 Activation

**Objective:** Consolidate Week 1, prepare Week 2 board, decide GO/NO-GO.

**Timeline:** 2026-05-09 (closure) or when collection ends

**Constraints:**
- No automatic approvals
- No NetBox writes
- No ApplyPlan creation
- Manual decision gate

---

## Overview

Week 1 closes on 2026-05-08. On 2026-05-09, consolidate all responses and decide if Week 2 can proceed with human review.

**GO Decision Criteria:**
- At least 1 item ready_for_review (or ready_with_changes)
- No critical security issues
- All responses validated
- Web UI 7/7 tests passing
- No secrets in data

**NO-GO Criteria:**
- 0 items ready_for_review
- Critical incidents blocking review
- Responses contain security issues

**Restricted GO:**
- Some items ready, others pending
- Proceed with ready items only
- Flag pending items for later intake

---

## Process

### Step 1 — Final Response Validation

```bash
python3 tools/local/validate_week1_responses.py \
  --template reports/pilot-device-compliance/week1-metadata-collection-template.csv \
  --responses-dir reports/pilot-device-compliance/week1-responses \
  --output reports/pilot-device-compliance/week1-response-validation-final.md \
  --device 4WNET-MNS-KTG-RX
```

**Output:** `week1-response-validation-final.md`

Validates all responses received (or lack thereof) by deadline.

### Step 2 — Prepare Week 2 Board

```bash
python3 tools/local/prepare_week2_review.py \
  --device 4WNET-MNS-KTG-RX \
  --device-id 1890 \
  --validation reports/pilot-device-compliance/week1-response-validation-final.md \
  --candidates reports/pilot-device-compliance/week2-review-candidates.md \
  --responses-dir reports/pilot-device-compliance/week1-responses \
  --output-dir reports/pilot-device-compliance/week2-review
```

**Outputs:**
- `reports/pilot-device-compliance/week2-review-candidates.md`
- `reports/pilot-device-compliance/week2-review/week2-review-board.md`
- `reports/pilot-device-compliance/week2-review/week2-review-decisions.csv` (template)
- `reports/pilot-device-compliance/week2-review/week2-approval-drafts/` (JSON drafts)

### Step 3 — Generate Final Validation Report

Create: `reports/pilot-device-compliance/outreach/execution/week1-final-validation-report.md`

```markdown
# Week 1 Final Validation Report — 4WNET-MNS-KTG-RX

## Summary

| Metric | Count |
|---|---:|
| Total Expected Items | 7 |
| Responses Received | [X] |
| Ready for Review | [Y] |
| Needs Clarification | [Z] |
| Blocked | [W] |
| Rejected | [V] |
| Still Pending | [U] |

## Per-Team Breakdown

| Team | Items | Responses | Ready | Clarification | Pending |
|---|---:|---:|---:|---:|---:|
| Service Team | 5 | ✓ | [Y] | [Z] | [U] |
| Network Ops | 1 | ✓ | [Y] | [Z] | [U] |
| BGP Team | 1 | ? | [Y] | [Z] | [U] |

## Items Advancing to Week 2

| Team | Object Type | Object Key | Owner | Status |
|---|---|---|---|---|
| ... | ... | ... | ... | ready_for_review |

## Items Not Advancing

| Team | Object Type | Object Key | Reason |
|---|---|---|---|
| ... | ... | ... | blocked / rejected / pending |

## Validation Status

✓ All responses validated
✓ No secrets/tokens found
✓ Template format verified
✓ Week 2 board generated

## Recommendations

- Week 2 ready with [Y] items
- [Z] items need clarification (can be handled in parallel)
- [U] items still pending (monitor/escalate as needed)
```

### Step 4 — Activation Gate

Create: `reports/pilot-device-compliance/week2-activation-gate.md`

```markdown
# Week 2 Activation Gate — 4WNET-MNS-KTG-RX

## Gate Checks

- [x] Week 1 response window closed (2026-05-08)
- [x] All responses validated
- [x] Week 2 board generated
- [x] No critical incidents open
- [x] Web UI 7/7 tests passing
- [x] No secrets in response files
- [x] No NetBox writes performed

## Decision

**Status:** GO_WEEK2_REVIEW

**Rationale:**
- [Y] items ready for human review
- [Z] items need clarification (will handle in parallel)
- [U] items still pending (continue monitoring)

## Approved Scope for Week 2

**Phase: Human Review (No Execution)**

- ✓ Human review of candidates
- ✓ Draft review board
- ✓ Decision CSV (operator filled)
- ✓ Validate decisions
- ✗ No automatic approvals
- ✗ No ApplyPlan creation
- ✗ No field deployment

## Timeline

- 2026-05-09: Gate opened, Week 2 board available
- 2026-05-10–2026-05-15: Human review window
- 2026-05-16: Decisions finalized
- 2026-05-17–2026-05-22: Promotion to ApprovalRecord (proposed)
- 2026-05-23+: Awaiting operational approval for execution

## Sign-off

**Gate:** OPEN
**Date:** 2026-05-09
**Approver:** [Operator]
```

### Step 5 — Update Web UI

Ensure routes available:

```
GET /service-engagement/4WNET-MNS-KTG-RX/responses
GET /service-engagement/4WNET-MNS-KTG-RX/week2-review
GET /service-engagement/4WNET-MNS-KTG-RX/week2-candidates
```

Display files:
- `week1-final-validation-report.md`
- `week2-activation-gate.md`
- `week2-review-board.md`

---

## Outcomes

### GO_WEEK2_REVIEW

All systems ready. Proceed to human review with no restrictions.

```
→ Publish Week 2 board
→ Open review decision window
→ Notify stakeholders
```

### GO_WITH_RESTRICTIONS

Some items ready, others pending. Proceed with ready items only.

```
→ Publish board with RESTRICTED scope
→ Human review restricted to ready items
→ Continue monitoring pending items
→ Integrate pending items when received
```

### NO_GO

No items ready. Defer Week 2.

```
→ Investigate root cause (communication? data quality?)
→ Extend Week 1 deadline if needed
→ Reschedule Week 2
```

---

## Safety

- No ApprovalRecord created automatically
- No ApplyPlan generated
- All approvals remain proposed/pending
- Manual verification gate required
- Audit trail complete

---

**Document Version:** 1.0
**Last Updated:** 2026-04-29
