# Skill: Approval Workflow

Orientações para revisar e aprovar propostas de importação ao NetBox de forma segura.

## Metadados

- **Name:** approval-workflow
- **Category:** netops, compliance, netbox
- **Version:** 1.0
- **Scope:** FASE 1.4 (design apenas, sem implementation)
- **Status:** documented, not_implemented
- **Dependencies:** ImportPlan, ComplianceAnalysis

## Descrição

Review de ImportPlan e aprovação de propostas de staged import, garantindo que:
- Nenhuma escrita no NetBox sem aprovação explícita
- Itens fora da naming convention são rejeitados
- Metadados suficientes antes de staged import
- Auditoria completa de decisões

## Quando usar

1. Após executar compliance analysis
2. Após gerar ImportPlan
3. Antes de qualquer staged import futuro
4. Quando revisor precisa avaliar propostas

## Entrada esperada

```json
{
  "import_plan": "ImportPlan JSON",
  "compliance_report": "Markdown compliance report",
  "device": "4WNET-MNS-KTG-RX",
  "device_id": 123
}
```

## Saída esperada

```json
{
  "approvals": [
    {
      "approval_id": "uuid",
      "proposal": {...},
      "decision": "approve|reject|request_changes|defer",
      "comment": "human-readable reason"
    }
  ],
  "summary": {
    "total_reviewed": 161,
    "approved": 59,
    "rejected": 10,
    "deferred": 5,
    "changes_requested": 2
  }
}
```

## Processo

### 1. Validar contexto

- [ ] Device identificado corretamente
- [ ] Compliance report é recente (<24h)
- [ ] ImportPlan foi gerado corretamente
- [ ] Nenhum erro óbvio no relatório

### 2. Revisar Safe Create Staged - Base

Para cada item com `category: base_inventory`:

Checklist:
- Nome segue padrão base? (Ethernet, Eth-Trunk, Management, etc)
- Não é subinterface (sem ponto)?
- Não sobrescreve objeto?

Decision tree:
```
naming_compliant = true
confidence = exact
no_conflict = true
  → APPROVE

ELSE
  → REJECT ou DEFER
```

### 3. Revisar Safe Create Staged - Service

Para cada item com `category: service`:

Checklist:
- Nome segue padrão serviço? (base.vlan_id)
- Tenant identificado?
- Service_type identificado?
- Criticality conhecido?
- Confidence excelente?

Decision tree:
```
naming_compliant = true
confidence ∈ {exact, normalized}
tenant_id ≠ null
service_type_id ≠ null
no_conflict = true
  → APPROVE

naming_compliant = false
  → REJECT (request_changes com sugestão de naming)

tenant_id = null OR service_type_id = null
  → REQUEST_CHANGES (coletar metadados)

confidence ∈ {ambiguous, none}
  → DEFER ou REJECT
```

### 4. Revisar Needs Review

Para cada item com `action: needs_review`:

Tipos:
- BGP peer → validar peer IP, ASN, description
- IP address → validar formato, VRF, interface pai
- VLAN → validar ID, propósito, tenant
- Naming inválido → sugerir naming válido

Decision tree:
```
pode_corrigir = true
humano_confirma = true
  → REQUEST_CHANGES (com sugestão específica)

não_pode_corrigir OR dados_insuficientes
  → DEFER ou REJECT
```

### 5. Revisar Blocked

Para cada item com `action: blocked`:

- Motivo está claro?
- Há forma de desbloquear?

Decision tree:
```
motivo_desbloqueável = true
recolher_dados_possível = true
  → DEFER (com próximos passos)

motivo_permanente
  → MARK_AS_IGNORED
```

### 6. Registrar decisões

Para cada item aprovado/rejeitado:

```json
{
  "approval_id": "unique_id",
  "import_plan_id": "...",
  "device": "...",
  "proposal": {...},
  "review": {
    "status": "approved|rejected|request_changes",
    "decision": "...",
    "reviewed_by": "you@company.com",
    "reviewed_at": "2026-04-28T14:30:00Z",
    "comment": "motivo claro"
  },
  "audit": {
    "evidence_hash": "sha256:...",
    "report_path": "..."
  }
}
```

### 7. Salvar ApprovalRecords

Diretório: `reports/pilot-device-compliance/approvals/`

Subdirs:
- `pending/` — aguardando confirmação
- `approved/` — aprovados, prontos para dry-run
- `rejected/` — rejeitados, não serão processados
- `applied/` — (futuro) aplicados no NetBox

Nomear arquivo:
```
approval-{device}-{timestamp}.json
approval-{object_key}-{timestamp}.json
```

## Critérios de aceite

### Agora (FASE 1.4)

- [ ] Posso revisar ImportPlan
- [ ] Posso documentar decisão (approve/reject/request_changes)
- [ ] Puedo salvar ApprovalRecord em JSON
- [ ] Arquivo contém evidence_hash para auditoria
- [ ] Arquivo não contém credenciais/secrets
- [ ] Posso revisar histórico de decisões

### Futuro (FASE 1.5)

- [ ] Posso executar dry-run antes de apply
- [ ] Posso confirmar dry-run com assinatura
- [ ] Posso visualizar diff esperado no NetBox
- [ ] Sistema registra resultado de apply
- [ ] Posso auditoria completa de quem aprovou o quê

## Anti-padrões — Não fazer

❌ Aprovar itens sem revisar evidence

❌ Aprovar itens fora da naming convention
- Regra crítica: naming inválido sempre → needs_review

❌ Aprovar itens com confidence ambiguous/none

❌ Aprovar itens blocked
- Exigem dados suficientes primeiro

❌ Adicionar secrets em approval comment

❌ Saltar validação de tenant/service_type para itens service

❌ Aprovar delete ou update de objetos existentes
- Apenas CREATE é permitido agora

## Fluxo rápido

```
1. Abrir ImportPlan report
2. Seção "Safe Create Staged - Base"
   → revisar rapidamente
   → aprovar se naming válido
3. Seção "Safe Create Staged - Service"
   → revisar cuidadosamente
   → aprovar se naming + tenant + service_type válidos
   → request_changes se faltam metadados
4. Seção "Needs Review"
   → revisar por tipo (BGP/IP/VLAN/naming)
   → reject se fora naming convention
   → request_changes se metadados incompletos
5. Seção "Blocked"
   → ignorar ou defer com próximos passos
6. Salvar ApprovalRecords em JSON
7. Confirmar segurança (read-only, sem secrets, auditável)
```

## Escalação

Se encontrar:

- **Token/credencial em evidence** → parar, notificar segurança
- **Operação delete proposta** → parar, investigar divergence
- **Conflito óbvio com produção** → defer, notificar topology team
- **Naming convention não clara** → defer, clarificar policy

## Documentação relacionada

- Approval Workflow Design (../docs/23-approval-workflow-design.md)
- ApprovalRecord Schema (../docs/24-approval-record-schema.md)
- Approval Workflow Review Prompt (../prompts/approval-workflow-review.md)
- ImportPlan design (../../netops_netbox_sync/docs/FASE_1_3_IMPORT_PLAN.md)
