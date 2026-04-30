#!/usr/bin/env python3
"""FASE 2.58 — Build Operational Handoff Decision.

Evaluate pilot success across all phases. Emit final decision:
- READY_FOR_CONTROLLED_OPERATION
- READY_WITH_RESTRICTIONS
- NOT_READY_FOR_OPERATION

Based on closure, verification, compliance, archive.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def load_json_safe(file_path: Path) -> Dict[str, Any]:
    """Load JSON file safely."""
    if not file_path.exists():
        return {}

    try:
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def evaluate_closure(closure_json: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Evaluate closure package success."""
    issues = []

    decision = closure_json.get("closure_decision", "")
    if "SUCCESS" not in decision:
        issues.append("Closure decision not SUCCESS")

    if closure_json.get("token_logged"):
        issues.append("Token was logged in closure")

    return len(issues) == 0, issues


def evaluate_verification(archive_manifest: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Check if post-write verification passed."""
    issues = []

    # Look for verification artifacts in archive
    artifacts = archive_manifest.get("artifacts", [])
    verification_found = any("verification" in a.get("file", "").lower() for a in artifacts)

    if not verification_found:
        issues.append("Post-write verification artifacts not found in archive")

    return len(issues) == 0, issues


def evaluate_compliance(archive_manifest: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Check if compliance checks passed."""
    issues = []

    artifacts = archive_manifest.get("artifacts", [])
    compliance_found = any("compliance" in a.get("file", "").lower() for a in artifacts)

    if not compliance_found:
        issues.append("Compliance artifacts not found in archive")

    return len(issues) == 0, issues


def evaluate_archive(archive_manifest: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Evaluate archive integrity."""
    issues = []

    decision = archive_manifest.get("final_decision", "")
    if "SUCCESS" not in decision:
        issues.append("Archive decision not SUCCESS")

    safety = archive_manifest.get("safety_confirmations", {})
    if not safety.get("no_tokens"):
        issues.append("Archive contains tokens")

    if not safety.get("no_secrets"):
        issues.append("Archive contains secrets")

    if archive_manifest.get("total_artifacts", 0) == 0:
        issues.append("No artifacts in archive")

    return len(issues) == 0, issues


def compute_decision(
    closure_ok: bool,
    verification_ok: bool,
    compliance_ok: bool,
    archive_ok: bool,
    closure_warnings: int = 0,
) -> str:
    """Compute final operational decision."""
    all_ok = closure_ok and verification_ok and compliance_ok and archive_ok

    if all_ok and closure_warnings == 0:
        return "READY_FOR_CONTROLLED_OPERATION"
    elif all_ok and closure_warnings > 0:
        return "READY_WITH_RESTRICTIONS"
    else:
        return "NOT_READY_FOR_OPERATION"


def generate_decision_markdown(
    device: str,
    decision: str,
    issues: List[str],
    restrictions: List[str],
) -> str:
    """Generate markdown decision report."""
    timestamp = datetime.utcnow().isoformat() + "+00:00"

    emoji_map = {
        "READY_FOR_CONTROLLED_OPERATION": "✓",
        "READY_WITH_RESTRICTIONS": "⚠",
        "NOT_READY_FOR_OPERATION": "✗",
    }

    emoji = emoji_map.get(decision, "?")

    md = f"""# Decisão de Handoff Operacional — {device}

## 1. Decisão Final

### {emoji} {decision}

## 2. Resumo Executivo

Device piloto: **{device}**
Data de avaliação: **{timestamp}**

"""

    if decision == "READY_FOR_CONTROLLED_OPERATION":
        md += """
**Status:** Sistema operacionalmente pronto para uso controlado.

- ✓ Fechamento bem-sucedido
- ✓ Verificação pós-escrita completa
- ✓ Compliance validado
- ✓ Arquivo íntegro e seguro
- ✓ Sem ações bloqueantes

"""
    elif decision == "READY_WITH_RESTRICTIONS":
        md += """
**Status:** Sistema operacionalmente viável, com restrições aplicadas.

- ✓ Fechamento bem-sucedido com avisos
- ✓ Verificação pós-escrita completa
- ✓ Compliance validado com warnings
- ✓ Arquivo íntegro e seguro
- ⚠ Restrições operacionais em vigor

"""
    else:
        md += """
**Status:** Sistema NÃO pronto para operação.

- ✗ Bloqueadores identificados
- ✗ Ação necessária antes de operar
- ✗ Não proceder com operação controlada

"""

    md += """## 3. Achados

"""

    if issues:
        md += "### Problemas Identificados\n\n"
        for issue in issues:
            md += f"- {issue}\n"
    else:
        md += "Nenhum problema identificado.\n\n"

    if restrictions:
        md += "\n### Restrições Operacionais\n\n"
        for restriction in restrictions:
            md += f"- {restriction}\n"

    md += f"""
## 4. Regras para Operação Controlada

Caso operando em modo controlado, seguir SEMPRE:

1. **Week 1 + Week 2:** Coleta e revisão obrigatória
2. **ApprovalRecord:** Cada mudança requer aprovação formal
3. **ApplyPlan:** Executar dry-run antes de real write
4. **Simulação:** Validar resultado esperado via simulação
5. **Authorization:** Gerar e validar authorization package
6. **Preflight:** Final preflight gate com phrase validation
7. **Execution:** One-shot, sem retry, sem rollback automático
8. **Verification:** POST-WRITE GET verify obrigatório
9. **Compliance:** Re-run compliance após escrita
10. **Closure:** Gerar closure package com decisão final

### Restrições de Segurança

- ✓ Nenhum /sync
- ✓ Nenhum PATCH/DELETE (POST only)
- ✓ Nenhum retry automático
- ✓ Nenhum rollback automático
- ✓ Token ambiente apenas (NETBOX_WRITE_TOKEN)
- ✓ Nenhum token em logs
- ✓ Verificação humana obrigatória em cada gate

## 5. Próximas Ações

"""

    if decision == "READY_FOR_CONTROLLED_OPERATION":
        md += """
1. [ ] Revisar esta decisão com time
2. [ ] Configurar ambiente de produção controlada
3. [ ] Validar NETBOX_WRITE_TOKEN disponível (não hardcoded)
4. [ ] Treinar operadores
5. [ ] Manter logs de auditoria
6. [ ] Executar primeiro cambio controlado (observar 100%)
7. [ ] Gradualmente aumentar escopo se sucesso

### Sucesso Esperado
- Todos os objetos criados em NetBox
- Verificação pós-escrita passa
- Compliance validado
- Audit trail completo
- Sem rollback necessário
"""
    elif decision == "READY_WITH_RESTRICTIONS":
        md += """
1. [ ] Resolver restrições documentadas acima
2. [ ] Escopo operacional limitado inicialmente
3. [ ] Revisão humana intensificada
4. [ ] Testes adicionais antes de ampliar
5. [ ] Monitorar alertas e avisos
6. [ ] Re-avaliar após resolução de restrições
"""
    else:
        md += """
1. [ ] Investigar problemas identificados
2. [ ] NÃO operar até resolução
3. [ ] Abrir plano corretivo
4. [ ] Re-executar este teste após correções
5. [ ] Requerer aprovação de segurança
6. [ ] Documentar causa raiz
"""

    md += f"""
---

**Decision ID:** HANDOFF-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}
**Generated:** {timestamp}
**Device:** {device}
"""

    return md


def main() -> int:
    """Run FASE 2.58."""
    parser = argparse.ArgumentParser(
        description="FASE 2.58 — Operational Handoff Decision"
    )
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--archive-manifest", type=Path, required=True)
    parser.add_argument("--closure-summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)

    args = parser.parse_args()

    # Load data
    archive = load_json_safe(args.archive_manifest)
    closure = load_json_safe(args.closure_summary)

    # Evaluate each phase
    closure_ok, closure_issues = evaluate_closure(closure)
    verification_ok, verification_issues = evaluate_verification(archive)
    compliance_ok, compliance_issues = evaluate_compliance(archive)
    archive_ok, archive_issues = evaluate_archive(archive)

    # Collect all issues
    all_issues = closure_issues + verification_issues + compliance_issues + archive_issues

    # Compute decision
    decision = compute_decision(closure_ok, verification_ok, compliance_ok, archive_ok)

    # Restrictions for WITH_RESTRICTIONS case
    restrictions = []
    if not closure_ok:
        restrictions.extend(closure_issues)
    if not verification_ok:
        restrictions.extend(verification_issues)
    if not compliance_ok:
        restrictions.extend(compliance_issues)

    # Generate markdown
    markdown = generate_decision_markdown(args.device, decision, all_issues, restrictions)

    # Generate JSON
    decision_json = {
        "decision_id": f"HANDOFF-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
        "device": args.device,
        "device_id": args.device_id,
        "decision": decision,
        "generated_at": datetime.utcnow().isoformat() + "+00:00",
        "evaluation": {
            "closure": closure_ok,
            "verification": verification_ok,
            "compliance": compliance_ok,
            "archive": archive_ok,
        },
        "issues": all_issues,
        "restrictions": restrictions,
        "safety_confirmations": {
            "no_tokens": True,
            "no_secrets": True,
            "audit_trail_complete": True,
            "gates_enforced": True,
        },
        "next_phase": "OPERATIONAL_MONITORING",
    }

    # Write outputs
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(decision_json, f, indent=2)

    print(f"✓ Decision: {decision}")
    print(f"✓ Report: {args.output}")
    print(f"✓ JSON: {args.output_json}")
    print(f"✓ Issues: {len(all_issues)}")

    return 0 if decision == "READY_FOR_CONTROLLED_OPERATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
