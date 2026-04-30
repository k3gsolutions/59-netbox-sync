#!/usr/bin/env python3
"""FASE 4.30 — Build Controlled Operation Index."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from webui.services.controlled_operation import list_controlled_cycles


def main() -> int:
    parser = argparse.ArgumentParser(description="FASE 4.30 — Build Controlled Operation Index")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()

    if not args.root.exists():
        print(f"✗ Root directory not found: {args.root}")
        return 1

    cycles = list_controlled_cycles(args.root)
    if not cycles:
        print(f"✗ No cycles found in {args.root}")
        return 1

    statuses = [cycle["current_status"] for cycle in cycles]
    if "action_required" in statuses:
        overall_status = "BLOCKED"
    elif "closed_with_restrictions" in statuses:
        overall_status = "WITH_RESTRICTIONS"
    elif all(status in {"planned", "closed_success"} for status in statuses):
        overall_status = "OPERATIONAL"
    else:
        overall_status = "IN_PROGRESS"

    measured_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "measured_at": measured_at,
        "total_cycles": len(cycles),
        "overall_status": overall_status,
        "cycles": cycles,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# Controlled Operation Index",
        "",
        "## 1. Overall Status",
        f"- Status: {overall_status}",
        f"- Total Cycles: {len(cycles)}",
        f"- Measured at: {measured_at}",
        "",
        "## 2. Cycle Summary",
        "",
        "| Cycle | Device | Status | Items | Handoff | Next Action |",
        "|-------|--------|--------|-------|---------|-------------|",
    ]
    for cycle in cycles:
        lines.append(
            f"| {cycle['cycle_id']} | {cycle['device']} | {cycle['current_status']} | "
            f"{cycle['total_items']}/{cycle['max_items']} | {cycle.get('handoff_decision') or 'N/A'} | "
            f"{cycle['next_action']} |"
        )

    lines.extend([
        "",
        "## 3. Detailed Status",
        "",
    ])

    for cycle in cycles:
        artifacts = ", ".join(cycle.get("key_artifacts", [])) or "None"
        lines.extend([
            f"### {cycle['cycle_id']} — {cycle['device']}",
            "",
            f"- **Status:** {cycle['current_status']}",
            f"- **Device ID:** {cycle['device_id']}",
            f"- **Max Items:** {cycle['max_items']}",
            f"- **Total Items Processed:** {cycle['total_items']}",
            f"- **Allowed Methods:** {', '.join(cycle['allowed_methods'])}",
            f"- **Forbidden Methods:** {', '.join(cycle['forbidden_methods'])}",
            f"- **Handoff Decision:** {cycle.get('handoff_decision') or 'N/A'}",
            f"- **Closure Decision:** {cycle.get('closure_decision') or 'N/A'}",
            f"- **Artifacts:** {artifacts}",
            f"- **Next Action:** {cycle['next_action']}",
            "",
            "---",
            "",
        ])

    lines.extend([
        "## 4. Key Artifacts",
        "",
        "Cycles and their essential files:",
        "- Scopes in `cycle-*/cycle-*-scope.json` or `cycle-*/CYCLE-*-SCOPE.json`",
        "- Handoff decisions in `cycle-*/cycle-*-handoff-decision.json`",
        "- Final archives in `cycle-*/final-archive/manifest.json`",
        "- Closure summaries in `cycle-*/real-write-execution/closure/` or `cycle-*/final-archive/`",
        "",
        f"---",
        f"Index built at {measured_at}",
        "",
    ])

    args.output.write_text("\n".join(lines), encoding="utf-8")

    print(f"✓ Index built: {len(cycles)} cycles")
    print(f"✓ Overall status: {overall_status}")
    print(f"✓ Markdown: {args.output}")
    print(f"✓ JSON: {args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
