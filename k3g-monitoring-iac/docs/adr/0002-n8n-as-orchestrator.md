# ADR 0002 — N8N como orquestrador principal

## Status
Aceito — Fase 0

## Contexto
Necessidade de orquestrar automações e integrações entre NetBox, Zabbix, Grafana, PostgreSQL e Redis.

## Decisão
Utilizar N8N como orquestrador principal de workflows, com controles de dry-run, audit log e DLQ.

## Consequências
- Não criar microserviço alternativo (ex.: FastAPI) para o mesmo fim.
- Workflows documentados antes da implementação.
- Centralização de credenciais e execuções no N8N.

## Referências
- `docs/09-n8n-workflows-strategy.md`
- `n8n/workflows/`