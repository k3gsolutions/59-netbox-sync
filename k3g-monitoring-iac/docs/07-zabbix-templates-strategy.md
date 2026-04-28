# 07 — Estratégia de Templates Zabbix

## Objetivo
Garantir que templates reflitam o modelo declarativo do NetBox e sejam versionados em Git.

## Diretrizes iniciais
- Templates base por vendor, role, service e governance.
- Tags consistentes com `zabbix/tag_taxonomy.yaml`.
- Macros padronizadas conforme criticidade.
- LLD e preprocessing documentados.

## Próximos passos
- Consolidar `zabbix/role_template_map.yaml`.
- Definir processos de export/import declarativo.
- Garantir idempotência e dry-run antes de aplicar.