# 10 — Brownfield Migration

## Contexto
Migrar ambientes existentes para o modelo GitOps exige:
- Captura do estado atual (via `netops_netbox_sync`, exportações Zabbix/Grafana).
- Normalização de dados NetBox.
- Provisionamento progressivo via N8N com dry-run.

## Estratégia
1. Exportar inventários atuais (Zabbix/Grafana).
2. Mapear divergências com NetBox.
3. Definir prioridade por criticidade.
4. Aplicar runbooks de backfill.
5. Validar com workflows em modo read-only antes de aplicar.

## Riscos
- Dados desatualizados.
- Mudanças manuais em produção.
- Falta de versionamento prévio.