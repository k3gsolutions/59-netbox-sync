# Workflow — Compliance Report

## Objetivo
Gerar relatório de compliance cruzando NetBox, Zabbix e `netops_netbox_sync`.

## Trigger
- Scheduler (semanal/mensal).
- Execução manual sob demanda.

## Input esperado
- Dados NetBox (SoT).
- Resultados `netops_netbox_sync` (auditoria).
- Inventário Zabbix.

## Output esperado
- Relatório consolidado (Markdown/PDF) com status de compliance.
- Registro em audit log.
- Envio para stakeholders (sem segredos).

## Nodes principais
1. Coletar dados (read-only).
2. Agregar e classificar divergências.
3. Gerar relatório (dry-run → output preview).
4. Notificar (e-mail/Git issue).

## Critérios de aceite
- Sem escrita direta em equipamentos.
- Relatório versionável.
- Audit log completo.

## Smoke test
- Dados fake com alguns warnings.

## Riscos
- Dados desatualizados.
- Volume de divergências alto.

## Anti-padrões
- Corrigir automaticamente.
- Falta de rastreabilidade.
