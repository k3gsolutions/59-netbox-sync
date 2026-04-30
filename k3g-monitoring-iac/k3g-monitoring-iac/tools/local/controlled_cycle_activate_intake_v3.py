#!/usr/bin/env python3
"""FASE 4.71 — Cycle-003 Intake Activation."""

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


def activate_intake(
    *,
    cycle_id: str,
    device: str,
    device_id: str,
    cycle_dir: Path,
    start_gate: Path,
    operation_index: Path,
    output: Path,
    output_json: Path,
) -> dict[str, Any]:
    """Activate cycle intake based on start gate."""
    sg = load_json(start_gate)
    sg_decision = sg.get("decision", "")

    issues = []

    # Validate start gate decision
    if not sg_decision:
        issues.append("start gate decision missing")
    elif "BLOCKED" in sg_decision:
        issues.append(f"start gate blocked: {sg.get('reason', 'unknown')}")
    elif "READY" not in sg_decision:
        issues.append(f"unsupported start gate decision: {sg_decision}")

    # Validate scope
    scope = load_json(cycle_dir / f"{cycle_id.upper()}-SCOPE.json")
    if not scope:
        issues.append("scope missing")
    else:
        if scope.get("max_items", 0) > 3:
            issues.append("max_items > 3")
        if scope.get("allowed_methods") != ["POST"]:
            issues.append("allowed_methods not POST-only")

    # Determine decision
    if issues:
        decision = "CYCLE_INTAKE_ACTIVATION_BLOCKED"
        reason = "; ".join(issues)
    elif "WITH_RESTRICTIONS" in sg_decision:
        decision = "CYCLE_INTAKE_ACTIVATED_WITH_RESTRICTIONS"
        reason = "Activated with restrictions from previous cycle"
    else:
        decision = "CYCLE_INTAKE_ACTIVATED"
        reason = "Activated without restrictions"

    result = {
        "activation_id": f"intake-{cycle_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "cycle_id": cycle_id,
        "device": device,
        "device_id": device_id,
        "activated_at": datetime.now(timezone.utc).isoformat(),
        "decision": decision,
        "reason": reason,
        "start_gate_decision": sg_decision,
        "restrictions": sg.get("restrictions", []) if "WITH_RESTRICTIONS" in decision else [],
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    # Markdown report
    lines = [
        f"# Intake Activation — {cycle_id.upper()}",
        "",
        f"## Decision: {decision}",
        "",
        f"- Device: {device} (ID: {device_id})",
        f"- Start Gate: {sg_decision}",
        f"- Reason: {reason}",
        "",
    ]

    if result.get("restrictions"):
        lines.append("## Restrictions")
        lines.append("")
        for r in result["restrictions"]:
            lines.append(f"- {r}")
        lines.append("")

    lines.extend([
        "## Next Step",
        "Week 1 Preparation" if "ACTIVATED" in decision else "Block intake until issues resolved",
        "",
        "---",
        f"Activated at {datetime.now(timezone.utc).isoformat()}",
    ])

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")

    return result


def main() -> int:
    """Run FASE 4.71."""
    parser = argparse.ArgumentParser(description="FASE 4.71 — Intake Activation")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--cycle-dir", type=Path, required=True)
    parser.add_argument("--start-gate", type=Path, required=True)
    parser.add_argument("--operation-index", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)

    args = parser.parse_args()
    result = activate_intake(
        cycle_id=args.cycle_id,
        device=args.device,
        device_id=args.device_id,
        cycle_dir=args.cycle_dir,
        start_gate=args.start_gate,
        operation_index=args.operation_index,
        output=args.output,
        output_json=args.output_json,
    )

    print(f"✓ Intake: {result.get('decision')}")
    print(f"✓ Report: {args.output}")
    return 0 if "BLOCKED" not in result.get("decision") else 1


if __name__ == "__main__":
    raise SystemExit(main())
