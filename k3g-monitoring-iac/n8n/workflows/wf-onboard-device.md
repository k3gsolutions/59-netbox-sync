# Workflow — Onboard Device

## Objetivo
Onboard de um novo dispositivo a partir de dados do NetBox, provisionando monitoramento.

## Trigger
- Evento manual ou webhook NetBox (device created/updated com monitoring_enabled=true).

## Input esperado
- Dados do dispositivo, tenant, roles, tags.

## Output esperado
- Host criado/atualizado no Zabbix.
- Dashboards provisionadas (se aplicável).
- Registro de audit log.

## Nodes principais
1. Validate data.
2. Dry-run calculation (templates, macros).
3. Apply to Zabbix (condicional).
4. Update GitOps artefacts (PR ou pipeline).
5. Audit log e notificação.

## Critérios de aceite
- Dry-run default.
- Idempotência garantida.
- Registro em audit log.

## Smoke test
- Device fictício com monitoring_enabled=true.
- Verificar dry-run e sem aplicação real.

## Riscos
- Falta de dados NetBox.
- Credenciais Zabbix inválidas.

## Anti-padrões
- Ignorar dry-run.
- Criar host sem tags corretas.
