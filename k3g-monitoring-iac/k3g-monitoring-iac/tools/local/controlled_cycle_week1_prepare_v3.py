#!/usr/bin/env python3
"""FASE 4.72 — Cycle-003 Week 1 Preparation."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def prepare_week1(
    *,
    cycle_id: str,
    device: str,
    device_id: str,
    cycle_dir: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Prepare Week 1 structure."""
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "responses").mkdir(exist_ok=True)
    (output_dir / "audit").mkdir(exist_ok=True)

    # Create plan
    plan_file = output_dir / f"{cycle_id.upper()}-WEEK1-PLAN.md"
    plan_text = f"""# Week 1 Plan — {cycle_id.upper()}

## Objetivo
Coletar respostas de teams para Cycle-003.

## Teams e Responsáveis
- Network Operations: interfaces, vlans, routing
- BGP Team: BGP configuration, AS paths
- Service Team: service endpoints, monitoring

## Coleta
- **Prazo**: Subnormal (para esta demonstração)
- **Formato**: CSV ou JSON
- **Local**: {output_dir}/responses/

## Validação
Após coleta:
1. Verificar presença de arquivo
2. Validar contra compliance registry
3. Identificar discrepâncias

## Próximo Passo
Week 1 Validation

---
Criado em {datetime.now(timezone.utc).isoformat()}
"""
    plan_file.write_text(plan_text, encoding="utf-8")

    # Create status template
    status_file = output_dir / f"{cycle_id.upper()}-WEEK1-STATUS.md"
    status_text = f"""# Week 1 Status — {cycle_id.upper()}

- **Ciclo**: {cycle_id}
- **Dispositivo**: {device}
- **Período**: Week 1
- **Status**: PREPARADO
- **Data**: {datetime.now(timezone.utc).isoformat()}

## Respostas
Aguardando coleta em: {output_dir}/responses/

## Próximos Passos
1. Coletar respostas
2. Validar
3. Avançar para Week 2

---
"""
    status_file.write_text(status_text, encoding="utf-8")

    result = {
        "preparation_id": f"week1-prep-{cycle_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "cycle_id": cycle_id,
        "prepared_at": datetime.now(timezone.utc).isoformat(),
        "status": "WEEK1_READY_FOR_RESPONSES",
        "files_created": {
            "plan": str(plan_file),
            "status": str(status_file),
            "responses_dir": str(output_dir / "responses"),
            "audit_dir": str(output_dir / "audit"),
        },
    }

    output_dir.parent / f"cycle-003-week1-preparation.json"
    return result


def main() -> int:
    """Run FASE 4.72."""
    parser = argparse.ArgumentParser(description="FASE 4.72 — Week 1 Preparation")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--cycle-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)

    args = parser.parse_args()
    result = prepare_week1(
        cycle_id=args.cycle_id,
        device=args.device,
        device_id=args.device_id,
        cycle_dir=args.cycle_dir,
        output_dir=args.output_dir,
    )

    print(f"✓ Week 1 prepared: {result.get('status')}")
    print(f"✓ Plan: {result['files_created']['plan']}")
    print(f"✓ Responses dir: {result['files_created']['responses_dir']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
