# FASE 2.35 — Week 2 Review Decision UI

**Status:** ✓ COMPLETO

## Objetivo

Preparar fluxo para humano preencher decisões da Semana 2 sem editar CSV manualmente, mantendo governança local.

## Rotas HTTP

### GET /service-engagement/{device}/week2-review/items

Lista items Week 2 para revisão.

**Resposta:** JSON com item_id, object_key, object_type, status, restriction, allowed_actions.

### GET /service-engagement/{device}/week2-review/items/{safe_item_id}

Detalhe de um item para modal de decisão.

**Resposta:** JSON com dados completos + draft_data + existing_decision.

### POST /service-engagement/{device}/week2-review/items/{safe_item_id}/decision

Salva decisão humana localmente.

**Payload:**
```json
{
  "reviewer": "alice",
  "decision": "approve_for_approval_record|request_changes|reject|defer|block",
  "reason": "...",
  "notes": "...",
  "approval_record_allowed": true
}
```

**Validações:**
- reviewer: obrigatório
- decision: obrigatório
- approve_for_approval_record: requer approval_record_allowed=true, reason ou notes
- request_changes: requer notes
- reject/block: requer reason
- defer: requer notes

## Armazenamento

### CSV

`reports/pilot-device-compliance/week2-review/week2-review-decisions.csv`

Colunas: item_id, reviewer, decision, reason, notes, reviewed_at, approval_record_allowed

### Audit JSON

`reports/pilot-device-compliance/week2-review/audit/decision-*.json`

Cada decisão gera arquivo de auditoria com timestamp, payload, security flags.

## Segurança

✓ Sem ApprovalRecord automático
✓ Sem ApplyPlan automático
✓ Sem NetBox writes
✓ Sem tokens
✓ Decisões locais apenas

## Próximos Passos

- validate_week2_review_decisions.py — validar decisões locais
- Promoção controlada para ApprovalRecords = etapa separada (manual)
