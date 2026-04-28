# Scripts — Automação Local

## Objetivo
Scripts auxiliares para exportação, lint e reconciliação em modo dry-run.

## Scripts planejados
- `lint_descriptions.py` — validar descrições conforme naming.
- `backfill_netbox.py` — auxiliar brownfield (dry-run).
- `export_zabbix_inventory.py` — export read-only.
- `export_grafana_inventory.py` — export read-only.
- `reconcile_dryrun.py` — comparar declarativo vs aplicado.

> Implementar gradualmente com testes em `tests/`.
