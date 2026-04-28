# 08 — Estratégia Grafana

## Objetivo
Provisionar dashboards e folders via GitOps, alinhados a multi-tenancy.

## Diretrizes iniciais
- Dashboards organizadas por contexto (`customer`, `carrier`, `infra`, `noc`, `platform`).
- Provisioning versionado em `grafana/provisioning/`.
- RBAC controlado via folders e permissões declarativas.
- Sem dashboards manuais por cliente.

## Próximos passos
- Definir datasources e strategy multi-tenant.
- Criar templates de dashboards base (placeholder).