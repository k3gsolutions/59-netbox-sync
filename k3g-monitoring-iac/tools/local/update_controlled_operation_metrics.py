#!/usr/bin/env python3
"""FASE 4.28 — Update Controlled Operation Metrics.

Update global operational metrics after cycle completion.
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


def count_cycle_directories(root: Path) -> int:
    """Count cycle directories."""
    count = 0
    for item in root.iterdir():
        if item.is_dir() and item.name.startswith("cycle-"):
            count += 1
    return count


def main() -> int:
    """Run FASE 4.28."""
    parser = argparse.ArgumentParser(description="FASE 4.28 — Update Metrics")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)

    args = parser.parse_args()

    # Count cycles
    total_cycles = count_cycle_directories(args.root)

    # Load last cycle if exists
    last_closure = {}
    last_handoff = {}
    if total_cycles > 0:
        cycle_001_dir = args.root / "cycle-001"
        if cycle_001_dir.exists():
            closure_file = cycle_001_dir / "real-write-execution" / "closure" / "cycle-001-closure-summary.json"
            handoff_file = cycle_001_dir / "cycle-001-handoff-decision.json"
            last_closure = load_json_safe(closure_file)
            last_handoff = load_json_safe(handoff_file)

    # Build metrics
    metrics = {
        "measured_at": datetime.utcnow().isoformat() + "+00:00",
        "total_cycles_defined": total_cycles,
        "cycles_completed": 1 if last_closure.get("decision") else 0,
        "cycles_closed_success": 1 if "SUCCESS" in last_closure.get("decision", "") else 0,
        "cycles_closed_with_warnings": 1 if "WARNINGS" in last_closure.get("decision", "") else 0,
        "cycles_action_required": 1 if "ACTION_REQUIRED" in last_closure.get("decision", "") else 0,
        "handoff_ready": 1 if last_handoff.get("decision") == "CYCLE_CLOSED_READY_FOR_NEXT_OPERATION" else 0,
        "handoff_with_restrictions": 1 if last_handoff.get("decision") == "CYCLE_CLOSED_WITH_RESTRICTIONS" else 0,
        "handoff_action_required": 1 if last_handoff.get("decision") == "CYCLE_ACTION_REQUIRED" else 0,
    }

    # Write JSON
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    # Write markdown
    markdown = f"""# Métricas de Operação Controlada

## 1. Status Geral
- Data: {metrics['measured_at']}
- Total Cycles Definidos: {metrics['total_cycles_defined']}
- Cycles Completados: {metrics['cycles_completed']}

## 2. Resultados
- Success: {metrics['cycles_closed_success']}
- With Warnings: {metrics['cycles_closed_with_warnings']}
- Action Required: {metrics['cycles_action_required']}

## 3. Handoff
- Ready for Next: {metrics['handoff_ready']}
- With Restrictions: {metrics['handoff_with_restrictions']}
- Action Required: {metrics['handoff_action_required']}

## 4. Próximos Passos
"""

    if metrics.get("handoff_ready", 0) > 0:
        markdown += "✓ Pronto para iniciar Cycle-002\n"
    elif metrics.get("handoff_with_restrictions", 0) > 0:
        markdown += "⚠ Resolver alertas antes de prosseguir\n"
    else:
        markdown += "✗ Bloquear próximos ciclos\n"

    markdown += f"""

---
Métricas medidas em {metrics['measured_at']}
"""

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")

    print(f"✓ Metrics updated: {total_cycles} cycles")
    print(f"✓ Report: {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
