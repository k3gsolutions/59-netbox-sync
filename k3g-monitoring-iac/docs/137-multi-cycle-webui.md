# FASE 4.32 — Multi-Cycle Web UI

## Objetivo
Expor visão somente leitura da operação controlada e dos ciclos.

## Rotas
- `/controlled-operation`
- `/controlled-operation/cycles`
- `/controlled-operation/{cycle_id}`
- `/controlled-operation/{cycle_id}/start-gate`
- `/controlled-operation/{cycle_id}/archive`
- `/controlled-operation/{cycle_id}/handoff`

## Regras
- Somente GET.
- Nenhuma escrita NetBox.
- Nenhum botão de apply, sync ou retry automático.
- `cycle_id` limitado a `cycle-\d+`.
