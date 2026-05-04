# Compliance Remediation Promotion Gate

FASE COMPLIANCE-REMEDIATION-004 avalia se os drafts locais podem seguir para o próximo fluxo.

## Regras

- Nenhuma promoção real acontece aqui.
- Nenhum `ApprovalRecord`.
- Nenhum `ApplyPlan`.
- Nenhuma escrita em NetBox.

## Endpoint

- `POST /compliance/jobs/{job_id}/remediation/promotion-gate`

Payload:

```json
{
  "operator": "Keslley",
  "confirm_human_reviewed_drafts": true
}
```

## Decisões

- `REMEDIATION_PROMOTION_CANDIDATE_READY`
- `REMEDIATION_PROMOTION_CANDIDATE_READY_WITH_WARNINGS`
- `REMEDIATION_PROMOTION_BLOCKED`

## Entrada

- `remediation-drafts.json`
- `remediation-draft-validation.json`

O gate só sinaliza prontidão para o fluxo seguinte. Ele não cria candidatos nem promove nada.

