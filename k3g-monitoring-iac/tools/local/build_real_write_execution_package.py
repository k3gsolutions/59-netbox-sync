#!/usr/bin/env python3
"""FASE 2.49 — Build Real Write Execution Package.

Create execution package from validated authorization. Generate execution_package.json
and REAL-WRITE-EXECUTION-PACKAGE.md with command template (no hardcoded token).
Zero writes, zero tokens, zero network calls.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4


def validate_preflight_gate(gate_file: Path) -> tuple[bool, str]:
    """Validate final preflight gate decision."""
    if not gate_file.exists():
        return False, f"Preflight gate not found: {gate_file}"

    try:
        content = gate_file.read_text(encoding="utf-8")
    except Exception as e:
        return False, f"Cannot read preflight gate: {e}"

    if "### READY_FOR_REAL_WRITE_EXECUTION_PACKAGE" in content:
        return True, "Preflight gate approved"
    elif "### READY_WITH_RESTRICTIONS" in content:
        return True, "Preflight gate approved with restrictions"
    else:
        return False, "Preflight gate decision not READY"


def load_authorization_request(request_file: Path) -> tuple[bool, str, Dict[str, Any]]:
    """Load authorization request."""
    if not request_file.exists():
        return False, f"Authorization request not found: {request_file}", {}

    try:
        with open(request_file, encoding="utf-8") as f:
            req = json.load(f)
    except Exception as e:
        return False, f"Cannot load authorization request: {e}", {}

    return True, "OK", req


def load_apply_plan(plan_file: Path) -> tuple[bool, str, Dict[str, Any]]:
    """Load ApplyPlan."""
    if not plan_file.exists():
        return False, f"ApplyPlan not found: {plan_file}", {}

    try:
        with open(plan_file, encoding="utf-8") as f:
            plan = json.load(f)
    except Exception as e:
        return False, f"Cannot load ApplyPlan: {e}", {}

    # Verify still dry_run
    if plan.get("mode") != "dry_run":
        return False, "ApplyPlan mode not dry_run", {}

    if plan.get("can_execute_real_write") is not False:
        return False, "can_execute_real_write is not false", {}

    return True, "OK", plan


def load_simulation_result(result_file: Path) -> tuple[bool, str, Dict[str, Any]]:
    """Load simulation result."""
    if not result_file.exists():
        return False, f"Simulation result not found: {result_file}", {}

    try:
        with open(result_file, encoding="utf-8") as f:
            sim = json.load(f)
    except Exception as e:
        return False, f"Cannot load simulation result: {e}", {}

    return True, "OK", sim


def validate_execution_items(
    plan: Dict[str, Any],
) -> tuple[bool, str, list]:
    """Validate items for execution."""
    items = plan.get("items", [])
    if not items:
        return False, "No items in ApplyPlan", []

    execution_items = []
    for item in items:
        # Validate method is POST
        method = item.get("method", "").upper()
        if method != "POST":
            return False, f"Item {item.get('approval_id')} has method {method}, only POST allowed", []

        # Validate endpoint is allowed
        endpoint = item.get("target_endpoint", "")
        forbidden_targets = ["/sync", "equipment", "ssh", "netconf"]
        for forbidden in forbidden_targets:
            if forbidden in endpoint.lower():
                return False, f"Item {item.get('approval_id')} has forbidden target: {endpoint}", []

        # Validate required fields
        if not item.get("approval_id"):
            return False, "Item missing approval_id", []
        if not item.get("object_type"):
            return False, "Item missing object_type", []
        if not item.get("object_key"):
            return False, "Item missing object_key", []
        if not item.get("target_endpoint"):
            return False, "Item missing target_endpoint", []
        if not item.get("proposed_payload"):
            return False, f"Item {item.get('approval_id')} missing payload", []
        if not item.get("rollback_hint"):
            return False, f"Item {item.get('approval_id')} missing rollback_hint", []

        execution_items.append({
            "item_id": item.get("item_id"),
            "approval_id": item.get("approval_id"),
            "object_type": item.get("object_type"),
            "object_key": item.get("object_key"),
            "method": method,
            "endpoint": endpoint,
            "payload": item.get("proposed_payload"),
            "expected_status_code": item.get("expected_result", "201"),
            "rollback_hint": item.get("rollback_hint"),
            "pre_write_checks": [
                "verify_endpoint_syntax",
                "verify_payload_structure",
                "verify_authorization_header",
            ],
            "post_write_checks": [
                "verify_response_status_code",
                "verify_response_has_id",
                "log_created_resource_id",
                "compare_with_expected_result",
            ],
        })

    return True, "OK", execution_items


def generate_execution_phrase(device: str, execution_package_id: str) -> str:
    """Generate execution phrase."""
    return f"EXECUTO_ESCRITA_REAL_{device}_{execution_package_id}"


def main() -> int:
    """Run FASE 2.49."""
    parser = argparse.ArgumentParser(description="FASE 2.49 — Build Real Write Execution Package")
    parser.add_argument("--authorization-request", type=Path, required=True, help="Authorization request JSON")
    parser.add_argument("--final-preflight-gate", type=Path, required=True, help="Final preflight gate markdown")
    parser.add_argument("--apply-plan", type=Path, required=True, help="ApplyPlan JSON")
    parser.add_argument("--simulation-result", type=Path, required=True, help="Simulation result JSON")
    parser.add_argument("--output-dir", type=Path, required=True, help="Output directory")
    parser.add_argument("--report", type=Path, help="Report path (default: {output_dir}/REAL-WRITE-EXECUTION-PACKAGE.md)")

    args = parser.parse_args()

    # Set report path
    report_path = args.report or (args.output_dir / "REAL-WRITE-EXECUTION-PACKAGE.md")

    # Validate preflight gate
    preflight_ok, preflight_reason = validate_preflight_gate(args.final_preflight_gate)
    if not preflight_ok:
        print(f"✗ Preflight gate not ready: {preflight_reason}")
        return 1

    # Load authorization request
    auth_ok, auth_reason, auth_request = load_authorization_request(args.authorization_request)
    if not auth_ok:
        print(f"✗ {auth_reason}")
        return 1

    # Load ApplyPlan
    plan_ok, plan_reason, plan = load_apply_plan(args.apply_plan)
    if not plan_ok:
        print(f"✗ {plan_reason}")
        return 1

    # Load simulation result
    sim_ok, sim_reason, simulation = load_simulation_result(args.simulation_result)
    if not sim_ok:
        print(f"✗ {sim_reason}")
        return 1

    # Validate items
    items_ok, items_reason, execution_items = validate_execution_items(plan)
    if not items_ok:
        print(f"✗ {items_reason}")
        return 1

    # Generate execution package ID and phrase
    execution_package_id = str(uuid4())
    device = auth_request.get("device")
    required_execution_phrase = generate_execution_phrase(device, execution_package_id)

    # Create execution_package.json
    execution_package = {
        "execution_package_id": execution_package_id,
        "device": device,
        "device_id": auth_request.get("device_id"),
        "apply_plan_id": plan.get("apply_plan_id"),
        "authorization_id": auth_request.get("authorization_id"),
        "generated_at": datetime.utcnow().isoformat() + "+00:00",
        "status": "prepared",
        "mode": "real_write_prepared",
        "execution_allowed": False,
        "token_required_in_next_phase": True,
        "explicit_confirm_required": True,
        "one_shot_execution": True,
        "max_items": len(execution_items),
        "items": execution_items,
        "safety_confirmations": {
            "no_write_executed": True,
            "no_token_read": True,
            "no_network_call": True,
            "package_only": True,
            "real_write_not_executed": True,
        },
        "required_next_phase": "FASE_2_53_EXECUTE_REAL_WRITE",
        "required_execution_phrase": required_execution_phrase,
    }

    # Generate report
    timestamp = datetime.utcnow().isoformat() + "+00:00"
    report_lines = [
        "# Real Write Execution Package",
        "",
        f"**Device:** {device}",
        f"**Device ID:** {auth_request.get('device_id')}",
        f"**Generated:** {timestamp}",
        "",
        "## 1. Status",
        "",
        "### PREPARED",
        "",
        "Execution package prepared. **No real write has been executed.**",
        "",
        "## 2. Critical Warning",
        "",
        "This package does NOT execute real write. Execution requires:",
        "- Separate FASE 2.53 execution phase",
        "- Explicit operator authorization",
        "- Exact confirmation phrase",
        "- One-shot execution",
        "",
        "## 3. Prepared Items",
        "",
        "| Item ID | Approval ID | Object Type | Object Key | Method | Endpoint | Expected Status | Rollback |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for item in execution_items:
        report_lines.append(
            f"| {item['item_id']} | {item['approval_id']} | "
            f"{item['object_type']} | {item['object_key']} | "
            f"{item['method']} | {item['endpoint']} | "
            f"{item['expected_status_code']} | {item['rollback_hint']} |"
        )

    report_lines.extend([
        "",
        "## 4. Next Phase Command",
        "",
        "Execute in FASE 2.53 with token from environment variable:",
        "",
        "```bash",
        "export NETBOX_WRITE_TOKEN='your-token-here'",
        "",
        "python3 tools/local/execute_real_write_once.py \\",
        f"  --execution-package {args.output_dir}/execution_package.json \\",
        f"  --operator 'Operator Name' \\",
        f"  --confirm-execution-phrase '{required_execution_phrase}' \\",
        "  --confirm-real-write-once",
        "```",
        "",
        "## 5. Operator Checklist",
        "",
        "Before execution (FASE 2.53):",
        "- [ ] Have token available in environment variable",
        "- [ ] Confirm exact execution phrase",
        "- [ ] Confirm device name and items",
        "- [ ] Confirm operational window",
        "- [ ] Know rollback procedure",
        "- [ ] Operator name will be logged",
        "",
        "## 6. Security Confirmations",
        "",
        "✓ No NetBox writes executed",
        "✓ No tokens read",
        "✓ No network calls made",
        "✓ Package prepared only",
        "✓ Execution blocked (execution_allowed=false)",
        "✓ Token required from environment (FASE 2.53 only)",
        "",
    ])

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Write execution_package.json
    package_file = args.output_dir / "execution_package.json"
    with open(package_file, "w", encoding="utf-8") as f:
        json.dump(execution_package, f, indent=2)

    # Write report
    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    print(f"✓ Execution package: {package_file}")
    print(f"✓ Execution report: {report_path}")
    print(f"✓ Required execution phrase: {required_execution_phrase}")
    print(f"✓ Status: PREPARED (execution_allowed=false)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
