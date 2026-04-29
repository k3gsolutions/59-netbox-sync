# Operational Handoff Procedures

**Status:** FASE 3.4
**Date:** 2026-04-29
**Version:** 1.0

---

## Overview

This document defines the procedures for handing over k3g-monitoring-iac to the Operations team (NOC) and Engineering team.

---

## Pre-Handoff Checklist

### Code Quality
- [x] All 7/7 security tests passing
- [x] Python syntax valid (py_compile)
- [x] Zero POST/PATCH/DELETE routes
- [x] Path traversal protected
- [x] Sensitive downloads blocked

### Documentation
- [x] Workflows documented
- [x] Roles defined
- [x] Stopping conditions listed
- [x] Support contacts identified
- [x] Escalation path defined

### Operational Readiness
- [x] Web UI tested
- [x] Approval Queue ready
- [x] Service Engagement ready
- [x] Batch operations validated
- [x] Compliance reports working

### Security
- [x] No tokens in code
- [x] No secrets exposed
- [x] Audit trails enabled
- [x] All writes require approval
- [x] Read-only enforcement verified

---

## Deployment Steps

### 1. Pre-Deployment Verification

```bash
# Syntax check
python3 -m py_compile webui/app.py

# Run security tests
python3 tools/local/test_webui_readonly.py

# Expected output: 7/7 tests passed ✅
```

### 2. Environment Setup

```bash
# Install dependencies
pip install -r webui/requirements.txt

# Verify jinja2 + fastapi
python3 -c "import jinja2, fastapi; print('OK')"
```

### 3. Start Web UI

```bash
# Development mode (with reload)
python3 -m uvicorn webui.app:app --host 127.0.0.1 --port 8890 --reload

# Production mode (without reload)
python3 -m uvicorn webui.app:app --host 0.0.0.0 --port 8890 --workers 4
```

### 4. Verify Access

```bash
# Test health endpoint
curl http://127.0.0.1:8890/health

# Expected response: {"status":"ok","version":"3.0"}
```

### 5. Run Full Test Suite

```bash
python3 tools/local/test_webui_readonly.py

# All 7/7 tests should PASS
```

---

## Role-Based Permissions

### NOC Operator

**Access Level:** Read-only

**Allowed Actions:**
- View dashboard
- View compliance reports
- View device details
- View approval queue
- View batch results
- Download reports (safe files only)
- Search files

**Restricted Actions:**
- No POST requests
- No file uploads
- No approvals (no API)
- No batch execution
- No device configuration

**Daily Checklist:**
1. Open dashboard (http://127.0.0.1:8890)
2. Review latest compliance report
3. Check approval queue status
4. Monitor incident backlog
5. Archive reviewed reports

### Approver

**Access Level:** Read + Approval decisions (CLI only)

**Allowed Actions:**
- All NOC operator actions
- Approve/reject approvals via CLI
- Review approval timelines
- Check risk assessments
- Comment on approvals

**Command Example:**
```bash
python3 tools/local/manage_approval_state.py \
  --approval-record approvals/pending/approval-XXXX.json \
  --action approve \
  --reason "Approved by [NAME]"
```

**Restricted Actions:**
- No writes via Web UI
- No direct NetBox API calls
- No batch execution without ops handoff

### Operations (Batch Executor)

**Access Level:** Read + Controlled writes

**Allowed Actions:**
- All NOC operator + Approver actions
- Execute approved batches (with token)
- Validate batch plans
- Dry-run execution
- Real batch execution (with approval)

**Command Flow:**
```bash
# 1. Validate
python3 tools/local/validate_batch_staged_apply_plan.py --plan ...

# 2. Dry-run
python3 tools/local/apply_batch_staged_netbox_objects.py --batch-plan ...

# 3. Real write (requires approval + token)
export NETBOX_WRITE_TOKEN="[TOKEN_FROM_APPROVER]"
python3 tools/local/apply_batch_staged_netbox_objects.py \
  --confirm-real-write-batch \
  --enable-real-post-implementation
```

**Restricted Actions:**
- No unapproved writes
- No token storage in files
- No /sync execution
- No equipment config changes

---

## Emergency Procedures

### If Web UI Crashes

1. **Check logs:**
   ```bash
   tail -50 /path/to/error.log
   ```

2. **Restart server:**
   ```bash
   # Kill existing process
   pkill -f "uvicorn webui.app"

   # Start fresh
   python3 -m uvicorn webui.app:app --host 127.0.0.1 --port 8890
   ```

3. **Verify:**
   ```bash
   curl http://127.0.0.1:8890/health
   ```

4. **If still failing:**
   - Check Python version (3.8+)
   - Verify jinja2 installed
   - Check port 8890 availability
   - Escalate to engineering

### If NetBox Connection Lost

1. **Check connectivity:**
   ```bash
   ping docs.k3gsolutions.com.br
   ```

2. **Check token validity:**
   ```bash
   # If token available, test API
   curl -H "Authorization: Token $NETBOX_WRITE_TOKEN" \
     https://docs.k3gsolutions.com.br/api/dcim/devices/
   ```

3. **Actions:**
   - Wait for NetBox recovery
   - Resume batch operations when available
   - No writes during outage

### If Token Leaked

1. **IMMEDIATE:**
   - Revoke token in NetBox UI
   - Remove from any exposed files
   - Notify security team

2. **Investigation:**
   - Check git logs for token exposure
   - Scan bash history
   - Check environment variables

3. **Recovery:**
   - Request new token from approver
   - Update approver contacts
   - Resume operations

---

## Monitoring & Health Checks

### Daily Checks

```bash
# Run security tests
python3 tools/local/test_webui_readonly.py

# Check Web UI status
curl http://127.0.0.1:8890/health

# Verify latest report
ls -lrt reports/pilot-device-compliance/current/
```

### Weekly Tasks

```bash
# Archive old reports
python3 tools/local/archive_compliance_report.py --report [FILE]

# Clean up applied approvals
find reports/pilot-device-compliance/approvals/applied/ -mtime +30 -delete

# Update compliance index
python3 tools/local/update_context_index.py
```

### Monthly Review

- [ ] Approval trends analysis
- [ ] Batch execution metrics
- [ ] Incident backlog review
- [ ] Documentation updates
- [ ] Team feedback collection

---

## Runbook Examples

### Example 1: Daily Compliance Review

**Time:** 30 minutes, start of shift

```
1. Open Web UI: http://127.0.0.1:8890
2. Click "Latest Report" card
3. Review divergences in section 5
4. Check action items needed (section 7)
5. If approved, archive report
6. Add notes to context/NEXT_ACTIONS.md
```

### Example 2: Service Team Engagement (Week 1)

**Time:** 1-2 hours, send on Monday

```
1. Go to /service-engagement/4WNET-MNS-KTG-RX
2. Download service-owner-engagement-package.md
3. Send to service teams:
   - Service Team: 5 subinterfaces
   - Network Ops: 1 IP
   - BGP Team: 1 BGP peer
4. Set reminder for Thu EOD (responses due)
5. Track responses in week1-metadata-collection.md
```

### Example 3: Approval Review & Decision

**Time:** 30-45 minutes per approval

```
1. Go to /approval-queue
2. Filter by "pending"
3. Click approval item
4. Review timeline + state history
5. Check risk assessment
6. Make decision (approve/reject)
7. Command:
   python3 tools/local/manage_approval_state.py \
     --action approve/reject \
     --reason "..."
```

### Example 4: Batch Execution (Ops Only)

**Time:** 1-2 hours

```
1. Validate plan:
   python3 tools/local/validate_batch_staged_apply_plan.py ...

2. Dry-run:
   python3 tools/local/apply_batch_staged_netbox_objects.py ...

3. Get approval from Approver:
   - Approval ID + reason
   - NETBOX_WRITE_TOKEN

4. Real write:
   export NETBOX_WRITE_TOKEN="..."
   python3 tools/local/apply_batch_staged_netbox_objects.py \
     --confirm-real-write-batch \
     --enable-real-post-implementation

5. Verify results:
   - Check batch-apply-result-*.md
   - Verify objects in NetBox
   - Archive results
```

---

## Transition Timeline

### Week 1 (2026-04-29 to 2026-05-08)
- Deploy Web UI
- NOC team familiarization
- Service team engagement begins
- Metadata collection

### Week 2 (2026-05-09 to 2026-05-15)
- Response processing
- ApprovalRecord creation
- Risk assessment
- Approval queue managed by Approver

### Week 3+ (2026-05-16+)
- Batch execution begins (Ops)
- Full operational handoff
- Continuous monitoring
- Future phase planning

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Web UI uptime | 99.9% | Manual checks |
| Security test pass rate | 100% (7/7) | Automated tests |
| Approval decision time | < 5 days | Review cycle |
| Batch execution success | 100% | Post-execution reports |
| Metadata collection rate | 100% | Week 1 responses |

---

## Handoff Sign-Off

```
Handoff Date: 2026-04-29

Technical Lead Approval:
Name: ________________
Date: ________________

Operations Manager:
Name: ________________
Date: ________________

Approver:
Name: ________________
Date: ________________
```

---

## See Also

- OPERATIONAL-HANDOFF-PACKAGE.md (operational summary)
- docs/46-service-owner-engagement.md (team engagement process)
- ROADMAP.md (full project roadmap)
- webui/README.md (Web UI technical docs)
