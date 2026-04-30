#!/usr/bin/env python3
"""FASE 4.60 - Post-write verification."""

from __future__ import annotations

import argparse
import http.client
import json
import os
import ssl
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.local.controlled_cycle_real_write_common import (  # noqa: E402
    has_forbidden_terms,
    https_parts,
    load_json,
    now_iso,
    s,
    summarize_issues,
    write_json,
    write_md,
)


def _default_conn_factory(host: str) -> http.client.HTTPSConnection:
    return http.client.HTTPSConnection(host, timeout=30, context=ssl.create_default_context())


def verify_post_write(
    *,
    cycle_id: str,
    execution_result_path: Path,
    execution_package_path: Path,
    netbox_url: str,
    device: str,
    device_id: str,
    output_json: Path,
    output_md: Path,
    token: str | None = None,
    conn_factory: Callable[[str], Any] | None = None,
) -> dict[str, Any]:
    execution_result = load_json(execution_result_path)
    execution_package = load_json(execution_package_path)
    if s(execution_result.get("status")) == "CYCLE_REAL_WRITE_ABORTED_PREFLIGHT_FAILED":
        payload = {
            "cycle_id": cycle_id,
            "decision": "CYCLE_POST_WRITE_VERIFICATION_NOT_APPLICABLE",
            "status": "NOT_APPLICABLE",
            "issues": ["execution aborted preflight"],
            "items": [],
            "safety_confirmations": {
                "local_only": True,
                "no_network_call": True,
                "no_token_read": True,
                "no_netbox_write": True,
                "no_apply_execution": True,
            },
        }
        write_json(output_json, payload)
        write_md(output_md, f"# {cycle_id.upper()} Post-Write Verification\n\n## Decision: NOT_APPLICABLE\n\n- execution aborted preflight\n")
        return payload

    issues: list[str] = []
    if not token:
        issues.append("NETBOX_WRITE_TOKEN missing")
    if not s(netbox_url).startswith("https://"):
        issues.append("netbox-url must start with https://")
    if s(execution_result.get("cycle_id")) != cycle_id:
        issues.append("cycle_id mismatch")
    if s(execution_result.get("execution_package_id")) != s(execution_package.get("execution_package_id")):
        issues.append("execution package mismatch")
    if s(execution_result.get("status")) not in {"CYCLE_REAL_WRITE_SUCCESS", "CYCLE_REAL_WRITE_PARTIAL_FAILED"}:
        issues.append(f"execution status is {execution_result.get('status')}, expected success or partial failure")
    if has_forbidden_terms(execution_result):
        issues.append("secret keyword found in execution result")

    if issues:
        payload = {
            "cycle_id": cycle_id,
            "decision": "CYCLE_POST_WRITE_VERIFICATION_FAILED",
            "status": "CYCLE_POST_WRITE_VERIFICATION_FAILED",
            "issues": issues,
            "items": [],
            "safety_confirmations": {
                "local_only": True,
                "no_network_call": True,
                "no_token_read": True,
                "no_netbox_write": True,
                "no_apply_execution": True,
            },
        }
        write_json(output_json, payload)
        write_md(output_md, f"# {cycle_id.upper()} Post-Write Verification\n\n## Decision: CYCLE_POST_WRITE_VERIFICATION_FAILED\n\n{summarize_issues(issues)}\n")
        return payload

    assert token is not None
    host, base_path = https_parts(netbox_url)
    conn = conn_factory(host) if conn_factory else _default_conn_factory(host)
    result_items: list[dict[str, Any]] = []
    status = "CYCLE_POST_WRITE_VERIFICATION_PASSED"
    drift_found = False

    for item in execution_result.get("items") or []:
        response_id = s(item.get("response_id"))
        item_status = s(item.get("status"))
        response_status = item.get("response_status")

        # Check if item is verifiable
        is_verifiable = (
            response_id and
            item_status == "CYCLE_REAL_WRITE_CREATED" and
            response_status in {200, 201, 202}
        )

        if not is_verifiable:
            result_items.append({**item, "verification_status": "skipped"})
            continue

        # Try to use verified_object from execution result first
        verified_object = item.get("verified_object") or {}
        if not verified_object:
            # Fetch from NetBox if not included
            verify_url = s(item.get("response_url")) or f"{base_path}{s(item.get('target_endpoint')).rstrip('/')}/{response_id}/"
            conn.request("GET", verify_url, headers={"Authorization": f"Token {token}", "Accept": "application/json"})
            resp = conn.getresponse()
            body = resp.read().decode("utf-8", errors="ignore")
            verified_object = json.loads(body) if body else {}
            if resp.status != 200:
                status = "CYCLE_POST_WRITE_VERIFICATION_FAILED"
                result_items.append({**item, "verification_status": "failed", "error": f"HTTP {resp.status}"})
                break

        # Validate proposed_payload fields match verified_object
        proposed_payload = item.get("proposed_payload") or {}
        drift = False
        for key, expected_value in proposed_payload.items():
            actual_value = verified_object.get(key)
            if s(actual_value) != s(expected_value):
                drift = True
                break

        if drift:
            drift_found = True
            result_items.append({**item, "verification_status": "drift", "verified_object": verified_object})
        else:
            result_items.append({**item, "verification_status": "verified", "verified_object": verified_object})

        if verified_object:
            write_json(output_json.parent / "post-write-audit" / f"{response_id}-verification.json",
                      {"response_id": response_id, "verified_object": verified_object, "verification_status": result_items[-1]["verification_status"]})

    if status == "CYCLE_POST_WRITE_VERIFICATION_PASSED" and drift_found:
        status = "CYCLE_POST_WRITE_VERIFICATION_PASSED_WITH_DRIFT"

    payload = {
        "cycle_id": cycle_id,
        "decision": status,
        "status": status,
        "items": result_items,
        "verified_at": now_iso(),
        "safety_confirmations": {
            "local_only": True,
            "no_network_call": True,
            "no_token_read": True,
            "no_netbox_write": True,
            "no_apply_execution": True,
        },
    }
    write_json(output_json, payload)
    write_md(output_md, f"# {cycle_id.upper()} Post-Write Verification\n\n## Decision: {status}\n\n- items: {len(result_items)}\n")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--execution-result", type=Path, required=True)
    parser.add_argument("--execution-package", type=Path, required=True)
    parser.add_argument("--netbox-url", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    args = parser.parse_args()
    result = verify_post_write(
        cycle_id=args.cycle_id,
        execution_result_path=args.execution_result,
        execution_package_path=args.execution_package,
        netbox_url=args.netbox_url,
        device=args.device,
        device_id=args.device_id,
        output_json=args.output_json,
        output_md=args.output_md,
        token=os.environ.get("NETBOX_WRITE_TOKEN"),
    )
    return 0 if s(result.get("decision")).startswith("CYCLE_POST_WRITE_VERIFICATION_PASSED") or s(result.get("decision")) == "CYCLE_POST_WRITE_VERIFICATION_NOT_APPLICABLE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
