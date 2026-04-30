# FASE 4.31 — Cycle Start Gate

## Objetivo
Liberar o início do próximo ciclo somente se o handoff anterior não exigir ação obrigatória e o template estiver íntegro.

## Comando
```bash
python3 tools/local/controlled_cycle_start_gate.py \
  --cycle-id cycle-002 \
  --previous-cycle cycle-001 \
  --cycle-dir reports/controlled-operation/cycle-002 \
  --previous-handoff reports/controlled-operation/cycle-001/cycle-001-handoff-decision.json \
  --operation-index reports/controlled-operation/controlled-operation-index.json \
  --output reports/controlled-operation/cycle-002/CYCLE-002-START-GATE.md \
  --output-json reports/controlled-operation/cycle-002/cycle-002-start-gate.json
```

## Decisões
- `CYCLE_START_READY`
- `CYCLE_START_READY_WITH_RESTRICTIONS`
- `CYCLE_START_BLOCKED`

## Segurança
- Só leitura de artefatos locais.
- Sem POST, PATCH, DELETE, /sync, apply ou rollback automático.
