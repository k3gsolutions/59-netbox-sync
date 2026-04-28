# AGENTS.md

## Regra de leitura
Antes de qualquer tarefa, leia:
1. `PROJECT_CONTEXT.md`
2. `context/CURRENT_STATE.md`
3. `context/NEXT_ACTIONS.md`
4. Arquivo específico da tarefa
5. Consulte `docs/13-ai-operating-model.md` para detalhes de operação da IA quando necessário.

Priorize arquivos de contexto para economizar tokens. Não leia o repositório inteiro sem necessidade.

## Regras de execução
- Não implemente nada fora da fase atual.
- Não altere decisões arquiteturais sem criar ADR.
- Não remova documentação existente sem justificar.
- Não chame APIs reais sem autorização explícita.
- Não implemente automação de produção nesta fase.
- Não altere o codebase `netops_netbox_sync` sem solicitação explícita.
- Não crie serviço FastAPI concorrente ao N8N.
- Mantenha separação entre documentação, GitOps, workflows, templates e ferramentas.

## Ao finalizar uma tarefa
Atualize, quando aplicável:
- `context/CURRENT_STATE.md`
- `context/NEXT_ACTIONS.md`
- `CHANGELOG.md`
- `PHASE0_BASELINE.md`
- ADRs, se houver decisão arquitetural

## Uso de prompts
- Code review: `prompts/code-review.md`
- Arquitetura: `prompts/architecture-review.md`
- Workflow N8N: `prompts/n8n-workflow-builder.md`
- Documentação: `prompts/docs-updater.md`
- Resumo de fase: `prompts/phase-summary.md`
- Zabbix templates: `prompts/zabbix-template-review.md`
- Grafana dashboards: `prompts/grafana-dashboard-review.md`
- NetBox data model: `prompts/netbox-data-model-review.md`
- Geração de testes: `prompts/test-generator.md`

Sempre informe no relatório final qual prompt orientou a atividade, quando aplicável.

## Uso de skills
- Code review operacional: `skills/code-review.skill.md`
- Manutenção de documentação: `skills/documentation-maintenance.skill.md`
- Workflows N8N: `skills/n8n-workflow.skill.md`
- Templates Zabbix: `skills/zabbix-template.skill.md`
- Dashboards Grafana: `skills/grafana-dashboard.skill.md`
- Modelagem NetBox: `skills/netbox-modeling.skill.md`
- Relatórios de compliance: `skills/compliance-report.skill.md`

Antes de executar tarefas relacionadas, leia a skill correspondente para seguir checklist e anti-padrões.

## Uso de ferramentas locais
- Sumário do repositório: `tools/local/summarize_repo.py`
- Atualização do índice de memória: `tools/local/update_context_index.py`
- Verificação de links: `tools/local/check_docs_links.py`
- Relatório da fase: `tools/local/generate_phase_report.py`
- Outros scripts utilitários em `tools/local/`

Execute as ferramentas sempre que a tarefa solicitar. Caso a ferramenta ainda seja stub, registre o resultado (ex.: `NotImplementedError`) e mantenha o status documentado.

## Criação de novos prompts, skills e tools
- Crie novos prompts ou skills quando surgir tarefa recorrente não coberta pelos existentes. Documente objetivo, quando usar, entrada/saída e anti-padrões.
- Crie novas ferramentas locais quando houver processo repetitivo que possa ser automatizado. Inclua docstring com objetivo, entradas, saídas, uso esperado e status.
- Atualize `context/MEMORY_INDEX.md` e `CHANGELOG.md` sempre que novos artefatos forem adicionados.

## Localização
Este guia aplica-se ao repositório em `/Users/keslleykssantos/projects/ativos/59-netbox_sync/k3g-monitoring-iac`. Certifique-se de executar tarefas neste diretório.