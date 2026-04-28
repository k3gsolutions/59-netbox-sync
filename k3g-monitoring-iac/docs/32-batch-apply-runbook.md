# Batch Apply Runbook

Guia passo-a-passo para selecionar, preparar, validar e executar batch staged apply controlado.

## 1. Pré-Requisitos

✅ Compliance report gerado
✅ ImportPlan gerado
✅ Candidatos identificados (base_inventory)
✅ ApprovalRecords para cada candidato
✅ Todos ApprovalRecords com status = dry_run_passed
✅ Todos ApplyPlans validados
✅ NETBOX_WRITE_TOKEN disponível (para real write apenas)
✅ Device já existe no NetBox

## 2. Seleção de Candidatos

### Critérios

- ✅ object_type = interface
- ✅ category = base_inventory
- ✅ action = safe_create_staged
- ✅ confidence = exact ou normalized
- ✅ approval_status = dry_run_passed
- ✅ readiness_status = ready
- ✅ sem secrets
- ✅ tags existem
- ✅ objeto não existe no NetBox

### Exemplo

Dispositivo: `4WNET-MNS-KTG-RX`

Candidatos:
- Eth-Trunk1 (se ainda não criado)
- GigabitEthernet0/5/0
- GigabitEthernet0/5/1

(Não incluir Eth-Trunk0, já foi criado em FASE 2.0)

## 3. Preparação de cada Candidato

Para cada interface:

### 3.1 Criar ApprovalRecord

```bash
python3 tools/local/create_approval_record.py \
  --device 4WNET-MNS-KTG-RX \
  --device-id 1890 \
  --object-type interface \
  --object-key <INTERFACE_NAME> \
  --action safe_create_staged \
  --code INTERFACE_MISSING_IN_NETBOX \
  --category base_inventory \
  --reason "Base interface inventory" \
  --confidence exact \
  --naming-compliant \
  --evidence '<JSON_EVIDENCE>' \
  --report-path reports/pilot-device-compliance/compliance-report.md \
  --report-timestamp 2026-04-28T...
```

Output: `approvals/pending/approval-<DEVICE>-<ID>-<TIMESTAMP>.json`

### 3.2 Aprovar ApprovalRecord

```bash
python3 tools/local/manage_approval_state.py approve \
  --approval approvals/pending/approval-*.json \
  --by "seu-nome" \
  --comment "Aprovado para batch staged apply"
```

Output: `approvals/approved/approval-*.json`

### 3.3 Marcar Dry-Run como Passed

```bash
python3 tools/local/manage_approval_state.py mark-dry-run-passed \
  --approval approvals/approved/approval-*.json \
  --by "seu-nome" \
  --dry-run-report approvals/pending/dry-run-*.md
```

### 3.4 Criar ApplyPlan

```bash
python3 tools/local/build_staged_apply_plan.py \
  --approval approvals/approved/approval-*.json \
  --output approvals/approved/
```

Output: `approvals/approved/apply-plan-<ID>.json`

### 3.5 Validar ApplyPlan

```bash
python3 tools/local/validate_staged_apply_plan.py \
  --plan approvals/approved/apply-plan-<ID>.json
```

Expected: Exit code 0 (válido)

### 3.6 Renderizar ApplyPlan

```bash
python3 tools/local/render_staged_apply_plan.py \
  --plan approvals/approved/apply-plan-<ID>.json \
  --output approvals/approved/apply-plan-<ID>.md
```

Output: Markdown com readiness status

## 4. Construir Batch ApplyPlan

Após preparar todos os 2-3 candidatos:

```bash
python3 tools/local/build_batch_staged_apply_plan.py \
  --plans \
    reports/pilot-device-compliance/approvals/approved/apply-plan-<ID1>.json \
    reports/pilot-device-compliance/approvals/approved/apply-plan-<ID2>.json \
    reports/pilot-device-compliance/approvals/approved/apply-plan-<ID3>.json \
  --output reports/pilot-device-compliance/approvals/approved/batch-apply-plan-<BATCH_ID>.json \
  --max-items 3
```

Output: `batch-apply-plan-<BATCH_ID>.json`

Structure:
```json
{
  "batch_id": "...",
  "generated_at": "2026-04-28T...",
  "max_items": 3,
  "total_items": 3,
  "device": "4WNET-MNS-KTG-RX",
  "device_id": 1890,
  "items": [
    { "apply_plan_id": "...", "approval_id": "...", "object_key": "..." },
    ...
  ],
  "readiness_status": "ready",
  "blocked_reasons": [],
  "write_policy": {
    "real_apply_enabled": false,
    "write_token_provided": false,
    "max_items": 3
  }
}
```

## 5. Validar BatchApplyPlan

```bash
python3 tools/local/validate_batch_staged_apply_plan.py \
  --plan reports/pilot-device-compliance/approvals/approved/batch-apply-plan-<BATCH_ID>.json
```

Expected: Exit code 0 (válido)

Verifica:
- ✅ total_items <= 3
- ✅ todos object_type = interface
- ✅ todos category = base_inventory
- ✅ todos action = safe_create_staged
- ✅ todos method = POST
- ✅ approval_ids únicos
- ✅ object_keys únicos
- ✅ sem secrets

## 6. Renderizar BatchApplyPlan

```bash
python3 tools/local/render_batch_staged_apply_plan.py \
  --plan reports/pilot-device-compliance/approvals/approved/batch-apply-plan-<BATCH_ID>.json \
  --output reports/pilot-device-compliance/approvals/approved/batch-apply-plan-<BATCH_ID>.md
```

Output: Markdown com:
- Resumo do batch
- Lista de itens
- Gates (todos devem passar)
- Payloads
- Política de escrita
- Segurança

Revisar antes de prosseguir.

## 7. Dry-Run Batch

```bash
python3 tools/local/apply_batch_staged_netbox_objects.py \
  --batch-plan reports/pilot-device-compliance/approvals/approved/batch-apply-plan-<BATCH_ID>.json \
  --netbox-url https://docs.k3gsolutions.com.br \
  --confirm-batch-id <BATCH_ID> \
  --operator "seu-nome"
```

Sem `--confirm-real-write-batch`: **zero POST**

Output: `reports/pilot-device-compliance/approvals/applied/batch-apply-result-<BATCH_ID>.md`

Conteúdo:
- Resumo do batch
- Resultado do preflight (todos os gates)
- Status: batch_preflight_passed ou batch_blocked
- Próximos passos
- Mensagem "DRY RUN: Would create 3 interfaces"

Revisar resultado antes de executar real write.

## 8. Real Write Batch

Se dry-run passou, executar real write:

```bash
NETBOX_WRITE_TOKEN="seu-token-aqui" \
python3 tools/local/apply_batch_staged_netbox_objects.py \
  --batch-plan reports/pilot-device-compliance/approvals/approved/batch-apply-plan-<BATCH_ID>.json \
  --netbox-url https://docs.k3gsolutions.com.br \
  --confirm-batch-id <BATCH_ID> \
  --operator "seu-nome" \
  --confirm-real-write-batch
```

Validações antes de POST:
- ✅ token presente
- ✅ batch_id confirmado
- ✅ operator informado
- ✅ todos os itens passam no preflight
- ✅ all-or-none: se qualquer item falhar, abortar

Durante POST:
- POST item 1 → se 201, continuar
- POST item 2 → se 201, continuar
- POST item 3 → se 201, sucesso total
- Se qualquer falhar: parar, registrar partial_failure

Output: `batch-apply-result-<BATCH_ID>.md` atualizado com:
- Resultado final: batch_applied, batch_partial_failed, ou batch_blocked
- NetBox object IDs para sucesso
- Erro detalhado se falha
- Timestamp de execução
- Auditoria completa

## 9. Pós-Apply: Compliance Report

Gerar novo compliance report:

```bash
# Via API (se servidor rodando)
curl -s -X POST http://127.0.0.1:8888/compliance/analyze/report \
  -H "Content-Type: application/json" \
  -d @reports/pilot-device-compliance/payload.local.json \
  > reports/pilot-device-compliance/pilot-device-compliance-report-after-batch-staged-apply.md

# Ou via script local se necessário
python3 tools/local/<compliance-script>.py \
  --device 4WNET-MNS-KTG-RX
```

## 10. Pós-Apply: Arquivo Report

Arquivar novo relatório:

```bash
python3 tools/local/archive_compliance_report.py \
  --report reports/pilot-device-compliance/pilot-device-compliance-report-after-batch-staged-apply.md \
  --device 4WNET-MNS-KTG-RX \
  --device-id 1890
```

Estrutura atualizada:
- `current/4WNET-MNS-KTG-RX-compliance-report.md` ← novo
- `history/4WNET-MNS-KTG-RX/2026-04-28T...` ← histórico
- `index.json` ← metadados atualizados

## 11. Pós-Apply: Comparação

Comparar antes/depois:

```bash
python3 tools/local/compare_compliance_reports.py \
  --old reports/pilot-device-compliance/current/<antes> \
  --new reports/pilot-device-compliance/current/<depois> \
  --output reports/pilot-device-compliance/comparisons/batch-staged-apply-comparison.md \
  --device 4WNET-MNS-KTG-RX
```

Output: `batch-staged-apply-comparison.md` com:
- Evolução por severidade (antes/agora/delta)
- Novas divergências
- Divergências resolvidas
- Divergências recorrentes

Esperado:
- 3 interfaces já não aparecem como INTERFACE_MISSING_IN_NETBOX
- 3 interfaces não aparecem como DESCRIPTION_NON_COMPLIANT (base_inventory)
- Podem aparecer como INTERFACE_DESCRIPTION_MISMATCH (review)
- Total de divergências reduz

## 12. Pós-Apply: Validação

Confirmar no NetBox UI:
1. Devices > Device > 4WNET-MNS-KTG-RX
2. Interfaces
3. Verificar:
   - Status: planned (staged)
   - Tags: discovery:staged, approval:*, etc
   - Custom fields: discovery_source, approval_id, etc
   - Nenhum erro

## 13. Registro e Documentação

Atualizar:
- `context/NEXT_ACTIONS.md` — próximos passos
- `CHANGELOG.md` — entrada de FASE 2.3
- `reports/pilot-device-compliance/pilot-device-summary.md` — estatísticas
- `docs/32-batch-apply-runbook.md` — este documento com resultados

## 14. Critério de Sucesso

✅ Batch com até 3 interfaces base_inventory
✅ Todas criadas com status 201 Created
✅ NetBox object IDs registrados
✅ Nenhum PATCH/DELETE
✅ Nenhuma configuração em equipamento
✅ Compliance pós-apply gerado
✅ Comparação antes/depois gerada
✅ Divergências reduzidas
✅ Auditoria completa

## 15. Critério de Parada

❌ Tag ausente → fix tags, retry
❌ Objeto já existe → skip item
❌ Batch >3 → dividir em lotos menores
❌ POST falha → investigar erro, não retry automático
❌ Token inválido → revisar credencial

## Referências

- [Controlled Batch Staged Apply Design](./31-controlled-batch-staged-apply.md)
- [Staged Apply Design](./27-staged-apply-design.md)
- [First Staged NetBox Write](./30-first-staged-netbox-write.md)
- [Tools README](../tools/local/README.md)
