# Grafana — Provisionamento e Dashboards

## Objetivo
Controlar dashboards, folders e datasources via GitOps, mantendo multi-tenancy e governança.

## Estrutura
- `dashboards/` — subpastas segmentadas (customer, carrier, infra, noc, platform).
- `folders/` — permissões declaradas (`permissions.yaml`).
- `provisioning/` — arquivos de provisioning (dashboards/datasources).

## Próximos passos
- Definir datasources e variáveis padrão.
- Criar templates iniciais para dashboards genéricas.
- Documentar processo de import/export GitOps.
