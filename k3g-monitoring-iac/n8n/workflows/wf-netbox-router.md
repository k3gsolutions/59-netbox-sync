# Workflow — NetBox Router Event

## Objetivo
Processar webhook do NetBox referente a dispositivos (routers) e refletir mudanças no Zabbix/Grafana.

## Trigger
- Webhook NetBox: evento de `device` com `monitoring_enabled=true`.

## Input esperado
- Payload JSON do NetBox com dados relevantes (device, tenant, tags, interfaces).

## Output esperado
- Atualização declarativa em Zabbix (host, templates, tags).
- Registro de audit log.
- Atualização de dashboards/artefatos GitOps quando aplicável.

## Nodes principais (planejado)
1. Validate payload.
2. Fetch device context from NetBox (read-only).
3. Resolve templates/tags (via Git).
4. Prepare dry-run result.
5. Conditional apply (dry-run vs apply).
6. Audit log + send to DLQ on failure.

## Critérios de aceite
- Idempotência.
- Dry-run suportado.
- Audit log registrado.
- Sem escrita direta em equipamento.
- Tratamento de erro direciona para `wf-error-handler`.

## Smoke test
- Simular webhook com device habilitado.
- Validar geração de payload dry-run.

## Riscos
- Dados incompletos no NetBox.
- Templates desalinhados.

## Anti-padrões
- Aplicar mudanças sem dry-run.
- Ignorar tags obrigatórias.
