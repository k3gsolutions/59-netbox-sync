# FASE 2.21 — Week 1 Response Intake After First Team Replies

**Objective:** Process first team responses, validate CSVs, classify items.

**Timeline:** 2026-05-02 onwards (as responses arrive)

**Constraints:**
- No NetBox writes
- No tokens in data
- Manual operator validation
- No automatic categorization decisions

---

## Overview

Teams respond to Week 1 outreach with CSVs containing metadata. Each response must be validated against template and categorized.

**Expected Response Files:**
- `service-team-response.csv`
- `network-ops-response.csv`
- `bgp-team-response.csv`

**Validation Scope:**
- Column existence + format
- Required fields filled
- Data type correctness
- Allowed values
- No secrets/tokens
- Object key matches template

**Categories:**
- `ready_for_review` — All validations passed, ready for Week 2
- `needs_clarification` — Response exists but incomplete/ambiguous
- `blocked` — Explicitly marked not to proceed
- `rejected` — Team rejected item
- `still_pending` — No response received

---

## Process

### Step 1 — Check Responses

```bash
ls -lh reports/pilot-device-compliance/week1-responses/ || true
```

Show received CSVs (if any).

### Step 2 — Validate Responses

```bash
python3 tools/local/validate_week1_responses.py \
  --template reports/pilot-device-compliance/week1-metadata-collection-template.csv \
  --responses-dir reports/pilot-device-compliance/week1-responses \
  --output reports/pilot-device-compliance/week1-response-validation.md \
  --device 4WNET-MNS-KTG-RX
```

**Output:** `week1-response-validation.md`

Validates:
- All mandatory columns exist in response CSV
- Required fields populated
- Data types match template expectations
- No forbidden values
- No tokens/credentials
- Object keys match template items

If no CSVs present: Report all teams as `still_pending` (no error).

### Step 3 — Update Snapshot

```bash
python3 tools/local/track_week1_outreach_execution.py \
  --device 4WNET-MNS-KTG-RX \
  --outreach-dir reports/pilot-device-compliance/outreach \
  --responses-dir reports/pilot-device-compliance/week1-responses \
  --output reports/pilot-device-compliance/outreach/execution/outreach-status-snapshot.md \
  --deadline 2026-05-08 \
  --reminder-date 2026-05-06
```

**Output:** Updated `outreach-status-snapshot.md`

Shows:
- Responses received count
- Pending count
- Per-team status

### Step 4 — Update Execution Log

Edit: `reports/pilot-device-compliance/outreach/execution/week1-execution-log.md`

Add section:

```markdown
## 3. Response Tracking

| Team | Response File | Status | Items | Ready | Pending |
|---|---|---|---:|---:|---:|
| Service Team | service-team-response.csv | received | 5 | [Y] | [N] |
| Network Ops | network-ops-response.csv | received | 1 | [Y] | [N] |
| BGP Team | bgp-team-response.csv | still_pending | 1 | 0 | 1 |

**Validation Timestamp:** [ISO datetime]
**Issues Found:** [count]
**Next Action:** [prepare intake report / send reminder / escalate]
```

### Step 5 — Create Intake Report

Create: `reports/pilot-device-compliance/week1-response-intake-report.md`

Template:

```markdown
# Week 1 Response Intake Report — 4WNET-MNS-KTG-RX

## Summary

| Metric | Count |
|---|---:|
| Total Expected Items | 7 |
| Responses Received | 2 |
| Teams Responded | 2/3 |
| Ready for Review | 5 |
| Needs Clarification | 1 |
| Blocked | 0 |
| Rejected | 0 |
| Still Pending | 1 |

## Per-Team Status

| Team | Items | Response | Status | Ready | Pending |
|---|---:|---|---|---:|---:|
| Service Team | 5 | ✓ received | ready_for_review | 5 | 0 |
| Network Ops | 1 | ✓ received | ready_for_review | 1 | 0 |
| BGP Team | 1 | ✗ not_sent | still_pending | 0 | 1 |

## Items Ready for Review

| Team | Object | Owner | Evidence |
|---|---|---|---|
| Service Team | Eth-Trunk0.10 | [owner] | [evidence] |
| Service Team | Eth-Trunk0.147 | [owner] | [evidence] |
| ... | ... | ... | ... |

## Items Needing Clarification

| Team | Object | Issue | Follow-up |
|---|---|---|---|
| ... | ... | ... | ... |

## Blocked/Rejected Items

(None)

## Still Pending

| Team | Items | Expected By | Action |
|---|---:|---|---|
| BGP Team | 1 | 2026-05-06 | Send reminder on date |

## Next Steps

1. If still_pending before 2026-05-06: monitor daily
2. On 2026-05-06: send reminders to non-responders
3. On 2026-05-08: escalate overdue items
4. On 2026-05-09: finalize and prepare Week 2
```

### Step 6 — Update Web UI

Ensure routes show new status:

```
GET /outreach/status                 → Shows updated snapshot
GET /service-engagement/{device}/week1-responses
GET /service-engagement/{device}/week1-candidates
```

If not yet implemented, update templates to display:
- `week1-response-validation.md`
- `week1-response-intake-report.md`

---

## Interpretation

### Ready for Review

Response complete, all validations passed. Proceed to Week 2 review.

```
→ Advance to Week 2 board preparation
```

### Needs Clarification

Response exists but missing/ambiguous fields. Request follow-up.

```
→ Send clarification request to team
→ Wait for updated response
→ Re-validate when received
```

### Blocked

Team explicitly marked item "do not proceed". Accept and move on.

```
→ Document reason
→ Do not include in Week 2
```

### Still Pending

No response yet. Monitor until reminder/escalation dates.

```
→ Continue monitoring until 2026-05-06
→ Send reminder on 2026-05-06
→ Escalate on 2026-05-08 EOD if still pending
```

---

## Timeline

| Date | Action | Status |
|---|---|---|
| **2026-05-02–05-05** | Responses arrive, validate daily | Intake |
| **2026-05-06** | Send reminders to non-responders | Conditional |
| **2026-05-08** | Deadline, escalate overdue | Conditional |
| **2026-05-09** | Final validation, Week 2 prep | Closure |

---

## Safety

- No NetBox writes
- No tokens in response CSVs
- No automatic decisions (operator reviews)
- Audit trail via intake report
- All responses archived in week1-responses/

---

**Document Version:** 1.0
**Last Updated:** 2026-04-29
