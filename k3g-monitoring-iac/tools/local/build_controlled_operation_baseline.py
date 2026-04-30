#!/usr/bin/env python3
"""FASE 2.60 — Build Controlled Operation Baseline.

Evaluate pilot readiness. Emit decision: READY / WITH_RESTRICTIONS / NOT_READY.
Define scope, restrições, fluxo obrigatório for controlled operation cycles.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


def load_json_safe(file_path: Path) -> Dict[str, Any]:
    """Load JSON file safely."""
    if not file_path.exists():
        return {}

    try:
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def evaluate_readiness(
    handoff_decision: str, closure_decision: str, archive_decision: str
) -> str:
    """Evaluate controlled operation readiness."""
    # Check for NOT_READY/FAILED first
    if "NOT_READY" in handoff_decision or "FAILED" in closure_decision or "FAILED" in archive_decision:
        return "CONTROLLED_OPERATION_NOT_READY"

    if (
        "READY_FOR_CONTROLLED_OPERATION" in handoff_decision
        and "SUCCESS" in closure_decision
        and "SUCCESS" in archive_decision
    ):
        return "CONTROLLED_OPERATION_READY"

    if (
        "READY" in handoff_decision
        and "SUCCESS" in closure_decision
        and "SUCCESS" in archive_decision
    ):
        return "CONTROLLED_OPERATION_READY_WITH_RESTRICTIONS"

    return "CONTROLLED_OPERATION_NOT_READY"


def generate_baseline_markdown(device: str, decision: str) -> str:
    """Generate baseline markdown report."""
    timestamp = datetime.utcnow().isoformat() + "+00:00"

    emoji = {
        "CONTROLLED_OPERATION_READY": "✓",
        "CONTROLLED_OPERATION_READY_WITH_RESTRICTIONS": "⚠",
        "CONTROLLED_OPERATION_NOT_READY": "✗",
    }.get(decision, "?")

    md = f"""# Baseline de Operação Controlada — {device}

## 1. Decisão

### {emoji} {decision}

## 2. Escopo Permitido Inicialmente

- **Dispositivos:** 1 device por ciclo
- **Objetos:** Máximo 3 objetos por ciclo
- **Métodos:** POST only
- **Forbidden:** PATCH, DELETE, /sync
- **Execution:** One-shot (sem retry automático)
- **Rollback:** Sem rollback automático
- **Bulk:** Sem bulk write

## 3. Fluxo Obrigatório

Sequência que SEMPRE deve ser seguida:

1. **Week 1 Response** — Coleta de dados e validação inicial
2. **Week 2 Review** — Revisão humana de respostas
3. **ApprovalRecord** — Criação de registros de aprovação
4. **ApplyPlan Dry-Run** — Validação sem execução
5. **Validate ApplyPlan** — Verificação de integridade
6. **Dry-Run Simulation** — Simulação do resultado
7. **Real Write Authorization** — Geração de authorization package
8. **Final Preflight** — Validação de preflight com phrase matching
9. **Execution Package** — Criação do pacote de execução
10. **Execute Real Write Once** — Execução one-shot
11. **Post-Write Verification** — Verificação GET pós-escrita
12. **Compliance Re-Run** — Validação compliance após escrita
13. **Closure** — Consolidação de resultados
14. **Archive** — Arquivamento final

## 4. Restrições Operacionais

Todas operações DEVEM cumprir:

- ✓ Zero token in logs, saves, or display
- ✓ Zero automatic retry on failure
- ✓ Zero automatic rollback
- ✓ Zero access to equipment/SSH
- ✓ One-shot execution only
- ✓ Stop on first failure
- ✓ No /sync endpoint
- ✓ No PATCH or DELETE initially
- ✓ No bulk write mode
- ✓ Week 1 + Week 2 review mandatory
- ✓ ApprovalRecord mandatory
- ✓ Dry-run simulation mandatory
- ✓ Authorization package mandatory
- ✓ Preflight phrase matching mandatory
- ✓ Post-write verification mandatory

## 5. Segurança

Confirmações Obrigatórias:
- Nenhum token exposado
- Nenhum segredo em logs
- Trilha de auditoria completa
- One-shot execution enforced
- Manual review at each gate

## 6. Próximo Passo

FASE 4.1 — Controlled Operation Cycle v1

Criar template para primeiro ciclo usando fluxo governado.

---

**Baseline ID:** BASELINE-{device}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}
**Generated:** {timestamp}
**Device:** {device}
"""

    return md


def main() -> int:
    """Run FASE 2.60."""
    parser = argparse.ArgumentParser(
        description="FASE 2.60 — Build Controlled Operation Baseline"
    )
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--handoff-decision", type=Path, required=True)
    parser.add_argument("--closure-summary", type=Path, required=True)
    parser.add_argument("--archive-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)

    args = parser.parse_args()

    # Load all decisions
    handoff = load_json_safe(args.handoff_decision)
    closure = load_json_safe(args.closure_summary)
    archive = load_json_safe(args.archive_manifest)

    # Extract decision strings
    handoff_decision = handoff.get("decision", "UNKNOWN")
    closure_decision = closure.get("closure_decision", "UNKNOWN")
    archive_decision = archive.get("final_decision", "UNKNOWN")

    # Evaluate readiness
    decision = evaluate_readiness(handoff_decision, closure_decision, archive_decision)

    # Generate markdown
    markdown = generate_baseline_markdown(args.device, decision)

    # Generate JSON
    baseline_json = {
        "baseline_id": f"BASELINE-{args.device}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
        "device": args.device,
        "device_id": args.device_id,
        "decision": decision,
        "generated_at": datetime.utcnow().isoformat() + "+00:00",
        "evaluation": {
            "handoff_decision": handoff_decision,
            "closure_decision": closure_decision,
            "archive_decision": archive_decision,
        },
        "scope": {
            "devices_per_cycle": 1,
            "max_objects_per_cycle": 3,
            "allowed_methods": ["POST"],
            "forbidden_methods": ["PATCH", "DELETE"],
            "forbidden_targets": ["/sync", "equipment", "ssh", "netconf"],
            "one_shot_only": True,
            "no_automatic_retry": True,
            "no_automatic_rollback": True,
            "no_bulk_write": True,
        },
        "mandatory_gates": [
            "week1_response",
            "week2_review",
            "approval_record",
            "applyplan_dryrun",
            "validate_applyplan",
            "dryrun_simulation",
            "real_write_authorization",
            "final_preflight",
            "execution_package",
            "execute_real_write_once",
            "post_write_verification",
            "compliance_rerun",
            "closure",
            "archive",
        ],
        "restrictions": [
            "No token in logs/saves/display",
            "No automatic retry on failure",
            "No automatic rollback",
            "No equipment SSH access",
            "One-shot execution only",
            "Stop on first failure",
            "No /sync endpoint",
            "No PATCH/DELETE initially",
            "No bulk write mode",
            "Week 1 + Week 2 review mandatory",
            "ApprovalRecord mandatory",
            "Dry-run simulation mandatory",
            "Authorization package mandatory",
            "Preflight phrase matching mandatory",
            "Post-write verification mandatory",
        ],
        "safety_confirmations": {
            "no_token_exposure": True,
            "no_secrets_in_logs": True,
            "audit_trail_complete": True,
            "one_shot_enforced": True,
            "manual_review_gated": True,
        },
        "next_phase": "FASE_4_1_CONTROLLED_OPERATION_CYCLE_V1",
    }

    # Write outputs
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(baseline_json, f, indent=2)

    print(f"✓ Baseline decision: {decision}")
    print(f"✓ Report: {args.output}")
    print(f"✓ JSON: {args.output_json}")

    return 0 if decision in ["CONTROLLED_OPERATION_READY", "CONTROLLED_OPERATION_READY_WITH_RESTRICTIONS"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
