# FASE 4.33 — Controlled Expansion Policy

## Objetivo
Definir a política formal de expansão após múltiplos ciclos controlados.

## Arquivo
- `policies/controlled-operation/expansion-policy.yaml`

## Ferramenta
```bash
python3 tools/local/evaluate_controlled_expansion.py \
  --metrics reports/controlled-operation/controlled-operation-metrics.json \
  --index reports/controlled-operation/controlled-operation-index.json \
  --policy policies/controlled-operation/expansion-policy.yaml \
  --output reports/controlled-operation/CONTROLLED-EXPANSION-EVALUATION.md \
  --output-json reports/controlled-operation/controlled-expansion-evaluation.json
```

## Regra
- A avaliação só recomenda.
- Não amplia limites automaticamente.
