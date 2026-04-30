#!/usr/bin/env python3
"""FASE 4.29 — Create Next Controlled Cycle Template.

Prepare template for next cycle if handoff permits.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def load_json_safe(file_path: Path) -> Dict[str, Any]:
    """Load JSON file safely."""
    if not file_path.exists():
        return {}
    try:
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def main() -> int:
    """Run FASE 4.29."""
    parser = argparse.ArgumentParser(description="FASE 4.29 — Create Next Cycle Template")
    parser.add_argument("--previous-cycle", required=True)
    parser.add_argument("--next-cycle", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--handoff-decision", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)

    args = parser.parse_args()

    # Load handoff decision
    handoff = load_json_safe(args.handoff_decision)
    decision = handoff.get("decision", "")

    # Check if creation is allowed
    if decision == "CYCLE_ACTION_REQUIRED":
        print(f"✗ Cannot create {args.next_cycle}: action required on {args.previous_cycle}")
        return 1

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Create scope
    scope = {
        "cycle_id": args.next_cycle,
        "device": args.device,
        "device_id": args.device_id,
        "status": "PLANNED_NOT_STARTED",
        "created_at": datetime.utcnow().isoformat() + "+00:00",
        "max_items": 3,
        "allowed_methods": ["POST"],
        "forbidden_methods": ["PATCH", "DELETE"],
        "forbidden_targets": ["/sync", "equipment", "ssh", "netconf"],
        "requires_week1": True,
        "requires_week2": True,
        "requires_approval_records": True,
        "requires_applyplan_dryrun": True,
        "requires_real_write_authorization": True,
        "requires_post_write_verification": True,
    }

    # Write scope
    scope_file = args.output_dir / f"{args.next_cycle}-scope.json"
    with open(scope_file, "w", encoding="utf-8") as f:
        json.dump(scope, f, indent=2)

    # Create plan
    plan_file = args.output_dir / f"{args.next_cycle}-PLAN.md"
    plan = f"""# {args.next_cycle} — Plano de Ciclo

## 1. Status
PLANNED_NOT_STARTED

## 2. Escopo
- Device: {args.device}
- Device ID: {args.device_id}
- Max Items: 3
- Methods: POST only
- Forbidden: PATCH, DELETE, /sync

## 3. Próximas Etapas
1. Week 1 Preparation
2. Week 2 Preparation
3. Approval Records
4. Dry-Run ApplyPlan
5. Real Write Authorization
6. Post-Write Verification

---
Plano criado em {scope['created_at']}
"""
    plan_file.write_text(plan, encoding="utf-8")

    # Create status
    status_file = args.output_dir / f"{args.next_cycle}-STATUS.md"
    status = f"""# {args.next_cycle} — Status do Ciclo

## Status Atual
PLANNED_NOT_STARTED

## Histórico
- Criado: {scope['created_at']}
- Previous Cycle: {args.previous_cycle}
- Handoff: {decision}

---
"""
    status_file.write_text(status, encoding="utf-8")

    # Create checklist
    checklist_file = args.output_dir / f"{args.next_cycle}-CHECKLIST.md"
    checklist = f"""# {args.next_cycle} — Checklist de Execução

## Pré-requisitos
- [ ] Ciclo anterior ({args.previous_cycle}) arquivado
- [ ] Handoff aprovado ({decision})
- [ ] Device confirmado ({args.device})

## Fase 1: Intake
- [ ] Responses coletadas
- [ ] Validação completada

## Fase 2: Approval
- [ ] Approval records criados
- [ ] ApplyPlan dry-run gerado

## Fase 3: Execution
- [ ] Autorização concedida
- [ ] Escrita real executada
- [ ] Verificação completa

## Fase 4: Closure
- [ ] Compliance validado
- [ ] Cycle fechado

---
"""
    checklist_file.write_text(checklist, encoding="utf-8")

    print(f"✓ Template created: {args.next_cycle}")
    print(f"✓ Scope: {scope_file}")
    print(f"✓ Plan: {plan_file}")
    print(f"✓ Status: {status_file}")
    print(f"✓ Checklist: {checklist_file}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
