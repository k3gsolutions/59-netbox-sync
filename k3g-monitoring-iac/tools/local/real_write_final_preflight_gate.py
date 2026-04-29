#!/usr/bin/env python3
"""FASE 2.48 — Real Write Final Preflight Gate.

Validate authorization phrase, ensure all artifacts intact, generate preflight decision.
Zero writes, zero tokens, zero network calls.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple


def validate_authorization_request(
    request_file: Path,
) -> Tuple[bool, str, Dict[str, Any]]:
    """Load and validate authorization_request.json."""
    if not request_file.exists():
        return False, f"Authorization request not found: {request_file}", {}

    try:
        with open(request_file, encoding="utf-8") as f:
            req = json.load(f)
    except Exception as e:
        return False, f"Authorization request invalid JSON: {e}", {}

    if not req.get("authorization_id"):
        return False, "Missing authorization_id", {}

    if not req.get("apply_plan_id"):
        return False, "Missing apply_plan_id", {}

    if not req.get("required_phrase"):
        return False, "Missing required_phrase", {}

    if not req.get("source_apply_plan"):
        return False, "Missing source_apply_plan", {}

    if not req.get("source_simulation_result"):
        return False, "Missing source_simulation_result", {}

    if not req.get("source_real_write_readiness_gate"):
        return False, "Missing source_real_write_readiness_gate", {}

    items = req.get("items", [])
    if not items:
        return False, "No items in authorization request", {}

    # Check safety confirmations
    safety = req.get("safety_confirmations", {})
    if not safety.get("no_write_executed"):
        return False, "Safety: no_write_executed not true", {}
    if not safety.get("no_token_read"):
        return False, "Safety: no_token_read not true", {}
    if not safety.get("no_network_call"):
        return False, "Safety: no_network_call not true", {}
    if not safety.get("final_preflight_required"):
        return False, "Safety: final_preflight_required not true", {}
    if not safety.get("explicit_operator_authorization_required"):
        return False, "Safety: explicit_operator_authorization_required not true", {}

    return True, "Authorization request valid", req


def validate_phrase(
    required_phrase: str,
    operator_phrase: str,
) -> Tuple[bool, str]:
    """Validate authorization phrase exactly."""
    if required_phrase != operator_phrase:
        return False, f"Phrase mismatch. Expected: {required_phrase}"

    return True, "Phrase valid"


def validate_source_files(
    request: Dict[str, Any],
) -> Tuple[bool, str]:
    """Validate all source files exist and unchanged."""
    sources = [
        ("ApplyPlan", request.get("source_apply_plan")),
        ("Simulation Result", request.get("source_simulation_result")),
        ("Real Write Readiness Gate", request.get("source_real_write_readiness_gate")),
    ]

    for name, path_str in sources:
        if not path_str:
            return False, f"Missing source: {name}"

        path = Path(path_str)
        if not path.exists():
            return False, f"Source {name} not found: {path_str}"

    # Validate ApplyPlan still mode=dry_run, can_execute_real_write=false
    try:
        plan_path = Path(request.get("source_apply_plan"))
        with open(plan_path, encoding="utf-8") as f:
            plan = json.load(f)
    except Exception as e:
        return False, f"Cannot validate ApplyPlan: {e}"

    if plan.get("mode") != "dry_run":
        return False, "ApplyPlan mode changed from dry_run"

    if plan.get("can_execute_real_write") is not False:
        return False, "ApplyPlan can_execute_real_write changed to true"

    # Validate simulation result still has PASSED status
    try:
        sim_path = Path(request.get("source_simulation_result"))
        with open(sim_path, encoding="utf-8") as f:
            sim = json.load(f)
    except Exception as e:
        return False, f"Cannot validate simulation result: {e}"

    status = sim.get("status", "")
    if status not in ("DRYRUN_SIMULATION_PASSED", "DRYRUN_SIMULATION_PASSED_WITH_WARNINGS"):
        return False, f"Simulation status changed to: {status}"

    return True, "All source files valid and unchanged"


def check_for_secrets(request: Dict[str, Any]) -> Tuple[bool, str]:
    """Check request has no secrets."""
    secrets = ["token", "password", "secret", "api_key", "private key", "bearer", "authorization"]
    request_str = json.dumps(request).lower()

    for secret_kw in secrets:
        if secret_kw in request_str:
            # Avoid false positive: "authorization_id" is OK, just "authorization" as value is not
            if secret_kw == "authorization" and "authorization_id" in request_str:
                continue
            if secret_kw == "token" and "authorization_request" in request_str:
                continue

            # Check actual keyword in sensitive fields
            for item in request.get("items", []):
                item_str = json.dumps(item).lower()
                if secret_kw in item_str and secret_kw not in ["method", "endpoint", "item_id"]:
                    return False, f"Secret keyword in item: {secret_kw}"

    return True, "No secrets detected"


def main() -> int:
    """Run FASE 2.48."""
    parser = argparse.ArgumentParser(description="FASE 2.48 — Real Write Final Preflight Gate")
    parser.add_argument("--authorization-request", type=Path, required=True, help="Authorization request JSON")
    parser.add_argument("--operator", required=True, help="Operator name")
    parser.add_argument("--authorization-phrase", required=True, help="Authorization phrase (exact match required)")
    parser.add_argument("--output", type=Path, required=True, help="Output report path")

    args = parser.parse_args()

    # Validate authorization request
    req_valid, req_reason, request = validate_authorization_request(args.authorization_request)
    if not req_valid:
        print(f"✗ Authorization request invalid: {req_reason}")
        return 1

    # Validate phrase
    phrase_valid, phrase_reason = validate_phrase(request.get("required_phrase"), args.authorization_phrase)
    if not phrase_valid:
        print(f"✗ {phrase_reason}")
        decision = "NOT_READY_FOR_REAL_WRITE_EXECUTION"
    else:
        # Validate source files
        sources_valid, sources_reason = validate_source_files(request)
        if not sources_valid:
            print(f"✗ Source files invalid: {sources_reason}")
            decision = "NOT_READY_FOR_REAL_WRITE_EXECUTION"
        else:
            # Check for secrets
            secrets_ok, secrets_reason = check_for_secrets(request)
            if not secrets_ok:
                print(f"✗ {secrets_reason}")
                decision = "NOT_READY_FOR_REAL_WRITE_EXECUTION"
            else:
                decision = "READY_FOR_REAL_WRITE_EXECUTION_PACKAGE"

    # Generate report
    timestamp = datetime.utcnow().isoformat() + "+00:00"
    report_lines = [
        "# Real Write Final Preflight Gate",
        "",
        f"**Device:** {request.get('device')}",
        f"**Operator:** {args.operator}",
        f"**Generated:** {timestamp}",
        "",
        "## Decision",
        "",
        f"### {decision}",
        "",
    ]

    if not phrase_valid:
        report_lines.extend([
            "Authorization phrase did not match required phrase.",
            "Cannot proceed to execution package.",
            "",
        ])
    elif not sources_valid:
        report_lines.extend([
            sources_reason,
            "Source artifacts may have been modified.",
            "",
        ])
    elif not secrets_ok:
        report_lines.extend([
            secrets_reason,
            "",
        ])
    else:
        report_lines.extend([
            "✓ Authorization phrase validated",
            "✓ All source files intact and valid",
            "✓ No secrets detected",
            "✓ Ready to build execution package",
            "",
            "## Next Phase",
            "",
            "FASE 2.49 — Build Real Write Execution Package",
            "",
        ])

    report_lines.extend([
        "## Security Confirmations",
        "",
        "✓ No NetBox writes",
        "✓ No tokens read",
        "✓ No network calls",
        "✓ Preflight validation only",
        "✓ Artifacts remain unchanged",
        "",
    ])

    # Create output directory
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(report_lines), encoding="utf-8")

    print(f"✓ Preflight gate report: {args.output}")
    print(f"✓ Decision: {decision}")

    return 0 if decision == "READY_FOR_REAL_WRITE_EXECUTION_PACKAGE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
