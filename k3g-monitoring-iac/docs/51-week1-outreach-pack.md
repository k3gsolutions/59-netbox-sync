# FASE 2.15 — Week 1 Outreach Pack

**Status:** COMPLETE
**Date:** 2026-04-29
**Version:** 1.0

---

## Overview

FASE 2.15 prepares communication materials for Week 1 response collection.

Generates outreach pack: summary, team messages, response tracker, scripts.

No NetBox writes. No tokens. Local only.

---

## What is Outreach Pack?

Collection of documents + scripts to:
1. Notify teams of metadata collection task
2. Provide response templates
3. Track response status
4. Escalate if needed

---

## Deliverables

### Documents (5 files)

**Location:** reports/pilot-device-compliance/outreach/

1. **outreach-summary.md**
   - Overview of task
   - Teams involved
   - Timeline
   - Status summary

2. **message-service-team.md**
   - Ready-to-send email
   - 5 subinterfaces listed
   - Fields explained
   - Example filled
   - Deadline emphasized

3. **message-network-ops.md**
   - Ready-to-send email
   - 1 IP address listed
   - Fields explained
   - Example filled
   - Deadline emphasized

4. **message-bgp-team.md**
   - Ready-to-send email
   - 1 BGP peer listed
   - Fields explained
   - Example filled
   - Deadline emphasized

5. **week1-response-tracker.md**
   - Status table per team
   - Responded / Total counts
   - Last update timestamp
   - Pending items
   - Blocker / Next action
   - Escalation rules
   - Timeline

### Scripts (2)

1. **generate_week1_outreach_pack.py**
   - Reads: week1-metadata-collection.md
   - Reads: week1-metadata-collection-template.csv
   - Generates: outreach-summary.md, week1-response-tracker.md
   - Execution: Single run after FASE 2.12
   - Output: Ready to distribute

2. **check_week1_response_status.py** (optional)
   - Scans: week1-responses/ directory
   - Counts: rows per CSV
   - Updates: week1-response-tracker.md
   - Execution: Periodic during Week 1 (daily)
   - Output: Status report with team progress

---

## Execution

### Generate Outreach Pack

```bash
python3 tools/local/generate_week1_outreach_pack.py \
  --device 4WNET-MNS-KTG-RX \
  --collection reports/pilot-device-compliance/week1-metadata-collection.md \
  --template reports/pilot-device-compliance/week1-metadata-collection-template.csv \
  --output-dir reports/pilot-device-compliance/outreach
```

**Output:**
```
✓ Extracted items from collection
  Subinterfaces: 5
  IP addresses: 1
  BGP peers: 1
✓ Outreach summary saved: outreach-summary.md
✓ Response tracker saved: week1-response-tracker.md
```

**Time:** ~1 second
**Cost:** Zero (no API calls, no writes)

### Monitor Response Status (Optional)

```bash
python3 tools/local/check_week1_response_status.py \
  --responses-dir reports/pilot-device-compliance/week1-responses \
  --outreach-dir reports/pilot-device-compliance/outreach \
  --deadline 2026-05-08
```

**Output:**
- week1-response-status.md (generated/updated)
- Summary counts (0/3 teams responded, etc.)

---

## Timeline

```
2026-04-29: FASE 2.15 executed (DONE)
            └─ generate_week1_outreach_pack.py runs
            └─ Generates outreach-summary.md
            └─ Generates week1-response-tracker.md

2026-05-02: Distribute messages to teams
            └─ message-service-team.md
            └─ message-network-ops.md
            └─ message-bgp-team.md
            └─ CSV templates attached

2026-05-02 to 2026-05-08: Teams fill responses
            └─ check_week1_response_status.py runs daily
            └─ Updates week1-response-tracker.md
            └─ Escalates if no response by 2026-05-06

2026-05-08 EOD: Response deadline
            └─ Any late responses marked overdue
            └─ Escalation triggered

2026-05-09: Validation (FASE 2.12 re-run)
            └─ Responses validated
            └─ Generate week1-response-validation.md

2026-05-09: Review board (FASE 2.13)
            └─ Validated items → review board
            └─ Week 2 begins
```

---

## Response Locations

**Where teams send responses:**

```
reports/pilot-device-compliance/week1-responses/
├── service-team-response.csv (5 rows expected)
├── network-ops-response.csv (1 row expected)
└── bgp-team-response.csv (1 row expected)
```

---

## Validation Rules

**Per Response CSV:**

| Check | Rule | Action |
|-------|------|--------|
| File exists | Must exist | Continue validation |
| Format | CSV, UTF-8 | Skip if corrupted |
| Columns | object_key + fields | Skip if missing |
| Values | Non-empty required | Classify as needs_clarification |
| Secrets | No passwords/tokens | Block (escalate) |
| Characters | ASCII only | Skip if non-ASCII |

---

## Escalation Matrix

| Trigger | Owner | Action | Deadline |
|---------|-------|--------|----------|
| No response by 2026-05-06 | Team lead | Send reminder | 2026-05-07 |
| Partial response by 2026-05-08 | Team lead | Request completion | 2026-05-09 EOD |
| No response by 2026-05-08 EOD | Director | Escalate | 2026-05-10 |
| Blocked items (secrets found) | Security | Investigate | ASAP |

---

## Web UI Integration

**New Routes (FASE 3.7):**
- GET /outreach — Overview of outreach pack
- GET /outreach/{team} — Team-specific message
- GET /operations/handoff — Operational procedures
- GET /operations/readiness — Pre-deployment checklist

**Read-only:** All routes are GET, no POST/PATCH/DELETE.

---

## Customization

Before sending messages, customize:

```markdown
## Contatos

- **K3G Lead:** [YOUR NAME / YOUR EMAIL]
- **Service Team Lead:** [NAME / EMAIL]
- **Network Ops Lead:** [NAME / EMAIL]
- **BGP Team Lead:** [NAME / EMAIL]
```

---

## Safety Confirmations

✅ Zero NetBox writes
✅ Zero NetBox API calls
✅ Zero tokens
✅ Local file I/O only
✅ No approval automation
✅ No ApprovalRecords generated
✅ Audit trail: week1-response-tracker.md
✅ Templated messages (no hardcoding)

---

## FAQ

**Q: What if a team doesn't respond?**
A: Mark as still_pending, escalate after deadline. Week 2 review cannot start.

**Q: What if response is partial?**
A: Classify as needs_clarification, request completion. Item waits for clarification.

**Q: Can I send message before 2026-05-02?**
A: Yes. Generate outreach pack immediately, send when ready. Just ensure 1-week window for responses.

**Q: What if outreach files already exist?**
A: Script will overwrite. Backup old pack if needed.

---

## See Also

- FASE 2.11 — Week 1 Metadata Collection
- FASE 2.12 — Week 1 Response Intake
- FASE 2.13 — Week 2 Review Board
- FASE 3.7 — Operations Dashboard
- docs/46-service-owner-engagement.md
- docs/48-week1-response-intake.md
