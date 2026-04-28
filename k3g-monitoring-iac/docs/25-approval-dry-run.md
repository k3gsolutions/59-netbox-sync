# Approval Dry-Run — FASE 1.5

Validação de payload NetBox sem escrever no NetBox. Read-only.

## Visão geral

Três ferramentas locais para criar e validar ApprovalRecords:

1. **create_approval_record.py** — cria ApprovalRecord JSON local
2. **render_approval_summary.py** — gera Markdown resumido
3. **dry_run_netbox_payload.py** — valida payload futuro (sem escrita)

Nenhuma API real. Nenhum token write. Apenas validação e auditoria.

## Ferramenta 1: create_approval_record.py

Cria ApprovalRecord JSON a partir de item do ImportPlan.

### Uso básico

```bash
python3 tools/local/create_approval_record.py \
  --device 4WNET-MNS-KTG-RX \
  --device-id 123 \
  --object-type interface \
  --object-key Eth-Trunk0 \
  --action safe_create_staged \
  --code INTERFACE_MISSING_IN_NETBOX \
  --category base_inventory \
  --reason "Base interface inventory (physical/LAG/management)" \
  --confidence exact \
  --naming-compliant \
  --evidence '{"interface": "Eth-Trunk0", "status": "up"}' \
  --report-path reports/pilot-device-compliance/current/... \
  --report-timestamp 2026-04-28T09:45:00Z
```

### Argumentos

**Obrigatórios:**
- `--device` — hostname do equipamento
- `--device-id` — ID NetBox DCIM
- `--object-type` — interface, ip_address, vrf, vlan, bgp_peer
- `--object-key` — identificador único (Eth-Trunk0, 10.0.0.1/24, etc)
- `--action` — safe_create_staged | needs_review
- `--code` — código de divergência
- `--reason` — motivo da classificação
- `--confidence` — exact | normalized | possible | ambiguous | none
- `--evidence` — JSON string com dados da divergência
- `--report-path` — caminho do relatório de compliance
- `--report-timestamp` — timestamp ISO8601 do relatório

**Opcionais:**
- `--category` — base_inventory | service
- `--naming-compliant` — flag se naming é válido
- `--import-plan-id` — ID do ImportPlan (auto-gerado se omitido)
- `--output` — diretório saída (default: approvals/pending/)

### Output

```json
{
  "approval_id": "uuid",
  "import_plan_id": "uuid",
  "device": "4WNET-MNS-KTG-RX",
  "device_id": 123,
  "proposal": {
    "object_type": "interface",
    "object_key": "Eth-Trunk0",
    "action": "safe_create_staged",
    "category": "base_inventory",
    "confidence": "exact",
    "naming_compliant": true,
    "reason": "...",
    "preferred_next_step": "..."
  },
  "review": {
    "status": "proposed",
    "reviewed_by": null,
    "reviewed_at": null,
    "decision": null,
    "comment": null
  },
  "audit": {
    "evidence_hash": "sha256:abc...",
    "report_path": "...",
    "report_timestamp": "..."
  }
}
```

### Validações

Bloqueia se:
- `action` = blocked ou ignore
- Service interface sem naming válido
- Credenciais em evidence (forbidden: password, token, secret, api_key)

## Ferramenta 2: render_approval_summary.py

Gera Markdown resumido de ApprovalRecord.

### Uso

```bash
python3 tools/local/render_approval_summary.py \
  approval-4WNET-MNS-KTG-RX-abc123-20260428.json \
  --output approval-summary.md
```

### Output

```markdown
# Approval Summary — abc123

## 1. Proposta
- **Objeto:** interface / Eth-Trunk0
- **Ação:** safe_create_staged
- **Razão:** ...

## 2. Evidência
- interface: Eth-Trunk0
- status: up

## 3. Avaliação de Risco
🟢 BAIXO RISCO
- Interface base (sem dependências de serviço)
- Naming válido
- Pode ser aprovado rapidamente

## 4. Checklist de Aprovação
- [ ] Nome segue padrão base?
- [ ] Não é subinterface?
- [ ] Status UP ou esperado?
- [ ] Sem conflito óbvio?

## 5. Decisão Pendente
Responda:
1. Approve? Comment: (motivo)
2. Reject? Comment: (motivo)
3. Request Changes? Changes: (lista)

## 6. Auditoria
- Criado em: 2026-04-28T...
- Evidence Hash: sha256:abc...

## 7. Segurança
✅ Read-only — Nenhuma escrita no NetBox
```

## Ferramenta 3: dry_run_netbox_payload.py

Valida payload NetBox futuro (sem escrita).

### Uso

```bash
python3 tools/local/dry_run_netbox_payload.py \
  --approval-id abc123 \
  --device 4WNET-MNS-KTG-RX \
  --object-type interface \
  --object-key Eth-Trunk0 \
  --action safe_create_staged \
  --evidence '{"status": "up", "mtu": 1500}' \
  --category base_inventory
```

### Output

Gera arquivo: `dry-run-abc123.md`

```markdown
# Dry-Run Report — abc123

**Device:** 4WNET-MNS-KTG-RX
**Object:** interface / Eth-Trunk0
**Action:** safe_create_staged

## Suggested NetBox Payload
```json
{
  "name": "Eth-Trunk0",
  "type": "1000base-t",
  "enabled": true,
  "mtu": 1500,
  "tags": ["discovery:netops_netbox_sync", "discovery:staged", "inventory:base-interface"]
}
```

## Validation Results
- INFO: 'type' field missing (will use default)

## Dry-Run Status
✓ **PASSED** — Ready for approval and staged import
```

### Validações

Schema validation por type:
- **interface:** name, type, enabled, mtu, description, tags
- **ip_address:** address, vrf, assigned_object
- **vrf:** name, description
- **vlan:** vid, name, description
- **bgp_peer:** asn, remote_asn, remote_ip, description

Sempre verifica: passwords, tokens, secrets

### Status de saída

- `0` se passou (sem ERRORs)
- `1` se falhou (contém ERRORs)

## Fluxo completo

```
1. Gerar ImportPlan (FASE 1.3)
   ↓
2. Revisor escolhe item para aprovação
   ↓
3. create_approval_record.py
   └→ approval-DEVICE-id-timestamp.json (status: proposed)
   ↓
4. render_approval_summary.py
   └→ approval-summary.md (review checklist)
   ↓
5. Revisor lê summary, toma decisão (approve/reject/request_changes)
   ↓
6. dry_run_netbox_payload.py
   └→ dry-run-id.md (validation report, if approved)
   ↓
7. Se dry-run passou:
   └→ move para approvals/approved/
   └→ aguardando staged import (FASE futuro)
   ↓
8. Se dry-run falhou ou rejeitado:
   └→ move para approvals/rejected/ ou
   └→ retorna para ajustes
```

## Exemplo: Base interface

```bash
# 1. Create approval record
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
  --report-path reports/.../-compliance-report.md \
  --report-timestamp 2026-04-28T09:45:00Z

# 2. Render summary for review
python3 tools/local/render_approval_summary.py \
  reports/pilot-device-compliance/approvals/pending/approval-*.json \
  --output approval-summary.md

# 3. Reviewer reads summary, decides to approve
# 4. Validate payload (dry-run)
python3 tools/local/dry_run_netbox_payload.py \
  --approval-id abc123 \
  --device 4WNET-MNS-KTG-RX \
  --object-type interface \
  --object-key Eth-Trunk0 \
  --action safe_create_staged \
  --evidence '{"status": "up", "mtu": 1500}' \
  --category base_inventory

# 5. If dry-run passed (exit code 0):
# Move to approved/
# Wait for staged import in next phase

# 6. If dry-run failed (exit code 1):
# Fix issues and retry
```

## Arquivos de saída

### ApprovalRecord

Localização:
```
reports/pilot-device-compliance/approvals/pending/
  approval-4WNET-MNS-KTG-RX-abc123-20260428.json
```

Status: `proposed` → será alterado para `approved` ou `rejected` após review

### Dry-Run Report

Localização:
```
reports/pilot-device-compliance/approvals/pending/
  dry-run-abc123.md
```

Propósito: Validação de schema e segurança antes de staged import

## Segurança

✅ **Read-only:**
- Nenhuma API real
- Nenhuma escrita no NetBox
- Nenhum token write usado
- Apenas validação local

✅ **Auditável:**
- approval_id único
- evidence_hash para integridade
- report_path e report_timestamp rastreáveis
- Sem credenciais em records

✅ **Validação:**
- Bloqueia secrets
- Valida schema por tipo
- Detecta naming inválido
- Rejeita items blocked/ignore

## Erros comuns

### "Cannot create approval for action=blocked"

Bloqueado pela validação. Items blocked precisam de dados suficientes antes.

Solução: Esperar que dados sejam coletados e compliance re-executado.

### "Service interface X has invalid naming"

Subinterface sem padrão base.vlan_id.

Solução: Corrigir naming ou rejeitar item.

### "ERROR: Missing 'address' field (required)"

IP address sem campo address.

Solução: Validar evidence, recolher dados.

### "Forbidden pattern in evidence: token"

Credencial em evidence.

Solução: Nunca adicionar segredos em evidence. Sanitizar antes.

## Próximos passos (FASE futuro)

- Implementar UI para review
- Executar staged import real (com token write)
- Registrar resultado em ApprovalRecord
- Auditoria completa

---

## Referências

- [Approval Workflow Design](./23-approval-workflow-design.md)
- [ApprovalRecord Schema](./24-approval-record-schema.md)
- [Approval Workflow Review Prompt](../prompts/approval-workflow-review.md)
