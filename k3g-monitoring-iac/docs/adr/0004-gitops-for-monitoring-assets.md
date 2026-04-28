# ADR 0004 — GitOps para ativos de monitoramento

## Status
Aceito — Fase 0

## Contexto
Templates, dashboards, taxonomias e workflows precisam de versionamento, revisão e rastreabilidade.

## Decisão
Versionar todos os artefatos de monitoramento (Zabbix, Grafana, N8N, runbooks) no Git, seguindo práticas GitOps.

## Consequências
- Alterações passam por PR/code review.
- Deploys devem ser idempotentes, com dry-run e rollback documentado.
- Git serve como fonte declarativa para provisioning.

## Referências
- `docs/07-zabbix-templates-strategy.md`
- `docs/08-grafana-strategy.md`
- `docs/09-n8n-workflows-strategy.md`