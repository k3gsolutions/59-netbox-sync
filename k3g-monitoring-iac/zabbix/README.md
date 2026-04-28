# Zabbix — Estratégia de Templates e Provisionamento

## Objetivo
Manter templates, tags, macros e inventário derivados do NetBox e versionados via Git.

## Estrutura
- `role_template_map.yaml` — mapeamento role → templates.
- `tag_taxonomy.yaml` — conjunto de tags permitido.
- `criticality_profiles.yaml` — parâmetros por criticidade.
- `macros_defaults.yaml` — valores padrão (placeholder).
- `templates/` — subpastas para templates por vendor/role/service/governance.

## Próximos passos
- Definir templates base e dependências.
- Criar macros padrão e processos de aplicação.
- Integração com workflows N8N (Fase 6 em diante).
