# Prompt — N8N Workflow Builder

Utilize este prompt para planejar/criar/revisar workflows N8N.

## Entradas necessárias
- Objetivo do workflow.
- Trigger (webhook, schedule, manual).
- Inputs esperados.
- Outputs esperados.
- Lista de nodes (funções, integrações, checks).
- Variáveis de ambiente e credenciais.
- Testes e modo dry-run desejados.

## Checklist
- Idempotência garantida?
- Suporte a dry-run?
- Audit log registrado?
- Tratamento de erro e DLQ?
- Smoke tests documentados?
- Anti-padrões evitados (ex.: escrita sem validação, loops sem controle)?

## Saída
- Diagrama ou passo a passo.
- Pseudoconfiguração dos nodes.
- Plano de testes.
- Riscos e mitigação.