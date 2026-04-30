#!/usr/bin/env python3
"""FASE 4.66 — Prepare Cycle-003 template."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def create_cycle_template(
    *,
    previous_cycle: str,
    next_cycle: str,
    device: str,
    device_id: str,
    handoff_decision: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Create next cycle template based on handoff."""
    output_dir.mkdir(parents=True, exist_ok=True)

    handoff = {}
    if handoff_decision.exists():
        try:
            handoff = json.loads(handoff_decision.read_text(encoding="utf-8"))
        except Exception:
            pass

    handoff_decision_status = handoff.get("decision", "UNKNOWN")

    if "ACTION_REQUIRED" in handoff_decision_status:
        # Cycle blocked
        return {
            "cycle_id": next_cycle,
            "status": "BLOCKED_ACTION_REQUIRED",
            "reason": f"Previous cycle {previous_cycle} requires action",
        }

    # Create Cycle-003 scope
    scope = {
        "cycle_id": next_cycle,
        "device": device,
        "device_id": device_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "PLANNED_NOT_STARTED",
        "previous_cycle": previous_cycle,
        "restrictions": "WITH_RESTRICTIONS" in handoff_decision_status,
        "max_devices": 1,
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
        "requires_expansion_check": False,
    }

    # Write scope
    scope_file = output_dir / f"{next_cycle.upper()}-SCOPE.json"
    scope_file.write_text(json.dumps(scope, indent=2, ensure_ascii=False), encoding="utf-8")

    # Write plan
    plan_file = output_dir / f"{next_cycle.upper()}-PLAN.md"
    plan_text = f"""# Plano — {next_cycle.upper()}

## Dispositivo
- **Nome**: {device}
- **ID**: {device_id}

## Ciclo Anterior
- **Ciclo**: {previous_cycle}
- **Decisão**: {handoff_decision_status}

## Escopo
- Max Devices: 1
- Max Items: 3
- Métodos: POST apenas
- Targets bloqueados: /sync, equipment, ssh, netconf

## Fases Requeridas
- Week 1: Intake + Validation
- Week 2: Human Review + Approval
- ApplyPlan: Dry-run + Simulation
- Real Write: Authorization + Execution
- Post-Write: Verification + Compliance + Closure

## Restrições
{'Mantidas da decisão anterior (WITH_RESTRICTIONS)' if 'WITH_RESTRICTIONS' in handoff_decision_status else 'Nenhuma restrição adicional'}

---
Criado em {datetime.now(timezone.utc).isoformat()}
"""
    plan_file.write_text(plan_text, encoding="utf-8")

    # Write status template
    status_file = output_dir / f"{next_cycle.upper()}-STATUS.md"
    status_text = f"""# Status — {next_cycle.upper()}

- **Ciclo**: {next_cycle}
- **Dispositivo**: {device}
- **Criado**: {datetime.now(timezone.utc).isoformat()}
- **Status**: PLANNED_NOT_STARTED
- **Restrições**: {'Sim' if 'WITH_RESTRICTIONS' in handoff_decision_status else 'Não'}

## Próximas Etapas
1. Week 1 Intake
2. Week 1 Validation
3. Week 2 Human Review
4. Week 2 Approvals
5. ApplyPlan Dry-Run
6. ApplyPlan Simulation
7. Real Write Authorization
8. Real Write Execution
9. Post-Write Verification
10. Post-Write Compliance
11. Closure

---
"""
    status_file.write_text(status_text, encoding="utf-8")

    # Write checklist
    checklist_file = output_dir / f"{next_cycle.upper()}-CHECKLIST.md"
    checklist_text = f"""# Checklist — {next_cycle.upper()}

## Preparação
- [ ] Dispositivo {device} confirmado
- [ ] Restrições do Cycle-002 documentadas
- [ ] Limites de escala STAY_CURRENT_LEVEL confirmados
- [ ] Equipes notificadas

## Week 1
- [ ] Intake executado
- [ ] Responses coletadas
- [ ] Validation completada
- [ ] Discrepâncias resolvidas

## Week 2
- [ ] Human review completado
- [ ] Approvals coletadas
- [ ] Approval records normalizados
- [ ] Readiness gate passou

## ApplyPlan
- [ ] Dry-run gerado
- [ ] Dry-run validado
- [ ] Simulation executada
- [ ] Resultado OK

## Real Write
- [ ] Authorization solicitada
- [ ] Preflight passou
- [ ] Write executado uma vez
- [ ] Nenhum retry/rollback

## Post-Write
- [ ] Verification completada
- [ ] Compliance verificada
- [ ] Closure gerada
- [ ] Archive completado

## Handoff
- [ ] Decisão handoff emitida
- [ ] Restrictions documentadas
- [ ] Next cycle preparado

---
Criado em {datetime.now(timezone.utc).isoformat()}
"""
    checklist_file.write_text(checklist_text, encoding="utf-8")

    return {
        "cycle_id": next_cycle,
        "status": "TEMPLATE_CREATED",
        "files": {
            "scope": str(scope_file),
            "plan": str(plan_file),
            "status": str(status_file),
            "checklist": str(checklist_file),
        },
    }


def main() -> int:
    """Run FASE 4.66."""
    parser = argparse.ArgumentParser(description="FASE 4.66 — Cycle-003 Template")
    parser.add_argument("--previous-cycle", required=True)
    parser.add_argument("--next-cycle", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--handoff-decision", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)

    args = parser.parse_args()
    result = create_cycle_template(
        previous_cycle=args.previous_cycle,
        next_cycle=args.next_cycle,
        device=args.device,
        device_id=args.device_id,
        handoff_decision=args.handoff_decision,
        output_dir=args.output_dir,
    )

    print(f"✓ Cycle template: {result.get('status')}")
    print(f"✓ Files created: {len(result.get('files', {}))}")
    for key, path in result.get("files", {}).items():
        print(f"  - {key}: {path}")

    return 0 if "BLOCKED" not in result.get("status") else 1


if __name__ == "__main__":
    raise SystemExit(main())
