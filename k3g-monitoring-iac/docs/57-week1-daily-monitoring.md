# FASE 2.19 — Week 1 Daily Monitoring / Reminder Execution

**Objective:** Monitor Week 1 responses daily, validate CSVs, execute reminders (2026-05-06), escalate overdue items (2026-05-08 EOD), close cycle (2026-05-09).

**Timeline:** 2026-05-02 (start) → 2026-05-09 (closure)

**Constraints:**
- No NetBox writes
- No automatic responses
- No automatic escalations — manual operator decision
- Manual audit trail
- Read-only Web UI

---

## Daily Routine (2026-05-02 through 2026-05-08)

Execute daily (or at least every 2 days):

```bash
cd /path/to/k3g-monitoring-iac

python3 tools/local/track_week1_outreach_execution.py \
  --device 4WNET-MNS-KTG-RX \
  --outreach-dir reports/pilot-device-compliance/outreach \
  --responses-dir reports/pilot-device-compliance/week1-responses \
  --output reports/pilot-device-compliance/outreach/execution/outreach-status-snapshot.md \
  --deadline 2026-05-08 \
  --reminder-date 2026-05-06
```

### Interpret Dashboard Output

**File Generated:** `reports/pilot-device-compliance/outreach/execution/outreach-status-snapshot.md`

**Metrics to Monitor:**

```
Total Teams: 3
Total Items: 7

Distribution Status:
  - sent: 3 (messages delivered)
  - reminder_sent: [count] (reminders sent, post-2026-05-06)
  - escalated: [count] (escalated, post-2026-05-08)
  - not_sent: [count] (never sent, investigate)

Response Status:
  - responses_received: [count] (CSVs arrived)
  - pending_responses: [count] (awaiting)
  - partial_responses: [count] (some items answered)
  - overdue: [count] (past 2026-05-08)
```

### Web UI Dashboard

Open daily:

```
http://127.0.0.1:8890/outreach/status
```

Shows:
- Per-team status (sent / reminder_sent / escalated)
- Response count
- Items awaiting
- Link to execution log

### Update Logs

After each run, update:

```bash
cat > reports/pilot-device-compliance/outreach/execution/week1-execution-log.md <<EOF
...
## 2. Snapshot Summary

Generated: [timestamp]

[Paste snapshot output]
...
EOF
```

---

## Response Intake (When CSVs Arrive)

### Receive Response CSV

Teams send responses as CSVs:
- `service-team-response.csv`
- `network-ops-response.csv`
- `bgp-team-response.csv`

### Save to Response Directory

```bash
mkdir -p reports/pilot-device-compliance/week1-responses

# Copy/move CSVs:
cp ~/Downloads/service-team-response.csv \
   reports/pilot-device-compliance/week1-responses/

cp ~/Downloads/network-ops-response.csv \
   reports/pilot-device-compliance/week1-responses/

cp ~/Downloads/bgp-team-response.csv \
   reports/pilot-device-compliance/week1-responses/
```

### Validate Response CSVs

Immediately after receiving, validate:

```bash
python3 tools/local/validate_week1_responses.py \
  --template reports/pilot-device-compliance/week1-metadata-collection-template.csv \
  --responses-dir reports/pilot-device-compliance/week1-responses \
  --output reports/pilot-device-compliance/week1-response-validation.md \
  --device 4WNET-MNS-KTG-RX
```

**Output:** `reports/pilot-device-compliance/week1-response-validation.md`

### Interpret Validation Results

File contains sections:

1. **Validation Summary** — Per-team pass/fail
2. **Per-Item Status** — Each of 7 items: valid / incomplete / error
3. **Issue Log** — Errors found (missing fields, invalid data)
4. **Ready for Review** — Items passing all checks

**Actions by Status:**

#### ✓ Valid Response

Team completed their CSV correctly. Item ready for Week 2 review.

```
→ Proceed to Week 2 review board preparation
```

#### ⚠ Incomplete Response

Team submitted CSV but some fields missing or unclear.

```
→ Record in week1-response-validation.md
→ Notify team of missing fields
→ Request clarification by [date]
→ Do NOT block Week 2 (may review partial + request clarification in parallel)
```

#### ✗ Invalid Response

CSV format error or data invalid (out of range, wrong type).

```
→ Record error in week1-response-validation.md
→ Notify team of error
→ Request re-submit
→ Block item from Week 2 until valid
```

### Update Operational Log

After validation, update:

```bash
cat >> reports/pilot-device-compliance/outreach/execution/week1-execution-log.md <<EOF

## 3. Response Tracking

| Team | Response Received | CSV File | Validation Status | Notes |
|---|---|---|---|---|
| Service Team | 2026-05-04 | service-team-response.csv | valid | All 5 items complete |
| Network Ops | 2026-05-03 | network-ops-response.csv | valid | 1 item complete |
| BGP Team | [pending] | — | — | Awaiting response |

EOF
```

### Update Distribution Log

Mark team status based on response:

```markdown
| Service Team | message-service-team.md | response_received | 2026-05-04 | — | — | — | CSV valid, 5/5 items complete |
```

### Run Updated Snapshot

After validating response CSVs:

```bash
python3 tools/local/track_week1_outreach_execution.py \
  --device 4WNET-MNS-KTG-RX \
  --outreach-dir reports/pilot-device-compliance/outreach \
  --responses-dir reports/pilot-device-compliance/week1-responses \
  --output reports/pilot-device-compliance/outreach/execution/outreach-status-snapshot.md \
  --deadline 2026-05-08 \
  --reminder-date 2026-05-06
```

---

## Reminder Cycle (2026-05-06)

On or around 2026-05-06, send reminders to teams without responses.

### Pre-Reminder Assessment

**Run snapshot to identify non-responders:**

```bash
python3 tools/local/track_week1_outreach_execution.py ...
```

**Check snapshot:**

```
Response Status:
  - responses_received: [X] teams responded
  - pending_responses: [Y] teams awaiting
```

**If Y > 0, send reminders to those teams.**

### Reminder Message Access

Web UI route:

```
http://127.0.0.1:8890/outreach/reminders/{team}
```

Or directly read files:

```bash
cat reports/pilot-device-compliance/outreach/execution/reminder-messages/reminder-service-team.md
cat reports/pilot-device-compliance/outreach/execution/reminder-messages/reminder-network-ops.md
cat reports/pilot-device-compliance/outreach/execution/reminder-messages/reminder-bgp-team.md
```

### Send Reminders

**For each non-responding team:**

1. Retrieve message from `/outreach/reminders/{team}`
2. Verify no tokens/secrets
3. Customize if needed (e.g., add team contact)
4. Send via chosen channel (Slack, email, etc.)
5. Record timestamp + sender

### Update Distribution Log

After sending reminders:

```markdown
| Service Team | message-service-team.md | reminder_sent | 2026-05-06 10:00 | [Your Name] | Slack | csmteam@company.com | Reminder for missing items |
```

### Generate Reminder Execution Report

Create: `reports/pilot-device-compliance/outreach/execution/week1-reminder-execution.md`

Template provided. Fill in:

```markdown
# Week 1 Reminder Execution — 4WNET-MNS-KTG-RX

## 1. Pre-Reminder Assessment

Teams requiring reminders:
- [ ] Service Team — 5 items pending
- [ ] Network Ops — 1 item pending
- [ ] BGP Team — 1 item pending

## 2. Reminder Execution

| Team | Reminder Sent | Sent At | Sent By | Channel | Recipients | Status |
|---|---|---|---|---|---|---|
| Service Team | yes | 2026-05-06 10:00 | [Your Name] | Slack | csmteam@company.com | sent |
| Network Ops | no | — | — | — | — | already_responded |
| BGP Team | yes | 2026-05-06 10:05 | [Your Name] | Email | bgp-team@company.com | sent |

## 3. Notes

[Any follow-ups, team acknowledgments, delays]
```

### Post-Reminder Snapshot

After sending reminders:

```bash
python3 tools/local/track_week1_outreach_execution.py ...
```

Check updated status — responses should come within 1-2 days.

---

## Escalation (2026-05-08 EOD)

On 2026-05-08 at end of day, assess remaining overdue items.

### Pre-Escalation Assessment

**Run snapshot:**

```bash
python3 tools/local/track_week1_outreach_execution.py ...
```

**Check:**

```
Response Status:
  - pending_responses: [X] teams still awaiting
  - overdue: [Y] items past deadline
```

### Escalation Decision

**If Y = 0:** All teams responded. Skip escalation. Proceed to closure.

**If Y > 0:** Escalate to director/coordination.

### Escalation Message

Web UI route:

```
http://127.0.0.1:8890/outreach/reminders/escalation
```

Or directly:

```bash
cat reports/pilot-device-compliance/outreach/execution/reminder-messages/escalation-template.md
```

### Send Escalation

1. Customize escalation message with team name + overdue items
2. Identify escalation recipients (director, coordination)
3. Send via defined channel
4. Record timestamp + sender + recipients

### Update Distribution Log

```markdown
| Service Team | message-service-team.md | escalated | 2026-05-08 17:00 | [Your Name] | Email | director@company.com | Escalated for 5 items still pending |
```

### Generate Escalation Execution Report

Create: `reports/pilot-device-compliance/outreach/execution/week1-escalation-execution.md`

Fill in escalation details:

```markdown
# Week 1 Escalation Execution — 4WNET-MNS-KTG-RX

## 1. Pre-Escalation Assessment

Teams overdue (no response by 2026-05-08 EOD):
- [ ] Service Team — 5 items
- [ ] Network Ops — [0/1 items]
- [ ] BGP Team — [0/1 items]

## 2. Escalation Execution

| Team | Escalated | Escalated At | Escalated By | Recipients | Notes |
|---|---|---|---|---|---|
| Service Team | yes | 2026-05-08 17:00 | [Your Name] | director@company.com | 5 items awaiting |
| Network Ops | no | — | — | — | Responded on 2026-05-04 |
| BGP Team | no | — | — | — | Responded on 2026-05-05 |

## 3. Director Decision

After escalation, wait for director follow-up:
- [ ] Approve proceeding to Week 2 with partial responses
- [ ] Extend deadline
- [ ] Escalate further / pause
```

### Decision Gate

**After escalation:**

- [ ] **Director approves proceeding** → continue to closure
- [ ] **Extend deadline** → continue daily monitoring
- [ ] **Critical escalation** → notify incident commander, pause cycle

---

## Final Closure (2026-05-09)

### Final Validation

Validate all responses received:

```bash
python3 tools/local/validate_week1_responses.py \
  --template reports/pilot-device-compliance/week1-metadata-collection-template.csv \
  --responses-dir reports/pilot-device-compliance/week1-responses \
  --output reports/pilot-device-compliance/week1-response-validation.md \
  --device 4WNET-MNS-KTG-RX
```

Review results:

```bash
cat reports/pilot-device-compliance/week1-response-validation.md
```

**Check per-team status:**

```
## Per-Team Summary

Service Team:
  - Items: 5
  - Valid: [count]
  - Incomplete: [count]
  - Invalid: [count]
  - Status: ready / needs_clarification / blocked
```

### Prepare Week 2

Generate Week 2 review board:

```bash
python3 tools/local/prepare_week2_review.py \
  --device 4WNET-MNS-KTG-RX \
  --device-id 1890 \
  --validation reports/pilot-device-compliance/week1-response-validation.md \
  --candidates reports/pilot-device-compliance/week2-review-candidates.md \
  --responses-dir reports/pilot-device-compliance/week1-responses \
  --output-dir reports/pilot-device-compliance/week2-review
```

**Outputs:**

```
reports/pilot-device-compliance/week2-review/
  └── week2-review-board.md          (review checklist)
  └── week2-review-decisions.csv     (human decision template)
  └── approval-drafts/               (JSON drafts)
      ├── approval-draft-001.json
      ├── approval-draft-002.json
      └── ...
```

### Generate Final Summary

Create: `reports/pilot-device-compliance/outreach/execution/week1-final-summary.md`

Compile:

```markdown
# Week 1 Final Summary — 4WNET-MNS-KTG-RX

## 1. Execution Summary

| Metric | Value | Status |
|---|---|---|
| Total Teams | 3 | — |
| Total Items | 7 | — |
| Responses Received | [X] | ✓ |
| Complete Responses | [Y] | — |
| Partial Responses | [Z] | — |
| Overdue / Escalated | [W] | ⚠ |

## 2. Per-Team Results

| Team | Items | Responses | Status |
|---|---:|---|---|
| Service Team | 5 | [Y/5] | complete / partial / overdue |
| Network Ops | 1 | [Y/1] | complete / partial / overdue |
| BGP Team | 1 | [Y/1] | complete / partial / overdue |

## 3. Week 2 Readiness

Candidates ready for Week 2 review:
- Service Team items: [Y/5]
- Network Ops items: [Y/1]
- BGP Team items: [Y/1]

Candidates blocked (need clarification):
- [List]

## 4. Safety Confirmations

- [x] No NetBox writes
- [x] No tokens
- [x] No automatic sends
- [x] Manual process
- [x] Audit trail complete

## 5. Next Step

→ Proceed to FASE 2.13: Week 2 Review Board Preparation
→ Timeline: 2026-05-09 onwards
```

### Verify Syntax & Tests

```bash
python3 -m py_compile webui/app.py
python3 -m py_compile tools/local/*.py

python3 tools/local/test_webui_readonly.py
```

All tests should pass.

---

## Reference: Status Interpretation

### Distribution Status

| Status | Meaning | Next Action |
|---|---|---|
| `not_sent` | Message never sent | Check blockers, resend |
| `sent` | Message sent, awaiting response | Continue monitoring |
| `reminder_sent` | Reminder sent 2026-05-06 | Wait 1-2 more days |
| `escalated` | Escalated 2026-05-08 EOD | Director decision pending |

### Response Status

| Status | Meaning | Next Action |
|---|---|---|
| `response_missing` | No CSV received | Send reminder / escalate |
| `partial_response` | CSV received, some items missing | Request clarification |
| `complete` | All items in CSV, valid | Ready for Week 2 |
| `overdue` | Response expected by 2026-05-08, not received | Escalate |

---

## Emergency Procedures

### Response Directory Does Not Exist

```bash
mkdir -p reports/pilot-device-compliance/week1-responses
```

### Validation Script Fails

```bash
python3 tools/local/validate_week1_responses.py \
  --template reports/pilot-device-compliance/week1-metadata-collection-template.csv \
  --responses-dir reports/pilot-device-compliance/week1-responses \
  --output reports/pilot-device-compliance/week1-response-validation.md \
  --device 4WNET-MNS-KTG-RX \
  --verbose
```

Check for:
- Missing CSV files
- Template file not found
- CSV format errors
- Device ID mismatch

### Web UI Dashboard Not Updating

Restart app:

```bash
pkill -f "uvicorn webui.app"
python3 -m uvicorn webui.app:app --host 127.0.0.1 --port 8890
```

Clear cache:

```bash
rm -f /tmp/outreach-cache.*
```

### Team Not Responding

**Before escalation:**

1. Verify message was sent (check distribution log)
2. Contact team directly (phone, Slack) to confirm receipt
3. Offer to extend deadline if technical blockers exist
4. Document reason for non-response in notes

---

## Timeline Summary

| Date | Action | Owner | Status |
|---|---|---|---|
| 2026-05-02 | Send Week 1 messages | Operator | ✓ |
| 2026-05-02–05-05 | Monitor daily for responses | Operator | Daily |
| 2026-05-06 | Send reminders to non-responders | Operator | Conditional |
| 2026-05-07–05-08 | Final monitoring + clarifications | Operator | Daily |
| 2026-05-08 EOD | Escalate overdue items | Operator | Conditional |
| 2026-05-09 | Final validation + Week 2 prep | Operator | ← YOU ARE HERE |
| 2026-05-09+ | Week 2 review board preparation | Operator | Next Phase |

---

## Checklist: Mark Complete

- [ ] Daily monitoring executed from 2026-05-02 through 2026-05-08
- [ ] All response CSVs validated
- [ ] Reminders sent on 2026-05-06 to non-responders
- [ ] Escalation completed on 2026-05-08 EOD if needed
- [ ] Final summary created
- [ ] Week 2 review board prepared
- [ ] All tests passing (7/7)
- [ ] No NetBox writes / tokens / external API calls
- [ ] Audit trail complete

**Phase Status:** `IN_PROGRESS` → `COMPLETE` (when all boxes checked)

---

**Document Version:** 1.0
**Last Updated:** 2026-04-29
**Author:** k3g-monitoring-iac Team
