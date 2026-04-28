# Workflow — Onboard Circuit

## Objetivo
Provisionar monitoramento de circuitos com base em eventos do NetBox.

## Trigger
- Webhook NetBox (circuit created/updated com monitoring_enabled=true).

## Input esperado
- Dados do circuito, tenant, service_type, endpoints.

## Output esperado
- Entradas Zabbix relacionadas (host/service).
- Atualização de dashboards específicas.
- Audit log.

## Nodes principais
1. Validar payload.
2. Consultar endpoints/infra no NetBox.
3. Resolver templates e tags.
4. Dry-run result.
5. Aplicar (opcional).
6. Audit log e DLQ se falhar.

## Critérios de aceite
- Idempotência.
- Dry-run obrigatório.
- Mapeamento com service_type.

## Smoke test
- Circuit fake com endpoints simulados.

## Riscos
- Dados incompletos de endpoints.
- Template inadequado.

## Anti-padrões
- Provisionar sem endpoints validados.
- Hardcode de configurações.
