# Roadmap — NetBox Sync Compliance

## Vision

Automated, read-only compliance analysis for network devices. Local report history, trend tracking, minimal secrets exposure.

## Current UI Milestones (Completed)

- FASE 3.10.2: modal save/save-and-close + safe local pipeline ✅
- FASE 3.12: response validation dashboard + UAT audit view ✅
- FASE 2.25: UAT cleanup and Week 1 real-readiness guardrails ✅
- FASE 3.13: PT-BR friendly UI copy review ✅
- FASE 2.26: UAT decision / cleanup execution ✅
- FASE 2.27: real Week 1 activation flow ✅
- FASE 2.28: real Week 1 execution via Web UI ✅
- FASE 2.29: real Week 1 final validation + Week 2 gate ✅
- FASE 3.14: operational usability polish ✅
- FASE 4.30: multi-cycle operation index ✅
- FASE 4.31: Cycle-002 start gate ✅
- FASE 4.32: multi-cycle Web UI ✅
- FASE 4.33: controlled expansion policy ✅
- FASE 4.34: Cycle-002 intake activation ✅
- FASE 4.35: Cycle-002 Week 1 preparation ✅
- FASE 4.36: Cycle-002 Week 1 response intake ✅
- FASE 4.37: Cycle-002 Week 1 validation ✅
- FASE 4.38: Cycle-002 Week 1 response seed / form ✅
- FASE 4.39: Cycle-002 Week 1 re-validation ✅
- FASE 4.40: Cycle-002 Week 2 preparation ✅
- FASE 4.41: Cycle-002 Week 2 human review ✅
- FASE 4.42: Cycle-002 promote drafts to proposed ApprovalRecords ✅
- FASE 4.43: Cycle-002 approval readiness gate ✅
- FASE 4.44: Cycle-002 Week 2 decision seed ✅
- FASE 4.45: Cycle-002 Week 2 re-review ✅
- FASE 4.46: Cycle-002 proposed approval test ✅
- FASE 4.47: Cycle-002 approval readiness re-gate ✅
- FASE 4.48: Cycle-002 manual approval review ✅
- FASE 4.49: Cycle-002 dry-run ApplyPlan generation ✅
- FASE 4.50: Cycle-002 dry-run ApplyPlan validation ✅
- FASE 4.51: Cycle-002 dry-run execution gate ✅
- FASE 4.52: Cycle-002 dry-run simulation ✅
- FASE 4.53: Cycle-002 real-write readiness gate ✅
- FASE 4.54: Cycle-002 real-write authorization package ✅
- FASE 4.55: Cycle-002 real-write final preflight ✅
- FASE 4.56: Cycle-002 real-write execution package ✅
- FASE 4.57: Cycle-002 execution package validation ✅
- FASE 4.58: Cycle-002 final no-write freeze ✅
- FASE 4.59: Cycle-002 real-write execution attempt blocked safely (no token, no write) ✅
- FASE 4.60: Cycle-002 post-write verification not applicable ✅
- FASE 4.61: Cycle-002 post-write compliance re-run not applicable ✅
- FASE 4.62: Cycle-002 closure package built locally ✅
- **FASE 3.16: Web UI Convention Registry Integration Reconciliation ✅**
- **FASE 3.16.1: Registry Fallback Hardening ✅**
- **FASE 2.33: Compliance Registry Operationalization ✅**
- **FASE 2.38: Manual Promotion to Proposed ApprovalRecords ✅**
- **FASE 2.39: ApplyPlan Readiness Gate ✅**

## Timeline

### ✅ FASE 1.0 — Core Read-Only Analysis (2026-04-28)

Device compliance analysis:
- SSH device collection (HuaweiNE8000)
- NetBox inventory loading with safe handling
- Automatic device_id resolution
- Object-level divergence detection
- Markdown report generation
- 58 unit tests, 100% mock

### ✅ FASE 1.1 — Report History & Versioning (2026-04-28)

Local report archiving:
- Structured directory layout (current/history)
- ISO8601 timestamps for audit trail
- index.json with metadata
- .gitignore to exclude raw JSON credentials
- archive_compliance_report.py script
- Documentation & examples

### FASE 1.2 — ImportPlan read-only (Q2 2026)

Gerar plano de enriquecimento do NetBox sem escrever nada.
- ImportPlan JSON com propostas de ação
- Relatório Markdown com propostas classificadas
- Classificação: safe_create_staged / needs_review / blocked / ignore
- Seção "Revisão humana obrigatória" no relatório
- Validação de naming convention para propostas

**Critério de aceite:**
- nenhum write no NetBox
- objeto fora da naming convention vira needs_review
- relatório indica por que não pode importar

**Estimated effort:** 2 semanas

### FASE 1.3 — NetBox Staged Import com aprovação humana (Q2-Q3 2026)

Permitir criação staged/planned no NetBox somente para objetos aprovados e conformes.
- Propostas de importação controladas e auditáveis
- `safe_create_staged` para casos conformes
- `needs_review` para objetos sem naming convention ou com dados incompletos
- `blocked` para casos ambíguos ou perigosos
- `ignore` para objetos temporários ou fora da política
- ImportPlan diferencia `base_inventory` vs `service`
- Interfaces base podem ser `safe_create_staged` sem naming de serviço
- Interfaces de serviço/subinterfaces só podem ser `safe_create_staged` com naming válido
- Subinterfaces inválidas viram `needs_review`
- BGP peers continuam `needs_review`
- IPs sem associação/naming continuam `needs_review`
- Escrita futura com token separado e fluxo de aprovação humana

**Critério de aceite:**
- exige aprovação humana
- exige dry-run anterior
- exige token de escrita separado
- não importa objeto fora da naming convention
- não sobrescreve objeto existente automaticamente
- não deleta objetos

**Estimated effort:** 4 semanas

### FASE 1.4 — UI/CLI de aprovação (Q3 2026)

Permitir que humano revise o ImportPlan, aprove/rejeite propostas e baixe relatórios.
- Lista de propostas com evidências
- Destaque de naming inválido e problemas de tenant/service_type
- Aprovação/rejeição de propostas
- Auditoria de quem aprovou e quando
- Download de relatório Markdown e JSON sanitizado

**Critério de aceite:**
- lista propostas
- mostra evidências
- destaca naming inválido
- permite aprovar apenas objetos conformes
- registra auditoria

**Estimated effort:** 3 semanas

### FASE 1.5 — Advanced Analytics (Q3 2026)

Dashboard & alerts:
- Compliance scoring (% divergences resolved)
- Severity trends over time
- Device comparison
- Email/Slack alerts for new divergences
- Scheduled daily/weekly analysis
- Report scheduling API

**Estimated effort:** 4 semanas

### ✅ FASE 2.0 — First Real Staged Write (2026-04-28)

**Completed:**
- Approval ID: `c9363dfb`
- Object: `Eth-Trunk0`
- Method: `POST`
- Result: `201 Created`
- NetBox object ID: `18228`
- Scope: 1 object
- No `PATCH`
- No `DELETE`
- No `/sync`
- No equipment configuration
- Tags verified before POST
- apply-result report generated
- Compliance pós-apply generated
- Before/after comparison generated
- Token not exposed

### ✅ FASE 2.7 — Real Batch POST Authorized Pilot

**Completed:**
- Batch ID: `4340469f`
- Device: `4WNET-MNS-KTG-RX` (device_id `1890`)
- Objects created: `Eth-Trunk1` (ID `18229`) and `GigabitEthernet0/5/0` (ID `18230`)
- Tags: `discovery:netops_netbox_sync`, `discovery:staged`, `source:device`, `approval:<approval_id>`
- Repeat batch run blocked by existing objects, validating all-or-none preflight
- No `PATCH`, no `DELETE`, no `/sync`, no equipment configuration changes
- Token not exposed
- Incident 18201/18202 from 2026-04-04 closed, no rollback needed
- Post-batch compliance and before/after comparison generated

### ✅ FASE 3.10 — Web UI Pending Item Editor Modal + Backend CSV Generation (2026-04-29)

**Completed:**
- Device-level pending-item queue added to Service Engagement / Responses / Week 2 pages
- Modal editor renders only the fields needed by team/object type
- Local-only POST saves unified Week 1 CSV and append-only audit JSON
- Secret keyword blocking and traversal blocking enforced
- No NetBox writes, no apply, no `/sync`, no ApprovalRecord auto-create, no ApplyPlan auto-create

### ✅ FASES 2.47-3.19 — Real Write Full Cycle (2026-04-29)

**Completed:**
- FASE 2.47-2.52: Pre-execution authorization & validation gates
- FASE 2.53: Real write execution (one-shot POST)
- FASE 2.54-2.56: Post-write verification, compliance re-run, closure
- FASE 2.57: Pilot final archive (SHA256 hashes, secret exclusion)
- FASE 2.58: Operational handoff decision (READY/WITH_RESTRICTIONS/NOT_READY)
- FASE 3.19: Web UI post-write integration (5 routes, read-only)
- 78+ tests passing (FASES 2.47-2.56)
- Pilot 4WNET-MNS-KTG-RX executed full cycle successfully
- System ready for controlled operation

### FASE 4.0 — Controlled Operation (Q2-Q3 2026)

**Completed (2026-04-29):**
- ✅ FASE 2.59: Final documentation & context sync
- ✅ FASE 2.60: Controlled operation baseline (scope, restrições, fluxo obrigatório)
- ✅ FASE 3.20: Controlled operation readiness tests (10 tests, all passing)
- ✅ FASE 4.1: Controlled operation cycle v1 (first cycle template)
- ✅ FASE 4.2: Cycle intake validation (scope guardrails, decision, markdown report)
- ✅ FASE 4.3: Week 1 preparation (structure creation, instructions, status)
- ✅ FASE 4.4: Operational metrics (cycle tracking, item metrics, guardrail status)
- ✅ FASE 4.5: Week 1 response intake (count, classify by team, decision)
- ✅ FASE 4.6: Week 1 validation (secret blocking, compliance checks, decision)
- ✅ FASE 4.7: Week 2 preparation (review board, decisions CSV, approval drafts)
- ✅ FASE 4.8: Week 2 human review validation (decision field, reviewer, approval_record_allowed)
- ✅ FASE 4.9: Promote approved Week 2 drafts to proposed ApprovalRecords
- ✅ FASE 4.10: Approval readiness gate (validate proposed records, block secrets)
- ✅ FASE 4.11: Manual approval review (human reviewer approves/rejects ApprovalRecords)
- ✅ FASE 4.12: Dry-run ApplyPlan generation (generate from approved records, mode=dry_run)
- ✅ FASE 4.13: Dry-run ApplyPlan validation (validate structure, safety flags, forbidden methods)
- ✅ FASE 4.14: Dry-run execution gate (pre-simulation validation)
- ✅ FASE 4.15: Dry-run simulation execution (100% local, no network calls)
- ✅ FASE 4.16: Real write readiness gate (consolidate governance chain)
- ✅ FASE 4.17: Build real write authorization package (consolidate evidence, generate phrase)
- ✅ FASE 4.18: Real write final preflight gate (validate authorization phrase)
- ✅ FASE 4.19: Build real write execution package (locked execution_allowed=false)
- ✅ FASE 4.20: Validate real write execution package (structural validation)
- ✅ FASE 4.21: Final no-write freeze check (5-layer safety validation)
- ✅ FASE 4.22: Execute real write once (22 preflight checks, one-shot POST, token via env)
- ✅ FASE 4.23: Post-write verification (GET-only verification of created objects)
- ✅ FASE 4.24: Compliance re-run after write (read-only local compliance checks)
- ✅ FASE 4.25: Closure package (consolidate execution/verification/compliance results)
- ✅ FASE 4.26: Final archive (SHA256 hashes, secret detection, manifest generation)
- ✅ FASE 4.27: Operational handoff decision (READY / WITH_RESTRICTIONS / ACTION_REQUIRED)
- ✅ FASE 4.28: Update controlled operation metrics (cycle tracking, success/warning/failure counts)
- ✅ FASE 4.29: Create next cycle template (scope constraints, plan, checklist, status)
- ✅ System: CONTROLLED_OPERATION_READY confirmed
- ✅ Test suites: 202+ tests all passing

**Planned (Next):**
- FASE 4.30: Cycle-002 readiness assessment (apply FASES 4.2-4.29 to second device)

**Guardrails (Enforced):**
- One device per cycle initially ✓
- Max 1-3 objects per cycle ✓
- POST only (no PATCH/DELETE initially) ✓
- No /sync, no bulk write, no automatic retry/rollback ✓
- Week 1 + Week 2 review + approval + dry-run + authorization + preflight + execution + verification + compliance + closure mandatory ✓
- Zero token exposure in logs/saves ✓
- One-shot execution only ✓
- Manual review at each gate ✓

**Status:** Foundation complete. Ready for cycle execution.

### FASE 2.1 — Tag Bootstrap & Batch Staged Apply (Q2-Q3 2026)

**Planned:**
- Controlled batch apply for approved staged objects
- Missing tag verification/bootstrap before apply
- Approval workflow integration with apply
- Per-object preflight checks and audit trail
- Still no DELETE, no unsafe update, no bulk overwrite
- Report before/after comparison as standard

**Estimated effort:** 4 semanas

**Recommended next:** FASE 2.2 — política para múltiplos staged applies em lote controlado, ainda limitado a base_inventory

### FASE 2.2 — Multi-Device Sync (Later)

Read-write mode beyond staged apply:
- Bulk device collection
- Recommended fixes to NetBox
- Device configuration changes (with approval)
- Multi-device dashboard
- Backup/rollback procedures

**Estimated effort:** 8 weeks

## Current Status

**FASE 1.2 COMPLETE** ✅

- core analysis working
- report history structure live
- ImportPlan read-only implemented
- local scripts tested
- documentation complete

**Next:** FASE 1.3 NetBox Staged Import com aprovação humana

## Blockers/Risks

- None current
- BGP plugin: optional best-effort (marked in warnings)
- Circuits: availability varies by NetBox version (marked partial)

## Dependencies

- Python 3.8+ (standard library only for local scripts)
- FastAPI (existing)
- Pynetbox (existing)
- Netmiko (existing)
- No additional dependencies planned for FASE 1.x

## Success Metrics

- [ ] FASE 1.0: 58 tests passing, 100% read-only
- [ ] FASE 1.1: Archive script tested, no secrets in Git
- [ ] FASE 1.2: Compare script working, CSV export tested
- [ ] FASE 1.3: Web UI loads, shows timeline
- [ ] FASE 1.4: Alerts working, compliance score calculated
- [ ] FASE 2.0: Sync working on test device, rollback tested

## Notes

- Keep all local scripts in Python standard library (no pip)
- Maintain read-only compliance through FASE 1.3
- FASE 2.0 introduces write capability (requires approval workflow)
- Web UI designed to work without backend changes (read-only data)

## Semana 2 atual

- Revisão humana em PT-BR.
- ApprovalRecords apenas proposed/pending.
- Nenhuma escrita NetBox.

## Operação controlada multi-ciclo

- Cycle-001 closed with restrictions.
- Cycle-002 planned and gated.
- Expansion remains recommendation-only.
