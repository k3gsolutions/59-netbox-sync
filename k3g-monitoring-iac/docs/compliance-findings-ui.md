# Compliance Findings UI (FASES COMPARE-004)

## Overview

The compliance job detail UI displays findings from policy comparison in a dedicated "Achados de Compliance" section.

Findings are shown as a sortable table with severity, scope, object, rule, and recommendation. Raw output and sensitive data are hidden.

---

## Location

**Route:** `GET /compliance/jobs/{job_id}`

**Template:** `webui/templates/compliance_job_detail.html`

---

## Section: Achados de Compliance

### Button: "Comparar com políticas"

**Visibility:** Shown after job creation  
**Enabled:** Only if parser validation is successful (`parser_safety_validation.decision != 'PARSER_SAFETY_INVALID'`)  
**Action:** POST `/compliance/jobs/{job_id}/compare` with `{operator, confirm_local_compare: true}`  
**On success:** Refresh page to show findings

### Summary Cards

Displayed when findings exist:
- **Blockers** — count of blocker findings (red badge if > 0)
- **Errors** — count of error findings
- **Warnings** — count of warning findings
- **Info** — count of info findings

### Findings Table

**Columns:**
- Severity (info, warning, error, blocker) — color-coded badge
- Scope (interface, bgp, route_policy, prefix_list, snmp)
- Object (object_name from finding)
- Rule (rule_id from finding)
- Title (human-readable title)
- Recommendation (action text)

**Sorting:** By severity (blocker → error → warning → info)

**Filtering:** Can filter by scope or severity via UI controls (optional)

### Device-level Findings

For each device in the job:
- Device name
- Count of findings per severity
- Link to COMPLIANCE-FINDINGS.md (downloadable via `/reports/download?path=...`)

---

## What is Shown

✓ Severity and status  
✓ Scope, object type, object name  
✓ Rule ID  
✓ Title and description  
✓ Evidence (source, field, value type)  
✓ Recommendation  
✓ Link to COMPLIANCE-FINDINGS.md markdown  
✓ Summary counts (blockers, errors, warnings, info)  

---

## What is NOT Shown

✗ Raw SSH output (hidden in any form)  
✗ Raw SNMP output  
✗ NetBox tokens or credentials  
✗ Sensitive config data  
✗ "Aplicar correção" / "Apply Fix" button (no auto-remediation)  
✗ Raw JSON artifacts (only summary displayed)  

---

## Finding Flags Visibility

Every finding shown in UI has:
- `write_required: false` — explicitly false, never requires NetBox write
- `approval_required: false` — explicitly false, never requires approval

These are enforced on the backend and guaranteed in the JSON response.

---

## State Transitions

**Before compare runs:**
- "Comparar com políticas" button is disabled (parser not validated)
- No findings section shown

**After compare succeeds:**
- "Comparar com políticas" button is disabled (compare already run)
- "Achados de Compliance" section appears with summary + table
- Links to COMPLIANCE-FINDINGS.md become available

**If compare finds blockers:**
- Section title shows red "BLOCKED" indicator
- Blocker findings highlighted in red
- Summary shows blocker count prominently

---

## Markdown Links

Each device's findings can be downloaded as COMPLIANCE-FINDINGS.md via:
```
/reports/download?path=compliance/jobs/<job_id>/comparison/devices/<device_id>/COMPLIANCE-FINDINGS.md
```

The link is provided in the UI as a downloadable report per device.

---

## Safety Guarantees

✓ **No write buttons** — finding table is read-only  
✓ **No auto-remediation** — operator must review manually  
✓ **No credential exposure** — tokens and passwords filtered  
✓ **No raw output shown** — only structured findings  
✓ **No approval shortcuts** — each finding flagged `approval_required: false`  

---

## References

- **FASE COMPLIANCE-COMPARE-004** — Compliance Findings UI
- **Template:** `webui/templates/compliance_job_detail.html`
- **Route:** `GET /compliance/jobs/{job_id}` in `webui/app.py`
- **Service:** `webui/services/compliance_compare.py`
