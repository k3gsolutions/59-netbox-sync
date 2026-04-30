#!/usr/bin/env python3
"""FASE 4.58 - Final no-write freeze check."""

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
    p.add_argument("--cycle-id", required=True)
    p.add_argument("--execution-package", type=Path, required=True)
    p.add_argument("--package-validation", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--output-json", type=Path, required=True)
    args = p.parse_args()

    package = load(args.execution_package)
    validation = load(args.package_validation)
    issues = []
    if s(validation.get("decision")) not in {"CYCLE_REAL_WRITE_EXECUTION_PACKAGE_VALID", "CYCLE_REAL_WRITE_EXECUTION_PACKAGE_VALID_WITH_WARNINGS"}:
        issues.append("package validation not ready")
    if package.get("execution_allowed") is not False:
        issues.append("execution_allowed must be false")
    if not s(package.get("required_execution_phrase")):
        issues.append("required_execution_phrase missing")
    secret_text = json.dumps(package).lower()
    secret_terms = [
        "netbox_write_token",
        "\"token\":",
        "\"password\":",
        "\"secret\":",
        "\"api_key\":",
        "\"private key\":",
        "\"bearer\":",
        "\"authorization\":",
        "authorization: token",
        "token=",
        "password=",
        "secret=",
        "api_key=",
        "bearer ",
        "/sync",
        "applied",
    ]
    if any(term in secret_text for term in secret_terms):
        issues.append("forbidden keyword found")
    if package.get("safety_confirmations", {}).get("no_write_executed") is not True:
        issues.append("no_write_executed must be true")
    if package.get("safety_confirmations", {}).get("no_token_read") is not True:
        issues.append("no_token_read must be true")
    if package.get("safety_confirmations", {}).get("no_network_call") is not True:
        issues.append("no_network_call must be true")

    decision = "CYCLE_READY_FOR_REAL_WRITE_PHASE" if not issues else "CYCLE_READY_WITH_RESTRICTIONS"
    if any("forbidden keyword" in i for i in issues) or any("must be false" in i for i in issues):
        decision = "CYCLE_NOT_READY_FOR_REAL_WRITE_PHASE"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join([
        f"# {args.cycle_id.upper()} Final No-Write Freeze Check",
        "",
        f"## Decision: {decision}",
        "",
        f"- execution_package: {args.execution_package.name}",
        f"- package_validation: {args.package_validation.name}",
        "",
        "## Issues",
    ] + ([f"- {i}" for i in issues] if issues else ["- none"]) + [
        "",
        "## Safety",
        "- No NetBox write",
        "- No /sync",
        "- No token",
    ]), encoding="utf-8")
    payload = {
        "cycle_id": args.cycle_id,
        "decision": decision,
        "issues": issues,
        "no_write_executed": True,
        "no_token_read": True,
        "no_network_call": True,
        "no_netbox_write": True,
        "no_apply_plan_created": True,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    status_file = args.output.parent.parent / "CYCLE-002-STATUS.md"
    status_file.write_text(f"# CYCLE-002\n\nStatus: {decision}\n", encoding="utf-8")
    print(f"✓ Final no-write freeze: {decision}")
    return 0 if decision.startswith("CYCLE_READY") else 1


if __name__ == "__main__":
    raise SystemExit(main())
