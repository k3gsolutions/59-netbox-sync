# Changelog

All notable changes to k3g-monitoring-iac netops_netbox_sync integration documented here.

## [3.0.1] — 2026-04-28

### FASE 3.0.1 — Web UI Test Closure
- ✅ Dependencies verified: fastapi==0.104.1, uvicorn==0.24.0, jinja2==3.1.2, markdown==3.5.1
- ✅ Syntax validation: 0 errors (app.py, app_simple.py, services)
- ✅ Security tests: 7/7 PASSING
- ✅ Live server: http://127.0.0.1:8890 (all routes responding)
- ✅ Path traversal blocked, denylist enforced, no POST routes
- ✅ Read-only enforcement verified

### FASE 2.7 — First Real Batch POST Execution ✅
- ✅ Batch ID: 4340469f-f73c-431f-853d-59355b32c54c
- ✅ Device: 4WNET-MNS-KTG-RX (device_id: 1890)
- ✅ Objects created: Eth-Trunk1 (ID: 18229), GigabitEthernet0/5/0 (ID: 18230)
- ✅ All-or-none policy enforced, audit trail complete
- ✅ FREEZE ready for closure

## [3.0] — 2026-04-28

### FASE 3.0 — Read-Only Web UI
- ✅ FastAPI application with Jinja2 templates
- ✅ 8 main routes, security features, file downloads
- ✅ Zero write endpoints, zero NetBox calls, zero credentials

## [2.7] — 2026-04-28

### FASE 2.7 — Real Batch POST
- ✅ Batch apply plan: device_id=1890, all payloads complete
- ✅ Validation script operational
- ✅ Incident investigation: INC-001/INC-002 root cause identified

## [2.6] — 2026-04-28

### FASE 2.6 — Real Batch POST with Fake Testing
- ✅ apply_batch_staged_netbox_objects.py implemented
- ✅ Fake response support, comprehensive validation
- ✅ All-or-none policy, test fixtures, token safety

## [2.5] — 2026-04-28

### FASE 2.5 — Manual NetBox Audit
- ✅ INC-001/INC-002 verified as unrelated (2026-04-04 objects)
- ✅ NO_ROLLBACK_NEEDED decision

## [2.4] — 2026-04-28

### FASE 2.4 — Incident Investigation
- ✅ Root cause analysis complete
- ✅ Corrective actions implemented

## [2.3] — 2026-04-28

### FASE 2.3 — Controlled Batch Staged Apply
- ✅ build_batch_staged_apply_plan.py, validate_batch_staged_apply_plan.py
- ✅ render_batch_staged_apply_plan.py, apply_batch_staged_netbox_objects.py
- ✅ Dry-run mode, all-or-none policy, batch result reporting

## [2.2] — 2026-04-24

### FASE 2.2 — Controlled Batch Design
- ✅ Design documents (docs/31, docs/32)
- ✅ Gates and policies defined

## [2.1] — 2026-04-21

### FASE 2.1 — Design Completion
- ✅ Workflow consolidation, policy documentation

## [2.0] — 2026-04-20

### FASE 2.0 — First Real NetBox Write
- ✅ apply_staged_netbox_object.py: first object created (Eth-Trunk0, ID: 18228)
- ✅ Safety checks, token security, dry-run mode

## [1.9] — 2026-04-19

### FASE 1.9 — Staged Apply Dry-Run Engine
- ✅ ApplyPlan generation, validation, rendering, simulation
- ✅ 13 readiness checks, zero API calls

## [1.8] — 2026-04-18

### FASE 1.8 — Staged Apply Design
- ✅ Architecture and contract documents

## [1.7] — 2026-04-17

### FASE 1.7 — Approval State Management
- ✅ manage_approval_state.py: state machine, audit trail

## [1.6] — 2026-04-16

### FASE 1.6 — End-to-End Approval Pilot
- ✅ Eth-Trunk0 pilot: complete workflow validation

## [1.5] — 2026-04-15

### FASE 1.5 — ApprovalRecord + Dry-run
- ✅ Scripts for record creation, summary rendering, validation

## [1.4] — 2026-04-14

### FASE 1.4 — Approval Workflow Design
- ✅ Workflow states, rules, audit requirements

## [1.3] — 2026-04-13

### FASE 1.3 — ImportPlan Read-Only
- ✅ /compliance/import-plan endpoint, classification system

## [1.2.1] — 2026-04-12

### FASE 1.2.1 — History Maintenance
- ✅ cleanup_compliance_history.py, export_compliance_csv.py

## [1.2] — 2026-04-11

### FASE 1.2 — Report Comparison
- ✅ compare_compliance_reports.py: divergence tracking

## [1.1] — 2026-04-10

### FASE 1.1 — Report History
- ✅ Directory structure, metadata, archiving

## [1.0.1] — 2026-04-09

### FASE 1.0.1 — Report Quality
- ✅ Hostname fallback, divergence separation

## [1.0] — 2026-04-08

### FASE 1.0 — Core Functionality
- ✅ Device compliance analysis, NetBox integration, 58 tests

---

**Status:** ✅ FASE 2.7 COMPLETE — Batch POST executed, 2 objects created
**Next:** FASE 2.8 — Base Inventory Expansion Policy
