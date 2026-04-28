# 00 — Projeto ISP Observability Automation Framework

## Objetivo
Criar uma plataforma idempotente de observabilidade para ISPs que projeta dados do NetBox em ferramentas de monitoramento, orquestrada pelo N8N e governada via GitOps.

## Pilares principais
- NetBox como única fonte técnica.
- N8N como orquestrador de automações.
- Zabbix e Grafana como projeções configuradas via Git.
- Stack operada com princípios de auditoria, dry-run e DLQ.

## Estrutura de documentação
- `01-architecture.md`: visão macro e integrações.
- `02-phase0-baseline.md`: foco da fase atual.
- `03-... / 04-...`: taxonomias e convenções.
- `adr/`: decisões arquiteturais.