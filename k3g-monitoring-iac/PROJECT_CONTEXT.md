# PROJECT_CONTEXT

## Objetivo
Estabelecer a base GitOps, documental e operacional da plataforma **ISP Observability Automation Framework**, garantindo contexto consistente entre sessões de trabalho com VSCode, Codex e Claude.

## Stack principal
- NetBox (SoT técnico)
- N8N (orquestrador)
- Zabbix (monitoramento)
- Grafana (visualização)
- Git/GitOps (versionamento)
- PostgreSQL (audit log, DLQ, drift)
- Redis (fila, retry, cache)
- Ferramenta auxiliar: `netops_netbox_sync`

## Decisões principais
- NetBox permanece única SoT técnica.
- N8N centraliza automações.
- Automação read-only nas fases iniciais.
- Toda automação deve ser idempotente, com dry-run e audit log.
- Documentação curta e focada em arquivos de contexto.

## Frentes
- **Frente A** — `netops_netbox_sync`: auditoria NetBox ⇄ dispositivo.
- **Frente B** — k3g-monitoring-iac: governança de observabilidade, GitOps, workflows.
- **Frente C** — Pilot Device Compliance: validação de readiness e geração de relatórios de divergência.

## Princípios não negociáveis
Ver `docs/02-phase0-baseline.md` e `docs/adr/` para detalhes. Em resumo: NetBox como SoT, N8N como orquestrador, Git versionando tudo, automação dry-run, sem escrita em equipamento nesta fase.

## Estado atual
- Estrutura inicial do repositório criada.
- Documentação base e ADRs disponíveis.
- Prompts, skills e ferramentas locais stubadas.
- Nenhuma automação operacional implementada.

## Próximos passos imediatos
1. Validar estrutura e revisar ROADMAP.
2. Confirmar taxonomias (service_types, criticality, naming).
3. Preparar exportações Zabbix/Grafana (scripts base).
4. Definir staging e estratégia de dry-run.
5. Priorizar próxima sprint de workflows N8N.