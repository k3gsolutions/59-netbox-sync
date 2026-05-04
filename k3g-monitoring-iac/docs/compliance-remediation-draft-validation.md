# Compliance Remediation Draft Validation

FASE COMPLIANCE-REMEDIATION-003 valida os rascunhos gerados localmente.

## Regras

- Nenhuma escrita em NetBox.
- Nenhum `ApprovalRecord`.
- Nenhum `ApplyPlan`.
- Validação só lê `remediation-drafts.json` e escreve artefatos locais.

## Endpoint

- `GET /compliance/jobs/{job_id}/remediation/drafts/validation`

## Decisões

- `REMEDIATION_DRAFTS_SAFE`
- `REMEDIATION_DRAFTS_SAFE_WITH_WARNINGS`
- `REMEDIATION_DRAFTS_UNSAFE`

## Validações

- `write_allowed` não pode ser `true`
- `execution_allowed` não pode ser `true`
- `requires_apply_plan` não pode ser `true`
- nenhum `ApprovalRecord`
- nenhum `ApplyPlan`
- nenhum comando proibido em `command_preview`
- nenhum token, password, secret ou cipher em `proposed_change`

