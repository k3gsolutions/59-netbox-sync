# Web UI — Read-Only Compliance & Governance Dashboard

**Version:** 3.0
**Status:** Local development
**Security:** Read-only, no writes, no tokens

---

## Overview

Local web interface for reviewing compliance reports, approval records, apply plans, batch results, and incidents.

- FastAPI + Jinja2 templates
- Static CSS (no JavaScript framework)
- Path traversal protection
- Denylist for sensitive files
- Local-only POST for pending-item responses
- No NetBox API integration

---

## Installation

### Option 1: Virtual Environment (Recommended)

```bash
# Create venv
python3 -m venv .venv-ui

# Activate
source .venv-ui/bin/activate  # macOS/Linux
# or
.venv-ui\Scripts\activate  # Windows

# Install dependencies
pip install -r webui/requirements.txt
```

### Option 2: Use Existing venv

```bash
.venv/bin/pip install -r webui/requirements.txt
```

---

## Running the UI

```bash
# If using .venv-ui
source .venv-ui/bin/activate
python3 -m uvicorn webui.app:app --host 127.0.0.1 --port 8890 --reload

# If using existing .venv
.venv/bin/python -m uvicorn webui.app:app --host 127.0.0.1 --port 8890 --reload
```

Then open: **http://127.0.0.1:8890**

---

## Features

### Dashboard
- Summary cards (devices, reports, approvals, incidents)
- Latest report link
- Latest batch result
- Quick navigation links

### Devices
- List all devices with history
- Device detail page
- Related approval records

### Reports
- View markdown reports (formatted HTML)
- Download as .md
- Download local CSV/JSON/TXT/LOG artifacts with safe extension checks
- Search across reports

### Controlled Operation
- Read-only multi-cycle index
- Cycle detail, start gate, archive, handoff
- Cycle-002 Week 1 and Week 2 review flow
- Real-write execution/readiness/verification/compliance/closure pages are read-only views of local artifacts

### Compliance Jobs
- Job review dashboard for prepared local jobs
- Job detail page with selected devices, safety block, and markdown gate artifacts
- Explicit collection start gate, still local-only
- Read-only collection plan per device
- Read-only collection simulation and safety validation
- SSH read-only policy, SSH preflight, controlled SSH execution, and raw output safety validation
- Vendor collection profiles, redaction, and parser staging
- Huawei NE8000 local parser baseline, parsed inventory artifacts, and parser safety validation
- Findings review, remediation draft generation, draft safety validation, and promotion gate
- Draft artifacts live under `reports/compliance/jobs/<job_id>/remediation/drafts/`
- No automatic collection, no SSH/SNMP/NETCONF, no NetBox writes

### Approvals
- List approval records by status (pending, approved, rejected, applied)
- View single approval (formatted JSON)
- Download JSON

### Apply Plans
- List all apply plans
- View as JSON or formatted
- Download

### Batch Results
- List batch apply results
- View markdown report
- Download

### Incidents
- List incident reports
- View markdown
- Download

### Comparisons
- List device comparisons
- View and download

### Service Engagement
- Device-level pending item queue
- Modal editor for Week 1 responses
- Unified CSV output for Week 1 validation
- Local audit trail for each save
- `ip_address` items can prefill detected interface/VRF and use `relation_type`
- Validation dashboard for Week 1 progress
- Local finalize action to prepare Week 2 when ready
- PT-BR-friendly copy for operators and NOC users
- Real Week 1 execution status and final validation are documented locally
- Next-step guidance is shown after save and on the device dashboard

### Controlled Operation
- Read-only multi-cycle index and cycle detail views
- Cycle-002 start gate, handoff, archive, and Week 1 pages
- Week 1 activation, preparation, intake, validation, and response seed pages are local-only
- Week 2 preparation page shows review board, decisions CSV, and local drafts
- Week 2 review, proposed approvals, and approval readiness pages are read-only
- Week 2 test decision seed can move the flow to a single proposed approval for manual review
- Manual approval review, approved-copy view, dry-run ApplyPlan generation, and dry-run validation pages are local-only
- No write buttons, no apply, no sync, no rollback automation

### Search
- Simple search across .md files
- Search in reports/, docs/, context/

---

## Security

### Protections
- ✅ Path traversal blocked (`..` disallowed)
- ✅ Denylist blocks sensitive files:
  - `payload.local.json`
  - Files with "raw" in name
  - Files with "token", "password", "secret"
- ✅ POST only for local response saving
- ✅ POST only for local validation/finalize pipeline
- ✅ No POST/PATCH/DELETE on controlled-operation review/approval pages
- ✅ Read-only only
- ✅ No NetBox API calls
- ✅ No write tokens needed
- ✅ Secret terms blocked in pending-item forms
- ✅ Remediation drafts stay local and never create ApprovalRecord or ApplyPlan

### Safe File Access
- Paths validated against `reports/` directory only
- Extensions whitelist: `.md`, `.json`, `.txt`, `.csv`, `.log`
- Markdown rendered to HTML (prevents script injection)
- File downloads blocked for sensitive extensions

---

## Structure

```
webui/
  app.py                 # FastAPI application
  requirements.txt       # Python dependencies
  README.md             # This file
  services/
    artifact_scanner.py # Path safety, file discovery
    markdown_loader.py  # Load and render markdown
    report_index.py     # Parse report metrics
  templates/
    base.html           # Layout template
    index.html          # Dashboard
    devices.html        # Device list
    device.html         # Device detail
    compliance_jobs.html # Compliance job dashboard
    compliance_job_detail.html # Compliance job detail
    approvals.html      # Approval list
    approval_view.html  # Approval detail
    apply_plans.html    # Apply plan list
    batch_results.html  # Batch result list
    incidents.html      # Incident list
    comparisons.html    # Comparison list
    report_view.html    # Report viewer
    search.html         # Search results
    service_engagement_pending_items.html # Pending queue page
    partials/           # Shared pending-item fragments
  static/
    style.css           # Stylesheet
    app.js              # Modal editor behavior
```

---

## Testing

### Syntax Check
```bash
python3 -m py_compile webui/app.py webui/services/*.py
```

### Security Tests
```bash
python3 tools/local/test_webui_readonly.py
```

Tests verify:
- ✅ Path traversal blocked
- ✅ Sensitive files blocked
- ✅ Local-only POST routes
- ✅ No write keywords in code
- ✅ Read-only enforced

---

## Limitations

- **No authentication** — local only, no login
- **No RBAC** — all users see everything
- **No approval actions** — read-only, no approve/reject/apply buttons
- **No NetBox API** — reads local files only
- **Basic search** — no advanced filters yet
- **Markdown rendering** — requires `markdown` library or fallback to <pre>

---

## Future Phases

- **FASE 3.1** — Advanced filters and search
- **FASE 3.2** — Approval timeline visualization
- **FASE 3.3** — Authentication/RBAC
- **FASE 3.4** — Read-only approval workflow UI (still no apply)
- **FASE 3.5** — Apply via UI (requires 3.4 + RBAC + approval)

---

## Configuration

### Port
Change in `app.py` or via command-line:
```bash
python3 -m uvicorn webui.app:app --host 127.0.0.1 --port 9999 --reload
```

### Host
Change to allow external access (not recommended for production):
```bash
python3 -m uvicorn webui.app:app --host 0.0.0.0 --port 8890 --reload
```

### Auto-reload
Remove `--reload` for production:
```bash
python3 -m uvicorn webui.app:app --host 127.0.0.1 --port 8890
```

---

## Troubleshooting

### Port Already in Use
```bash
# Use different port
python3 -m uvicorn webui.app:app --port 8891
```

### Jinja2 Not Found
```bash
# Install dependencies
pip install -r webui/requirements.txt
```

### Templates Not Found
Ensure you're running from project root:
```bash
cd /path/to/k3g-monitoring-iac
python3 -m uvicorn webui.app:app --host 127.0.0.1 --port 8890 --reload
```

---

## Status

✅ Implemented:
- Dashboard with summary cards
- Device list and detail
- Report viewer with markdown rendering
- Approval records (list and detail)
- Apply plans list
- Batch results list
- Incidents list
- Comparisons list
- Simple search
- Path traversal protection
- Denylist for sensitive files
- CSS styling (responsive)

⏳ Not implemented (future phases):
- Authentication
- RBAC
- Approval actions
- Advanced filters
- Timeline visualization
- NetBox API integration

---

## Support

- **Read-only only** — No changes made to files or NetBox
- **Local only** — No external access by default
- **Safe downloads** — Sensitive files blocked
- **FREEZE honored** — UI respects project freeze status (informational only)

## Week 2 Review

- Tela de revisão humana da Semana 2 em PT-BR.
- Registros propostos ficam em `approvals/pending/`.
- Nenhuma ação aplica mudanças no NetBox.

---

**Last updated:** 2026-04-28
**Owner:** Claude Haiku 4.5
**Version:** 3.0

## Multi-cycle operation

- Read-only controlled-operation views live at `/controlled-operation`.
- Cycle-002 start gate and expansion evaluation are local and advisory only.
