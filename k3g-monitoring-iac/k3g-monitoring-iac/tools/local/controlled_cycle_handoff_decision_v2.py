#!/usr/bin/env python3
"""FASE 4.64 — Handoff decision for Cycle-002."""

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


def s(value: Any) -> str:
    """Safe string conversion."""
    return str(value or "").strip()


def handoff_decision(
    *,
    cycle_id: str,
    device: str,
    device_id: str,
    closure_summary: Path,
    archive_manifest: Path,
    output: Path,
    output_json: Path,
) -> dict[str, Any]:
    """Determine handoff decision based on closure and archive."""
    closure = load_json(closure_summary)
    archive = load_json(archive_manifest)

    closure_status = s(closure.get("status"))
    archive_status = s(archive.get("status"))

    # Determine handoff decision
    decision = "CYCLE_ACTION_REQUIRED"
    reason = "Unknown state"

    if "ACTION_REQUIRED" in closure_status or "SECURITY_ISSUE" in archive_status:
        decision = "CYCLE_ACTION_REQUIRED"
        reason = "Closure or archive failed"
    elif ("SUCCESS" in closure_status) and ("SUCCESS" in archive_status):
        decision = "CYCLE_CLOSED_READY_FOR_NEXT_OPERATION"
        reason = "Execution completed successfully"
    elif (("WARNINGS" in closure_status or "DRIFT" in closure_status or "WITH_WARNINGS" in closure_status) and
          ("WARNINGS" in archive_status or "SUCCESS" in archive_status or "WITH_WARNINGS" in archive_status)):
        decision = "CYCLE_CLOSED_WITH_RESTRICTIONS"
        reason = "Execution completed with warnings - restrições mantidas"
    else:
        decision = "CYCLE_ACTION_REQUIRED"
        reason = f"Unknown: closure={closure_status}, archive={archive_status}"

    result = {
        "decision_id": f"handoff-{cycle_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "cycle_id": cycle_id,
        "device": device,
        "device_id": device_id,
        "decided_at": datetime.now(timezone.utc).isoformat(),
        "decision": decision,
        "reason": reason,
        "closure_status": closure_status,
        "archive_status": archive_status,
        "restrictions": [
            "Manter max_items=3",
            "Manter allowed_methods=[POST]",
            "Manter 1 device por ciclo",
            "Manter STAY_CURRENT_LEVEL de expansão",
            "Normalizar validadores para enum/status",
        ] if "RESTRICTIONS" in decision else [],
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    # Markdown report
    lines = [
        f"# Decisão de Handoff — {cycle_id.upper()}",
        "",
        "## 1. Decisão",
        f"**{decision}**",
        "",
        "## 2. Resumo Executivo",
        f"- Escrita real: {closure_status}",
        f"- Arquivo: {archive_status}",
        f"- Razão: {reason}",
        "",
    ]

    if result.get("restrictions"):
        lines.extend([
            "## 3. Restrições para Próximo Ciclo",
            "",
        ])
        for r in result["restrictions"]:
            lines.append(f"- {r}")
        lines.append("")

    lines.extend([
        "## 4. Recomendação",
    ])

    if "READY_FOR_NEXT_OPERATION" in decision:
        lines.append("Ciclo pronto para operação normal. Sem restrições adicionais.")
    elif "WITH_RESTRICTIONS" in decision:
        lines.append("Ciclo pronto, mas com restrições. Manter limites de escala e continuar validação de normalização.")
    else:
        lines.append("Ação requerida antes de próximo ciclo.")

    lines.extend([
        "",
        "---",
        f"Decidido em {datetime.now(timezone.utc).isoformat()}",
    ])

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")

    return result


def main() -> int:
    """Run FASE 4.64."""
    parser = argparse.ArgumentParser(description="FASE 4.64 — Handoff Decision")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--closure-summary", type=Path, required=True)
    parser.add_argument("--archive-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)

    args = parser.parse_args()
    result = handoff_decision(
        cycle_id=args.cycle_id,
        device=args.device,
        device_id=args.device_id,
        closure_summary=args.closure_summary,
        archive_manifest=args.archive_manifest,
        output=args.output,
        output_json=args.output_json,
    )

    print(f"✓ Handoff: {result.get('decision')}")
    print(f"✓ Report: {args.output}")
    print(f"✓ JSON: {args.output_json}")

    return 0 if "ACTION_REQUIRED" not in result.get("decision") else 1


if __name__ == "__main__":
    raise SystemExit(main())
