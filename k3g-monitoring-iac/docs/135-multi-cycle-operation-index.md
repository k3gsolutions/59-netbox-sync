# FASE 4.30 — Multi-Cycle Operation Index

## Objetivo
Criar um índice global dos ciclos controlados com status, handoff, artefatos e próximo passo.

## Comando
```bash
python3 tools/local/build_controlled_operation_index.py \
  --root reports/controlled-operation \
  --output reports/controlled-operation/CONTROLLED-OPERATION-INDEX.md \
  --output-json reports/controlled-operation/controlled-operation-index.json
```

## Saída
- `reports/controlled-operation/CONTROLLED-OPERATION-INDEX.md`
- `reports/controlled-operation/controlled-operation-index.json`

## Leitura
- `cycle-001` aparece como encerrado com restrições.
- `cycle-002` aparece como planejado.
- Nenhuma escrita NetBox.
