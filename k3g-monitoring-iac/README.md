# k3g-monitoring-iac

## Visão geral
O projeto **k3g-monitoring-iac** define a fundação GitOps e documental para uma plataforma de observabilidade automatizada voltada a ISPs. Ele estrutura documentação, taxonomias, prompts, skills, ferramentas locais e o baseline necessário para evoluir operações com NetBox, N8N, Zabbix e Grafana.

## O que este projeto não é
- Não é o orquestrador principal (papel do N8N).
- Não executa automações em produção nesta fase.
- Não substitui o `netops_netbox_sync`.
- Não contém workflows N8N prontos.
- Não aplica configurações diretamente em equipamentos.

## Arquitetura de alto nível
- NetBox como single source of truth técnico.
- N8N como orquestrador de automações.
- Zabbix como executor de monitoramento.
- Grafana como visualização.
- Git como controle declarativo de templates, dashboards, workflows e runbooks.
- PostgreSQL para audit log, DLQ e relatórios de drift.
- Redis para filas, retry e cache.
- Ferramentas auxiliares para manter baseline e contexto atualizado.

## Estado atual
- Estrutura inicial da FASE 0 criada.
- Documentação base organizada em `docs/`.
- Prompts e skills disponíveis em `prompts/` e `skills/`.
- Ferramentas locais stubadas em `tools/local/`.
- ADRs iniciais registradas em `docs/adr/`.
- Nenhuma automação operacional implementada.

## Como navegar
1. Leia `PROJECT_CONTEXT.md` para visão rápida.
2. Consulte `context/` para estado atual, mapa do sistema e próximas ações.
3. Use `docs/` para detalhes arquiteturais, taxonomias e decisões.
4. Utilize `prompts/` e `skills/` para interações com IA e revisões.
5. Verifique `ROADMAP.md` e `PHASE0_BASELINE.md` para acompanhamento.

## Fase atual
FASE 0 — Baseline e organização.

## Próximos passos
- Validar estrutura inicial e documentação.
- Consolidar naming conventions e taxonomias.
- Preparar exportações de inventário.
- Definir staging e estratégia de dry-run.
- Evoluir ferramentas locais conforme necessidade.

## Relação com netops_netbox_sync
O projeto `netops_netbox_sync` é uma ferramenta complementar de auditoria NetBox ⇄ dispositivo.
Ele não substitui o N8N.
- netops_netbox_sync: coleta estado aplicado, gera compliance e suporta brownfield.
- k3g-monitoring-iac: define padrões, workflows, templates, dashboards, taxonomia e governança.

## Localização do repositório
Este repositório está versionado em `/Users/keslleykssantos/projects/ativos/59-netbox_sync/k3g-monitoring-iac` dentro do workspace principal `59-netbox_sync`.