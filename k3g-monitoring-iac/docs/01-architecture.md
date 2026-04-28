# 01 — Arquitetura

## Visão macro
```
NetBox (SoT) → Webhooks → N8N → Zabbix / Grafana / PostgreSQL / Redis
                               ↑
                               └── GitOps (templates, workflows, runbooks)

netops_netbox_sync (auditoria) → NetBox / dispositivos
```

## Componentes
- **NetBox**: dados técnicos, custom fields, naming, tags.
- **N8N**: orquestra onboarding, atualização, reconciliação, reports.
- **Zabbix**: hosts, templates, macros e tags derivados do NetBox.
- **Grafana**: dashboards e folders provisionados via GitOps.
- **PostgreSQL/Redis**: suporte à automação (audit, DLQ, queue).
- **Git**: repositório declarativo do baseline e artefatos.
- **netops_netbox_sync**: auditoria de compliance read-only.

## Princípios arquiteturais
- Idempotência, dry-run e audit log em toda automação.
- Documentação curta e atualizada.
- Sem escrita direta em equipamento nas fases iniciais.
- ADRs para mudanças relevantes.

## Integrações planejadas
- Webhooks do NetBox alimentando workflows N8N.
- N8N provisioning declarativo em Zabbix e Grafana.
- Exportações automatizadas de inventário.
- Relatórios de drift e compliance usando `netops_netbox_sync`.
