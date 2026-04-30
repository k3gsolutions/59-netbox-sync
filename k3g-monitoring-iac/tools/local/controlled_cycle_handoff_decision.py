#!/usr/bin/env python3
"""FASE 4.27 — Controlled Operation Cycle Operational Handoff Decision.

Emit final handoff decision based on cycle completion status.
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


def determine_handoff_decision(
    closure_summary: Dict[str, Any],
    archive_manifest: Dict[str, Any],
) -> str:
    """Determine handoff decision based on cycle results."""
    # ACTION_REQUIRED - failures in any phase
    closure_decision = closure_summary.get("decision", "")
    if "ACTION_REQUIRED" in closure_decision or "FAILED" in closure_decision:
        return "CYCLE_ACTION_REQUIRED"

    # ACTION_REQUIRED - secrets in archive
    if archive_manifest.get("secrets_found_count", 0) > 0:
        return "CYCLE_ACTION_REQUIRED"

    # ACTION_REQUIRED - archive action required
    archive_status = archive_manifest.get("status", "")
    if "ACTION_REQUIRED" in archive_status:
        return "CYCLE_ACTION_REQUIRED"

    # WITH_RESTRICTIONS - warnings present
    if "WARNINGS" in closure_decision or "WITH_DRIFT" in closure_decision:
        return "CYCLE_CLOSED_WITH_RESTRICTIONS"

    # READY - all passed
    if "SUCCESS" in closure_decision:
        return "CYCLE_CLOSED_READY_FOR_NEXT_OPERATION"

    return "CYCLE_ACTION_REQUIRED"


def main() -> int:
    """Run FASE 4.27."""
    parser = argparse.ArgumentParser(description="FASE 4.27 — Handoff Decision")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--closure-summary", type=Path, required=True)
    parser.add_argument("--archive-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)

    args = parser.parse_args()

    # Load results
    closure = load_json_safe(args.closure_summary)
    archive = load_json_safe(args.archive_manifest)

    # Determine decision
    decision = determine_handoff_decision(closure, archive)

    # Build result
    result = {
        "cycle_id": args.cycle_id,
        "device": args.device,
        "device_id": args.device_id,
        "decision": decision,
        "decided_at": datetime.utcnow().isoformat() + "+00:00",
        "closure_decision": closure.get("decision"),
        "archive_status": archive.get("status"),
        "secrets_found": archive.get("secrets_found_count", 0),
    }

    # Write JSON
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    # Write markdown
    emoji = {
        "CYCLE_CLOSED_READY_FOR_NEXT_OPERATION": "✓",
        "CYCLE_CLOSED_WITH_RESTRICTIONS": "⚠",
        "CYCLE_ACTION_REQUIRED": "✗",
    }.get(decision, "?")

    markdown = f"""# Decisão de Handoff — {args.cycle_id}

## 1. Decisão
{emoji} **{decision}**

## 2. Resumo Executivo
- Cycle: {args.cycle_id}
- Device: {args.device}
- Closure: {closure.get('decision')}
- Archive: {archive.get('status')}
- Secrets Found: {archive.get('secrets_found_count', 0)}

## 3. Recomendação
"""

    if decision == "CYCLE_CLOSED_READY_FOR_NEXT_OPERATION":
        markdown += "✓ Pronto para iniciar Cycle-002 com mesmo modelo.\n"
    elif decision == "CYCLE_CLOSED_WITH_RESTRICTIONS":
        markdown += "⚠ Resolver alertas antes de ampliar escopo.\n"
    else:
        markdown += "✗ Bloquear próximos ciclos até correção.\n"

    markdown += f"""

---
Decisão em {result['decided_at']}
"""

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")

    print(f"✓ Handoff decision: {decision}")
    print(f"✓ Cycle: {args.cycle_id}")
    print(f"✓ Report: {args.output}")

    return 0 if decision != "CYCLE_ACTION_REQUIRED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
