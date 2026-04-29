# Governance & Security Checklist — FASES 2.34, 2.35, 3.17

## Máximas de Governança

- [x] Nenhuma escrita NetBox
  - Confirmado: App apenas GET/POST local
  - Sem client NetBox
  - Sem IP/secrets

- [x] Nenhum token
  - Confirmado: Sem auth headers
  - Sem API keys em código
  - Sem credentials persistidas

- [x] Nenhum apply
  - Confirmado: Sem /sync
  - Sem ApplyPlan automático
  - Sem template render to devices

- [x] Nenhum /sync
  - Confirmado: Routes não chamam sync
  - Sem background job
  - Sem scheduler

- [x] Nenhum ApprovalRecord automático
  - Confirmado: Week2Decision apenas salva CSV
  - Sem ApprovalRecord criado por POST
  - Decisão humana é pré-requisito

- [x] Nenhum ApplyPlan automático
  - Confirmado: Sem geração de apply plans
  - Sem batch execution
  - Sem asset refresh

- [x] Revisão humana obrigatória
  - Confirmado: reviewer field obrigatório
  - Sem default values
  - Sem auto-approval

- [x] Registry é fonte oficial
  - Confirmado: 13 policies versionadas em YAML
  - Sem fallback silencioso
  - Validação em load

## Security Checks

- [x] Path traversal protegido
  - POLICY_WHITELIST em app.py
  - safe_resolve_path() utilizado
  - Sem glob patterns em user input

- [x] Secrets não expontos
  - CSV audit não contém tokens
  - YAML mascarado em GET /policies/{name}
  - Sem raw policy content in logs

- [x] Decisões auditadas
  - Cada decisão gera JSON com timestamp
  - audit/ directory segregado
  - reviewer field rastreado

- [x] Sem estado mutable via POST
  - POST /decision apenas salva CSV
  - Sem estado NetBox modificado
  - Sem asset changed

- [x] Testes passando
  - app.py compila
  - services compilam
  - Week2Decision tests ✓
  - Validation tests ✓

## Artefatos Segregados

- [x] CSV de decisões isolado
  - reports/pilot-device-compliance/week2-review/week2-review-decisions.csv
  - Local apenas
  - Sem sync para NetBox

- [x] Audit trail segregado
  - reports/pilot-device-compliance/week2-review/audit/
  - Imutável após creation
  - Timestamp + payload

- [x] Reports segregados
  - reports/compliance-policy-impact-*.md
  - reports/pilot-device-compliance/compliance-policy-impact-baseline.*
  - Sem dados vivos

## Próxima Gate (FASE 2.36+)

Antes de promoção para ApprovalRecords:
- [ ] Validação de todas as decisões (validate_week2_review_decisions.py)
- [ ] Revisão manual de 100% das propostas
- [ ] Approval records criados manualmente via CLI separate
- [ ] Sem automação de ApprovalRecord creation

