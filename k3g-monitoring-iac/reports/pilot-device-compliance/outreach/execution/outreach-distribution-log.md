# Outreach Distribution Log — 4WNET-MNS-KTG-RX

**Device:** 4WNET-MNS-KTG-RX (device_id: 1890)
**Week 1 Window:** 2026-05-02 to 2026-05-08 EOD
**Generated:** 2026-04-29

---

## Objetivo

Registrar quando, para quem e por qual canal os pacotes Week 1 foram enviados.

Manual log. Operador atualiza após enviar cada mensagem.

---

## Distribution Status

| Team | Message File | Sent At | Sent By | Channel | Recipients | Status | Notes |
|---|---|---|---|---|---|---|---|
| Service Team | message-service-team.md | — | — | — | — | **not_sent** | Awaiting manual send |
| Network Ops | message-network-ops.md | — | — | — | — | **not_sent** | Awaiting manual send |
| BGP Team | message-bgp-team.md | — | — | — | — | **not_sent** | Awaiting manual send |

---

## Status Values

Allowed status values:

- **not_sent** — Message not yet sent
- **sent** — Message sent, awaiting response
- **acknowledged** — Team acknowledged receipt
- **response_received** — CSV received, awaiting validation
- **partial_response** — Some items responded, some pending
- **complete** — All items responded, validation complete
- **overdue** — No response by 2026-05-08 EOD
- **escalated** — Escalation triggered, director notified

---

## How to Update

1. Open Web UI → /outreach/{team}
2. Copy message
3. Send manually via email/Slack/Teams
4. Update this table:
   - **Sent At:** timestamp when sent (ISO 8601)
   - **Sent By:** your name
   - **Channel:** email, slack, teams, etc.
   - **Recipients:** team names/emails
   - **Status:** sent

5. When response received:
   - Save CSV to: `reports/pilot-device-compliance/week1-responses/`
   - Expected filenames:
     - service-team-response.csv
     - network-ops-response.csv
     - bgp-team-response.csv
   - Update **Status:** response_received

6. Run validation:
   ```bash
   python3 tools/local/validate_week1_responses.py ...
   python3 tools/local/check_week1_response_status.py ...
   ```

7. Update **Status:** based on validation result

---

## Critical Dates

- **2026-05-02:** Week 1 starts. First messages sent.
- **2026-05-06:** Reminder date (for non-responders, send reminder)
- **2026-05-08 EOD:** Absolute deadline. No more responses accepted.
- **2026-05-09:** Escalation triggered if needed.

---

## Example Workflow

### Step 1: Send Service Team Message

1. Go to Web UI: /outreach/service-team
2. Copy entire message
3. Create email draft
4. Add attachment: week1-metadata-collection-template.csv
5. Send to: service-team@company.com
6. Update log:

```
| Service Team | message-service-team.md | 2026-05-02T09:30:00Z | John Smith | email | service-team@company.com | sent | CSV template attached |
```

### Step 2: Monitor for Response

- Check email for CSV response
- Save as: service-team-response.csv in week1-responses/
- Run: `python3 tools/local/validate_week1_responses.py`
- Update log:

```
| Service Team | message-service-team.md | 2026-05-02T09:30:00Z | John Smith | email | service-team@company.com | response_received | CSV received 2026-05-05, 4/5 items |
```

### Step 3: Validate Response

- Check validation report
- If valid: status = complete
- If partial: status = partial_response (need clarification)
- If missing: status = response_missing (send reminder on 2026-05-06)

---

## Reminders (2026-05-06)

For teams without response or with partial response, send reminder message.

Reminder messages available at: /outreach/reminders

Update log:

```
| Service Team | reminder-service-team.md | 2026-05-06T10:00:00Z | John Smith | email | service-team@company.com | reminded | Reminder sent for missing subinterfaces |
```

---

## Escalation (2026-05-08 EOD)

If team status still overdue after deadline, escalate to director.

Escalation template available at: /outreach/reminders/escalation

Update log:

```
| Service Team | escalation-template.md | 2026-05-08T18:00:00Z | John Smith | email | director@company.com | escalated | No response by deadline. Escalated. |
```

---

## Notes

- **No automatic sends:** All messages sent manually by operator.
- **No API calls:** All tracking via file system + Web UI.
- **No tokens:** No credentials stored or exposed.
- **Audit trail:** This log is the official record of Week 1 outreach.

---

**Status:** Ready to populate with outreach execution data.

