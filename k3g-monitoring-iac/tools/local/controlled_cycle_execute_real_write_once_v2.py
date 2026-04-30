#!/usr/bin/env python3
"""FASE 4.59 - Execute Cycle-002 real write once.

Safer by default. If preflight fail, abort before any write.
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import ssl
import sys
import uuid
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.local.controlled_cycle_real_write_common import (  # noqa: E402
    cycle_dir,
    ensure_allowed_target,
    has_forbidden_terms,
    https_parts,
    load_approved_records,
    load_json,
    now_iso,
    s,
    summarize_issues,
    write_json,
    write_md,
)


def _default_conn_factory(host: str) -> http.client.HTTPSConnection:
    return http.client.HTTPSConnection(host, timeout=30, context=ssl.create_default_context())


def _abort_result(
    *,
    cycle_id: str,
    execution_package: dict[str, Any],
    operator: str,
    issues: list[str],
    output_json: Path,
    output_md: Path,
) -> dict[str, Any]:
    execution_id = f"exec-result-{cycle_id}-{uuid.uuid4().hex[:8]}"
    items = []
    for item in execution_package.get("items") or []:
        items.append(
            {
                "item_id": item.get("item_id") or item.get("approval_id"),
                "approval_id": item.get("approval_id"),
                "object_type": item.get("object_type"),
                "object_key": item.get("object_key"),
                "method": item.get("method"),
                "target_endpoint": item.get("target_endpoint"),
                "proposed_payload": item.get("proposed_payload") or {},
                "expected_result": item.get("expected_result"),
                "rollback_hint": item.get("rollback_hint"),
                "response_status": None,
                "response_id": None,
                "response_url": None,
                "verification_status": "not_attempted",
                "status": "CYCLE_REAL_WRITE_NOT_ATTEMPTED",
                "error": "preflight aborted",
            }
        )
    payload = {
        "execution_id": execution_id,
        "cycle_id": cycle_id,
        "execution_package_id": execution_package.get("execution_package_id"),
        "device": execution_package.get("device"),
        "device_id": execution_package.get("device_id"),
        "operator": operator,
        "started_at": now_iso(),
        "finished_at": now_iso(),
        "status": "CYCLE_REAL_WRITE_ABORTED_PREFLIGHT_FAILED",
        "one_shot_execution": True,
        "retry_attempted": False,
        "rollback_attempted": False,
        "token_logged": False,
        "token_saved": False,
        "no_write_attempted": True,
        "items": items,
        "issues": issues,
        "safety_confirmations": {
            "token_not_logged": True,
            "token_not_saved": True,
            "no_sync_called": True,
            "no_patch_delete": True,
            "no_equipment_access": True,
            "one_shot_only": True,
        },
    }
    write_json(output_json, payload)
    md = [
        f"# {cycle_id.upper()} Real Write Execution Result",
        "",
        "## Decision: CYCLE_REAL_WRITE_ABORTED_PREFLIGHT_FAILED",
        "",
        "## Issues",
        summarize_issues(issues),
        "",
        "## Safety",
        "- No write attempted",
        "- No token logged",
        "- No token saved",
        "- No /sync",
        "- No PATCH/DELETE",
    ]
    write_md(output_md, "\n".join(md))
    return payload


def execute_real_write_once(
    *,
    cycle_id: str,
    execution_package_path: Path,
    operator: str,
    confirm_execution_phrase: str,
    confirm_real_write_once: bool,
    netbox_url: str,
    output_json: Path,
    output_md: Path,
    token: str | None = None,
    conn_factory: Callable[[str], Any] | None = None,
) -> dict[str, Any]:
    execution_package = load_json(execution_package_path)
    freeze_path = execution_package_path.parent / "CYCLE-002-FINAL-NO-WRITE-FREEZE-CHECK.json"
    freeze = load_json(freeze_path)
    issues: list[str] = []

    if s(execution_package.get("cycle_id")) != cycle_id:
        issues.append("cycle_id mismatch")
    if s(execution_package.get("status")) != "prepared":
        issues.append("status must be prepared")
    if s(execution_package.get("mode")) != "real_write_prepared":
        issues.append("mode must be real_write_prepared")
    if execution_package.get("execution_allowed") is not False:
        issues.append("execution_allowed must remain false")
    if execution_package.get("token_required_in_next_phase") is not True:
        issues.append("token_required_in_next_phase must be true")
    if execution_package.get("explicit_confirm_required") is not True:
        issues.append("explicit_confirm_required must be true")
    if execution_package.get("one_shot_execution") is not True:
        issues.append("one_shot_execution must be true")
    if not s(operator):
        issues.append("operator required")
    if not confirm_real_write_once:
        issues.append("confirm-real-write-once required")
    if not token:
        issues.append("NETBOX_WRITE_TOKEN missing")
    if not s(netbox_url).startswith("https://"):
        issues.append("netbox-url must start with https://")
    if s(execution_package.get("required_execution_phrase")) != s(confirm_execution_phrase):
        issues.append("execution phrase mismatch")
    if s(freeze.get("decision")) not in {"CYCLE_READY_FOR_REAL_WRITE_PHASE", "CYCLE_READY_WITH_RESTRICTIONS"}:
        issues.append("freeze not ready")

    items = execution_package.get("items") or []
    if not items:
        issues.append("items missing")
    if int(execution_package.get("max_items") or 0) > 3:
        issues.append("max_items too high")
    for item in items:
        if s(item.get("method")) != "POST":
            issues.append(f"{item.get('approval_id')}: method must be POST")
        endpoint = s(item.get("target_endpoint"))
        if not ensure_allowed_target(endpoint):
            issues.append(f"{item.get('approval_id')}: endpoint blocked")
        if has_forbidden_terms(item.get("proposed_payload")):
            issues.append(f"{item.get('approval_id')}: secret terms in payload")

    if issues:
        return _abort_result(
            cycle_id=cycle_id,
            execution_package=execution_package,
            operator=operator,
            issues=issues,
            output_json=output_json,
            output_md=output_md,
        )

    assert token is not None
    host, base_path = https_parts(netbox_url)
    conn = conn_factory(host) if conn_factory else _default_conn_factory(host)
    audit_dir = execution_package_path.parent / "execution-audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    started_at = now_iso()
    execution_id = f"exec-result-{cycle_id}-{uuid.uuid4().hex[:8]}"
    result_items: list[dict[str, Any]] = []
    write_failed = False
    failure_message = ""

    def _headers() -> dict[str, str]:
        return {
            "Authorization": f"Token {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    for item in items:
        endpoint = s(item.get("target_endpoint"))
        payload = item.get("proposed_payload") or {}
        full_endpoint = f"{base_path}{endpoint}" if base_path else endpoint
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        conn.request("POST", full_endpoint, body=body, headers=_headers())
        response = conn.getresponse()
        response_body = response.read().decode("utf-8", errors="ignore")
        try:
            response_json = json.loads(response_body) if response_body else {}
        except Exception:
            response_json = {}
        response_id = response_json.get("id")
        response_url = response_json.get("url") or response.getheader("Location") or ""
        if response.status not in {200, 201, 202} or not response_id:
            write_failed = True
            failure_message = f"{item.get('approval_id')}: POST failed"
            result_items.append(
                {
                    "item_id": item.get("item_id") or item.get("approval_id"),
                    "approval_id": item.get("approval_id"),
                    "object_type": item.get("object_type"),
                    "object_key": item.get("object_key"),
                    "method": "POST",
                    "target_endpoint": endpoint,
                    "proposed_payload": payload,
                    "expected_result": item.get("expected_result"),
                    "rollback_hint": item.get("rollback_hint"),
                    "response_status": response.status,
                    "response_id": response_id,
                    "response_url": response_url,
                    "verification_status": "failed",
                    "status": "CYCLE_REAL_WRITE_FAILED",
                    "error": failure_message,
                }
            )
            break

        verify_path = response_url or f"{full_endpoint.rstrip('/')}/{response_id}/"
        conn.request("GET", verify_path, headers={"Authorization": f"Token {token}", "Accept": "application/json"})
        verify_response = conn.getresponse()
        verify_body = verify_response.read().decode("utf-8", errors="ignore")
        try:
            verify_json = json.loads(verify_body) if verify_body else {}
        except Exception:
            verify_json = {}
        verified = verify_response.status == 200 and s(verify_json.get("id")) == s(response_id)
        if not verified:
            write_failed = True
            failure_message = f"{item.get('approval_id')}: verification failed"
            result_items.append(
                {
                    "item_id": item.get("item_id") or item.get("approval_id"),
                    "approval_id": item.get("approval_id"),
                    "object_type": item.get("object_type"),
                    "object_key": item.get("object_key"),
                    "method": "POST",
                    "target_endpoint": endpoint,
                    "proposed_payload": payload,
                    "expected_result": item.get("expected_result"),
                    "rollback_hint": item.get("rollback_hint"),
                    "response_status": response.status,
                    "response_id": response_id,
                    "response_url": response_url,
                    "verification_status": "failed",
                    "status": "CYCLE_REAL_WRITE_FAILED",
                    "error": failure_message,
                }
            )
            break

        item_result = {
            "item_id": item.get("item_id") or item.get("approval_id"),
            "approval_id": item.get("approval_id"),
            "object_type": item.get("object_type"),
            "object_key": item.get("object_key"),
            "method": "POST",
            "target_endpoint": endpoint,
            "proposed_payload": payload,
            "expected_result": item.get("expected_result"),
            "rollback_hint": item.get("rollback_hint"),
            "response_status": response.status,
            "response_id": response_id,
            "response_url": response_url or verify_path,
            "verified_object": verify_json,
            "verification_status": "verified",
            "status": "CYCLE_REAL_WRITE_CREATED",
            "pre_write_checks": item.get("pre_write_checks") or [],
            "post_write_checks": item.get("post_write_checks") or [],
        }
        result_items.append(item_result)
        write_json(audit_dir / f"{s(response_id) or s(item_result['item_id'])}-execution.json", item_result)

    finished_at = now_iso()
    status = "CYCLE_REAL_WRITE_SUCCESS"
    if write_failed and result_items:
        status = "CYCLE_REAL_WRITE_PARTIAL_FAILED"
    elif write_failed:
        status = "CYCLE_REAL_WRITE_FAILED"

    payload = {
        "execution_id": execution_id,
        "cycle_id": cycle_id,
        "execution_package_id": execution_package.get("execution_package_id"),
        "device": execution_package.get("device"),
        "device_id": execution_package.get("device_id"),
        "operator": operator,
        "started_at": started_at,
        "finished_at": finished_at,
        "status": status,
        "one_shot_execution": True,
        "retry_attempted": False,
        "rollback_attempted": False,
        "token_logged": False,
        "token_saved": False,
        "no_write_attempted": False,
        "items": result_items,
        "safety_confirmations": {
            "token_not_logged": True,
            "token_not_saved": True,
            "no_sync_called": True,
            "no_patch_delete": True,
            "no_equipment_access": True,
            "one_shot_only": True,
        },
    }
    write_json(output_json, payload)
    md = [
        f"# {cycle_id.upper()} Real Write Execution Result",
        "",
        f"## Decision: {status}",
        "",
        f"- execution_package: {execution_package.get('execution_package_id', '')}",
        f"- items: {len(result_items)}",
        "",
        "## Safety",
        "- No token logged",
        "- No token saved",
        "- No /sync",
        "- No PATCH/DELETE",
        "- One-shot only",
    ]
    write_md(output_md, "\n".join(md))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--execution-package", type=Path, required=True)
    parser.add_argument("--operator", required=True)
    parser.add_argument("--confirm-execution-phrase", required=True)
    parser.add_argument("--confirm-real-write-once", action="store_true")
    parser.add_argument("--netbox-url", required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    args = parser.parse_args()

    result = execute_real_write_once(
        cycle_id=args.cycle_id,
        execution_package_path=args.execution_package,
        operator=args.operator,
        confirm_execution_phrase=args.confirm_execution_phrase,
        confirm_real_write_once=args.confirm_real_write_once,
        netbox_url=args.netbox_url,
        output_json=args.output_json,
        output_md=args.output_md,
        token=os.environ.get("NETBOX_WRITE_TOKEN"),
    )
    return 0 if s(result.get("status")) == "CYCLE_REAL_WRITE_SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
