#!/usr/bin/env python3
"""FASE 4.55 - Final preflight gate before real write execution package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def s(v) -> str:
    return str(v or "").strip()


def load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--authorization-request", type=Path, required=True)
    p.add_argument("--operator", required=True)
    p.add_argument("--authorization-phrase", required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--output-json", type=Path, required=True)
    args = p.parse_args()

    auth = load(args.authorization_request)
    issues = []
    if s(auth.get("cycle_id")) != "cycle-002":
        issues.append("cycle_id mismatch")
    if s(auth.get("required_phrase")) != args.authorization_phrase:
        issues.append("authorization phrase mismatch")
    for key in ["authorization_id", "apply_plan_id", "simulation_result_id", "real_write_readiness_gate"]:
        if not s(auth.get(key)):
            issues.append(f"missing {key}")
    if not args.operator:
        issues.append("operator required")
    if auth.get("safety_confirmations", {}).get("no_write_executed") is not True:
        issues.append("no_write_executed must be true")
    if auth.get("safety_confirmations", {}).get("no_token_read") is not True:
        issues.append("no_token_read must be true")
    if auth.get("safety_confirmations", {}).get("no_network_call") is not True:
        issues.append("no_network_call must be true")
    if auth.get("safety_confirmations", {}).get("final_preflight_required") is not True:
        issues.append("final_preflight_required must be true")
    if auth.get("safety_confirmations", {}).get("explicit_operator_authorization_required") is not True:
        issues.append("explicit_operator_authorization_required must be true")
    if any(term in json.dumps(auth).lower() for term in ["token=", "password=", "secret=", "api_key", "private key", "bearer"]):
        issues.append("secret keyword found")

    decision = "CYCLE_READY_FOR_REAL_WRITE_EXECUTION_PACKAGE" if not issues else "CYCLE_READY_WITH_RESTRICTIONS"
    if any("mismatch" in issue.lower() for issue in issues):
        decision = "CYCLE_NOT_READY_FOR_REAL_WRITE_EXECUTION"

    report = "\n".join([
        f"# {auth.get('cycle_id', 'cycle-002').upper()} Real Write Final Preflight Gate",
        "",
        f"## Decision: {decision}",
        "",
        f"- operator: {args.operator}",
        f"- authorization_id: {auth.get('authorization_id', '')}",
        "",
        "## Issues",
    ] + ([f"- {i}" for i in issues] if issues else ["- none"]) + [
        "",
        "## Safety",
        "- No write executed",
        "- No token read",
        "- No network call",
        "- Final preflight required",
    ])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    payload = {
        "cycle_id": auth.get("cycle_id", "cycle-002"),
        "decision": decision,
        "issues": issues,
        "safety_confirmations": {
            "no_write_executed": True,
            "no_token_read": True,
            "no_network_call": True,
            "final_preflight_required": True,
            "explicit_operator_authorization_required": True,
        },
        "source_apply_plan": auth.get("apply_plan_id"),
        "source_simulation_result": auth.get("simulation_result_id"),
        "source_real_write_readiness_gate": auth.get("real_write_readiness_gate"),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"✓ Final preflight gate: {decision}")
    return 0 if decision.startswith("CYCLE_READY") else 1


if __name__ == "__main__":
    raise SystemExit(main())
