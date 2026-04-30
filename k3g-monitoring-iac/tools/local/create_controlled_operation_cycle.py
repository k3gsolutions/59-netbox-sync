#!/usr/bin/env python3
"""FASE 4.1 — Create Controlled Operation Cycle.

Generate cycle template directory with PLAN.md, SCOPE.json, CHECKLIST.md, STATUS.md.
No execution, purely template generation for upcoming cycle.
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
    """Run FASE 4.1."""
    parser = argparse.ArgumentParser(
        description="FASE 4.1 — Create Controlled Operation Cycle"
    )
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)

    args = parser.parse_args()

    baseline = load_json_safe(args.baseline)
    timestamp = datetime.utcnow().isoformat() + "+00:00"

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # CYCLE PLAN
    plan = f"""# {args.cycle_id.upper()} — Ciclo Operacional Controlado

## 1. Objetivo

Executar novo ciclo controlado usando o fluxo governado de escrita real.

## 2. Device

- **Device:** {args.device}
- **Device ID:** {args.device_id}
- **Status:** PLANNED_NOT_STARTED

## 3. Escopo

- **Máximo de objetos:** 3
- **Métodos:** POST only
- **Forbidden:** PATCH, DELETE, /sync, bulk write

## 4. Gates Obrigatórios

Sequência SEMPRE a seguir:

1. [ ] Week 1 Response — Coleta de dados
2. [ ] Week 2 Review — Revisão humana
3. [ ] ApprovalRecord — Registros de aprovação
4. [ ] ApplyPlan Dry-Run — Validação sem execução
5. [ ] Dry-Run Simulation — Simulação do resultado
6. [ ] Real Write Authorization — Authorization package
7. [ ] Final Preflight — Preflight gate com phrase
8. [ ] Execution Package — Pacote de execução
9. [ ] Execute Real Write Once — One-shot execution
10. [ ] Post-Write Verification — GET verification
11. [ ] Compliance Re-Run — Compliance validation
12. [ ] Closure — Consolidação de resultados
13. [ ] Archive — Arquivamento final

## 5. Restrições

- ✓ Nenhum token em logs/saves
- ✓ One-shot execution (sem retry)
- ✓ Sem rollback automático
- ✓ One device por ciclo
- ✓ Máximo 3 objetos
- ✓ POST only
- ✓ Stop on first failure

## 6. Métricas de Sucesso

- Escrita one-shot executada
- Post-write verification passed
- Compliance validation passed
- Closure success
- Audit trail completo

## 7. Próximas Ações

1. Selecionar objetos para ciclo
2. Executar Week 1 response
3. Executar Week 2 review
4. Prosseguir sequencialmente

---

**Cycle ID:** {args.cycle_id}
**Device:** {args.device}
**Created:** {timestamp}
**Status:** PLANNED_NOT_STARTED
"""

    # SCOPE JSON
    scope = {
        "cycle_id": args.cycle_id,
        "device": args.device,
        "device_id": args.device_id,
        "status": "planned",
        "created_at": timestamp,
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
        "requires_compliance_rerun": True,
        "requires_closure": True,
        "requires_archive": True,
        "one_shot_only": True,
        "no_automatic_retry": True,
        "no_automatic_rollback": True,
        "safety_confirmations": {
            "no_token_exposure": True,
            "read_only_until_execution": True,
            "manual_review_gated": True,
        },
    }

    # CHECKLIST
    checklist = f"""# {args.cycle_id.upper()} — Checklist Operacional

## Pré-Ciclo

- [ ] Baseline de operação controlada confirmado
- [ ] Device {args.device} operacional
- [ ] Fluxo governado compreendido
- [ ] Gates obrigatórios identificados
- [ ] Token NETBOX_WRITE_TOKEN preparado (não hardcoded)

## Durante o Ciclo

### Week 1 Response
- [ ] Objetos identificados
- [ ] Dados coletados
- [ ] Validação inicial passed

### Week 2 Review
- [ ] Respostas revisadas
- [ ] Aprovações solicitadas
- [ ] ApprovalRecords criados

### Approvals
- [ ] Todos os ApprovalRecords proposed
- [ ] Revisores atribuídos
- [ ] Evidência documentada

### ApplyPlan
- [ ] ApplyPlan gerado (dry-run=true)
- [ ] Validação de preflight passed
- [ ] Simulação completada

### Real Write Authorization
- [ ] Authorization package gerado
- [ ] Phrase gerada e documentada
- [ ] Operador confirmado

### Execution
- [ ] Preflight gate passed
- [ ] Execution package validado
- [ ] Operador confirmou execução
- [ ] One-shot execution executado
- [ ] Sem retry
- [ ] Sem rollback

### Post-Write
- [ ] Post-write verification passed
- [ ] Compliance re-run passed
- [ ] Closure gerado
- [ ] Archive gerado

## Pós-Ciclo

- [ ] Resultados revisados
- [ ] Artefatos arquivados
- [ ] Lições aprendidas documentadas
- [ ] Próximo ciclo planejado

---

**Checklist para:** {args.cycle_id}
**Device:** {args.device}
"""

    # STATUS JSON
    status = {
        "cycle_id": args.cycle_id,
        "device": args.device,
        "device_id": args.device_id,
        "status": "PLANNED_NOT_STARTED",
        "created_at": timestamp,
        "phase": "planning",
        "gates": {
            "week1_response": None,
            "week2_review": None,
            "approval_record": None,
            "applyplan_dryrun": None,
            "real_write_authorization": None,
            "execute_real_write_once": None,
            "post_write_verification": None,
            "compliance_rerun": None,
            "closure": None,
            "archive": None,
        },
        "events": [
            {
                "timestamp": timestamp,
                "event": "CYCLE_CREATED",
                "status": "PLANNED_NOT_STARTED",
            }
        ],
    }

    # Write files
    plan_file = args.output_dir / f"{args.cycle_id.upper()}-PLAN.md"
    plan_file.write_text(plan, encoding="utf-8")

    scope_file = args.output_dir / f"{args.cycle_id.upper()}-SCOPE.json"
    with open(scope_file, "w", encoding="utf-8") as f:
        json.dump(scope, f, indent=2)

    checklist_file = args.output_dir / f"{args.cycle_id.upper()}-CHECKLIST.md"
    checklist_file.write_text(checklist, encoding="utf-8")

    status_file = args.output_dir / f"{args.cycle_id.upper()}-STATUS.json"
    with open(status_file, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2)

    print(f"✓ Cycle {args.cycle_id} created")
    print(f"✓ Plan: {plan_file}")
    print(f"✓ Scope: {scope_file}")
    print(f"✓ Checklist: {checklist_file}")
    print(f"✓ Status: {status_file}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
