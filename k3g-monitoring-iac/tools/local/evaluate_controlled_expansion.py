#!/usr/bin/env python3
"""FASE 4.33 — Evaluate Controlled Expansion."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from webui.services.controlled_operation import load_json_safe


def load_policy(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}
    except Exception:
        return {}


def evaluate(index: dict, policy: dict) -> str:
    cycles = index.get("cycles", [])
    if not cycles:
        return "EXPANSION_BLOCKED"

    action_required = [cycle for cycle in cycles if cycle.get("current_status") == "action_required"]
    if action_required:
        return "EXPANSION_BLOCKED"

    successful = [cycle for cycle in cycles if cycle.get("current_status") == "closed_success"]
    restrictions = [cycle for cycle in cycles if cycle.get("current_status") == "closed_with_restrictions"]
    level_1 = int(policy.get("expansion_levels", {}).get("level_1_controlled", {}).get("required_successful_cycles", 2))
    level_2 = int(policy.get("expansion_levels", {}).get("level_2_limited_scale", {}).get("required_successful_cycles", 5))

    if len(successful) >= level_2:
        return "ELIGIBLE_FOR_LEVEL_2_LIMITED_SCALE"
    if len(successful) >= level_1:
        return "ELIGIBLE_FOR_LEVEL_1_CONTROLLED"
    if successful or restrictions:
        return "STAY_CURRENT_LEVEL"
    return "STAY_CURRENT_LEVEL"


def main() -> int:
    parser = argparse.ArgumentParser(description="FASE 4.33 — Evaluate Controlled Expansion")
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()

    metrics = load_json_safe(args.metrics)
    index = load_json_safe(args.index)
    policy = load_policy(args.policy)

    if not index.get("cycles"):
        print("✗ No cycles found in index")
        return 1

    recommendation = evaluate(index, policy)
    cycles = index.get("cycles", [])
    successful_cycles = sum(1 for cycle in cycles if cycle.get("current_status") == "closed_success")
    action_required_cycles = sum(1 for cycle in cycles if cycle.get("current_status") == "action_required")
    measured_at = datetime.now(timezone.utc).isoformat()

    result = {
        "evaluated_at": measured_at,
        "total_cycles": len(cycles),
        "successful_cycles": successful_cycles,
        "action_required_cycles": action_required_cycles,
        "recommendation": recommendation,
        "limits_changed": False,
        "current_limits": policy.get("current_limits", {}),
        "policy_version": policy.get("version", "unknown"),
        "metrics_snapshot": metrics,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, indent=2), encoding="utf-8")

    lines = [
        "# Controlled Expansion Evaluation",
        "",
        "## 1. Assessment",
        f"**{recommendation}**",
        "",
        "## 2. Metrics",
        f"- Total Cycles: {len(cycles)}",
        f"- Successful Cycles: {successful_cycles}",
        f"- Action Required: {action_required_cycles}",
        "",
        "## 3. Current Limits",
        f"- Max Devices per Cycle: {result['current_limits'].get('max_devices_per_cycle', 1)}",
        f"- Max Items per Cycle: {result['current_limits'].get('max_items_per_cycle', 3)}",
        f"- Allowed Methods: {', '.join(result['current_limits'].get('allowed_methods', ['POST']))}",
        f"- Forbidden Methods: {', '.join(result['current_limits'].get('forbidden_methods', ['PATCH', 'DELETE']))}",
        "",
        "## 4. Recommendation",
    ]
    if recommendation == "EXPANSION_BLOCKED":
        lines.append("Expansion blocked. Resolve action-required cycles first.")
    elif recommendation == "ELIGIBLE_FOR_LEVEL_2_LIMITED_SCALE":
        lines.append("Eligible for Level 2 (Limited Scale).")
        lines.append("Manager approval and formal change control remain mandatory.")
    elif recommendation == "ELIGIBLE_FOR_LEVEL_1_CONTROLLED":
        lines.append("Eligible for Level 1 (Controlled).")
        lines.append("Keep current limits for the next cycle.")
    else:
        lines.append("Stay at current level.")

    lines.extend([
        "",
        "## 5. Important",
        "**Limits will NOT be changed automatically.** Recommendation only.",
        "",
        "---",
        f"Evaluated at {measured_at}",
        "",
    ])

    args.output.write_text("\n".join(lines), encoding="utf-8")

    print(f"✓ Expansion evaluation: {recommendation}")
    print(f"✓ Successful cycles: {successful_cycles}")
    print(f"✓ Action required cycles: {action_required_cycles}")
    print(f"✓ Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
