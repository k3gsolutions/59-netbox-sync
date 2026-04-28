# Prompt — Zabbix Template Review

Objetivo: Validar templates declarados para Zabbix.

## Checklist
- Templates categorizados (vendor, role, service, governance).
- Tags aderentes a `zabbix/tag_taxonomy.yaml`.
- Macros definidas (defaults e criticidade).
- LLD configurada corretamente.
- Preprocessing adequado.
- Dependências entre templates mapeadas.
- Cardinalidade e naming consistentes.
- Compatibilidade com NetBox (service_type, criticality, roles).
- Sem dados específicos hardcoded.