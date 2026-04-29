# Week 1 Operator Runsheet — 4WNET-MNS-KTG-RX

**Timeline:** 2026-05-02 (start) → 2026-05-09 (closure)

---

## Step 1: Start Web UI

```bash
cd /Users/keslleykssantos/projects/ativos/59-netbox_sync/k3g-monitoring-iac
source .venv/bin/activate
python3 -m uvicorn webui.app:app --host 127.0.0.1 --port 8890 --reload
```

**Verify:** Open http://127.0.0.1:8890 → shows k3g Compliance & Governance header

---

## Step 2: Open Outreach Pages

Verify all pages load correctly:

```
http://127.0.0.1:8890/outreach                         ✓
http://127.0.0.1:8890/outreach/service-team           ✓
http://127.0.0.1:8890/outreach/network-ops            ✓
http://127.0.0.1:8890/outreach/bgp-team               ✓
http://127.0.0.1:8890/outreach/status                 ✓
http://127.0.0.1:8890/outreach/execution-log          ✓
http://127.0.0.1:8890/outreach/reminders              ✓
http://127.0.0.1:8890/operations/handoff               ✓
http://127.0.0.1:8890/operations/readiness             ✓
```

---

## Step 3: Send Messages Manually (2026-05-02)

For each team:

### Service Team

1. Open: http://127.0.0.1:8890/outreach/service-team
2. Copy message text
3. Attach CSV template: `reports/pilot-device-compliance/week1-metadata-collection-template.csv`
4. Send via **Slack/Email/Teams** to: `service-team@company.com`
5. Record in `outreach-distribution-log.md`:
   - Team: Service Team
   - Status: sent
   - Sent At: [timestamp]
   - Sent By: [your name]
   - Channel: [Slack/Email/Teams]
   - Recipients: service-team@company.com

### Network Ops

1. Open: http://127.0.0.1:8890/outreach/network-ops
2. Copy message text
3. Attach CSV template
4. Send to: `network-ops@company.com`
5. Record in distribution log

### BGP Team

1. Open: http://127.0.0.1:8890/outreach/bgp-team
2. Copy message text
3. Attach CSV template
4. Send to: `bgp-team@company.com`
5. Record in distribution log

---

## Step 4: Generate Initial Snapshot

After sending all messages:

```bash
cd /Users/keslleykssantos/projects/ativos/59-netbox_sync/k3g-monitoring-iac

python3 tools/local/track_week1_outreach_execution.py \
  --device 4WNET-MNS-KTG-RX \
  --outreach-dir reports/pilot-device-compliance/outreach \
  --responses-dir reports/pilot-device-compliance/week1-responses \
  --output reports/pilot-device-compliance/outreach/execution/outreach-status-snapshot.md \
  --deadline 2026-05-08 \
  --reminder-date 2026-05-06
```

**Verify:** Check http://127.0.0.1:8890/outreach/status → shows 3 teams, 7 items, 0 responses

---

## Step 5: Update Execution Log

Edit: `reports/pilot-device-compliance/outreach/execution/week1-execution-log.md`

Fill in:
- Date/time of distribution
- Channels used
- Recipients for each team
- Any issues encountered

---

## Step 6: Daily Monitoring (2026-05-02 to 2026-05-08)

**Every day:**

1. Check for response CSVs in: `reports/pilot-device-compliance/week1-responses/`
2. If CSVs arrived, validate:
   ```bash
   python3 tools/local/validate_week1_responses.py \
     --template reports/pilot-device-compliance/week1-metadata-collection-template.csv \
     --responses-dir reports/pilot-device-compliance/week1-responses \
     --output reports/pilot-device-compliance/week1-response-validation.md \
     --device 4WNET-MNS-KTG-RX
   ```
3. Update snapshot:
   ```bash
   python3 tools/local/track_week1_outreach_execution.py \
     --device 4WNET-MNS-KTG-RX \
     --outreach-dir reports/pilot-device-compliance/outreach \
     --responses-dir reports/pilot-device-compliance/week1-responses \
     --output reports/pilot-device-compliance/outreach/execution/outreach-status-snapshot.md \
     --deadline 2026-05-08 \
     --reminder-date 2026-05-06
   ```
4. Check dashboard: http://127.0.0.1:8890/outreach/status

---

## Step 7: Send Reminders (2026-05-06)

On or after 2026-05-06:

1. Check snapshot for teams with status != `complete` or `response_received`
2. For each non-responding team, open reminder:
   - http://127.0.0.1:8890/outreach/reminders/service-team
   - http://127.0.0.1:8890/outreach/reminders/network-ops
   - http://127.0.0.1:8890/outreach/reminders/bgp-team
3. Copy reminder message
4. Send manually to team
5. Update distribution-log.md with:
   - Status: reminder_sent
   - Sent At: [timestamp]

---

## Step 8: Escalate Overdue (2026-05-08 EOD)

At end of 2026-05-08:

1. Check snapshot for overdue items (status = `overdue`)
2. If any overdue:
   - Open: http://127.0.0.1:8890/outreach/reminders/escalation
   - Copy escalation message
   - Customize with team name + items
   - Send to director/coordination
   - Update distribution-log.md with:
     - Status: escalated
     - Escalated At: [timestamp]
     - Escalated By: [your name]

---

## Step 9: Finalize Week 1 (2026-05-09)

1. Run final validation:
   ```bash
   python3 tools/local/validate_week1_responses.py \
     --template reports/pilot-device-compliance/week1-metadata-collection-template.csv \
     --responses-dir reports/pilot-device-compliance/week1-responses \
     --output reports/pilot-device-compliance/week1-response-validation.md \
     --device 4WNET-MNS-KTG-RX
   ```

2. Prepare Week 2:
   ```bash
   python3 tools/local/prepare_week2_review.py \
     --device 4WNET-MNS-KTG-RX \
     --device-id 1890 \
     --validation reports/pilot-device-compliance/week1-response-validation.md \
     --candidates reports/pilot-device-compliance/week2-review-candidates.md \
     --responses-dir reports/pilot-device-compliance/week1-responses \
     --output-dir reports/pilot-device-compliance/week2-review
   ```

3. Fill in: `week1-final-summary.md`

---

## Emergency Contacts

If something breaks:

1. Web UI won't start: Check port 8890 not in use: `lsof -i :8890`
2. Snapshot fails: Check directories exist: `ls reports/pilot-device-compliance/week1-responses/`
3. CSV validation fails: Check template path: `ls reports/pilot-device-compliance/week1-metadata-collection-template.csv`
4. Messages missing: Check: `ls reports/pilot-device-compliance/outreach/message-*.md`

---

## Timeline Summary

| Date | Action | Owner |
|---|---|---|
| 2026-05-02 | Send messages (Step 3) | Operator |
| 2026-05-02 | Generate snapshot (Step 4) | Operator |
| 2026-05-02–05 | Daily monitoring (Step 6) | Operator |
| 2026-05-06 | Send reminders (Step 7) | Operator |
| 2026-05-08 EOD | Escalate (Step 8) | Operator |
| 2026-05-09 | Finalize (Step 9) | Operator |

---

**Status:** Runsheet Ready for Execution
