# 12 — Observability of Observability

## Objetivo
Monitorar saúde da própria stack de observabilidade (N8N, NetBox, DLQ, pipelines).

## Diretrizes
- KPIs: latência de eventos, backlog de DLQ, falhas de provisioning, disponibilidade da stack.
- Alertas direcionados aos times responsáveis.
- Dashboards agregadas em Grafana (folder `platform`).

## Próximos passos
- Identificar métricas e logs relevantes.
- Definir workflows N8N de auto-monitoramento na Fase 7.