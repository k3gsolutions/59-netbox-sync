# Operational Handoff Package

**Date:** 2026-04-29
**Status:** Ready for NOC/Operations team
**Version:** 1.0

---

## Executive Summary

k3g-monitoring-iac project is ready for operational handoff to Network Operations Center (NOC) and Engineering teams. All read-only functionality is production-ready. Staged write operations are controlled and validated.

### Current State

✅ **Web UI** — Production ready (read-only)
✅ **Approval Workflow** — Implemented (manual approval required)
✅ **Compliance Reporting** — Automated (read-only)
✅ **Service Engagement** — Ready for team engagement
✅ **Batch Operations** — Controlled with strict validation

### Security

✅ No write-capable POST/PATCH/DELETE routes to NetBox; local POST stays restricted to file saves and local validation
✅ Path traversal protected
✅ Sensitive downloads blocked
✅ CSV/JSON/TXT/LOG downloads allowed only for safe artifacts
✅ No tokens in files or logs
✅ All writes require explicit approval
✅ Audit trail for all operations
✅ Week 2 board can be prepared locally only after validation passes
✅ PT-BR copy review documented for operator UX
✅ Real Week 1 execution log and final validation artifacts available
✅ Cycle-002 Week 1 activation/preparation/intake/validation artifacts available
✅ Cycle-002 Week 1 response seed/re-validation artifacts available
✅ Cycle-002 Week 2 preparation artifacts available
✅ Cycle-002 Week 2 human review, proposed approvals, and readiness-gate artifacts available
✅ Cycle-002 Week 2 test decision seed and manual-approval-ready gate available
✅ Cycle-002 manual approval review, dry-run ApplyPlan generation, and dry-run validation artifacts available
✅ Cycle-002 dry-run execution gate, simulation, real-write readiness, authorization, preflight, execution package, and freeze artifacts available
✅ Cycle-002 real-write execution attempt was blocked safely in preflight because no `NETBOX_WRITE_TOKEN` existed and the execution package target endpoint was not executable

---

## How to Start

### 1. Start Web UI Server

```bash
cd /Users/keslleykssantos/projects/ativos/59-netbox_sync/k3g-monitoring-iac

# Start Web UI (port 8890)
python3 -m uvicorn webui.app:app --host 127.0.0.1 --port 8890 --reload

# Access at: http://127.0.0.1:8890
```

### 2. Access Dashboard

**URL:** http://127.0.0.1:8890

**Main Sections:**
- Dashboard (summary metrics)
- Devices (device list + detail)
- Service Engagement (team collaboration)
- Approval Queue (approval status)
- Batch Results (execution history)
- Compliance Reports (audit trail)
- Execution log and validation gate for real Week 1

### 3. Daily Checklist

- [ ] Open dashboard
- [ ] Check latest compliance report
- [ ] Review approval queue
- [ ] Check service engagement status
- [ ] Verify batch results
- [ ] Download reports if needed

---

## Core Workflows

### Read-Only Operations (NOC)

#### Daily Compliance Review
1. Open dashboard
2. Check "Latest Report" card
3. Review divergences
4. Check incidents
5. Archive report if reviewed

#### Device Drill-Down
1. Go to /devices
2. Select device
3. View compliance history
4. Check related approvals
5. Download reports

#### Approval Queue Monitoring
1. Go to /approval-queue
2. Filter by status (pending, approved, etc.)
3. Review approval timeline
4. Check state history
5. View related batch results

#### Service Engagement
1. Go to /service-engagement
2. Select device (e.g., 4WNET-MNS-KTG-RX)
3. Download engagement package
4. Open the pending-item editor
5. Save the response locally only
6. Download the generated CSV from the UI if needed
7. Track the generated CSV and validation report
8. Open the validation dashboard
9. Use the PT-BR friendly labels if the operator needs the UI in Portuguese
9. Run local validation or finalize responses
10. Check the real execution log and final validation report

#### Controlled Operation / Cycle-002
1. Open /controlled-operation
2. Review Cycle-002 start gate and Week 1 status
3. Use /controlled-operation/cycle-002/week1 for local command links and response seed guidance
4. Check intake and validation pages after responses exist
5. Use /controlled-operation/cycle-002/week2 for review board and local drafts
6. Use /controlled-operation/cycle-002/week2/review for human review status
7. Use /controlled-operation/cycle-002/approvals and /controlled-operation/cycle-002/approvals/readiness for proposed approvals and gate checks
8. Use /controlled-operation/cycle-002/approvals/manual-review for explicit human approval review
9. Use /controlled-operation/cycle-002/applyplan and /controlled-operation/cycle-002/applyplan/validation for local dry-run artifacts only
10. Use /controlled-operation/cycle-002/applyplan/dryrun-gate and /controlled-operation/cycle-002/applyplan/simulation for local simulation-only views
11. Use /controlled-operation/cycle-002/applyplan/real-write-readiness, /real-write-authorization, /real-write-preflight, /real-write-package, and /real-write-freeze as read-only gates
12. Do not write NetBox, apply, sync, or trigger automation from these pages

### Controlled Write Operations (Ops + Approver)

#### Staged Apply (Requires Approval)

```bash
# 1. Validate batch plan
python3 tools/local/validate_batch_staged_apply_plan.py \
  --plan reports/pilot-device-compliance/approvals/approved/batch-apply-plan-fixed.json \
  --expected-device-id 1890 \
  --expected-device 4WNET-MNS-KTG-RX

# 2. Dry-run (no writes)
python3 tools/local/apply_batch_staged_netbox_objects.py \
  --batch-plan reports/pilot-device-compliance/approvals/approved/batch-apply-plan-fixed.json \
  --netbox-url https://docs.k3gsolutions.com.br \
  --confirm-batch-id "BATCH_ID" \
  --operator "OPERATOR_NAME"

# 3. Real write (requires approval + token)
export NETBOX_WRITE_TOKEN="[TOKEN_FROM_APPROVER]"
python3 tools/local/apply_batch_staged_netbox_objects.py \
  --batch-plan reports/pilot-device-compliance/approvals/approved/batch-apply-plan-fixed.json \
  --netbox-url https://docs.k3gsolutions.com.br \
  --confirm-batch-id "BATCH_ID" \
  --operator "OPERATOR_NAME" \
  --confirm-real-write-batch \
  --enable-real-post-implementation
```

#### Approval Decision (Approver)

1. Review approval in queue (/approval-queue)
2. Check approval timeline (/approval-timeline/{id})
3. Review risk assessment
4. Approve/reject via ApprovalRecord state management:

```bash
# Approve
python3 tools/local/manage_approval_state.py \
  --approval-record reports/pilot-device-compliance/approvals/pending/approval-XXXX.json \
  --action approve \
  --reason "Approved by [NAME]"

# Reject
python3 tools/local/manage_approval_state.py \
  --approval-record reports/pilot-device-compliance/approvals/pending/approval-XXXX.json \
  --action reject \
  --reason "Does not meet criteria"
```

---

## Permissions & Roles

### NOC Operator
- **Read:** All reports, approvals, devices, batch results
- **Write:** None (read-only)
- **Responsibilities:**
  - Monitor approvals queue
  - Review compliance reports daily
  - Escalate issues to Approver
  - Download reports for archive

### Approver
- **Read:** All reports, approvals, compliance
- **Write:** Approve/reject approvals via CLI (not UI)
- **Responsibilities:**
  - Review approval records
  - Assess risk level
  - Make approval decisions
  - Provide feedback to service teams

### Operations (Batch Execution)
- **Read:** All reports, approvals, batch plans
- **Write:** Execute approved batches (with approval + token)
- **Responsibilities:**
  - Dry-run validation
  - Real batch execution
  - Post-execution compliance verification
  - Incident escalation if needed

### Service Team Lead
- **Read:** Service engagement materials, enrichment requirements
- **Write:** Metadata responses via the local pending-item modal
- **Responsibilities:**
  - Collect tenant/service_type/criticality
  - Provide evidence for approval
  - Respond to clarification requests

---

## Stopping Conditions (DO NOT PROCEED)

### Stop If:

❌ **Token appears in file or log**
- Immediately isolate the token file
- Revoke token in NetBox
- Escalate to security team

❌ **Compliance report has contradictions**
- Do not approve/execute
- Escalate to engineering
- Investigate root cause

❌ **Object already exists in NetBox**
- Batch will be blocked (all-or-none policy)
- Check why object exists
- Update ImportPlan if necessary

❌ **Critical incident opened**
- Pause all approvals/writes
- Investigate incident
- Resume only after resolution

❌ **Web UI security test fails**
- Do not deploy
- Debug test failure
- Fix before production use

❌ **ApplyPlan with incomplete payload**
- Do not execute
- Request payload re-validation
- Check staged_payload completeness

❌ **Device_id divergent between reports**
- Do not execute batch
- Verify device in NetBox
- Update ImportPlan device_id

---

## Maintenance & Monitoring

### Weekly Tasks

- [ ] Archive old compliance reports
- [ ] Clean up applied approvals
- [ ] Verify Web UI tests pass
- [ ] Check incident backlog
- [ ] Update service engagement status

### Monthly Tasks

- [ ] Review approval trends
- [ ] Audit approval decisions
- [ ] Check batch execution success rate
- [ ] Update documentation
- [ ] Plan next phase initiatives

### Emergency Procedures

#### If Web UI Crashes
1. Check error logs: stderr output
2. Verify jinja2 + dependencies installed
3. Restart server
4. Test with `/health` endpoint
5. Escalate if persistent

#### If NetBox API Unavailable
1. Check NetBox status page
2. Verify network connectivity
3. Check NETBOX_WRITE_TOKEN validity
4. Escalate to NetBox team
5. Resume when service restored

#### If Token Leaked
1. Revoke token immediately in NetBox
2. Isolate any exposed files
3. Escalate to security team
4. Request new token
5. Update CI/CD configs

---

## Operational Metrics

### Track These

| Metric | Target | Check |
|--------|--------|-------|
| Approval decision time | < 1 week | Weekly review |
| Batch execution success | 100% | After each batch |
| Compliance report frequency | Daily/Weekly | CI job output |
| Web UI uptime | 99.9% | Manual checks |
| Test pass rate | 7/7 (100%) | Before deploy |

---

## Handoff Checklist

- [x] Web UI ready (7/7 tests)
- [x] All documentation complete
- [x] Workflows documented
- [x] Security verified
- [x] Roles defined
- [x] Stopping conditions listed
- [x] Support contacts identified

---

## Support & Escalation

### For Questions

**NOC Operations Issues:**
- Contact: [OPS_LEAD_EMAIL]
- Slack: [OPS_SLACK_CHANNEL]

**Approval Decisions:**
- Contact: [APPROVER_EMAIL]
- Escalation: [SUPERVISOR_EMAIL]

**Web UI / Technical Issues:**
- Contact: [ENGINEERING_LEAD_EMAIL]
- GitHub: [ISSUES_LINK]

### Escalation Path

1. **Level 1:** Team lead (immediate response)
2. **Level 2:** Supervisor (24hr response)
3. **Level 3:** Director (urgent escalation)

---

## Next Phases

### FASE 2.12 (Week 1+ Execution)
- Response intake from service teams
- Metadata validation
- ApprovalRecord creation

### FASE 2.13 (Week 2+ Review)
- Risk assessment
- Approval decisions
- Batch readiness

### FASE 2.14 (Week 3+ Execution)
- Batch execution
- Compliance verification
- Incident resolution

### FASE 3.5+ (Future)
- Batch scheduling UI
- Service compliance trends
- Advanced filtering/reporting

---

## References

- **docs/46-service-owner-engagement.md** — Process documentation
- **docs/47-operational-handoff.md** — Detailed runbook
- **ROADMAP.md** — Full project roadmap
- **CHANGELOG.md** — Version history
- **webui/README.md** — Web UI documentation

---

**Status:** ✅ READY FOR OPERATIONS HANDOFF
**Date:** 2026-04-29
**Approved By:** [TECH_LEAD]
**NOC Start Date:** 2026-05-01

## Atualização Semana 2

- Execução real da Semana 1 registrada.
- Semana 2 em revisão humana.
- Registros de Aprovação seguem apenas proposed/pending.

## Multi-cycle operation

- Controlled-operation index and Cycle-002 start gate are available in read-only mode.
- Expansion stays recommendation-only.
