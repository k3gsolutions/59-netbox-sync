# FASE 3.0 — Read-Only Web UI for Compliance & Governance

**Status:** ✅ IMPLEMENTED
**Date:** 2026-04-28
**Version:** 3.0
**Security:** Read-only, no writes, no tokens

---

## Objective

Provide local web interface for browsing compliance reports, approval records, apply plans, batch results, and incidents without any write capabilities.

---

## Scope

### Included
- ✅ Dashboard with summary cards
- ✅ Device list and device detail
- ✅ Report viewer (markdown → HTML)
- ✅ Approval records (list + detail view)
- ✅ Apply plans (list + detail)
- ✅ Batch results (list + detail)
- ✅ Incidents (list + detail)
- ✅ Comparisons (list + detail)
- ✅ Simple search across .md files
- ✅ Safe file downloads
- ✅ Path traversal protection
- ✅ Denylist for sensitive files
- ✅ Responsive CSS styling

### Not Included (Future)
- ❌ Authentication / RBAC
- ❌ Approval actions
- ❌ Apply via UI
- ❌ NetBox API integration
- ❌ Edit/write any files
- ❌ POST/PATCH/DELETE endpoints

---

## Architecture

### Stack
- **Framework:** FastAPI (Python web framework)
- **Templates:** Jinja2 (HTML templating)
- **Styling:** CSS (plain, no JavaScript framework)
- **Markdown:** Optional markdown library (falls back to <pre> if not available)

### Services
1. **artifact_scanner.py**
   - List reports, devices, approvals, apply plans, batch results, incidents
   - Safe path resolution (prevent traversal)
   - Denylist enforcement

2. **markdown_loader.py**
   - Load markdown files
   - Render to HTML (safe)
   - Load JSON files

3. **report_index.py**
   - Parse report metadata
   - Extract metrics
   - Load index.json if available

### Routes
| Route | Method | Purpose |
|-------|--------|---------|
| `/` | GET | Dashboard home |
| `/devices` | GET | List all devices |
| `/devices/{device}` | GET | Device detail |
| `/reports/view` | GET | View markdown report |
| `/reports/download` | GET | Download file safely |
| `/approvals` | GET | List approvals |
| `/approvals/{id}` | GET | Approval detail |
| `/apply-plans` | GET | List apply plans |
| `/batch-results` | GET | List batch results |
| `/incidents` | GET | List incidents |
| `/comparisons` | GET | List comparisons |
| `/search` | GET | Search markdown files |
| `/health` | GET | Health check |

---

## Security Features

### Path Traversal Protection
- Blocks `..` in paths
- All paths resolved within `reports/` directory
- Validates against base path

### Denylist
Blocks access to:
- `payload.local.json` — sensitive configuration
- Files with `raw` in name — raw data (likely sensitive)
- Files with `token`, `password`, `secret` — credentials

### Read-Only Enforcement
- ✅ No POST endpoints
- ✅ No PATCH endpoints
- ✅ No DELETE endpoints
- ✅ No PUT endpoints
- ✅ All responses are read-only (HTML/JSON/files)

### No Tokens Required
- No NETBOX_WRITE_TOKEN needed
- No NETBOX_READ_TOKEN needed
- Reads only local files

### Safe File Access
- File downloads restricted to `.md`, `.json`, `.txt`
- Sensitive files blocked by denylist
- Markdown rendered (prevents script injection)

---

## Installation & Running

### Install Dependencies
```bash
# Create and activate venv
python3 -m venv .venv-ui
source .venv-ui/bin/activate

# Install
pip install -r webui/requirements.txt
```

### Run Server
```bash
python3 -m uvicorn webui.app:app --host 127.0.0.1 --port 8890 --reload
```

### Open UI
```
http://127.0.0.1:8890
```

---

## Testing

### Syntax Validation
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
- ✅ No POST routes
- ✅ No write code patterns
- ✅ Read-only enforced

---

## Usage Examples

### View a Report
1. Click "Dashboard"
2. Click "Latest Report" or go to `/reports/view?path=reports/pilot-device-compliance/pilot-device-compliance-20260428.md`
3. View rendered HTML, download .md

### Browse Approvals
1. Click "Approvals"
2. Filter by status: pending, approved, rejected, applied
3. Click approval name to view JSON detail
4. Download JSON

### Check Batch Results
1. Click "Batch Results"
2. See list of recent batches
3. Click to view result report (markdown)
4. Download report

### Search Across Docs
1. Navigate to `/search?q=device_id`
2. See matching files and line previews
3. Click to open in report viewer

---

## Limitations

**Known Limitations:**
- No authentication (local-only intended)
- No RBAC (all users see all files)
- No filters or advanced search (basic substring search only)
- Markdown rendering requires optional `markdown` library
- No real-time updates (static file reads)
- No approval workflow actions
- No NetBox API calls (by design)

**By Design:**
- ✅ Read-only (no writes)
- ✅ No tokens required
- ✅ Local only (no external access default)
- ✅ Simple (no complex dependencies)
- ✅ Safe (path traversal protected)

---

## Future Phases

### FASE 3.1 — Search & Filters
- Advanced search (regex, date range)
- Filter approvals by device, status, action
- Filter batch results by device, status
- Sort capabilities

### FASE 3.2 — Timeline Visualization
- Approval workflow timeline
- Batch execution timeline
- Incident timeline
- Gantt chart for device approvals

### FASE 3.3 — Authentication
- Login UI
- User roles (viewer, reviewer, admin)
- Session management
- RBAC groups

### FASE 3.4 — Approval Workflow UI
- Read-only approval detail with metadata
- No actions yet (still read-only)
- Show approval state machine
- Timeline of state changes

### FASE 3.5 — Approval Actions
- Requires FASE 3.3 + 3.4
- Approve button (still no apply)
- Reject button with comment
- Add to batch button (readonly, no execute)
- Requires RBAC + double-confirmation

---

## Configuration

### Change Port
```bash
python3 -m uvicorn webui.app:app --port 9999
```

### Allow External Access
```bash
python3 -m uvicorn webui.app:app --host 0.0.0.0 --port 8890
# WARNING: Not recommended without authentication
```

### Disable Auto-reload (Production)
```bash
python3 -m uvicorn webui.app:app --host 127.0.0.1 --port 8890
```

---

## Monitoring & Health

### Health Check
```bash
curl http://127.0.0.1:8890/health
# Response: {"status": "ok", "version": "3.0"}
```

### Logs
All requests logged by uvicorn (standard ASGI logging)

### Performance
- Lightweight (no database)
- Fast (file I/O only)
- Minimal CPU footprint

---

## Compliance

### FREEZE Status
- ✅ Respects project FREEZE (informational display)
- ✅ No bypass or ignore of FREEZE
- ✅ No apply actions possible
- ✅ No writes to NetBox
- ✅ No changes to files

### Security Compliance
- ✅ No unauthorized access to sensitive files
- ✅ Path traversal protected
- ✅ Denylist enforced
- ✅ No token leakage
- ✅ No external API calls

---

## Files & Directory Structure

```
webui/
  app.py                    # FastAPI application
  requirements.txt          # Python dependencies
  README.md                 # User guide
  services/
    artifact_scanner.py     # File discovery & safety
    markdown_loader.py      # Markdown rendering
    report_index.py         # Report parsing
  templates/
    base.html               # Base layout
    index.html              # Dashboard
    devices.html            # Device list
    device.html             # Device detail
    approvals.html          # Approval list
    approval_view.html      # Approval detail
    apply_plans.html        # Apply plan list
    batch_results.html      # Batch result list
    incidents.html          # Incident list
    comparisons.html        # Comparison list
    report_view.html        # Report viewer
    search.html             # Search results
  static/
    style.css               # Responsive stylesheet

docs/
  34-web-ui-readonly.md     # This documentation

tools/local/
  test_webui_readonly.py    # Security tests
```

---

## Checklist

✅ **Implementation**
- [x] FastAPI app with all routes
- [x] Jinja2 templates (13 pages)
- [x] CSS styling (responsive)
- [x] Services (artifact_scanner, markdown_loader, report_index)
- [x] Path traversal protection
- [x] Denylist enforcement
- [x] Safe file downloads
- [x] Markdown rendering (with fallback)

✅ **Testing**
- [x] Syntax validation
- [x] Security tests (7 tests)
- [x] Path traversal blocked
- [x] Denylist enforced
- [x] No POST routes
- [x] No write keywords

✅ **Documentation**
- [x] Installation instructions
- [x] Usage examples
- [x] Security features
- [x] Configuration options
- [x] Future phases
- [x] README.md (user guide)

✅ **Confirmations**
- [x] No NetBox writes
- [x] No tokens required
- [x] No POST/PATCH/DELETE
- [x] No /sync
- [x] No equipment modifications
- [x] Read-only only
- [x] Downloads safe
- [x] Path traversal blocked

---

## Status

**FASE 3.0 COMPLETE** ✅
**FASE 3.0.1 COMPLETE** ✅ (Test closure)

- ✅ Ready for local testing
- ✅ Ready for integration
- ✅ Ready for future phases
- ✅ All security tests passing (7/7)
- ✅ Zero write endpoints verified
- ✅ Path traversal blocked
- ✅ Denylist enforced

---

**Last Updated:** 2026-04-28T20:30:00Z
**Owner:** Claude Haiku 4.5
**Version:** 3.0
