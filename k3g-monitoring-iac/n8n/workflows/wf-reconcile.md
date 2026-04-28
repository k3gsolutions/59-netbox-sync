# Workflow — Reconcile

## Objetivo
Comparar estado desejado (NetBox/Git) com estado aplicado (Zabbix/Grafana) e gerar ações corretivas.

## Trigger
- Scheduler diário/semanal.
- Execução manual (dry-run).

## Input esperado
- Snapshot NetBox.
- Exportações Zabbix/Grafana.
- Dados do `netops_netbox_sync` (quando aplicável).

## Output esperado
- Relatório de divergências.
- Registro em DLQ/Audit se falhas.
- Ações sugeridas (sem aplicar automaticamente nesta fase).

## Nodes principais
1. Coletar dados (read-only).
2. Normalizar e comparar.
3. Classificar divergências.
4. Gerar relatório (Markdown/JSON).
5. Notificar stakeholders.

## Critérios de aceite
- Read-only.
- Relatório legível.
- Sem alterações diretas.

## Smoke test
- Dados simulados com divergências simples.

## Riscos
- Dados inconsistentes.
- Alto volume de divergências.

## Anti-padrões
- Corrigir automaticamente sem validação.
- Ignorar divergências críticas.
