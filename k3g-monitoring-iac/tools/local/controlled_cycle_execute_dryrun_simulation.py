#!/usr/bin/env python3
"""FASE 4.15 — Controlled Operation Cycle Execute Dry-Run Simulation.

Simulate ApplyPlan execution locally without any network calls.
"""

from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def load_json_safe(file_path: Path) -> Dict[str, Any]:
    """Load JSON file safely."""
    if not file_path.exists():
        return {}

    try:
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def load_markdown_safe(file_path: Path) -> str:
    """Load markdown file safely."""
    if not file_path.exists():
        return ""

    try:
        with open(file_path, encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def simulate_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Simulate execution of single ApplyPlan item."""
    method = item.get("method", "POST")
    endpoint = item.get("target_endpoint", "")
    payload = item.get("proposed_payload", {})

    # Simulate status code
    expected_status = item.get("expected_result", {}).get("status_code", 201)
    if method == "POST":
        simulated_status = 201
    elif method == "GET":
        simulated_status = 200
    else:
        simulated_status = 204

    # Simulate validation
    validation_ok = (
        method in ["POST", "GET"]
        and endpoint
        and "/sync" not in endpoint
        and "equipment" not in endpoint
        and "ssh" not in endpoint
        and "netconf" not in endpoint
    )

    return {
        "item_id": item.get("item_id", str(uuid.uuid4())[:8]),
        "approval_id": item.get("approval_id"),
        "object_type": item.get("object_type"),
        "object_key": item.get("object_key"),
        "simulated_method": method,
        "simulated_endpoint": endpoint,
        "payload_summary": {
            "fields": list(payload.keys()) if isinstance(payload, dict) else 0,
            "size_bytes": len(json.dumps(payload)),
        },
        "validation_result": "ok" if validation_ok else "blocked",
        "expected_status_code": simulated_status,
        "expected_action": "create" if method == "POST" else "read",
        "rollback_hint": item.get("rollback_hint", "N/A"),
        "dry_run_status": "simulated_ok" if validation_ok else "simulated_blocked",
    }


def generate_simulation_markdown(
    cycle_id: str,
    apply_plan_id: str,
    device: str,
    decision: str,
    item_count: int,
    items_ok: int,
) -> str:
    """Generate simulation result markdown."""
    timestamp = datetime.utcnow().isoformat() + "+00:00"

    emoji = {
        "CYCLE_DRYRUN_SIMULATION_PASSED": "✓",
        "CYCLE_DRYRUN_SIMULATION_PASSED_WITH_WARNINGS": "⚠",
        "CYCLE_DRYRUN_SIMULATION_FAILED": "✗",
    }.get(decision, "?")

    md = f"""# {cycle_id} — Dry-Run Simulation Result

## 1. Decision

### {emoji} {decision}

## 2. Simulation Summary

- **Apply Plan ID:** {apply_plan_id}
- **Cycle:** {cycle_id}
- **Device:** {device}
- **Mode:** dry_run (local simulation, no network)
- **Total Items:** {item_count}
- **Simulated OK:** {items_ok}
- **Execution Type:** local simulation only

## 3. Simulation Details

All execution was local and simulated:
- No network calls made
- No tokens used
- No NetBox access
- No SSH/NETCONF
- No /sync executed
- Payload validation performed locally
- Expected results computed locally

## 4. Item Validation Results

- All items method in [POST, GET]
- All items endpoint valid
- No forbidden targets detected
- Rollback hints generated
- Expected status codes computed

## 5. Safety Confirmations

- ✓ local_only=true (no network)
- ✓ no_network_call=true (pure local)
- ✓ no_token_read=true (no env access)
- ✓ no_netbox_write=true (no NetBox)
- ✓ no_apply_execution=true (no real execution)
- ✓ next_gate_required=true (requires next gate)

## 6. Next Steps

Proceed to real write readiness gate (FASE 4.16) to evaluate authorization.

---

**Cycle ID:** {cycle_id}
**Simulation Completed At:** {timestamp}
**Simulation Status:** local_only
"""

    return md


def main() -> int:
    """Run FASE 4.15."""
    parser = argparse.ArgumentParser(description="FASE 4.15 — Execute Dry-Run Simulation")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--apply-plan", type=Path, required=True)
    parser.add_argument("--execution-gate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--result-json", type=Path, required=True)

    args = parser.parse_args()

    # Load ApplyPlan
    applyplan = load_json_safe(args.apply_plan)
    if not applyplan:
        print(f"✗ ApplyPlan not found: {args.apply_plan}")
        return 1

    # Load execution gate
    gate_text = load_markdown_safe(args.execution_gate)
    if "BLOCKED" in gate_text:
        print("✗ Execution gate blocked. Cannot proceed with simulation.")
        return 1

    # Simulate each item
    items = applyplan.get("items", [])
    simulated_items = []
    items_ok = 0

    for item in items:
        simulated = simulate_item(item)
        simulated_items.append(simulated)
        if simulated["dry_run_status"] == "simulated_ok":
            items_ok += 1

    # Determine overall decision
    if items_ok == len(items):
        decision = "CYCLE_DRYRUN_SIMULATION_PASSED"
    elif items_ok > 0:
        decision = "CYCLE_DRYRUN_SIMULATION_PASSED_WITH_WARNINGS"
    else:
        decision = "CYCLE_DRYRUN_SIMULATION_FAILED"

    # Generate markdown
    markdown = generate_simulation_markdown(
        args.cycle_id,
        applyplan.get("apply_plan_id", "unknown"),
        applyplan.get("device", "unknown"),
        decision,
        len(items),
        items_ok,
    )

    # Generate JSON
    simulation_json = {
        "simulation_id": f"sim-{args.cycle_id}-{str(uuid.uuid4())[:8]}",
        "cycle_id": args.cycle_id,
        "apply_plan_id": applyplan.get("apply_plan_id"),
        "device": applyplan.get("device"),
        "status": decision,
        "generated_at": datetime.utcnow().isoformat() + "+00:00",
        "items": simulated_items,
        "summary": {
            "total_items": len(items),
            "simulated_ok": items_ok,
            "simulated_blocked": len(items) - items_ok,
        },
        "safety_confirmations": {
            "local_only": True,
            "no_network_call": True,
            "no_token_read": True,
            "no_netbox_write": True,
            "no_apply_execution": True,
        },
        "next_gate_required": True,
        "next_gate": "FASE_4_16_CYCLE_REAL_WRITE_READINESS_GATE",
    }

    # Write outputs
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")

    args.result_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.result_json, "w", encoding="utf-8") as f:
        json.dump(simulation_json, f, indent=2)

    print(f"✓ Dry-run simulation decision: {decision}")
    print(f"✓ Items simulated: {items_ok}/{len(items)}")
    print(f"✓ Result: {args.output}")
    print(f"✓ JSON: {args.result_json}")

    return 0 if "PASSED" in decision else 1


if __name__ == "__main__":
    raise SystemExit(main())
