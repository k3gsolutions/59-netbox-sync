# Roadmap — NetBox Sync Compliance

## Vision

Automated, read-only compliance analysis for network devices. Local report history, trend tracking, minimal secrets exposure.

## Current UI Milestones

- FASE 3.10.2: modal save/save-and-close + safe local pipeline
- FASE 3.12: response validation dashboard + UAT audit view
- FASE 2.25: UAT cleanup and Week 1 real-readiness guardrails
- FASE 3.13: PT-BR friendly UI copy review
- FASE 2.26: UAT decision / cleanup execution
- FASE 2.27: real Week 1 activation flow
- FASE 2.28: real Week 1 execution via Web UI
- FASE 2.29: real Week 1 final validation + Week 2 gate
- FASE 3.14: operational usability polish

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
