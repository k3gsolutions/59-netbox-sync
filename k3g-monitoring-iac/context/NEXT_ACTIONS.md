# Next Actions — 2026-04-29 (FASES 2.47-3.19, 2.38, 2.39, 2.60, 4.1, 3.20, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10, 4.11, 4.12, 4.13 Complete)

## Just Completed (FASES 4.11-4.13)

**4.13 — Controlled Operation Cycle Dry-Run ApplyPlan Validation** ✅ COMPLETE
- ✅ Created controlled_cycle_validate_dryrun_applyplan.py
- ✅ Validates dry-run ApplyPlan structure and safety
- ✅ Enforces: mode=dry_run, safety flags, can_execute_real_write=false, no secrets
- ✅ Blocks: PATCH/DELETE methods, /sync target, authorization keywords
- ✅ Decision: CYCLE_DRYRUN_APPLYPLAN_VALID / VALID_WITH_WARNINGS / INVALID
- ✅ All tests passing (16/16 in comprehensive test suite)

**4.12 — Controlled Operation Cycle Generate Dry-Run ApplyPlan** ✅ COMPLETE
- ✅ Created controlled_cycle_generate_dryrun_applyplan.py
- ✅ Generates dry-run ApplyPlan from approved ApprovalRecords
- ✅ Validates each approved record before inclusion
- ✅ Sets all safety flags: dry_run_only=true, no_apply_execution=true, etc.
- ✅ Execution policy enforced: no real write capability, requires next gate
- ✅ All tests passing (16/16 in comprehensive test suite)

**4.11 — Controlled Operation Cycle Manual Approval Decision** ✅ COMPLETE
- ✅ Created controlled_cycle_manual_approval_review.py
- ✅ Validates and approves proposed ApprovalRecords
- ✅ Creates approved copies with human reviewer attribution
- ✅ Adds required state_history events for audit trail
- ✅ Decision: CYCLE_APPROVAL_REVIEW_APPROVED / WITH_RESTRICTIONS / BLOCKED
- ✅ All tests passing (16/16 in comprehensive test suite)

## Status
- Complete workflow: Week 2 review → approval decision → dry-run ApplyPlan → validation
- All 162+ tests passing across all FASES 2.47-4.13
- Cycle-001 ready for next phase (execution testing)

## Current State

### FASE 2.39 ✅ **COMPLETE** — ApplyPlan Readiness Gate
- ✅ Validates proposed ApprovalRecords for readiness
- ✅ Checks status, reviewer, evidence, safety flags
- ✅ Decision: READY_FOR_APPROVAL_REVIEW or NOT_READY_FOR_APPLYPLAN
- ✅ No ApplyPlan creation (validation only)
- ✅ 39/39 tests passing

### FASE 2.38 ✅ **COMPLETE** — Manual Promotion to Proposed ApprovalRecords
- ✅ Reads week2-review-decisions.csv
- ✅ Promotes only rows with approval_record_allowed=true + reviewer + reviewed_at
- ✅ Creates ApprovalRecords with status=proposed
- ✅ Generates promotion report
- ✅ Zero NetBox writes, manual_review_required enforced
- ✅ 39/39 tests passing

### FASE 3.14 ✅ **COMPLETE** — Web UI Operational Usability Polish
- ✅ Próximo passo visível em Service Engagement / Validation
- ✅ Card de Execução Real da Semana 1 no painel
- ✅ Mensagem pós-salvar do modal mostra status e próximo passo
- ✅ Menus e rótulos revisados em PT-BR operacional

### FASE 2.29 ✅ **COMPLETE** — Real Week 1 Final Validation + Week 2 Gate
- ✅ Validação final real gerada
- ✅ Gate Week 2 atualizado para GO_WEEK2_REVIEW_WITH_RESTRICTIONS
- ✅ Week 2 board preparado

### FASE 2.28 ✅ **COMPLETE** — Real Week 1 Execution via Web UI
- ✅ Execution log gerado
- ✅ UAT arquivado não interferiu no fluxo real
- ✅ CSVs e audits permaneceram locais

### FASE 3.13 ✅ **COMPLETE** — Web UI PT-BR Friendly Translation + UX Copy Review
- ✅ Core UI copy translated to PT-BR
- ✅ Modal, validation, outreach, approvals, reports, and dashboard labels reviewed
- ✅ Internal routes, enums, and technical names preserved

### FASE 2.27 ✅ **COMPLETE** — Real Week 1 Activation Flow
- ✅ Real activation flow documented
- ✅ Operator path centers on modal save, local CSV, local validation, and Week 2 prep
- ✅ Human review remains mandatory

### FASE 2.26 ✅ **COMPLETE** — UAT Decision / Cleanup Execution
- ✅ UAT rows archived out of active `week1-responses/`
- ✅ Readiness now reports `GO_REAL_WEEK1_CLEAN`
- ✅ Archive kept under `week1-responses/uat-archive/`

### FASE 3.12 ✅ **COMPLETE** — Web UI Response Validation Dashboard
- ✅ Validation dashboard route and audit route added
- ✅ Summary cards and item table available
- ✅ Finalize and validation actions exposed

### FASE 3.10.2 ✅ **COMPLETE** — Pending Modal Save & Close + Auto Local Pipeline
- ✅ Modal has Save and Save & Close
- ✅ Save triggers safe local pipeline
- ✅ Local validation and finalize endpoints added
- ✅ Week 2 board can prepare automatically when ready

### FASE 2.25 ✅ **COMPLETE** — UAT Cleanup / Real Week 1 Readiness
- ✅ UAT audit report generated
- ✅ Readiness report generated
- ✅ UAT archive/reset/keep-as-real guarded by confirmation
- ✅ Active UAT state cleaned to real-ready

### FASE 3.11 ✅ **COMPLETE** — Web UI Pending Editor UAT
- ✅ Service Team / Network Ops / BGP Team items saved locally
- ✅ CSV and audit JSON generated in week1-responses/
- ✅ Week 1 validation executed successfully
- ✅ Controlled UAT documented in WEBUI-PENDING-EDITOR-UAT.md

### FASE 3.10.1 ✅ **COMPLETE** — CSV Download Fix + IP Address Form Intelligence
- ✅ Safe CSV download fixed for `/reports/download`
- ✅ Allowed extensions: `.csv`, `.json`, `.txt`, `.log`, `.md`
- ✅ Sensitive files and traversal remain blocked
- ✅ `ip_address` form prefill/validation updated for detected interface/VRF
- ✅ `relation_type` added and `service_relation` is conditional

## Earlier Completed

### FASE 3.10 ✅ **COMPLETE** — Web UI Pending Item Editor Modal + Backend CSV Generation
- ✅ Pending queue routes added for device / response / week2 pages
- ✅ Modal editor renders team-specific fields
- ✅ Local-only POST saves unified CSV and audit JSON
- ✅ Secret blocking + path traversal blocking confirmed
- ✅ 19/19 safety tests passing
- ✅ Week 1 validation command shown in UI
- ✅ No NetBox writes, no apply, no /sync, no ApprovalRecord auto-create, no ApplyPlan auto-create

## Just Completed

### FASE 2.11 ✅ **COMPLETE** — Week 1 Metadata Collection
- ✅ Collection workflow documented (timeline, criteria, format)
- ✅ CSV template created (7 items, 3 teams)
- ✅ Acceptance criteria defined per object type
- ✅ Response tracking format (pending → validated → approved)
- ✅ Week 1 target: 2026-05-02 to 2026-05-08

### FASE 3.3 ✅ **COMPLETE** — Service Engagement Viewer
- ✅ Two new read-only routes (/service-engagement, /service-engagement/{device})
- ✅ Templates for engagement overview + device-specific view
- ✅ Links to engagement packages, readiness, enrichment, week1 collection
- ✅ Dashboard integration (quick links updated)
- ✅ 7/7 tests still passing

### FASE 3.4 ✅ **COMPLETE** — Operational Handoff
- ✅ OPERATIONAL-HANDOFF-PACKAGE.md (quick start guide)
- ✅ docs/47-operational-handoff.md (detailed runbook)
- ✅ Roles defined + responsibilities
- ✅ Deployment + startup procedures
- ✅ Emergency procedures (Web UI crash, NetBox outage, token leak)
- ✅ Monitoring checklist (daily, weekly, monthly)
- ✅ Runbook examples (compliance review, engagement, approvals, batch execution)
- ✅ Ready for NOC/Ops handoff on 2026-05-01

### FASE 3.1.1 ✅ **COMPLETE** — Web UI Test Closure
- ✅ Fixed jinja2 import test (environment setup)
- ✅ All 7/7 security tests passing
- ✅ Zero write routes verified
- ✅ Path traversal + denylist confirmed

### FASE 3.2 ✅ **COMPLETE** — Approval Queue Timeline UI
- ✅ Approval queue route with filters (/approval-queue)
- ✅ Approval timeline route (/approval-timeline/{id})
- ✅ State history visualization (timeline of transitions)
- ✅ Grouped by status (pending, approved, applied, rejected)
- ✅ 7/7 tests still passing

### FASE 2.10 ✅ **COMPLETE** — Service Owner Engagement Preparation
- ✅ Engagement package created (3 teams, 6 items, timeline)
- ✅ Process documentation (46-service-owner-engagement.md)
- ✅ Roles & responsibilities defined
- ✅ Week 1 engagement plan ready
- ✅ Response format standardized

## Previously Completed

### FASE 3.1 ✅ **COMPLETE** — Web UI UX, Filters & Drill-down
- ✅ Enhanced dashboard (9 cards, better metrics)
- ✅ Batch result drill-down (`/batch-results/{batch_id}`)
- ✅ Filters: approvals (status), apply-plans (readiness), batch-results (result)
- ✅ Improved search (line numbers, highlighting, match count)
- ✅ 6/7 tests passing (environment-specific test)
- Status: Web UI at http://127.0.0.1:8890 (read-only, enhanced)

### FASE 2.9 ✅ **COMPLETE** — Service Candidate Enrichment Readiness
- ✅ Analysis: 1 ready, 6 missing_metadata, 0 blocked
- ✅ docs/45-service-candidate-enrichment-workflow.md (10 readiness categories)
- ✅ reports/.../service-candidate-enrichment-plan.md (gap analysis & timeline)
- ✅ Enrichment needs: tenant (5 subinterfaces), interface/VRF (1 IP), remote_asn (1 BGP)
- ✅ Owner engagement plan (service team, network ops, BGP team)
- ✅ Timeline: week 1 (engagement) → week 2 (approval) → week 3+ (execution)

## Immediate Next Steps

### FASE 2.10+ Execution (Next Week: 2026-05-02)
- **Week 1:** Distribute engagement package to 3 teams
  - Service Team: 5 subinterfaces (tenant, service_type, criticality)
  - Network Ops: 1 IP address (interface, VRF mapping)
  - BGP Team: 1 BGP peer (remote_asn, remote_bgp_group)
  - Target: All metadata collected by EOW Thursday 2026-05-02

### FASE 2.11 (Following Week: 2026-05-09)
- Review + validate enriched metadata
- Create ApprovalRecords with enriched data
- Dry-run validation
- Risk assessment (BAIXO/MÉDIO/ALTO)
- Target: ApprovalRecords ready by EOW Friday 2026-05-15

### FASE 2.12+ (Week 3+: 2026-05-16)
- Approval decisions
- Batch execution
- Compliance verification

### FASE 2.8 (Deferred)
- Base inventory expansion (scheduled after service enrichment stabilizes)
- Additional interfaces beyond pilot

### FASE 3.3+ (Future)
- Batch scheduling UI (read-only)
- Approval metrics dashboard
- Service compliance trends

---

# Next Actions — FASE 1.7+

## FASE 1.6 Complete ✅

**Piloto end-to-end testado:**
- ApprovalRecord generation com validação
- Markdown summary rendering com risk assessment
- Dry-run validation com schema checks
- Zero API calls, zero NetBox writes
- Item: Eth-Trunk0 (base_inventory, safe_create_staged, exact confidence)
- Resultado: Piloto PASSED, workflow confirmado

Arquivo: `reports/pilot-device-compliance/approvals/pending/PILOT-FASE-1-6-RESULT.md`

---

## FASE 1.7 Complete ✅

**Estado Management implementado:**
- Script manage_approval_state.py com 4 comandos
- State machine: proposed → approved/rejected/changes_requested
- File movement automático entre approvals/{pending,approved,rejected,changes_requested}/
- state_history imutável com audit trail (from/to/by/at/reason)
- Backup automático antes de cada save
- Validações rigorosas para approve (action, naming, confidence)
- Testes completos: approve, reject, request-changes, mark-dry-run-passed
- Documentação: docs/26-approval-state-management.md
- Piloto FASE 1.6 atualizado: c9363dfb em approved/ com status=dry_run_passed

---

## FASE 1.8 Complete ✅

**Staged Apply Design documentado:**
- docs/27-staged-apply-design.md (segurança, objetos permitidos, design futuro)
- docs/28-staged-apply-contract.md (contratos, schemas, exemplos)
- ApplyPlan schema definido
- StagedPayload format definido
- Error/blocking codes definidos
- Dry-run requirements claros
- Audit trail design

---

## FASE 1.9 — Staged Apply Dry-Run Engine

### Objective
Implementar engine local para gerar, validar e simular ApplyPlan.

### Scripts

**1. build_staged_apply_plan.py**
- Ler ApprovalRecord status=dry_run_passed
- Validar prerequisites
- Gerar ApplyPlan com readiness_checks
- Output: JSON

**2. validate_staged_apply_plan.py**
- Validar ApplyPlan
- 14 checks definidos
- Exit code: 0 (válido) | 1 (bloqueado)
- Output: validation result JSON

**3. render_staged_apply_plan.py**
- Renderizar ApplyPlan em Markdown
- Output: readable summary com bloqueios

**4. simulate_staged_apply.py**
- Simular resultado de apply
- Zero API calls
- Output: simulation result JSON + Markdown

### Testing

- Use pilot c9363dfb (dry_run_passed)
- Gerar ApplyPlan
- Validar
- Renderizar
- Simular
- Confirmar: zero API, zero writes, real_apply_enabled=false

---

## FASE 1.7.1 — `/compliance/approve` HTTP Endpoint

### Objective (Futuro, depois FASE 1.9)
Expor state management via HTTP endpoint para integração com UIs/workflows.

### Tasks

**1. Create `/compliance/approve` endpoint (netops_netbox_sync)**
- POST /compliance/approve
- Request body:
  ```json
  {
    "approval_id": "c9363dfb-...",
    "decision": "approve|reject|request_changes",
    "reviewed_by": "usuario@empresa.com",
    "comment": "..."
  }
  ```
- Response: ApprovalRecord com status atualizado
- Call manage_approval_state.py via subprocess
- No NetBox writes
- Return status (proposed → approved) e próximo passo

**2. Tests**
- POST /compliance/approve with valid approval_id → 200
- Move file to approved/ on decision=approve
- Return updated ApprovalRecord
- Validation: reject if approval_id not found, decision invalid
- Ensure state_history recorded correctly

**3. Security**
- No write tokens used
- No NetBox API calls
- Audit trail: reviewed_by + timestamp + comment
- Validate: approval_id format, decision enum

---

## FASE 1.7.1 — Batch Generation Script

### Task
Criar script para gerar ApprovalRecords em lote a partir de um ImportPlan.

```bash
python3 tools/local/batch_create_approvals.py \
  --import-plan reports/pilot-device-compliance/import-plan-4WNET-MNS-KTG-RX.json \
  --device 4WNET-MNS-KTG-RX \
  --device-id 1890 \
  --filter "category=base_inventory" \
  --output reports/pilot-device-compliance/approvals/pending/
```

- Parse ImportPlan (JSON ou Markdown)
- Generate ApprovalRecord para cada item matching filter
- Default filter: action=safe_create_staged
- Suportar inclusive opções de filtro por category, confidence, object_type
- Output: batch-<timestamp>.json com lista de approval_ids criados

---

## FASE 1.8 — CI Integration

### Task
Integrar geração de ApprovalRecords em pipeline.

**Trigger:**
- Após cada `/compliance/import-plan/report` bem-sucedido
- Gerar batch de ApprovalRecords (safe_create_staged items)
- Arquivar ImportPlan a reports/pilot-device-compliance/history/

**Artifacts:**
- approval-*.json files em approvals/pending/
- Notificação para revisor (email ou webhook)

---

## FASE 1.9 — Web UI (Basic)

### Task
Interface básica para revisão de approvals.

**Features:**
- GET /ui/approvals → lista approvals/pending/
- GET /ui/approvals/{id} → renderiza approval-summary.md
- POST /ui/approvals/{id}/approve → form submission
- POST /ui/approvals/{id}/reject → form submission

**Implementation:**
- Usar FastAPI + templates (Jinja2)
- No database (tudo em filesystem)
- Renderizar approval-summary.md como HTML
- Form com decision, comment fields

---

## FASE 2.0 Complete ✅

- Primeiro staged apply real executado no NetBox
- Approval ID: `c9363dfb`
- Objeto: `Eth-Trunk0`
- Método: `POST`
- Resultado: `201 Created`
- NetBox object ID: `18228`
- Escopo: 1 objeto
- Nenhum `PATCH`
- Nenhum `DELETE`
- Nenhum `/sync`
- Nenhuma configuração em equipamento
- Token não exposto
- Tags verificadas antes do `POST`
- Compliance pós-apply gerado
- Correção base/service aplicada no netops_netbox_sync
- Total de divergências pós-ajuste: 161
- Eth-Trunk0 não aparece mais como INTERFACE_MISSING_IN_NETBOX
- Eth-Trunk0 não aparece mais como DESCRIPTION_NON_COMPLIANT
- Eth-Trunk0 aparece apenas como INTERFACE_DESCRIPTION_MISMATCH (ação review)

## FASE 2.1 — Next Actions

- Documentar política de batch staged applies controlado para base_inventory
- Consolidar o fluxo completo Device → Compliance → ImportPlan → Approval → Dry-run → Staged Apply → Pós-Compliance
- Registrar lições aprendidas no `reports/pilot-device-compliance/README.md`
- Atualizar `docs/31-...` com estratégia de tag bootstrap e batch apply
- Definir política para múltiplos staged applies em lote controlado, ainda limitado a base_inventory

---

- [x] Workflow completo testado (FASE 1.6 pilot)
- [x] ApprovalRecord schema validado
- [x] Dry-run validation working
- [x] Zero secrets in records
- [x] Zero API calls
- [x] Documentation complete
- [ ] Implementar /compliance/approve
- [ ] Implementar batch_create_approvals.py
- [ ] Tests para /compliance/approve
- [ ] CI integration
- [ ] Web UI
- [ ] Staged import (FASE 2.0)

## FASE 2.7 — Real Batch POST Authorized Pilot Completed
- Batch ID: `4340469f` executed on `4WNET-MNS-KTG-RX` (device_id `1890`)
- Objects created: `Eth-Trunk1` ID `18229`, `GigabitEthernet0/5/0` ID `18230`
- Preflight all-or-none validated by repeat run blocked on existing objects
- No `PATCH`, no `DELETE`, no `/sync`, no equipment configuration changes
- Token not exposed
- Incident 18201/18202 closed, no rollback needed
- Post-batch compliance and before/after comparison created

## Próximas fases recomendadas
- FASE 2.8 — Base Inventory Expansion Policy
- FASE 2.9 — Service Candidate Enrichment Workflow, sem escrita
- FASE 3.0 — Web UI read-only

---

## Referências

- [Approval Workflow Design](../docs/23-approval-workflow-design.md)
- [ApprovalRecord Schema](../docs/24-approval-record-schema.md)
- [Approval Dry-Run](../docs/25-approval-dry-run.md)
- [Pilot Report](../reports/pilot-device-compliance/approvals/pending/PILOT-FASE-1-6-RESULT.md)

## Próximos Passos

- Revisar a Semana 2 manualmente.
- Promover apenas itens aprovados para proposed/pending.
- Manter NetBox fora do fluxo local.
