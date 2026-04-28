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

### Planned (FASE 1.7+)
- `/compliance/approve` endpoint com state management
- Batch generation script para ApprovalRecords
- CI integration para gerar approvals automaticamente
- Web UI básica para revisão
- Staged import real com execution (FASE 2.0)
- Trend analysis & alertas

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
