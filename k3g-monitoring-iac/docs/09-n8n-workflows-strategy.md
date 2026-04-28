# 09 — Estratégia de Workflows N8N

## Objetivo
Orquestrar automações de monitoramento com N8N, garantindo idempotência e governança.

## Diretrizes
- Workflows documentados em Markdown antes da implementação.
- Cada workflow com trigger, inputs, outputs, nodes, dry-run, audit log, DLQ.
- Erros direcionados a workflows de tratamento (`wf-error-handler`).
- Credenciais gerenciadas fora do repositório.

## Próximos passos
- Detalhar workflows críticos: onboarding device/circuit, reconcile, compliance.
- Definir smoke tests e variáveis de ambiente.