# Prompt — Grafana Dashboard Review

Objetivo: Avaliar dashboards e provisioning declarativo.

## Checklist
- Uso de dashboards genéricas (sem duplicação por cliente).
- Variáveis alinhadas às tags do Zabbix.
- Pastas e RBAC definidas (vide `grafana/folders`).
- Provisioning via GitOps (`grafana/provisioning/`).
- Estratégia multi-tenant coerente.
- Processo de remoção/atualização controlado.
- Monitoração da própria plataforma incluída.