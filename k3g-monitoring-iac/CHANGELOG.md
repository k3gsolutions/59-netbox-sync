# Changelog

## [Unreleased]

### Added — FASE 1.1 & 1.2

**Report History & Versioning (FASE 1.1)**
- Estrutura local para histórico de relatórios: `reports/pilot-device-compliance/{current,history,comparisons}`
- Padrão completo em `docs/20-report-history-standard.md`
- Script Python `tools/local/archive_compliance_report.py` para arquivar relatórios
- Script `tools/local/init_report_structure.py` para inicializar estrutura
- `.gitignore` para excluir raw JSON com credenciais (payload*.json, *raw*.json, *secret*.json)
- `index.json` estruturado com metadados device (device_id, last_report, reports_count)
- ISO8601 timestamps para histórico (ex: `2026-04-28T05:53:48Z`)

**Report Comparison (FASE 1.2)**
- Script `tools/local/compare_compliance_reports.py` para comparar dois relatórios
- Tabela: evolução por severidade (antes/agora/delta)
- Tabela: novas divergências
- Tabela: divergências resolvidas
- Tabela: divergências recorrentes
- Chave de divergência: (code, object_type, object_key, scope)
- Parseamento local de Markdown, sem API real

**History Maintenance (FASE 1.2.1)**
- Script `tools/local/cleanup_compliance_history.py` — limpeza por data com keep-days + keep-count
- Dry-run mode (padrão) e --apply para execução real
- Script `tools/local/export_compliance_csv.py` — exportar histórico em CSV com metadata opcional
- Documentação: `docs/22-compliance-history-maintenance.md`

### Documentation

- `docs/20-report-history-standard.md` — naming convention, retenção, comparação, Web UI
- `docs/21-netbox-staged-import-strategy.md` — estratégia futura de importação assistida do NetBox
- `docs/22-compliance-history-maintenance.md` — cleanup workflows, security, BI integration
- `reports/pilot-device-compliance/README.md` — guia local rápido
- `tools/local/README.md` — scripts disponíveis e uso

### Added — FASE 1.3
- Implementação de `/compliance/import-plan` e `/compliance/import-plan/report`.
- ImportPlan classifica `safe_create_staged`, `needs_review`, `blocked` e `ignore`.
- ImportPlan diferencia `base_inventory` vs `service`.
- Interfaces base podem ser `safe_create_staged` sem naming de serviço.
- Interfaces de serviço/subinterfaces só podem ser `safe_create_staged` com naming válido.
- Subinterfaces inválidas viram `needs_review`.
- BGP peers continuam `needs_review`.
- IPs sem associação/naming continuam `needs_review`.
- Naming inválido nunca vira `safe_create_staged`.
- Nunca gera `delete`.
- Sem escrita no NetBox.
- Sem `/sync`.
- Sem alteração em equipamento.
- Total de itens no ImportPlan: 161.
- Safe create staged: 59.
- Needs review: 92.
- Blocked: 0.
- Ignored: 10.
- Markdown separa `Base Inventory` e `Service Candidates`.
- Base Inventory representa inventário físico/lógico base.
- Service Candidates representa itens que dependem de regra de serviço/naming.
- ImportPlan real gerado para `4WNET-MNS-KTG-RX`.
- `netops_netbox_sync` tests: 32 passing.

### Added — FASE 1.4

**Approval Workflow Design**
- Fluxo de aprovação humana documentado: 7 estados (proposed, approved, needs_review, rejected, dry_run_passed, applied_staged, expired)
- 5 decisões possíveis: approve, reject, request_changes, defer, mark_as_ignored
- Regras de aprovação diferenciadas: base_inventory (relaxado) vs service_candidates (strict)
- Dry-run padrão obrigatório antes de qualquer POST/PATCH
- Requisitos de auditoria: approval_id único, evidence_hash, relatório rastreável
- Validação: sem secrets, sem deletes, sem bloqueados/ignorados aprovados
- Documentação completa: `docs/23-approval-workflow-design.md` (396 linhas)
- Schema JSON: `docs/24-approval-record-schema.md` (529 linhas com exemplos)
- Skill definição: `skills/approval-workflow.skill.md` (271 linhas)
- Review prompt reutilizável: `prompts/approval-workflow-review.md` (249 linhas)

### Added — FASE 1.5

**ApprovalRecord Local + Dry-Run de Payload**
- Script `tools/local/create_approval_record.py` — gera ApprovalRecord JSON localmente
  - Validação: bloqueia secrets, naming-inválido para service, blocked/ignore actions
  - Gera approval_id (UUID), evidence_hash (SHA256), timestamps ISO8601
  - Estrutura: approvals/pending/approval-{device}-{id}-{timestamp}.json
- Script `tools/local/render_approval_summary.py` — Markdown resumido com checklist
  - Seções: Proposta, Evidência, Avaliação de Risco (🟢/🟡/🔴), Checklist, Decisão, Auditoria, Segurança
  - Risco: BAIXO para base_inventory, MÉDIO para service com naming OK, ALTO para invalid/needs_review
- Script `tools/local/dry_run_netbox_payload.py` — validação de payload sem escrita
  - Schema validation por tipo (interface, ip_address, vrf, vlan, bgp_peer)
  - Secret detection (password, token, secret, api_key, ssh)
  - Sugestão de payload NetBox com tags (discovery:staged, source:device)
  - Exit code: 0 (passou) / 1 (erros)
- Documentação: `docs/25-approval-dry-run.md` (365 linhas com exemplos completos)
- Workflow completo: create → render → review → dry-run → approved/rejected
- Zero API calls, zero NetBox writes, apenas validação local

### Completed — FASE 1.6

**End-to-End Approval Dry-Run Pilot**
- Piloto completo com item real: Eth-Trunk0 (base_inventory, safe_create_staged, exact confidence)
- ApprovalRecord generation com validação (ID: c9363dfb)
- Approval summary rendering com 7 seções e risk assessment (🟢 BAIXO RISCO)
- Dry-run validation com exit code 0 (PASSED)
- Suggested NetBox payload gerado com tags
- Zero API calls, zero NetBox writes confirmado
- Arquivo: reports/pilot-device-compliance/approvals/pending/PILOT-FASE-1-6-RESULT.md
- Workflow completo: create_approval_record → render_approval_summary → dry_run_netbox_payload

### Completed — FASE 1.7

**Approval State Management (Local)**
- Script `tools/local/manage_approval_state.py` com 4 comandos
- Comando approve: proposed → approved (com validação strict)
- Comando reject: proposed → rejected
- Comando request-changes: proposed → changes_requested
- Comando mark-dry-run-passed: approved → dry_run_passed
- State machine com transições válidas
- File movement automático: pending/ → approved/ / rejected/ / changes_requested/
- state_history append-only audit trail (from/to/by/at/reason/tool_version)
- Backup automático antes de cada save
- Validações rigorosas: action, naming_compliant, confidence, forbidden patterns
- Documentação: `docs/26-approval-state-management.md`
- Testes completos: approve, reject, request-changes, mark-dry-run-passed
- Piloto c9363dfb: proposed → approved → dry_run_passed (PASSOU)
- Zero API calls, zero NetBox writes, zero secrets

### Completed — FASE 1.8

**Staged Apply Design (Design Only, No Implementation)**
- Documento `docs/27-staged-apply-design.md`: princípios, objetos permitidos/bloqueados, regras segurança
- Documento `docs/28-staged-apply-contract.md`: contratos de entrada/saída, schemas, exemplos
- ApplyPlan schema: readiness_checks, write_policy, validation
- StagedPayload format: com tags staged e custom_fields
- Error/blocking codes: 11 códigos definidos
- Dry-run requirements: obrigatório antes de apply futuro
- Audit trail design: approval_id, applied_by, applied_at, payload_hash, result
- Objetos permitidos (inicial): interface base_inventory apenas
- Objetos bloqueados: IP, VRF, VLAN, BGP, UPDATE, DELETE
- Write policy: real_apply_enabled=false, write_token_provided=false
- Zero API, zero NetBox writes, design only

### Completed — FASE 1.9

**Staged Apply Dry-Run Engine (Local, Zero API/Writes)**
- Script `tools/local/build_staged_apply_plan.py`: gera ApplyPlan a partir de ApprovalRecord
  - Valida prerequisites (status=dry_run_passed, action=safe_create_staged)
  - Corre 13 readiness checks
  - Gera ApplyPlan JSON com readiness_status
  - Zero API, zero writes
- Script `tools/local/validate_staged_apply_plan.py`: valida ApplyPlan
  - Verificações: campos obrigatórios, write_policy, action, method, object_type
  - Exit code: 0 (válido) / 1 (bloqueado)
  - Zero API, zero writes
- Script `tools/local/render_staged_apply_plan.py`: renderiza ApplyPlan em Markdown
  - 7 seções: Resumo, Readiness Status, Checks, Bloqueios, Payload, Política, Segurança
  - Readiness status: 🟢 READY / 🔴 BLOCKED
  - Zero API, zero writes
- Script `tools/local/simulate_staged_apply.py`: simula resultado de apply
  - Resultado: would_create_staged (201) ou would_fail_blocked (400)
  - Prevê estado futuro: approval_status → applied_staged
  - Rollback hint: DELETE /api/dcim/interfaces/{id}/
  - Zero API, zero writes
- Teste com piloto c9363dfb: ApplyPlan → Validate → Render → Simulate (TODOS PASSARAM)
  - ApplyPlan ID: 8017f140-07a4-4401-bbed-42f7e705a6af
  - Readiness Status: ready
  - Checks: 12/13 PASSED (1 NOT_CHECKED — requer API futuro)
  - Simulação: WOULD CREATE STAGED com status=201
- Documentação: `docs/29-staged-apply-dry-run-engine.md` (complete guide com exemplos)
- Zero API calls, zero NetBox writes, simulation only
- real_apply_enabled=false, write_token_provided=false confirmados
- Arquivos gerados em approvals/approved/: apply-plan-*.json, apply-plan-*.md, apply-simulation-*.md

### Completed — FASE 2.0

**First Real NetBox Write (Staged Apply)**
- Script `tools/local/apply_staged_netbox_object.py` — primeira escrita real controlada
  - Dry-run mode (padrão): validações sem escrita
  - Real write mode: requer --confirm-real-write + NETBOX_WRITE_TOKEN env var
  - Validações obrigatórias: approval_id, readiness_status=ready, action=safe_create_staged
  - Preflight GET: verifica se objeto existe antes de POST
  - Abort conditions: 11 critérios de parada (nenhum token, approval divergente, objeto existe, >1 item, tag missing, etc)
  - Payload validation: detecta secrets (password, token, secret, api_key, ssh)
  - Token security: env var apenas (nunca em args, nunca em output)
  - One object at a time: aborta se ApplyPlan tem >1 objeto
  - Resultado: relatório Markdown em approvals/applied/apply-result-*.md
  - Exit code: 0 (sucesso) / 1 (falha)
- Documentação: `docs/30-first-staged-netbox-write.md`
- Teste dry-run com piloto c9363dfb: PASSED (nenhuma escrita real)
- Pronto para escrita autorizada com NETBOX_WRITE_TOKEN
- Zero API calls (até --confirm-real-write)
- Zero NetBox writes (até autorização)

### Hotfix — FASE 2.0 (Tag Preflight Check)
- Erro real encontrado: tags não existem no NetBox (400 Bad Request)
- **Solução:** adicionar preflight check para tags antes do POST
  - GET /api/extras/tags/?name=<tag> para cada tag no payload
  - Se tag não existir: aborta antes do POST
  - Gera apply-result com reason=TAG_MISSING
  - Lista tags ausentes para criação manual
  - Não cria tags automaticamente (fase futura)
- Script `tools/local/apply_staged_netbox_object.py` atualizado:
  - Nova função `extract_tags_from_payload(payload)`
  - Nova função `check_tags_exist(netbox_url, token, tag_names)`
  - Tag check no fluxo real write (depois preflight GET, antes POST)
  - Render melhorado para TAG_MISSING com instruções
- Documentação atualizada: docs/30, tools/local/README.md, CHANGELOG.md
- Validações: 11 critérios agora incluem tag check
- Mensagem clara: "Create missing tags in NetBox or execute future controlled tag bootstrap phase"

### Added — FASE 2.0
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
- Tags verificadas antes do POST
- Relatório `apply-result` gerado
- Compliance pós-apply gerado
- Comparação antes/depois gerada

### Completed — FASE 2.2 (Design)
- ✅ docs/31-controlled-batch-staged-apply.md
- ✅ docs/32-batch-apply-runbook.md
- ✅ Design: batch limitado a 3 objetos
- ✅ Design: somente base_inventory interfaces
- ✅ Design: all-or-none preflight, item-by-item execution
- ✅ Design: 15+ gates definidos
- ✅ Design: estados do lote documentados
- ✅ Zero código de escrita
- ✅ Zero API calls

### Completed — FASE 2.3 (Implementação)
- ✅ Script: tools/local/build_batch_staged_apply_plan.py
- ✅ Script: tools/local/validate_batch_staged_apply_plan.py
- ✅ Script: tools/local/render_batch_staged_apply_plan.py
- ✅ Script: tools/local/apply_batch_staged_netbox_objects.py
- ✅ Pilot: máx 2 itens (Eth-Trunk1, GigabitEthernet0/5/0)
- ✅ Dry-run: teste sem writes
- ✅ Real write: pronto para execução com --confirm-real-write-batch
- ✅ Validações: all-or-none preflight
- ✅ Validações: item-by-item execution
- ✅ Validações: token via env var
- ✅ Validações: sem secrets
- ✅ Output: batch-apply-result-<batch_id>.md

### Added — FASE 2.7
- Real batch POST autorizado executado para batch `4340469f` em `4WNET-MNS-KTG-RX` (device_id `1890`)
- Objetos criados no NetBox: `Eth-Trunk1` (ID `18229`) e `GigabitEthernet0/5/0` (ID `18230`)
- Tags aplicadas: `discovery:netops_netbox_sync`, `discovery:staged`, `source:device`, `approval:<approval_id>`
- Reexecução do batch bloqueada corretamente por `object already exists`, validando o preflight all-or-none
- Nenhum `PATCH`, nenhum `DELETE`, nenhum `/sync`, nenhuma configuração em equipamento
- Token não exposto em arquivo ou relatório
- Incidente anterior encerrado: `18201`/`18202` eram objetos antigos de `2026-04-04`, `no_rollback_needed`
- Compliance pós-batch gerado e comparação antes/depois registrada
- Próximas fases recomendadas: FASE 2.8 — Base Inventory Expansion Policy; FASE 2.9 — Service Candidate Enrichment Workflow, sem escrita; FASE 3.0 — Web UI read-only

### Planned — FASE 2.2 (Design)
- ✅ Documentação: docs/31-controlled-batch-staged-apply.md (design e gates)
- ✅ Documentação: docs/32-batch-apply-runbook.md (runbook operacional)
- Batch limitado a máximo 3 objetos
- Somente base_inventory interfaces
- All-or-none preflight
- Item-by-item execution
- Estados do lote: planned, preflight_passed, apply_started, applied, partial_failed, blocked
- Gates por item e por lote definidos (15+ critérios)
- Zero código de escrita em FASE 2.2 (design only)
- Zero API calls (design only)

### Planned — FASE 2.4 (Service Candidate Readiness)
- Documentação: docs/33-service-candidate-readiness.md
- Script: tools/local/analyze_service_candidate_readiness.py
- Validação de readiness para service candidates
- Classificação: ready_for_review, missing_metadata, naming_failed, ambiguous, blocked, ignored
- Zero writes
- Zero token write
- Zero equipamento
- Relatório com recomendações

### Planned (FASE 2.5+)
- `/compliance/approve` endpoint com state management
- CI integration para gerar approvals automaticamente
- Web UI básica para revisão
- Service candidate batch readiness (sem escrita)
- Trend analysis & alertas
- Scheduled apply (time-based execution)

### Fixed

- Hostname fallback agora usa NetBox device.name quando inventory.hostname=unknown
- Divergências agregadas separadas de objeto-a-objeto no Markdown

---

## [1.0] — 2026-04-28

**Initial Release**

- Device compliance analysis (read-only)
- NetBox inventory loading with safe field handling
- Automatic device_id resolution by name/IP
- Object-level divergence detection
- Markdown compliance report generation
- 58 unit tests, 100% read-only

## [3.0.1] — 2026-04-28

### Web UI Test Closure
- ✅ All 7 security tests passing
- ✅ Path traversal protection verified
- ✅ Denylist enforcement verified
- ✅ Zero POST/PATCH/DELETE routes confirmed
- ✅ Dependencies resolved (FastAPI, Jinja2, Uvicorn, Markdown)
- ✅ Live server online at http://127.0.0.1:8890

### Improvements
- Fixed test_no_post_routes() to inspect app_simple correctly
- Enhanced denylist with pattern matching
- Added fallback path resolution for templates and static files

### Status
- FASE 3.0 + 3.0.1 COMPLETE
- Web UI read-only verified
- Ready for integration and future phases (3.1+)

