# Approval State Management — FASE 1.7

Gerenciamento local de estados do ApprovalRecord sem escrita no NetBox.

## Estados e Transições

### Estados Válidos

- **proposed**: Estado inicial (criado por create_approval_record.py)
- **approved**: Revisado e aprovado (move para approvals/approved/)
- **rejected**: Revisado e rejeitado (move para approvals/rejected/)
- **changes_requested**: Revisão solicitou mudanças (final nesta fase)
- **dry_run_passed**: Aprovado e dry-run validado (final nesta fase)
- **ignored**: Marcado como ignorado (final)

### Grafo de Transições

```
proposed
  ├─→ approved (via approve)
  ├─→ rejected (via reject)
  ├─→ changes_requested (via request-changes)
  └─→ ignored (via mark-ignored)

approved
  ├─→ dry_run_passed (via mark-dry-run-passed)
  └─→ expired (via mark-expired)

rejected (final)
changes_requested (final)
dry_run_passed (final)
ignored (final)
```

## Movimentação de Arquivos

| Transição | Origem | Destino |
|-----------|--------|---------|
| create | N/A | approvals/pending/ |
| approve | pending/ | approvals/approved/ |
| reject | pending/ | approvals/rejected/ |
| request-changes | pending/ | approvals/changes_requested/ |
| mark-dry-run-passed | approved/ | approvals/approved/ (stay) |
| mark-ignored | pending/ | approvals/ignored/ |

## Script: manage_approval_state.py

### Sintaxe

```bash
python3 tools/local/manage_approval_state.py <comando> \
  --approval <arquivo-json> \
  --by <operador> \
  [opções adicionais]
```

### Comandos

#### approve

Transiciona para approved. Validações:
- action deve ser `safe_create_staged`
- Se category=service: naming_compliant deve ser true
- confidence deve ser exact ou normalized
- Nenhum secret em evidence

```bash
python3 tools/local/manage_approval_state.py approve \
  --approval reports/pilot-device-compliance/approvals/pending/<id>.json \
  --by "nome-revisor" \
  --comment "Aprovado para staged import"
```

**Efeitos:**
- Status: proposed → approved
- Move arquivo: pending/ → approved/
- Atualiza: reviewed_by, reviewed_at, decision, comment
- Adiciona state_history entry

#### reject

Transiciona para rejected. Sem validações.

```bash
python3 tools/local/manage_approval_state.py reject \
  --approval reports/pilot-device-compliance/approvals/pending/<id>.json \
  --by "nome-revisor" \
  --reason "Dados insuficientes"
```

**Efeitos:**
- Status: proposed → rejected
- Move arquivo: pending/ → rejected/
- Atualiza: reviewed_by, reviewed_at, decision, rejection_reason
- Adiciona state_history entry

#### request-changes

Transiciona para changes_requested. Sem validações.

```bash
python3 tools/local/manage_approval_state.py request-changes \
  --approval reports/pilot-device-compliance/approvals/pending/<id>.json \
  --by "nome-revisor" \
  --reason "Ajustar descrição: remover caracteres especiais"
```

**Efeitos:**
- Status: proposed → changes_requested
- Move arquivo: pending/ → changes_requested/
- Atualiza: reviewed_by, reviewed_at, decision, rejection_reason
- Adiciona state_history entry

#### mark-dry-run-passed

Transiciona para dry_run_passed. Apenas de approved.

```bash
python3 tools/local/manage_approval_state.py mark-dry-run-passed \
  --approval reports/pilot-device-compliance/approvals/approved/<id>.json \
  --by "nome-validador" \
  --dry-run-report reports/.../dry-run-<id>.md
```

**Efeitos:**
- Status: approved → dry_run_passed
- Arquivo permanece em approved/
- Atualiza: dry_run_by, dry_run_at, audit.dry_run_report
- Adiciona state_history entry

## Estrutura de ApprovalRecord

### Seção review (atualizada)

```json
{
  "review": {
    "status": "proposed|approved|rejected|changes_requested|dry_run_passed|ignored",
    "reviewed_by": "operador",
    "reviewed_at": "ISO8601",
    "decision": "approve|reject|request_changes|mark_ignored",
    "comment": "...",
    "rejection_reason": "...",
    "dry_run_by": "operador",
    "dry_run_at": "ISO8601"
  }
}
```

### Seção audit (atualizada)

```json
{
  "audit": {
    "dry_run_report": "path/to/dry-run-<id>.md"
  }
}
```

### Campo state_history (novo)

```json
{
  "state_history": [
    {
      "from": "proposed",
      "to": "approved",
      "by": "operador",
      "at": "ISO8601",
      "tool_version": "1.0",
      "reason": "Aprovado para staged import"
    }
  ]
}
```

## Validações

### approve

Bloqueia se:
- action ≠ safe_create_staged
- category = service E naming_compliant ≠ true
- confidence ∉ {exact, normalized}
- Evidence contém forbidden patterns (password, token, secret, api_key, ssh)

### reject, request-changes, mark-dry-run-passed

- Nenhuma validação obrigatória
- Apenas verificação de transição válida

## Backup e Recuperação

Cada save_approval_record cria backup:
```
<arquivo>.backup.2026-04-28T10:42:22.771415+00:00
```

## Segurança

✅ **Read-only:**
- Nenhuma API real
- Nenhuma escrita NetBox
- Nenhum token write
- Apenas manipulação de JSON local

✅ **Auditável:**
- state_history imutável (append-only)
- Todos os operadores registrados (by + at)
- Razões documentadas

✅ **Sem Secrets:**
- Validação de forbidden patterns
- Evidence sanitizado

## Limitações (FASE 1.7)

- Nenhuma execução de staged import (FASE 2.0)
- Nenhuma sincronização com NetBox
- Nenhum endpoint HTTP (será FASE 1.7.1)
- Nenhuma notificação automática

## Próximos Passos (FASE 1.7+)

### FASE 1.7.1
- Implementar `/compliance/approve` endpoint HTTP
  - POST /compliance/approve
  - Accept decision + comment em request body
  - Call manage_approval_state.py via subprocess
  - Return updated ApprovalRecord JSON

### FASE 1.7.2
- Batch generation script para gerar ApprovalRecords em lote
- Filter por category, confidence, object_type

### FASE 2.0
- Staged import real com token write separado
- Call NetBox API para criar/atualizar objetos
- Move ApprovalRecord para approvals/applied/

## Exemplos

### Aprovação completa (piloto FASE 1.6)

```bash
# Item: Eth-Trunk0 (base_inventory, safe_create_staged, exact)

# 1. Criar ApprovalRecord
python3 tools/local/create_approval_record.py \
  --device 4WNET-MNS-KTG-RX \
  --device-id 1890 \
  --object-type interface \
  --object-key Eth-Trunk0 \
  --action safe_create_staged \
  --code INTERFACE_MISSING_IN_NETBOX \
  --category base_inventory \
  --reason "Base LAG interface" \
  --confidence exact \
  --naming-compliant \
  --evidence '{"applied": 1, "status": "up"}'

# 2. Renderizar summary para review
python3 tools/local/render_approval_summary.py \
  reports/pilot-device-compliance/approvals/pending/approval-*.json

# 3. Revisor aprova
python3 tools/local/manage_approval_state.py approve \
  --approval reports/pilot-device-compliance/approvals/pending/approval-*.json \
  --by "revisor-nome" \
  --comment "OK para staged import"

# 4. Validar dry-run
python3 tools/local/dry_run_netbox_payload.py \
  --approval-id <id> \
  --device 4WNET-MNS-KTG-RX \
  --object-type interface \
  --object-key Eth-Trunk0 \
  --action safe_create_staged \
  --evidence '{"status": "up", "mtu": 1500}' \
  --category base_inventory

# 5. Marcar dry-run como passed
python3 tools/local/manage_approval_state.py mark-dry-run-passed \
  --approval reports/pilot-device-compliance/approvals/approved/approval-*.json \
  --by "validador-nome" \
  --dry-run-report reports/.../dry-run-<id>.md

# Resultado: ApprovalRecord em approvals/approved/ com status=dry_run_passed
# Pronto para staged import real em FASE 2.0
```

### Rejeição

```bash
python3 tools/local/manage_approval_state.py reject \
  --approval reports/pilot-device-compliance/approvals/pending/approval-*.json \
  --by "revisor-qa" \
  --reason "Interface não aparece em produção; aguardar evidência do device"

# Resultado: ApprovalRecord movido para approvals/rejected/
```

### Mudanças solicitadas

```bash
python3 tools/local/manage_approval_state.py request-changes \
  --approval reports/pilot-device-compliance/approvals/pending/approval-*.json \
  --by "revisor-arquitetura" \
  --reason "Adicionar MTU 9000 para jumbo frames; resubmit quando houver especificação"

# Resultado: ApprovalRecord movido para approvals/changes_requested/
```

## Referências

- [ApprovalRecord Schema](./24-approval-record-schema.md)
- [Approval Dry-Run](./25-approval-dry-run.md)
- [Pilot Report](../reports/pilot-device-compliance/approvals/pending/PILOT-FASE-1-6-RESULT.md)
