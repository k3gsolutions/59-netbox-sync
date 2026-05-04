# Compliance Remediation Drafts

FASES COMPLIANCE-REMEDIATION-001–004 criam um fluxo local para gerar rascunhos de remediação a partir dos findings revisados.

## Regras

- Nenhuma escrita em NetBox.
- Nenhum `/sync`.
- Nenhuma conexão com equipamento.
- Nenhum `ApprovalRecord`.
- Nenhum `ApplyPlan`.
- Rascunhos são apenas artefatos locais em `reports/compliance/jobs/<job_id>/remediation/drafts/`.

## Artefatos

- `remediation-drafts.json`
- `REMEDIATION-DRAFTS.md`
- `remediation-draft-validation.json`
- `REMEDIATION-DRAFT-VALIDATION.md`
- `remediation-promotion-gate.json`
- `REMEDIATION-PROMOTION-GATE.md`

## Endpoint

- `POST /compliance/jobs/{job_id}/remediation/drafts`

Payload:

```json
{
  "operator": "Keslley",
  "confirm_generate_drafts": true
}
```

## Saída

Cada draft é descritivo e sempre inclui:

- `write_allowed=false`
- `execution_allowed=false`
- `requires_apply_plan=false`
- `requires_approval=true`
- bloco `safety`

