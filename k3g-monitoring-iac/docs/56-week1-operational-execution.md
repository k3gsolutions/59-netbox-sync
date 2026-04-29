# FASE 2.18 — Week 1 Operational Execution

**Objective:** Execute manual distribution of Week 1 outreach pack to 3 teams. Register sends. Generate initial snapshot.

**Timeline:** 2026-05-02 (start) through operational window

**Constraints:**
- No NetBox writes
- No tokens
- No automatic sends — operator controls
- No external API calls
- Read-only Web UI
- Manual audit trail

---

## Overview

Week 1 outreach targets 3 teams for metadata collection:
- **Service Team** — 5 subinterfaces (Eth-Trunk1/2/3, GigabitEthernet0/1/0, GigabitEthernet0/5/0)
- **Network Ops** — 1 IP (192.168.1.100)
- **BGP Team** — 1 BGP peer (AS65001)

**Total:** 7 items across 3 teams.

Messages generated:
- `message-service-team.md` — CSM contact, 5 items listed, deadline 2026-05-08 EOD
- `message-network-ops.md` — NetOps contact, 1 item listed, deadline 2026-05-08 EOD
- `message-bgp-team.md` — BGP contact, 1 item listed, deadline 2026-05-08 EOD

Responses expected via:
- `service-team-response.csv` — Template: `week1-metadata-collection-template.csv`
- `network-ops-response.csv` — Template: `week1-metadata-collection-template.csv`
- `bgp-team-response.csv` — Template: `week1-metadata-collection-template.csv`

---

## Step 1 — Validate Web UI

Start Web UI if not running:

```bash
python3 -m uvicorn webui.app:app --host 127.0.0.1 --port 8890 --reload
```

### Verify Routes

Test each route in browser or curl:

```bash
curl http://127.0.0.1:8890/outreach
curl http://127.0.0.1:8890/outreach/service-team
curl http://127.0.0.1:8890/outreach/network-ops
curl http://127.0.0.1:8890/outreach/bgp-team
curl http://127.0.0.1:8890/outreach/status
curl http://127.0.0.1:8890/outreach/execution-log
curl http://127.0.0.1:8890/outreach/reminders
```

### Validation Checklist

- [ ] `/outreach` loads, shows team links
- [ ] `/outreach/{team}` displays message + download button
- [ ] `/outreach/status` shows snapshot with teams/items counts
- [ ] `/outreach/execution-log` displays distribution log table
- [ ] `/outreach/reminders` shows reminder index
- [ ] No 500 errors
- [ ] No POST/PATCH/DELETE routes exposed
- [ ] Paths do not escape to parent directories
- [ ] No sensitive files leaked

---

## Step 2 — Prepare Manual Distribution

### Message Content Verification

Before sending, open and verify each message:

```bash
cat reports/pilot-device-compliance/outreach/message-service-team.md
cat reports/pilot-device-compliance/outreach/message-network-ops.md
cat reports/pilot-device-compliance/outreach/message-bgp-team.md
```

**Verification Checklist:**

- [ ] No tokens/credentials in message
- [ ] No passwords
- [ ] No secrets or raw JSON
- [ ] No URLs to sensitive systems
- [ ] No internal IP addresses exposed unnecessarily
- [ ] Contact info matches team roster
- [ ] Deadline clearly stated (2026-05-08 EOD)
- [ ] CSV template clearly referenced
- [ ] Template path is accessible to recipients

### Template Verification

```bash
cat reports/pilot-device-compliance/week1-metadata-collection-template.csv
```

**Checklist:**

- [ ] All 7 items listed in template
- [ ] No pre-filled responses (empty data columns)
- [ ] Column headers clear
- [ ] CSV format valid (test with: `python3 -c "import csv; csv.reader(open('...'))..."`)

### Checklist Verification

Distribution checklist exists at:
- `reports/pilot-device-compliance/outreach/execution/manual-send-checklist.md`

Review before each send:

```bash
cat reports/pilot-device-compliance/outreach/execution/manual-send-checklist.md
```

---

## Step 3 — Register Manual Sends

### Distribution Log

**File:** `reports/pilot-device-compliance/outreach/execution/outreach-distribution-log.md`

This table tracks when messages are sent, who sent them, and to whom.

**Process:**

1. **For each team:**
   - Copy message from `/outreach/{team}` or directly from file
   - Send via chosen channel (email, Slack, Teams, etc.)
   - Note: Attach or link the CSV template
   - Record timestamp of send

2. **Update distribution-log.md:**

```markdown
| Service Team | message-service-team.md | sent | 2026-05-02 10:30 | [Your Name] | Slack | csmteam@company.com | [Notes] |
| Network Ops | message-network-ops.md | sent | 2026-05-02 10:35 | [Your Name] | Email | netops@company.com | [Notes] |
| BGP Team | message-bgp-team.md | sent | 2026-05-02 10:40 | [Your Name] | Slack | bgp-team@company.com | [Notes] |
```

**Status Values:**
- `not_sent` — Not yet sent (default)
- `sent` — Message sent, awaiting response
- `reminder_sent` — Reminder sent on 2026-05-06
- `escalated` — Escalated on 2026-05-08 EOD

### Operational Log

Create/update: `reports/pilot-device-compliance/outreach/execution/week1-execution-log.md`

Fill in sections as you execute:
- **Distribution Summary** — Team name, message file, status, send info
- **Operational Notes** — Any blockers or communication issues
- **Safety Confirmations** — Verify none were violated

---

## Step 4 — Generate Post-Send Snapshot

After sending all messages, generate status snapshot:

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

### Expected Output

**File:** `reports/pilot-device-compliance/outreach/execution/outreach-status-snapshot.md`

Contents:

```
# Week 1 Response Status Snapshot — 4WNET-MNS-KTG-RX

Generated: [timestamp]
Deadline: 2026-05-08 EOD
Reminder Date: 2026-05-06

## Summary

Total Teams: 3
Total Items: 7

Distribution Status:
  - sent: 3
  - not_sent: 0
  - reminder_sent: 0
  - escalated: 0

Response Status:
  - responses_received: 0
  - pending_responses: 3
  - partial_responses: 0
  - overdue: 0

## Per-Team Status

| Team | Items | Sent | Responses | Status |
|---|---:|---|---:|---|
| Service Team | 5 | yes | 0 | sent (awaiting) |
| Network Ops | 1 | yes | 0 | sent (awaiting) |
| BGP Team | 1 | yes | 0 | sent (awaiting) |
```

### Verify via Web UI

Open `/outreach/status` and `/outreach/execution-log` to verify:
- Teams shown correctly
- Item counts match (7 total)
- Status reflects sends
- Distribution log populated

---

## Step 5 — Create Execution Log

Create: `reports/pilot-device-compliance/outreach/execution/week1-execution-log.md`

This is a master log for the Week 1 cycle. Fill in:

```markdown
# Week 1 Execution Log — 4WNET-MNS-KTG-RX

## 1. Distribution Summary

| Team | Message File | Status | Sent At | Sent By | Channel | Recipients | Notes |
|---|---|---|---|---|---|---|---|
| Service Team | message-service-team.md | sent | 2026-05-02 10:30 | [Your Name] | Slack | csmteam@company.com | — |
| Network Ops | message-network-ops.md | sent | 2026-05-02 10:35 | [Your Name] | Email | netops@company.com | — |
| BGP Team | message-bgp-team.md | sent | 2026-05-02 10:40 | [Your Name] | Slack | bgp-team@company.com | — |

## 2. Snapshot Summary

[Paste output from track_week1_outreach_execution.py above]

## 3. Response Tracking

(No responses yet, to be updated as CSVs arrive)

## 4. Safety Confirmations

- [x] No NetBox writes
- [x] No tokens
- [x] No automatic sends
- [x] Read-only Web UI
```

---

## Troubleshooting

### Message File Not Found

If Web UI returns 404 for `/outreach/{team}`:

```bash
ls -la reports/pilot-device-compliance/outreach/message-*.md
```

Ensure all 3 message files exist. If missing, regenerate via:

```bash
python3 tools/local/generate_week1_outreach_pack.py \
  --metadata reports/pilot-device-compliance/week1-metadata-collection.md \
  --template reports/pilot-device-compliance/week1-metadata-collection-template.csv \
  --output-dir reports/pilot-device-compliance/outreach
```

### Snapshot Script Fails

If script errors:

```bash
python3 tools/local/track_week1_outreach_execution.py \
  --device 4WNET-MNS-KTG-RX \
  --outreach-dir reports/pilot-device-compliance/outreach \
  --responses-dir reports/pilot-device-compliance/week1-responses \
  --output reports/pilot-device-compliance/outreach/execution/outreach-status-snapshot.md \
  --deadline 2026-05-08 \
  --reminder-date 2026-05-06 \
  --verbose 2>&1 | head -50
```

Check:
- Response directory exists: `mkdir -p reports/pilot-device-compliance/week1-responses`
- Outreach directory populated: `ls reports/pilot-device-compliance/outreach/`
- CSV template available: `ls reports/pilot-device-compliance/week1-metadata-collection-template.csv`

### Web UI Not Responding

```bash
curl -v http://127.0.0.1:8890/outreach 2>&1 | head -20
```

Check:
- Process running: `ps aux | grep uvicorn`
- Port available: `lsof -i :8890`
- Python syntax: `python3 -m py_compile webui/app.py`

---

## Timeline

| Date | Action | Status |
|---|---|---|
| 2026-05-02 | Send Week 1 messages to 3 teams | ← YOU ARE HERE |
| 2026-05-02–05-06 | Monitor for responses | Daily |
| 2026-05-06 | Send reminders to non-respondents | Conditional |
| 2026-05-08 EOD | Escalate overdue items | Conditional |
| 2026-05-09 | Final validation, prepare Week 2 | Closure |

---

## Safety Confirmations (Critical)

Before marking FASE 2.18 complete, verify:

- [ ] **No NetBox writes** — No `/sync`, no `apply`, no API calls to NetBox
- [ ] **No tokens in messages** — All messages verified for credentials
- [ ] **No automatic sends** — Operator sent each message manually
- [ ] **Read-only Web UI** — All routes are GET-only, no forms
- [ ] **Local files only** — No external API calls
- [ ] **Audit trail** — Distribution log and execution log populated
- [ ] **7/7 tests passing** — Run test suite

---

## Next Phase

→ **FASE 2.19 — Week 1 Daily Monitoring / Reminder Execution**

Continue with daily monitoring, response validation, reminders, and escalation cycles through 2026-05-09.

---

**Document Version:** 1.0
**Last Updated:** 2026-04-29
**Author:** k3g-monitoring-iac Team
