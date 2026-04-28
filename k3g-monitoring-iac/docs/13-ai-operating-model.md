# 13 — AI Operating Model

## 1. Propósito
Estabelecer como Codex, Claude e demais agentes de IA devem operar no projeto **k3g-monitoring-iac**, garantindo consistência, economia de tokens e rastreabilidade entre sessões.

## 2. Ordem recomendada de leitura
1. `PROJECT_CONTEXT.md`
2. `context/CURRENT_STATE.md`
3. `context/NEXT_ACTIONS.md`
4. `docs/13-ai-operating-model.md` (este documento)
5. Arquivos específicos da tarefa
6. `context/MEMORY_INDEX.md` para localizar material adicional

Evite ler diretórios inteiros sem necessidade. Consulte o índice ou resumos antes de abrir arquivos extensos.

## 3. Uso de prompts reutilizáveis
- `prompts/code-review.md` — revisões de código/automação.
- `prompts/architecture-review.md` — avaliação arquitetural e aderência a ADRs.
- `prompts/n8n-workflow-builder.md` — planejamento/validação de workflows N8N.
- `prompts/docs-updater.md` — atualização de documentação e contexto.
- `prompts/phase-summary.md` — fechamento ou status da fase.
- `prompts/zabbix-template-review.md`, `grafana-dashboard-review.md`, `netbox-data-model-review.md`, `test-generator.md` — revisões especializadas.

Sempre registre no relatório qual prompt guiou a atividade, quando aplicável.

## 4. Uso de skills locais
Antes de executar ações operacionais, leia a skill correspondente em `skills/`:
- Code review (`code-review.skill.md`)
- Documentação (`documentation-maintenance.skill.md`)
- Workflows N8N (`n8n-workflow.skill.md`)
- Templates Zabbix (`zabbix-template.skill.md`)
- Dashboards Grafana (`grafana-dashboard.skill.md`)
- Modelagem NetBox (`netbox-modeling.skill.md`)
- Relatórios de compliance (`compliance-report.skill.md`)

Cada skill traz objetivo, checklist, anti-padrões e critérios de saída.

## 5. Uso de ferramentas locais (`tools/local/`)
Ferramentas devem ser executadas conforme solicitado nas tarefas. Estado atual:
- `summarize_repo.py` — Stub. Objetivo: resumir estrutura e atualizar `context/MEMORY_INDEX.md`.
- `update_context_index.py` — Stub. Objetivo: recalcular índice de memória.
- `check_docs_links.py` — Stub. Objetivo: validar links internos.
- `generate_phase_report.py` — Stub. Objetivo: gerar resumo da fase.
- `lint_markdown.py` — Planejado para lint leve (ainda não executado).

Ao executar ferramentas stub, espere `NotImplementedError` e registre o resultado no relatório da tarefa.

## 6. Criação de novos artefatos
- **Prompts/skills**: crie quando surgir necessidade recorrente não coberta. Documente objetivo, uso e anti-padrões. Atualize `CHANGELOG.md` e `context/MEMORY_INDEX.md`.
- **Ferramentas**: crie scripts em `tools/local/` para tarefas repetitivas. Inclua docstrings com objetivo, entradas, saídas, uso esperado e status (stub/ativo).
- **ADRs**: toda decisão arquitetural relevante deve gerar/atualizar ADR em `docs/adr/` e ser listada em `DECISIONS.md`.

## 7. Economia de tokens e leitura incremental
- Priorize arquivos de contexto e índices antes de abrir documentação extensa.
- Use `context/MEMORY_INDEX.md` para localizar rapidamente o arquivo correto.
- Mantenha documentação concisa para reduzir necessidade de re-leitura.

## 8. Atualização de contexto ao final das tarefas
Sempre avaliar se é necessário atualizar:
- `context/CURRENT_STATE.md`
- `context/NEXT_ACTIONS.md`
- `context/MEMORY_INDEX.md`
- `CHANGELOG.md`
- `PHASE0_BASELINE.md`

Registre ferramentas executadas (mesmo se falharem por stub) e decisões tomadas.

## 9. Restrições operacionais
- **Não** chamar APIs reais (NetBox, Zabbix, Grafana, dispositivos) sem autorização explícita.
- **Não** implementar automação de produção nesta fase.
- **Não** alterar o repositório `netops_netbox_sync` sem pedido direto.
- **Não** criar serviços concorrentes ao N8N.
- **Sempre** manter separação entre documentação, GitOps, workflows e templates.

## 10. Encerramento de tarefas
Ao finalizar uma tarefa:
1. Atualize arquivos de contexto aplicáveis.
2. Documente mudanças no `CHANGELOG.md`.
3. Informe ferramentas executadas e resultados (incluindo falhas esperadas em stubs).
4. Registre próximos passos recomendados.
5. Confirme que as restrições foram respeitadas.

Este modelo operacional garante continuidade do projeto ao alternar entre diferentes IAs e sessões de trabalho.
Mantê-lo atualizado faz parte da FASE 0.
