#!/usr/bin/env python3
"""FASE 2.56 — Build Post-Write Closure Package.

Consolidate execution, verification, and compliance results.
Generate final decision and closure package.
No network calls, no token reads, purely local aggregation.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from uuid import uuid4


def load_execution_result(result_file: Path) -> Tuple[bool, str, Dict[str, Any]]:
    """Load execution result."""
    if not result_file.exists():
        return False, f"File not found: {result_file}", {}

    try:
        with open(result_file, encoding="utf-8") as f:
            result = json.load(f)
    except Exception as e:
        return False, f"Invalid JSON: {e}", {}

    return True, "OK", result


def consolidate_results(
    execution: Dict[str, Any],
    verification: Dict[str, Any],
    compliance: Dict[str, Any],
) -> Dict[str, Any]:
    """Consolidate all phase results into closure package."""
    execution_success = execution.get("status") == "REAL_WRITE_SUCCESS"
    verification_success = verification.get("status") == "POST_WRITE_VERIFICATION_SUCCESS"
    compliance_success = compliance.get("status") == "POST_WRITE_COMPLIANCE_SUCCESS"

    all_success = execution_success and verification_success and compliance_success

    closure_decision = "WRITE_EXECUTION_COMPLETE_SUCCESS" if all_success else "WRITE_EXECUTION_COMPLETE_FAILURE"

    return {
        "closure_decision": closure_decision,
        "execution_success": execution_success,
        "verification_success": verification_success,
        "compliance_success": compliance_success,
        "execution_id": execution.get("execution_id"),
        "verification_id": verification.get("verification_id"),
        "compliance_run_id": compliance.get("compliance_run_id"),
        "device": execution.get("device"),
        "device_id": execution.get("device_id"),
        "total_items": execution.get("items", []).__len__(),
        "created_items": sum(1 for item in execution.get("items", []) if "CREATED" in item.get("status", "")),
        "verified_items": verification.get("verified_count", 0),
        "compliance_checks_passed": compliance.get("checks_passed", 0),
        "compliance_checks_total": compliance.get("total_checks", 0),
    }


def main() -> int:
    """Run FASE 2.56."""
    parser = argparse.ArgumentParser(
        description="FASE 2.56 — Build Post-Write Closure Package"
    )
    parser.add_argument("--execution-result", type=Path, required=True)
    parser.add_argument("--verification-result", type=Path, required=True)
    parser.add_argument("--compliance-result", type=Path, required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)

    args = parser.parse_args()

    closure_id = str(uuid4())
    timestamp = datetime.utcnow().isoformat() + "+00:00"

    # Load all results
    exec_ok, exec_reason, execution = load_execution_result(args.execution_result)
    if not exec_ok:
        print(f"✗ Execution result invalid: {exec_reason}")
        return 1

    verif_ok, verif_reason, verification = load_execution_result(
        args.verification_result
    )
    if not verif_ok:
        print(f"✗ Verification result invalid: {verif_reason}")
        return 1

    comp_ok, comp_reason, compliance = load_execution_result(args.compliance_result)
    if not comp_ok:
        print(f"✗ Compliance result invalid: {comp_reason}")
        return 1

    # Consolidate
    consolidated = consolidate_results(execution, verification, compliance)

    # Generate closure JSON
    closure_json = {
        "closure_package_id": closure_id,
        "generated_at": timestamp,
        "device": args.device,
        "closure_decision": consolidated["closure_decision"],
        "phases": {
            "FASE_2_53_EXECUTION": {
                "status": execution.get("status"),
                "execution_id": execution.get("execution_id"),
                "success": consolidated["execution_success"],
            },
            "FASE_2_54_VERIFICATION": {
                "status": verification.get("status"),
                "verification_id": verification.get("verification_id"),
                "success": consolidated["verification_success"],
            },
            "FASE_2_55_COMPLIANCE": {
                "status": compliance.get("status"),
                "compliance_run_id": compliance.get("compliance_run_id"),
                "success": consolidated["compliance_success"],
            },
        },
        "summary": {
            "total_items": consolidated["total_items"],
            "created_items": consolidated["created_items"],
            "verified_items": consolidated["verified_items"],
            "compliance_checks_passed": consolidated["compliance_checks_passed"],
            "compliance_checks_total": consolidated["compliance_checks_total"],
        },
        "token_logged": False,
        "audit_trail_complete": True,
    }

    # Generate markdown
    decision_emoji = "✓" if consolidated["closure_decision"] == "WRITE_EXECUTION_COMPLETE_SUCCESS" else "✗"

    result_md = f"""# Pacote de Fechamento Pós-Escrita — {args.device}

## 1. Decisão Final

### {decision_emoji} {consolidated['closure_decision']}

## 2. Resumo das Fases

| Fase | Status | ID | Resultado |
|---|---|---|---|
| FASE 2.53 (Execução) | {execution.get('status')} | {execution.get('execution_id')} | {"✓ SUCESSO" if consolidated['execution_success'] else "✗ FALHA"} |
| FASE 2.54 (Verificação) | {verification.get('status')} | {verification.get('verification_id')} | {"✓ SUCESSO" if consolidated['verification_success'] else "✗ FALHA"} |
| FASE 2.55 (Compliance) | {compliance.get('status')} | {compliance.get('compliance_run_id')} | {"✓ SUCESSO" if consolidated['compliance_success'] else "✗ FALHA"} |

## 3. Estatísticas

- **Device:** {args.device}
- **Total de itens:** {consolidated['total_items']}
- **Itens criados:** {consolidated['created_items']}
- **Itens verificados:** {consolidated['verified_items']}
- **Compliance checks (passed/total):** {consolidated['compliance_checks_passed']}/{consolidated['compliance_checks_total']}

## 4. Artefatos Gerados

- ✓ REAL-WRITE-EXECUTION-RESULT.json
- ✓ REAL-WRITE-EXECUTION-RESULT.md
- ✓ POST-WRITE-VERIFICATION-RESULT.json
- ✓ POST-WRITE-VERIFICATION-RESULT.md
- ✓ POST-WRITE-COMPLIANCE-RESULT.json
- ✓ POST-WRITE-COMPLIANCE-RESULT.md
- ✓ CLOSURE-PACKAGE.json (este)
- ✓ CLOSURE-PACKAGE.md (este)

## 5. Próximas Ações

"""

    if consolidated["closure_decision"] == "WRITE_EXECUTION_COMPLETE_SUCCESS":
        result_md += """
✓ **Todas as fases completadas com sucesso.**

### Ações recomendadas:

1. Revisar todos os artefatos e confirmar
2. Arquivar pacote de fechamento
3. Fechar ticket de mudança (se aplicável)
4. Notificar stakeholders
5. Atualizar documentação se necessário
6. Continuar com próximas mudanças programadas

### Estado do sistema:

- NetBox atualizado com todas as mudanças
- Todas as mudanças verificadas e validadas
- Compliance revalidado
- Audit trail completo
- **Sistema pronto para operação normal**
"""
    else:
        result_md += """
✗ **Falha detectada em uma ou mais fases.**

### Ações recomendadas:

1. Revisar logs de erro em detalhes
2. Identificar qual fase falhou
3. Se FASE 2.53: Sem rollback necessário (nenhuma criação bem-sucedida)
4. Se FASE 2.54: Problemas de conectividade ou dados inconsistentes
5. Se FASE 2.55: Compliance não passou - investigar divergências
6. Escalar se necessário
7. Documentar lição aprendida

### Estado do sistema:

- NetBox: Estado parcial ou inconsistente
- Verificação: Incompleta
- Compliance: Falhou
- **Requer ação manual antes de continuar**
"""

    result_md += f"""
---

**Closure Package ID:** {closure_id}
**Generated:** {timestamp}
**Device:** {args.device}
"""

    # Write results
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(closure_json, f, indent=2)

    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(result_md, encoding="utf-8")

    print(f"✓ Closure package: {args.output_json}")
    print(f"✓ Closure report: {args.output_md}")
    print(f"✓ Decision: {consolidated['closure_decision']}")

    return 0 if consolidated["closure_decision"] == "WRITE_EXECUTION_COMPLETE_SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
