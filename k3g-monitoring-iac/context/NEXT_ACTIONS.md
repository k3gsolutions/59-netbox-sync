# Next Actions — Roadmap

## FASE 1.2 — ImportPlan read-only

- Documentar a estratégia de importação assistida em `docs/21-netbox-staged-import-strategy.md`.
- Definir `ImportPlan` JSON e relatórios Markdown com ações classificadas.
- Validar que objetos fora da naming convention não sejam importados e sejam marcados como `needs_review`.
- Garantir que nenhum write no NetBox ocorra nesta fase.
- Incluir seção de revisão humana obrigatória no relatório.

## FASE 1.3 — NetBox Staged Import com aprovação humana

- Planejar fluxo de criação staged apenas para objetos conformes.
- Definir tokens separados de escrita e read-only.
- Garantir que atualizações existentes exijam revisão humana.
- Assegurar que deleções nunca sejam automáticas.
- Exigir dry-run e auditoria antes de aplicar alterações.
- Validar base/service interface classification para `safe_create_staged` e `needs_review`.
- Preparar FASE 1.4 — Approval Workflow Design.

## FASE 1.4 — UI/CLI de aprovação

- Definir interface de revisão de `ImportPlan` com evidências e recomendações.
- Permitir aprovar/rejeitar propostas e baixar relatórios Markdown e JSON sanitizado.
- Registrar auditoria de aprovação e rejeição.
- Destacar naming inválido e razões de bloqueio.
- Confirmar que `safe_create_staged` só é possível para objetos conformes e aprovados.

## Checklist before FASE 1.4

- [ ] Documentar estratégia NetBox Staged Import
- [ ] Definir classificação `safe_create_staged` / `needs_review` / `blocked` / `ignore`
- [ ] Incluir regras de naming convention em relatórios
- [ ] Confirmar que nenhum write no NetBox será feito
- [ ] Documentar token de escrita separado e dry-run obrigatório
- [ ] Planejar tags e custom fields sugeridos para importação
