#!/usr/bin/env python3
"""FASE 4.57 - Validate real write execution package."""

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
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--output-json", type=Path, required=True)
    args = p.parse_args()

    package = load(args.execution_package)
    issues = []
    if s(package.get("cycle_id")) != "cycle-002":
        issues.append("cycle_id mismatch")
    if s(package.get("status")) != "prepared":
        issues.append("status must be prepared")
    if package.get("execution_allowed") is not False:
        issues.append("execution_allowed must be false")
    if package.get("token_required_in_next_phase") is not True:
        issues.append("token_required_in_next_phase must be true")
    if package.get("explicit_confirm_required") is not True:
        issues.append("explicit_confirm_required must be true")
    if package.get("one_shot_execution") is not True:
        issues.append("one_shot_execution must be true")
    if not s(package.get("required_execution_phrase")):
        issues.append("required_execution_phrase required")
    if s(package.get("required_next_phase")) != "FASE_4_59_CYCLE002_EXECUTE_REAL_WRITE_ONCE":
        issues.append("required_next_phase mismatch")
    if len(package.get("items") or []) == 0:
        issues.append("items required")
    if int(package.get("max_items") or 0) > 3:
        issues.append("max_items must be <= 3")
    if any(term in json.dumps(package).lower() for term in ["token=", "password=", "secret=", "api_key", "private key", "bearer", "applied"]):
        issues.append("secret/applied keyword found")
    for item in package.get("items") or []:
        if s(item.get("method")) != "POST":
            issues.append(f"{item.get('approval_id')}: method must be POST")
        for key in ["target_endpoint", "proposed_payload", "rollback_hint", "expected_result", "pre_write_checks", "post_write_checks"]:
            if not item.get(key):
                issues.append(f"{item.get('approval_id')}: missing {key}")
        if any(term in json.dumps(item).lower() for term in ["token=", "password=", "secret=", "api_key", "private key", "bearer", "applied"]):
            issues.append(f"{item.get('approval_id')}: secret/applied keyword found")

    decision = "CYCLE_REAL_WRITE_EXECUTION_PACKAGE_VALID" if not issues else "CYCLE_REAL_WRITE_EXECUTION_PACKAGE_VALID_WITH_WARNINGS"
    if any("must be" in issue for issue in issues):
        decision = "CYCLE_REAL_WRITE_EXECUTION_PACKAGE_INVALID"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join([
        f"# {args.cycle_id.upper()} Real Write Execution Package Validation",
        "",
        f"## Decision: {decision}",
        "",
        f"- execution_package: {args.execution_package.name}",
        f"- items: {len(package.get('items') or [])}",
        "",
        "## Issues",
    ] + ([f"- {i}" for i in issues] if issues else ["- none"]) + [
        "",
        "## Safety",
        "- No NetBox write",
        "- No token",
        "- No ApplyPlan execution",
    ]), encoding="utf-8")
    payload = {
        "cycle_id": args.cycle_id,
        "decision": decision,
        "issues": issues,
        "execution_package": args.execution_package.name,
        "no_netbox_write": True,
        "no_apply_execution": True,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"✓ Execution package validation: {decision}")
    return 0 if decision.startswith("CYCLE_REAL_WRITE_EXECUTION_PACKAGE_VALID") else 1


if __name__ == "__main__":
    raise SystemExit(main())
