#!/usr/bin/env python3
"""FASE 4.61 - Local read-only compliance re-run after write."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.local.controlled_cycle_real_write_common import has_forbidden_terms, load_json, now_iso, s, summarize_issues, write_json, write_md  # noqa: E402


def _load_registry(registry: Path) -> dict[str, object]:
    payload: dict[str, object] = {}
    if registry.is_file():
        data = yaml.safe_load(registry.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
        return {}
    if registry.is_dir():
        for path in sorted(registry.rglob("*.yaml")):
            payload[path.name] = yaml.safe_load(path.read_text(encoding="utf-8"))
        for path in sorted(registry.rglob("*.yml")):
            payload[path.name] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload


def rerun_compliance(
    *,
    cycle_id: str,
    device: str,
    device_id: str,
    execution_result_path: Path,
    post_write_verification_path: Path,
    policy_registry: Path,
    output_json: Path,
    output_md: Path,
) -> dict[str, object]:
    execution_result = load_json(execution_result_path)
    verification = load_json(post_write_verification_path)
    if s(execution_result.get("status")) == "CYCLE_REAL_WRITE_ABORTED_PREFLIGHT_FAILED":
        payload = {
            "cycle_id": cycle_id,
            "device": device,
            "device_id": device_id,
            "decision": "CYCLE_POST_WRITE_COMPLIANCE_NOT_APPLICABLE",
            "status": "NOT_APPLICABLE",
            "items": [],
            "issues": ["execution aborted preflight"],
            "safety_confirmations": {
                "local_only": True,
                "no_network_call": True,
                "no_token_read": True,
                "no_netbox_write": True,
                "no_apply_execution": True,
            },
        }
        write_json(output_json, payload)
        write_md(output_md, f"# {cycle_id.upper()} Post-Write Compliance Re-Run\n\n## Decision: NOT_APPLICABLE\n\n- execution aborted preflight\n")
        return payload

    issues: list[str] = []
    if has_forbidden_terms(execution_result) or has_forbidden_terms(verification):
        issues.append("secret keyword found")
    if s(execution_result.get("cycle_id")) != cycle_id or s(verification.get("cycle_id")) != cycle_id:
        issues.append("cycle_id mismatch")
    if s(execution_result.get("device")) != device or s(execution_result.get("device_id")) != str(device_id):
        issues.append("device mismatch")
    registry = _load_registry(policy_registry)
    if not registry:
        issues.append("policy registry empty")

    result_items = []
    warnings = False
    # Iterate through verification items (already verified)
    for item in verification.get("items") or []:
        verification_status = s(item.get("verification_status"))
        if verification_status == "verified":
            item_status = "CYCLE_POST_WRITE_COMPLIANCE_OK"
        elif verification_status == "drift":
            item_status = "CYCLE_POST_WRITE_COMPLIANCE_PASSED_WITH_WARNINGS"
            warnings = True
        elif verification_status == "skipped":
            # Item was not verifiable, skip it
            item_status = "CYCLE_POST_WRITE_COMPLIANCE_SKIPPED"
        else:
            item_status = "CYCLE_POST_WRITE_COMPLIANCE_FAILED"
            issues.append(f"{item.get('object_key')}: verification {verification_status}")
        result_items.append(
            {
                "object_key": item.get("object_key"),
                "object_type": item.get("object_type"),
                "verification_status": verification_status,
                "status": item_status,
                "drift_fields": item.get("drift_fields") or [],
                "convention_violations": [],
            }
        )

    decision = "CYCLE_POST_WRITE_COMPLIANCE_PASSED"
    if issues:
        decision = "CYCLE_POST_WRITE_COMPLIANCE_FAILED"
    elif warnings:
        decision = "CYCLE_POST_WRITE_COMPLIANCE_PASSED_WITH_WARNINGS"

    payload = {
        "cycle_id": cycle_id,
        "device": device,
        "device_id": device_id,
        "decision": decision,
        "status": decision,
        "generated_at": now_iso(),
        "items": result_items,
        "issues": issues,
        "registry": str(policy_registry),
        "safety_confirmations": {
            "local_only": True,
            "no_network_call": True,
            "no_token_read": True,
            "no_netbox_write": True,
            "no_apply_execution": True,
        },
    }
    write_json(output_json, payload)
    write_md(output_md, f"# {cycle_id.upper()} Post-Write Compliance Re-Run\n\n## Decision: {decision}\n\n{summarize_issues(issues)}\n")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--execution-result", type=Path, required=True)
    parser.add_argument("--post-write-verification", type=Path, required=True)
    parser.add_argument("--policy-registry", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    args = parser.parse_args()
    result = rerun_compliance(
        cycle_id=args.cycle_id,
        device=args.device,
        device_id=args.device_id,
        execution_result_path=args.execution_result,
        post_write_verification_path=args.post_write_verification,
        policy_registry=args.policy_registry,
        output_json=args.output_json,
        output_md=args.output_md,
    )
    return 0 if s(result.get("decision")).startswith("CYCLE_POST_WRITE_COMPLIANCE_PASSED") or s(result.get("decision")) == "CYCLE_POST_WRITE_COMPLIANCE_NOT_APPLICABLE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
