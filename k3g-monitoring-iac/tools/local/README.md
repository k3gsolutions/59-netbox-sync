# Local Tools

Scripts Python standard library para compliance report archiving, comparação, limpeza.

## Scripts

### archive_compliance_report.py

Arquivar relatório novo para histórico e atualizar current.

```bash
python3 tools/local/archive_compliance_report.py \
  --report <file.md> \
  --device <DEVICE-NAME> \
  [--device-id <ID>] \
  [--root .]
```

**Args:**
- `--report` (required) — caminho a relatório .md
- `--device` (optional) — nome device (auto-detecta de título se omitido)
- `--device-id` (optional) — ID para index.json
- `--root` (optional) — diretório raiz (default: .)

**Output:**
- Arquivo em `history/{DEVICE}/{TIMESTAMP}-compliance-report.md`
- Atualiza `current/{DEVICE}-compliance-report.md`
- Atualiza `index.json`

### compare_compliance_reports.py

Comparar dois relatórios, mostrar divergências novas/resolvidas/recorrentes.

```bash
python3 tools/local/compare_compliance_reports.py \
  --old <report-antigo.md> \
  --new <report-novo.md> \
  --output <comparison.md> \
  [--device <DEVICE-NAME>]
```

**Args:**
- `--old` (required) — relatório anterior
- `--new` (required) — relatório novo
- `--output` (optional) — arquivo saída (stdout se omitido)
- `--device` (optional) — nome device (auto-detecta se omitido)

**Output:**
- Tabela: evolução por severidade (antes/agora/delta)
- Tabela: novas divergências
- Tabela: divergências resolvidas
- Tabela: divergências recorrentes
- Comparação baseada em Markdown, sem API real

### cleanup_compliance_history.py

Remover relatórios antigos conforme política de retenção (keep-days + keep-count).

```bash
python3 tools/local/cleanup_compliance_history.py \
  [--root .] \
  [--keep-days 90] \
  [--keep-count 100] \
  [--apply]
```

**Args:**
- `--root` (optional) — diretório raiz (default: .)
- `--keep-days` (optional) — manter últimos N dias (default: 90)
- `--keep-count` (optional) — manter últimas N execuções por device (omit para sem limite)
- `--apply` (optional) — executar deletion (default: dry-run apenas lista)

**Comportamento:**
- Dry-run (padrão): lista relatórios que seriam deletados
- Atualiza `index.json` com novos `reports_count` após deletion
- Nunca deleta `current/`, `comparisons/`, `index.json`

### export_compliance_csv.py

Exportar histórico em CSV para análise, BI tools, Grafana.

```bash
python3 tools/local/export_compliance_csv.py \
  [--root .] \
  [--output compliance-history.csv] \
  [--include-metadata]
```

**Args:**
- `--root` (optional) — diretório raiz (default: .)
- `--output` (optional) — arquivo saída (default: compliance-history.csv)
- `--include-metadata` (optional) — incluir total_divergences, highest_severity, status, netbox_loaded

**Output CSV:**
- `device` — device name
- `device_id` — NetBox ID
- `last_report` — timestamp ISO8601
- `reports_count` — número de execuções
- (se --include-metadata) `total_divergences`, `highest_severity`, `status`, `netbox_loaded`

## Standard Library Only

Sem dependências externas. Compatível com Python 3.8+.

- `json` — index.json
- `pathlib` — file ops
- `re` — parse titles
- `datetime` — timestamps ISO8601
- `shutil` — copy files
- `argparse` — CLI

### create_approval_record.py

Criar ApprovalRecord local a partir de item do ImportPlan.

```bash
python3 tools/local/create_approval_record.py \
  --device 4WNET-MNS-KTG-RX \
  --device-id 123 \
  --object-type interface \
  --object-key Eth-Trunk0 \
  --action safe_create_staged \
  --code INTERFACE_MISSING_IN_NETBOX \
  --category base_inventory \
  --reason "Base interface inventory" \
  --confidence exact \
  --naming-compliant \
  --evidence '{"interface": "Eth-Trunk0", "status": "up"}' \
  --report-path reports/.../compliance-report.md \
  --report-timestamp 2026-04-28T09:45:00Z
```

**Output:** ApprovalRecord JSON em `approvals/pending/`

### render_approval_summary.py

Gerar Markdown resumido de ApprovalRecord para revisão.

```bash
python3 tools/local/render_approval_summary.py \
  approval-record.json \
  --output approval-summary.md
```

**Output:** Markdown com checklist de aprovação

### dry_run_netbox_payload.py

Validar payload NetBox futuro (sem escrita).

```bash
python3 tools/local/dry_run_netbox_payload.py \
  --approval-id abc123 \
  --device 4WNET-MNS-KTG-RX \
  --object-type interface \
  --object-key Eth-Trunk0 \
  --action safe_create_staged \
  --evidence '{"status": "up"}' \
  --category base_inventory
```

**Output:** Dry-run report em `approvals/pending/dry-run-*.md`

### manage_approval_state.py

Gerenciar transição de estado de ApprovalRecord (local, sem API).

```bash
# Aprovar
python3 tools/local/manage_approval_state.py approve \
  --approval approvals/pending/approval-*.json \
  --by "nome-operador" \
  --comment "Aprovado"

# Rejeitar
python3 tools/local/manage_approval_state.py reject \
  --approval approvals/pending/approval-*.json \
  --by "nome-operador" \
  --reason "Motivo rejeição"

# Solicitar mudanças
python3 tools/local/manage_approval_state.py request-changes \
  --approval approvals/pending/approval-*.json \
  --by "nome-operador" \
  --reason "Motivo mudanças"

# Marcar dry-run como passado
python3 tools/local/manage_approval_state.py mark-dry-run-passed \
  --approval approvals/approved/approval-*.json \
  --by "nome-operador" \
  --dry-run-report approvals/pending/dry-run-*.md
```

**Output:**
- Move arquivo entre approvals/{pending,approved,rejected,changes_requested}/
- Atualiza status, reviewed_by, state_history
- Cria backup automático

### build_staged_apply_plan.py

Gerar ApplyPlan local a partir de ApprovalRecord (dry-run, sem API).

```bash
python3 tools/local/build_staged_apply_plan.py \
  --approval approvals/approved/approval-*.json \
  --output approvals/approved/
```

**Output:** ApplyPlan JSON com readiness checks

### validate_staged_apply_plan.py

Validar ApplyPlan contra 13 critérios.

```bash
python3 tools/local/validate_staged_apply_plan.py \
  --plan approvals/approved/apply-plan-*.json
```

**Exit Code:** 0 (válido) / 1 (bloqueado)

### render_staged_apply_plan.py

Renderizar ApplyPlan em Markdown.

```bash
python3 tools/local/render_staged_apply_plan.py \
  --plan approvals/approved/apply-plan-*.json \
  --output approvals/approved/apply-plan-*.md
```

**Output:** Markdown com readiness status e checks

### simulate_staged_apply.py

Simular resultado de apply (sem API, sem writes).

```bash
python3 tools/local/simulate_staged_apply.py \
  --plan approvals/approved/apply-plan-*.json \
  --output approvals/approved/apply-simulation-*.md
```

**Output:** Markdown com resultado simulado (would_create_staged)

### apply_staged_netbox_object.py

Aplicar interface staged real no NetBox (primeira escrita controlada).

**Dry-run (padrão, sem escrita):**
```bash
python3 tools/local/apply_staged_netbox_object.py \
  --plan approvals/approved/apply-plan-*.json \
  --netbox-url https://docs.k3gsolutions.com.br \
  --confirm-approval-id <approval_id> \
  --operator "seu-nome"
```

**Real write (com --confirm-real-write):**
```bash
NETBOX_WRITE_TOKEN="token-here" python3 tools/local/apply_staged_netbox_object.py \
  --plan approvals/approved/apply-plan-*.json \
  --netbox-url https://docs.k3gsolutions.com.br \
  --confirm-approval-id <approval_id> \
  --operator "seu-nome" \
  --confirm-real-write
```

**Validações:**
- Approval_id confirmation
- Preflight GET (objeto não existe)
- Tag existence check (GET /api/extras/tags/ para cada tag)
- Payload validation (nenhum secret)
- Token via env var (nunca em args)
- Only 1 object at a time

**Tag Check (2.0-hotfix):**
- Extrai tags do staged_payload
- Para cada tag: GET /api/extras/tags/?name=<tag>
- Se tag não existir: aborta antes do POST
- Gera apply-result com reason=TAG_MISSING
- Lista tags ausentes para criação manual
- Mensagem: "Create missing tags in NetBox or execute future controlled tag bootstrap phase"

**Output:**
- Relatório em approvals/applied/apply-result-*.md
- Exit code 0 = sucesso, 1 = falha

### build_batch_staged_apply_plan.py

Gerar BatchApplyPlan a partir de múltiplos ApplyPlans individuais (FASE 2.3).

```bash
python3 tools/local/build_batch_staged_apply_plan.py \
  --plans \
    approvals/approved/apply-plan-ITEM1.json \
    approvals/approved/apply-plan-ITEM2.json \
  --output approvals/approved/batch-apply-plan-<timestamp>.json \
  --max-items 3
```

**Validações:**
- total_items <= max_items
- todos object_type=interface
- todos category=base_inventory
- approval_ids únicos
- object_keys únicos
- sem secrets

### validate_batch_staged_apply_plan.py

Validar BatchApplyPlan contra gates.

```bash
python3 tools/local/validate_batch_staged_apply_plan.py \
  --plan approvals/approved/batch-apply-plan-<timestamp>.json
```

Exit code: 0 (válido) / 1 (inválido)

### render_batch_staged_apply_plan.py

Renderizar BatchApplyPlan em Markdown.

```bash
python3 tools/local/render_batch_staged_apply_plan.py \
  --plan approvals/approved/batch-apply-plan-<timestamp>.json \
  --output approvals/approved/batch-apply-plan-<batch_id>.md
```

Output: Markdown com readiness status, gates, itens, política

### apply_batch_staged_netbox_objects.py

Aplicar batch staged (múltiplos objetos, até 3 neste piloto).

**Dry-run (padrão, zero writes):**
```bash
python3 tools/local/apply_batch_staged_netbox_objects.py \
  --batch-plan approvals/approved/batch-apply-plan-<timestamp>.json \
  --netbox-url https://docs.k3gsolutions.com.br \
  --confirm-batch-id <batch_id> \
  --operator "seu-nome"
```

**Real write (com --confirm-real-write-batch):**
```bash
NETBOX_WRITE_TOKEN="..." python3 tools/local/apply_batch_staged_netbox_objects.py \
  --batch-plan approvals/approved/batch-apply-plan-<timestamp>.json \
  --netbox-url https://docs.k3gsolutions.com.br \
  --confirm-batch-id <batch_id> \
  --operator "seu-nome" \
  --confirm-real-write-batch
```

**Validações:**
- All-or-none preflight
- Item-by-item execution
- Token via env var
- Máximo 2 itens (piloto)
- FASE 2.7 autorizado: batch real POST validado com objeto existente bloqueando reexecução
- Nenhum PATCH/DELETE

**Output:**
- Relatório em approvals/applied/batch-apply-result-<batch_id>.md
- Exit code 0 = sucesso, 1 = falha

### analyze_service_candidate_readiness.py

Analisar readiness de service candidates (read-only, FASE 2.4).

```bash
python3 tools/local/analyze_service_candidate_readiness.py \
  --import-plan reports/pilot-device-compliance/import-plan-4WNET.md \
  --output reports/pilot-device-compliance/service-candidate-readiness.md \
  --device 4WNET-MNS-KTG-RX
```

Classificações:
- ready_for_review: pronto para enriquecimento/aprovação
- missing_metadata: faltam campos obrigatórios
- naming_failed: naming convention inválido
- ambiguous: múltiplas interpretações
- blocked: impossível prosseguir
- ignored: não é service candidate

Output: Markdown com tabelas e resumo

**Validações:**
- object_type: interface, bgp_peer, ip_address
- campos obrigatórios por tipo
- base_inventory excluded (ignored)
- nenhuma API write
- nenhum token write
- nenhum equipamento

## Integração CI

Futuro: rodar `archive_compliance_report.py` após cada `/compliance/analyze/report`.

Integração com approval: rodar scripts acima antes de staged import real (FASE 2.0).
Integração com batch: rodar `build_batch_staged_apply_plan.py` → `validate_batch_staged_apply_plan.py` → `apply_batch_staged_netbox_objects.py`.
