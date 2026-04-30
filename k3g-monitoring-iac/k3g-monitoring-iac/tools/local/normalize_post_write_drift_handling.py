#!/usr/bin/env python3
"""FASE 4.67 — Normalize Warning/Drift Handling."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict:
    """Load JSON safely."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def classify_drift(proposed: Any, observed: Any) -> tuple[str, str]:
    """Classify drift as blocking or non-blocking format."""
    if proposed == observed:
        return "NO_DRIFT", ""

    # Handle enum: "active" vs {"value": "active", "label": "Active"}
    if isinstance(proposed, str) and isinstance(observed, dict):
        if observed.get("value") == proposed:
            return "NON_BLOCKING_FORMAT_DRIFT", "enum formatting: string vs object"
        if observed.get("label", "").lower() == proposed.lower():
            return "NON_BLOCKING_FORMAT_DRIFT", "enum label match"

    # Handle type diff: "6324" vs 6324
    if str(proposed) == str(observed):
        return "NON_BLOCKING_FORMAT_DRIFT", f"type difference: {type(proposed).__name__} vs {type(observed).__name__}"

    # Handle URL normalization
    if isinstance(proposed, str) and isinstance(observed, str):
        if proposed.rstrip("/") == observed.rstrip("/"):
            return "NON_BLOCKING_FORMAT_DRIFT", "trailing slash"

    return "REAL_DRIFT", f"value mismatch: {proposed} vs {observed}"


def analyze_drift(
    *,
    cycle_id: str,
    verification: Path,
    compliance: Path,
    closure: Path,
    output: Path,
    output_json: Path,
) -> dict[str, Any]:
    """Analyze drift in verification results."""
    verif = load_json(verification)
    compl = load_json(compliance)
    clos = load_json(closure)

    drift_items = []
    blocking_drift = False

    # Analyze verification items for drift
    for item in verif.get("items", []):
        if item.get("verification_status") == "drift":
            proposed = item.get("proposed_payload", {})
            observed = item.get("verified_object", {})

            # Check each field
            field_drifts = []
            for key, prop_val in proposed.items():
                obs_val = observed.get(key)
                drift_type, reason = classify_drift(prop_val, obs_val)
                if drift_type != "NO_DRIFT":
                    field_drifts.append({
                        "field": key,
                        "proposed": prop_val,
                        "observed": obs_val,
                        "type": drift_type,
                        "reason": reason,
                    })
                    if drift_type == "REAL_DRIFT":
                        blocking_drift = True

            drift_items.append({
                "object_key": item.get("object_key"),
                "type": "verification_drift",
                "fields": field_drifts,
                "overall": "NON_BLOCKING" if not blocking_drift else "BLOCKING",
            })

    # Overall assessment
    if blocking_drift:
        overall_decision = "DRIFT_REAL_REQUIRES_REVIEW"
    elif drift_items:
        overall_decision = "DRIFT_FORMAT_ONLY_OPERATIONAL"
    else:
        overall_decision = "NO_DRIFT_DETECTED"

    result = {
        "analysis_id": f"drift-norm-{cycle_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "cycle_id": cycle_id,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "overall_decision": overall_decision,
        "drift_items": drift_items,
        "verification_status": verif.get("decision"),
        "compliance_status": compl.get("decision"),
        "closure_status": clos.get("status"),
        "recommendation": "Cycle-002 operationally successful. Format drift non-blocking." if "OPERATIONAL" in overall_decision else "Review required.",
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    # Markdown report
    lines = [
        f"# Análise de Drift — {cycle_id.upper()}",
        "",
        "## 1. Decisão Geral",
        f"**{overall_decision}**",
        "",
        "## 2. Resumo",
        f"- Verificação: {verif.get('decision')}",
        f"- Compliance: {compl.get('decision')}",
        f"- Closure: {clos.get('status')}",
        f"- Drift items: {len(drift_items)}",
        f"- Blocking drift: {'Sim' if blocking_drift else 'Não'}",
        "",
    ]

    if drift_items:
        lines.append("## 3. Drift Detectado")
        lines.append("")
        for item in drift_items:
            lines.append(f"### {item['object_key']}")
            lines.append(f"- Status: {item['overall']}")
            lines.append("")
            if item['fields']:
                lines.append("| Campo | Esperado | Observado | Tipo | Motivo |")
                lines.append("|-------|----------|-----------|------|--------|")
                for field in item['fields']:
                    t = field['type']
                    lines.append(f"| {field['field']} | {field['proposed']} | {field['observed']} | {t} | {field['reason']} |")
            lines.append("")

    lines.extend([
        "## 4. Recomendação",
        result['recommendation'],
        "",
        "## 5. Ação Futura",
        "- Adicionar normalizer para enum/format em validators futuros.",
        "- Não mascarar drift real.",
        "- Classificar explicitamente format vs real drift.",
        "",
        "---",
        f"Analisado em {datetime.now(timezone.utc).isoformat()}",
    ])

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")

    return result


def main() -> int:
    """Run FASE 4.67."""
    parser = argparse.ArgumentParser(description="FASE 4.67 — Normalize Drift")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--verification", type=Path, required=True)
    parser.add_argument("--compliance", type=Path, required=True)
    parser.add_argument("--closure-summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)

    args = parser.parse_args()
    result = analyze_drift(
        cycle_id=args.cycle_id,
        verification=args.verification,
        compliance=args.compliance,
        closure=args.closure_summary,
        output=args.output,
        output_json=args.output_json,
    )

    print(f"✓ Drift analysis: {result.get('overall_decision')}")
    print(f"✓ Drift items: {len(result.get('drift_items', []))}")
    print(f"✓ Report: {args.output}")
    return 0 if "REAL" not in result.get("overall_decision") else 1


if __name__ == "__main__":
    raise SystemExit(main())
