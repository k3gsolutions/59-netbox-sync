# FASE 1 Roadmap — Report Tooling

## FASE 1.0 ✅ Core Analysis

Core compliance analysis with read-only NetBox integration.

**Completed:**
- Device SSH collection (HuaweiNE8000)
- NetBox inventory loading
- Object-level divergence detection
- Markdown report generation
- 58 unit tests, 100% mock

## FASE 1.1 ✅ Report History

Local report archiving with structured metadata.

**Completed:**
- Directory structure: `current/`, `history/`, `comparisons/`
- `archive_compliance_report.py` — archive new reports
- `init_report_structure.py` — initialize structure
- `index.json` with metadata
- `.gitignore` excludes raw JSON credentials
- Documentation: `docs/20-report-history-standard.md`

## FASE 1.2 ✅ Report Comparison & Cleanup

Report comparison and history retention.

**Completed:**
- ✅ `compare_compliance_reports.py` — diff between executions
- ✅ `cleanup_compliance_history.py` — retention policy with keep-days + keep-count
- ✅ `export_compliance_csv.py` — historical export to CSV
- ✅ CI integration documented in `docs/22-compliance-history-maintenance.md`
- ✅ Documentation: `docs/22-compliance-history-maintenance.md`

## FASE 1.3 ✅ ImportPlan Read-Only

Read-only enrichment proposals para o NetBox.

**Completed:**
- `/compliance/import-plan` implementado
- `/compliance/import-plan/report` implementado
- ImportPlan classifica `safe_create_staged`, `needs_review`, `blocked`, `ignore`
- ImportPlan diferencia `base_inventory` vs `service`
- Markdown separa `Base Inventory` e `Service Candidates`
- Base Inventory representa inventário físico/lógico base
- Service Candidates representa itens que dependem de regra de serviço/naming
- Total de itens no ImportPlan: 161
- Safe create staged: 59
- Needs review: 92
- Blocked: 0
- Ignored: 10
- Interfaces base podem ser `safe_create_staged` sem naming de serviço
- Interfaces de serviço/subinterfaces só podem ser `safe_create_staged` com naming válido
- Subinterfaces inválidas viram `needs_review`
- BGP peers continuam `needs_review`
- IPs sem associação/naming continuam `needs_review`
- Naming inválido nunca vira `safe_create_staged`
- Nunca gera `delete`
- Sem escrita no NetBox
- Sem `/sync`
- Sem alteração em equipamento
- ImportPlan real gerado para `4WNET-MNS-KTG-RX`
- Netops_netbox_sync tests: 32 passing

## FASE 1.4 Web UI Prototype

Lightweight browser interface for report viewing.

**Planned:**
- Device list with last report
- Timeline view (executions per device)
- Report viewer (Markdown)
- Diff viewer (execution comparison)
- Basic filtering (severity, date range)
- Export to CSV

**Effort:** 3 weeks

## FASE 1.5 Advanced Analytics

Dashboard & alerting.

**Planned:**
- Compliance scoring (% resolved)
- Severity trends
- Email/Slack alerts
- Scheduled analysis
- Report scheduling API

**Effort:** 4 weeks

---

## Quick Checklist FASE 1.2

- [x] `cleanup_compliance_history.py` implemented (195 lines, dry-run by default)
- [x] `export_compliance_csv.py` implemented (155 lines, metadata extraction)
- [x] CI hook example documented in `docs/22-compliance-history-maintenance.md`
- [x] Scripts tested with sample reports (dry-run cleanup, CSV export verified)
- [x] No API calls in local scripts (standard library only: json, pathlib, re, datetime, csv)
- [x] No secrets in outputs (Markdown parsing, metadata extraction only)
