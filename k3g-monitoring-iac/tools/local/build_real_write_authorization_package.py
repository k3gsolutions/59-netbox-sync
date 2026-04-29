#!/usr/bin/env python3
"""FASE 2.47 — Real Write Authorization Package.

Build authorization package for real write. Validates readiness gate,
consolidates evidence, generates authorization phrase. Zero writes, zero tokens.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple
from uuid import uuid4


def validate_readiness_gate(gate_file: Path) -> Tuple[str, str]:
    """Validate real-write-readiness-gate.md decision."""
    if not gate_file.exists():
        return "BLOCKED", f"Gate file missing: {gate_file}"

    try:
        content = gate_file.read_text(encoding="utf-8")
    except Exception as e:
        return "BLOCKED", f"Cannot read gate: {e}"

    # Extract decision from markdown heading
    if "### READY_FOR_REAL_WRITE_REVIEW" in content:
        return "AUTHORIZED_PACKAGE_READY", "Gate approved for real write review"
    elif "### READY_WITH_RESTRICTIONS" in content:
        return "READY_WITH_RESTRICTIONS", "Approved with restrictions"
    elif "### NOT_READY_FOR_REAL_WRITE" in content:
        return "BLOCKED", "Gate decision: NOT_READY_FOR_REAL_WRITE"
    else:
        return "BLOCKED", "No decision found in gate"


def validate_apply_plan(plan_file: Path) -> Tuple[bool, str]:
    """Validate ApplyPlan structure."""
    if not plan_file.exists():
        return False, f"ApplyPlan not found: {plan_file}"

    try:
        with open(plan_file, encoding="utf-8") as f:
            plan = json.load(f)
    except Exception as e:
        return False, f"ApplyPlan invalid JSON: {e}"

    if plan.get("mode") != "dry_run":
        return False, f"Mode is {plan.get('mode')}, not dry_run"

    if plan.get("can_execute_real_write") is not False:
        return False, "can_execute_real_write is not false"

    if plan.get("requires_next_gate") is not True:
        return False, "requires_next_gate is not true"

    items = plan.get("items", [])
    if not items:
        return False, "No items in ApplyPlan"

    for item in items:
        if not item.get("approval_id"):
            return False, f"Item missing approval_id"
        if not item.get("proposed_payload"):
            return False, f"Item {item.get('approval_id')} missing payload"
        if not item.get("rollback_hint"):
            return False, f"Item {item.get('approval_id')} missing rollback_hint"

    return True, "ApplyPlan valid"


def validate_simulation_result(result_file: Path) -> Tuple[bool, str]:
    """Validate simulation result."""
    if not result_file.exists():
        return False, f"Simulation result not found: {result_file}"

    try:
        with open(result_file, encoding="utf-8") as f:
            result = json.load(f)
    except Exception as e:
        return False, f"Simulation result invalid JSON: {e}"

    status = result.get("status", "")
    if status not in ("DRYRUN_SIMULATION_PASSED", "DRYRUN_SIMULATION_PASSED_WITH_WARNINGS"):
        return False, f"Simulation status is {status}, not PASSED/WITH_WARNINGS"

    if not result.get("simulation_id"):
        return False, "No simulation_id"

    items = result.get("items", [])
    if not items:
        return False, "No items in simulation"

    return True, "Simulation result valid"


def validate_approved_records(
    approved_dir: Path,
    plan: Dict[str, Any],
) -> Tuple[bool, str, list]:
    """Validate all source approval records exist and are approved."""
    if not approved_dir.exists():
        return False, f"Approved dir not found: {approved_dir}", []

    source_ids = set()
    for item in plan.get("items", []):
        source_ids.add(item.get("approval_id"))

    found_records = []
    for approval_id in source_ids:
        found = False
        for record_file in approved_dir.glob("approval-record-*.json"):
            try:
                with open(record_file, encoding="utf-8") as f:
                    record = json.load(f)
            except Exception:
                continue

            if record.get("approval_record_id") == approval_id:
                # Validate it's approved
                if record.get("status") != "approved":
                    return False, f"Record {approval_id} status is {record.get('status')}, not approved", []

                if not record.get("approved_by"):
                    return False, f"Record {approval_id} missing approved_by", []

                if not record.get("approved_at"):
                    return False, f"Record {approval_id} missing approved_at", []

                # Check state_history
                state_history = record.get("state_history", [])
                states = [s.get("to", "").lower() for s in state_history if isinstance(s, dict)]
                if "approved_for_dry_run_applyplan" not in states:
                    return False, f"Record {approval_id} missing approved_for_dry_run_applyplan transition", []

                found_records.append({
                    "approval_id": approval_id,
                    "object_type": record.get("object_type"),
                    "object_key": record.get("object_key"),
                    "approved_by": record.get("approved_by"),
                })
                found = True
                break

        if not found:
            return False, f"Approval record {approval_id} not found in {approved_dir}", []

    return True, "All approval records valid", found_records


def check_for_secrets(plan: Dict[str, Any]) -> Tuple[bool, str]:
    """Check for secrets in payloads."""
    secrets = ["token", "password", "secret", "api_key", "private key", "bearer", "authorization"]

    for item in plan.get("items", []):
        payload = item.get("proposed_payload", {})
        payload_str = json.dumps(payload).lower()
        for secret_kw in secrets:
            if secret_kw in payload_str:
                return False, f"Secret keyword in item {item.get('approval_id')}: {secret_kw}"

    return True, "No secrets detected"


def generate_authorization_phrase(device: str, apply_plan_id: str) -> str:
    """Generate authorization phrase."""
    return f"AUTORIZO_PRE_FLIGHT_ESCRITA_REAL_{device}_{apply_plan_id}"


def main() -> int:
    """Run FASE 2.47."""
    parser = argparse.ArgumentParser(description="FASE 2.47 — Real Write Authorization Package")
    parser.add_argument("--device", required=True, help="Device name")
    parser.add_argument("--device-id", required=True, type=int, help="Device ID")
    parser.add_argument("--apply-plan", type=Path, required=True, help="ApplyPlan JSON")
    parser.add_argument("--simulation-result", type=Path, required=True, help="Simulation result JSON")
    parser.add_argument("--real-write-readiness-gate", type=Path, required=True, help="Readiness gate markdown")
    parser.add_argument("--approved-dir", type=Path, required=True, help="Approved records directory")
    parser.add_argument("--output-dir", type=Path, required=True, help="Output directory")
    parser.add_argument("--report", type=Path, help="Report path (default: {output_dir}/REAL-WRITE-AUTHORIZATION-PACKAGE.md)")

    args = parser.parse_args()

    # Set report path
    report_path = args.report or (args.output_dir / "REAL-WRITE-AUTHORIZATION-PACKAGE.md")

    # Validate gate
    gate_status, gate_reason = validate_readiness_gate(args.real_write_readiness_gate)
    if gate_status == "BLOCKED":
        print(f"✗ Authorization blocked: {gate_reason}")
        report_lines = [
            "# Real Write Authorization Package",
            "",
            f"**Device:** {args.device} (ID: {args.device_id})",
            f"**Generated:** {datetime.utcnow().isoformat()}+00:00",
            "",
            "## Decision",
            "",
            "### BLOCKED",
            gate_reason,
            "",
        ]
        args.output_dir.mkdir(parents=True, exist_ok=True)
        report_path.write_text("\n".join(report_lines), encoding="utf-8")
        return 1

    # Load ApplyPlan
    try:
        with open(args.apply_plan, encoding="utf-8") as f:
            plan = json.load(f)
    except Exception as e:
        print(f"✗ Cannot load ApplyPlan: {e}")
        return 1

    apply_plan_id = plan.get("apply_plan_id")

    # Validate ApplyPlan
    plan_valid, plan_reason = validate_apply_plan(args.apply_plan)
    if not plan_valid:
        print(f"✗ ApplyPlan invalid: {plan_reason}")
        return 1

    # Validate simulation
    sim_valid, sim_reason = validate_simulation_result(args.simulation_result)
    if not sim_valid:
        print(f"✗ Simulation result invalid: {sim_reason}")
        return 1

    # Load simulation
    with open(args.simulation_result, encoding="utf-8") as f:
        simulation = json.load(f)

    # Validate approved records
    records_valid, records_reason, found_records = validate_approved_records(args.approved_dir, plan)
    if not records_valid:
        print(f"✗ Approved records invalid: {records_reason}")
        return 1

    # Check for secrets
    secrets_ok, secrets_reason = check_for_secrets(plan)
    if not secrets_ok:
        print(f"✗ {secrets_reason}")
        return 1

    # Generate authorization ID and phrase
    authorization_id = str(uuid4())
    required_phrase = generate_authorization_phrase(args.device, apply_plan_id)

    # Create authorization_request.json
    authorization_request = {
        "authorization_id": authorization_id,
        "device": args.device,
        "device_id": args.device_id,
        "apply_plan_id": apply_plan_id,
        "package_status": gate_status,
        "required_phrase": required_phrase,
        "generated_at": datetime.utcnow().isoformat() + "+00:00",
        "source_apply_plan": str(args.apply_plan),
        "source_simulation_result": str(args.simulation_result),
        "source_real_write_readiness_gate": str(args.real_write_readiness_gate),
        "approved_records": found_records,
        "items": [
            {
                "item_id": item.get("item_id"),
                "approval_id": item.get("approval_id"),
                "object_type": item.get("object_type"),
                "object_key": item.get("object_key"),
                "method": item.get("method"),
                "endpoint": item.get("target_endpoint"),
                "expected_result": item.get("expected_result"),
                "rollback": item.get("rollback_hint"),
            }
            for item in plan.get("items", [])
        ],
        "safety_confirmations": {
            "no_write_executed": True,
            "no_token_read": True,
            "no_network_call": True,
            "final_preflight_required": True,
            "explicit_operator_authorization_required": True,
        },
        "next_phase": "FASE_2_48_REAL_WRITE_FINAL_PREFLIGHT_GATE",
    }

    # Generate report
    timestamp = datetime.utcnow().isoformat() + "+00:00"
    report_lines = [
        "# Real Write Authorization Package",
        "",
        f"**Device:** {args.device} (ID: {args.device_id})",
        f"**Generated:** {timestamp}",
        "",
        "## 1. Status",
        "",
        f"### {gate_status}",
        gate_reason,
        "",
        "## 2. Executive Summary",
        "",
        f"- Device: {args.device}",
        f"- Device ID: {args.device_id}",
        f"- Apply Plan ID: {apply_plan_id}",
        f"- Total items: {len(plan.get('items', []))}",
        f"- Simulation result: {simulation.get('status')}",
        f"- Real write readiness gate: {gate_status}",
        "",
        "## 3. Evidence Chain",
        "",
        "| Phase | Artifact | Status |",
        "|---|---|---|",
        f"| ApprovalRecords approved | {args.approved_dir} | OK |",
        f"| ApplyPlan dry-run | {args.apply_plan} | OK |",
        f"| Validation ApplyPlan | (via readiness gate) | OK |",
        f"| Dry-run execution gate | (via readiness gate) | OK |",
        f"| Dry-run simulation | {args.simulation_result} | {simulation.get('status')} |",
        f"| Real write readiness gate | {args.real_write_readiness_gate} | {gate_status} |",
        "",
        "## 4. Proposed Items for Future Real Write",
        "",
        "| Item ID | Approval ID | Object Type | Object Key | Method | Endpoint | Expected Result | Rollback |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for item in plan.get("items", []):
        report_lines.append(
            f"| {item.get('item_id')} | {item.get('approval_id')} | "
            f"{item.get('object_type')} | {item.get('object_key')} | "
            f"{item.get('method')} | {item.get('target_endpoint')} | "
            f"{item.get('expected_result')} | {item.get('rollback_hint')} |"
        )

    report_lines.extend([
        "",
        "## 5. Human Authorization Checklist",
        "",
        "- [ ] Review all items.",
        "- [ ] Confirm operational window.",
        "- [ ] Confirm responsible operator.",
        "- [ ] Confirm rollback strategy.",
        "- [ ] Confirm token will be provided only in execution phase.",
        "- [ ] Confirm no out-of-scope changes.",
        "- [ ] Confirm one-shot audited execution.",
        "",
        "## 6. Required Authorization Phrase",
        "",
        "Use this phrase exactly in next gate (FASE 2.48):",
        "",
        f"```\n{required_phrase}\n```",
        "",
        "## 7. Security Confirmations",
        "",
        "✓ No NetBox writes",
        "✓ No tokens read",
        "✓ No network calls",
        "✓ Package consolidates evidence only",
        "✓ No automatic progression",
        "",
    ])

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Write authorization_request.json
    auth_request_file = args.output_dir / "authorization_request.json"
    with open(auth_request_file, "w", encoding="utf-8") as f:
        json.dump(authorization_request, f, indent=2)

    # Write report
    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    print(f"✓ Authorization package: {report_path}")
    print(f"✓ Authorization request: {auth_request_file}")
    print(f"✓ Required phrase: {required_phrase}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
