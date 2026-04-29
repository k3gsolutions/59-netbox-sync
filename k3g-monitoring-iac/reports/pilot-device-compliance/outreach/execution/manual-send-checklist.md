# Manual Send Checklist — Week 1 Outreach

**Device:** 4WNET-MNS-KTG-RX
**Process:** Manual message distribution (zero automation)
**Deadline:** 2026-05-08 EOD

---

## Before Sending

### 1. Verify Message
- [ ] Open Web UI: /outreach
- [ ] Click team link (service-team, network-ops, or bgp-team)
- [ ] Read full message
- [ ] Confirm no secrets/tokens in message
- [ ] Confirm no hardcoded email addresses (customize)

### 2. Verify Recipients
- [ ] Confirm team lead name and email
- [ ] Confirm team members to CC (if any)
- [ ] Verify no inactive emails
- [ ] Test email address format

### 3. Verify Attachment
- [ ] Download template CSV: week1-metadata-collection-template.csv
- [ ] Confirm correct columns:
  - Service Team: object_key, tenant, service_type, criticality, owner, evidence
  - Network Ops: object_key, interface, vrf, owner, evidence
  - BGP Team: object_key, remote_asn, remote_bgp_group, owner, evidence
- [ ] Confirm no data pre-filled (should be empty template)
- [ ] Confirm UTF-8 encoding

### 4. Verify Deadline
- [ ] Deadline: 2026-05-08 EOD
- [ ] Add to email reminder (suggest they respond by 2026-05-07)
- [ ] Note: No responses after 2026-05-08 EOD accepted

---

## Sending

### 1. Create Draft

**Subject line:**
```
[Device 4WNET-MNS-KTG-RX] Week 1 Metadata Collection — {TEAM}
```

**Body:**
```
Copy from /outreach/{team} (render as text or plain markdown)
```

**Attachments:**
```
week1-metadata-collection-template.csv
(for the specific team)
```

**Recipients:**
```
To: team-lead@company.com
Cc: [team members, if applicable]
```

### 2. Customization

Replace placeholders in message:
- `[K3G Lead]` → your name
- `[email]` → your email
- `[Name/Email]` → specific team contact
- `[Slack]` → team slack channel (optional)

### 3. Send

- [ ] Review entire email one more time
- [ ] No secrets visible
- [ ] CSV attachment included
- [ ] Recipients correct
- [ ] **Send**

---

## After Sending

### 1. Record in Log

Update: `outreach-distribution-log.md`

```
| Service Team | message-service-team.md | 2026-05-02T09:30:00Z | Your Name | email | team@company.com | sent | Notes |
```

**Required fields:**
- **Sent At:** ISO 8601 timestamp
- **Sent By:** your name
- **Channel:** email, slack, teams, etc.
- **Recipients:** team distribution list
- **Status:** sent
- **Notes:** optional (e.g., "CSV template attached", "Reminder in email")

### 2. Monitor Responses

Expected location:
```
reports/pilot-device-compliance/week1-responses/
├── service-team-response.csv
├── network-ops-response.csv
└── bgp-team-response.csv
```

Check daily for incoming CSVs.

### 3. When Response Received

- [ ] Save CSV to week1-responses/
- [ ] Verify filename matches expected (service-team-response.csv, etc.)
- [ ] Check encoding (UTF-8)
- [ ] Run validation:
  ```bash
  python3 tools/local/validate_week1_responses.py \
    --template week1-metadata-collection-template.csv \
    --responses-dir week1-responses \
    --output week1-response-validation.md \
    --device 4WNET-MNS-KTG-RX
  ```
- [ ] Update log with status: **response_received**

### 4. Validate Response

- [ ] Run: `python3 tools/local/check_week1_response_status.py`
- [ ] Review validation report
- [ ] Check for:
  - All required fields filled
  - No secrets/sensitive data
  - No special characters
  - Values match validation rules
- [ ] Update log with validation result:
  - **complete** → ready for Week 2
  - **partial_response** → send to team for clarification
  - **response_missing** → plan reminder for 2026-05-06

---

## Reminder Workflow (2026-05-06)

If team status = "response_missing" or "partial_response" on 2026-05-06:

### 1. Get Reminder Message

- [ ] Go to Web UI: /outreach/reminders/{team}
- [ ] Copy reminder message
- [ ] Send manually to team

### 2. Record Reminder

Update log:
```
| Service Team | reminder-service-team.md | 2026-05-06T10:00:00Z | Your Name | email | team@company.com | reminded | Reminder sent |
```

### 3. Monitor for Response

- [ ] Check for response by 2026-05-07 EOD
- [ ] If received: validate and update log
- [ ] If not received: plan escalation for 2026-05-08

---

## Escalation Workflow (2026-05-08 EOD)

If team status = "overdue" or "response_missing" after 2026-05-08 EOD:

### 1. Get Escalation Template

- [ ] Go to Web UI: /outreach/reminders/escalation
- [ ] Copy escalation message
- [ ] Customize with team info

### 2. Send Escalation

- [ ] Send to director/supervisor (not team lead)
- [ ] Include summary of:
  - Team
  - Items requested
  - Response deadline (2026-05-08 EOD)
  - Action needed

### 3. Record Escalation

Update log:
```
| Service Team | escalation-template.md | 2026-05-08T18:00:00Z | Your Name | email | director@company.com | escalated | No response by deadline |
```

### 4. Follow Up

- [ ] Director responds within 1 business day
- [ ] Escalation resolution recorded
- [ ] Next steps determined

---

## Troubleshooting

### Problem: Email bounced
- [ ] Verify email address is correct
- [ ] Use Web UI /outreach to confirm team contact
- [ ] Try alternate contact method (Slack, Teams)
- [ ] Update log with bounce note

### Problem: CSV received but corrupted
- [ ] Ask team to re-send
- [ ] Verify UTF-8 encoding
- [ ] Check column headers match template
- [ ] Note in validation report

### Problem: No response by reminder date
- [ ] Send reminder (2026-05-06)
- [ ] If still no response by 2026-05-07 EOD: escalate

### Problem: Partial response (some fields missing)
- [ ] Mark as: partial_response
- [ ] Identify missing fields
- [ ] Send clarification request
- [ ] Set new deadline (2026-05-08 EOD for clarification)

---

## Safety Checklist

- [ ] No tokens/secrets in messages
- [ ] No API calls triggered
- [ ] No automatic sends
- [ ] No NetBox writes
- [ ] No configuration changes
- [ ] All tracking via local files
- [ ] All decisions manual (operator controlled)
- [ ] Audit trail logged (distribution log + snapshot)

---

**Status:** Ready for Week 1 outreach execution.

