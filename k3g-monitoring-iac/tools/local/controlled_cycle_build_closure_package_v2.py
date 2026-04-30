#!/usr/bin/env python3
"""FASE 4.62 - Build Cycle-002 closure package."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.local.controlled_cycle_real_write_common import load_json, now_iso, s, write_json, write_md  # noqa: E402


def build_closure_package(
    *,
    cycle_id: str,
    device: str,
    device_id: str,
    execution_result_path: Path,
    post_write_verification_path: Path,
    post_write_compliance_path: Path,
    output_dir: Path,
    report: Path,
) -> dict[str, object]:
    execution_result = load_json(execution_result_path)
    verification = load_json(post_write_verification_path)
    compliance = load_json(post_write_compliance_path)

    execution_status = s(execution_result.get("status"))
    verification_decision = s(verification.get("decision"))
    compliance_decision = s(compliance.get("decision"))

    status = "CYCLE_CLOSED_NOT_APPLICABLE"
    reason = "execution not applicable"

    if execution_status == "CYCLE_REAL_WRITE_SUCCESS":
        # All three phases must pass for complete success
        if (verification_decision == "CYCLE_POST_WRITE_VERIFICATION_PASSED" and
            compliance_decision == "CYCLE_POST_WRITE_COMPLIANCE_PASSED"):
            status = "CYCLE_CLOSED_SUCCESS"
            reason = "execution, verification, and compliance all passed"
        # Warnings if drift or compliance warnings present
        elif (verification_decision == "CYCLE_POST_WRITE_VERIFICATION_PASSED_WITH_DRIFT" or
              compliance_decision == "CYCLE_POST_WRITE_COMPLIANCE_PASSED_WITH_WARNINGS"):
            status = "CYCLE_CLOSED_WITH_WARNINGS"
            reason = "execution passed with drift or warnings in verification/compliance"
        # Action required if either phase failed
        else:
            status = "CYCLE_CLOSED_ACTION_REQUIRED"
            reason = f"verification: {verification_decision}; compliance: {compliance_decision}"
    elif execution_status in {"CYCLE_REAL_WRITE_FAILED", "CYCLE_REAL_WRITE_PARTIAL_FAILED"}:
        status = "CYCLE_CLOSED_ACTION_REQUIRED"
        reason = "real write execution failed"
    elif execution_status == "CYCLE_REAL_WRITE_ABORTED_PREFLIGHT_FAILED":
        status = "CYCLE_CLOSED_ACTION_REQUIRED"
        reason = "real write execution aborted on preflight"

    output_dir.mkdir(parents=True, exist_ok=True)
    closure_id = f"closure-{cycle_id}-{uuid.uuid4().hex[:8]}"
    payload = {
        "closure_id": closure_id,
        "cycle_id": cycle_id,
        "device": device,
        "device_id": device_id,
        "status": status,
        "decision": status,
        "generated_at": now_iso(),
        "reason": reason,
        "execution_result": execution_result_path.name,
        "post_write_verification": post_write_verification_path.name,
        "post_write_compliance": post_write_compliance_path.name,
        "safety_confirmations": {
            "no_write_executed": s(execution_result.get("status")) != "CYCLE_REAL_WRITE_SUCCESS",
            "no_token_read": True,
            "no_network_call": True,
            "closure_only": True,
            "real_write_not_reexecuted": True,
        },
    }
    filename = f"{cycle_id}-closure-summary.json"
    write_json(output_dir / filename, payload)
    write_md(report, f"# {cycle_id.upper()} Closure Package\n\n## Decision: {status}\n\n- {reason}\n")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--execution-result", type=Path, required=True)
    parser.add_argument("--post-write-verification", type=Path, required=True)
    parser.add_argument("--post-write-compliance", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = build_closure_package(
        cycle_id=args.cycle_id,
        device=args.device,
        device_id=args.device_id,
        execution_result_path=args.execution_result,
        post_write_verification_path=args.post_write_verification,
        post_write_compliance_path=args.post_write_compliance,
        output_dir=args.output_dir,
        report=args.report,
    )
    return 0 if s(result.get("status")).startswith("CYCLE_CLOSED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
