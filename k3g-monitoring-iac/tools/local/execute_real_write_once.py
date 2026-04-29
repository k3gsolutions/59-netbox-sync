#!/usr/bin/env python3
"""FASE 2.53 — Execute Real Write Once.

Execute single real write to NetBox from approved execution_package.json.
Token from environment only. One-shot, no retries, no partials.
No tokens in logs/results.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from uuid import uuid4

try:
    import requests
except ImportError:
    requests = None


def read_token_from_env() -> Optional[str]:
    """Read NETBOX_WRITE_TOKEN from environment. Never log or print."""
    return os.environ.get("NETBOX_WRITE_TOKEN")


def validate_token_exists() -> bool:
    """Check token exists without returning or logging it."""
    return "NETBOX_WRITE_TOKEN" in os.environ


def load_execution_package(package_file: Path) -> Tuple[bool, str, Dict[str, Any]]:
    """Load and validate execution_package.json."""
    if not package_file.exists():
        return False, f"Package not found: {package_file}", {}

    try:
        with open(package_file, encoding="utf-8") as f:
            pkg = json.load(f)
    except Exception as e:
        return False, f"Invalid JSON: {e}", {}

    # Validate critical fields
    if pkg.get("status") != "prepared":
        return False, f"Status is {pkg.get('status')}, not prepared", {}

    if pkg.get("mode") != "real_write_prepared":
        return False, f"Mode is {pkg.get('mode')}, not real_write_prepared", {}

    if pkg.get("execution_allowed") is not False:
        return False, "execution_allowed must be false", {}

    if not pkg.get("required_execution_phrase"):
        return False, "Missing required_execution_phrase", {}

    if not pkg.get("items"):
        return False, "No items in package", {}

    return True, "Package valid", pkg


def validate_freeze_check(freeze_file: Path) -> Tuple[bool, str]:
    """Validate FINAL-NO-WRITE-FREEZE-CHECK.md decision."""
    if not freeze_file.exists():
        return False, f"Freeze check not found: {freeze_file}"

    try:
        content = freeze_file.read_text(encoding="utf-8")
    except Exception as e:
        return False, f"Cannot read freeze check: {e}"

    if "### READY_FOR_REAL_WRITE_PHASE" in content:
        return True, "Freeze check READY"

    return False, "Freeze check not READY_FOR_REAL_WRITE_PHASE"


def validate_confirmation(required_phrase: str, operator_phrase: str) -> bool:
    """Validate execution phrase exactly."""
    return required_phrase == operator_phrase


def validate_items(items: list) -> Tuple[bool, str]:
    """Validate all items before executing."""
    forbidden_keywords = [
        "token", "password", "secret", "api_key",
        "private key", "bearer", "authorization"
    ]

    for item in items:
        # Check method
        method = item.get("method", "").upper()
        if method != "POST":
            return False, f"Item {item.get('item_id')} has method {method}, only POST allowed"

        # Check endpoint
        endpoint = item.get("endpoint", "")
        forbidden_targets = ["/sync", "equipment", "ssh", "netconf"]
        for forbidden in forbidden_targets:
            if forbidden in endpoint.lower():
                return False, f"Item {item.get('item_id')} has forbidden endpoint: {endpoint}"

        # Check for secrets in payload
        payload = item.get("payload", {})
        payload_str = json.dumps(payload).lower()
        for keyword in forbidden_keywords:
            if keyword in payload_str:
                return False, f"Item {item.get('item_id')} contains forbidden keyword: {keyword}"

    return True, "All items valid"


def execute_post_request(
    token: str,
    netbox_url: str,
    endpoint: str,
    payload: Dict[str, Any],
) -> Tuple[bool, Optional[int], Optional[Dict[str, Any]], str]:
    """Execute POST request to NetBox API.

    Returns: (success, http_status, response_json, error_message)
    Never log token.
    """
    if requests is None:
        return False, None, None, "requests library not available"

    url = netbox_url.rstrip("/") + endpoint
    headers = {
        "Authorization": f"Token {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=30,
        )

        if response.status_code in (200, 201, 202):
            try:
                result = response.json()
                return True, response.status_code, result, ""
            except Exception:
                return False, response.status_code, None, "Response not JSON"
        else:
            try:
                error_detail = response.json()
            except Exception:
                error_detail = response.text

            return False, response.status_code, None, f"HTTP {response.status_code}: {error_detail}"

    except requests.exceptions.Timeout:
        return False, None, None, "Request timeout"
    except requests.exceptions.ConnectionError:
        return False, None, None, "Connection error"
    except Exception as e:
        return False, None, None, f"Request error: {str(e)}"


def verify_created_resource(
    token: str,
    netbox_url: str,
    item: Dict[str, Any],
    response: Dict[str, Any],
) -> Tuple[bool, str]:
    """Verify created resource via GET request.

    Never log token.
    """
    if requests is None:
        return False, "requests not available"

    resource_id = response.get("id")
    if not resource_id:
        return False, "No id in response"

    # Build GET URL from endpoint + id
    endpoint = item.get("endpoint", "")
    url = f"{netbox_url.rstrip('/')}{endpoint.rstrip('/')}/{resource_id}/"

    headers = {
        "Authorization": f"Token {token}",
        "Accept": "application/json",
    }

    try:
        response_get = requests.get(url, headers=headers, timeout=30)

        if response_get.status_code == 200:
            result = response_get.json()
            # Verify key fields match
            if result.get("id") == resource_id:
                return True, "Verified"
            return False, "ID mismatch in verification"
        else:
            return False, f"Verification failed: HTTP {response_get.status_code}"

    except Exception as e:
        return False, f"Verification error: {str(e)}"


def main() -> int:
    """Run FASE 2.53."""
    parser = argparse.ArgumentParser(description="FASE 2.53 — Execute Real Write Once")
    parser.add_argument("--execution-package", type=Path, required=True)
    parser.add_argument("--operator", required=True)
    parser.add_argument("--confirm-execution-phrase", required=True)
    parser.add_argument("--confirm-real-write-once", action="store_true")
    parser.add_argument("--netbox-url", required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    parser.add_argument("--freeze-check", type=Path, help="Path to freeze check file")

    args = parser.parse_args()

    execution_id = str(uuid4())
    timestamp_start = datetime.utcnow().isoformat() + "+00:00"

    # Mandatory confirmation
    if not args.confirm_real_write_once:
        print("✗ Execution blocked: --confirm-real-write-once not provided")
        return 1

    # Load package
    pkg_ok, pkg_reason, package = load_execution_package(args.execution_package)
    if not pkg_ok:
        print(f"✗ Package invalid: {pkg_reason}")
        return 1

    execution_package_id = package.get("execution_package_id")
    device = package.get("device")
    device_id = package.get("device_id")
    required_phrase = package.get("required_execution_phrase")
    items = package.get("items", [])

    # Validate phrase
    if not validate_confirmation(required_phrase, args.confirm_execution_phrase):
        print("✗ Execution phrase mismatch")
        return 1

    # Validate token exists (don't read it yet)
    if not validate_token_exists():
        print("✗ NETBOX_WRITE_TOKEN not in environment")
        return 1

    # Validate freeze check if provided
    if args.freeze_check:
        freeze_ok, freeze_reason = validate_freeze_check(args.freeze_check)
        if not freeze_ok:
            print(f"✗ Freeze check failed: {freeze_reason}")
            return 1

    # Validate items
    items_ok, items_reason = validate_items(items)
    if not items_ok:
        print(f"✗ Items invalid: {items_reason}")
        return 1

    # Validate NetBox URL
    if not args.netbox_url.startswith("https://"):
        print("✗ NetBox URL must use HTTPS")
        return 1

    # NOW read token (first and only time)
    token = read_token_from_env()

    # Execute items
    executed_items = []
    failed_at_item = None
    overall_status = "REAL_WRITE_SUCCESS"

    for item in items:
        item_id = item.get("item_id")
        endpoint = item.get("endpoint")
        payload = item.get("payload")

        item_start = datetime.utcnow().isoformat() + "+00:00"
        item_result = {
            "item_id": item_id,
            "approval_id": item.get("approval_id"),
            "object_type": item.get("object_type"),
            "object_key": item.get("object_key"),
            "method": "POST",
            "endpoint": endpoint,
            "started_at": item_start,
            "status": None,
            "http_status": None,
            "response_id": None,
            "verification_status": None,
            "error_sanitized": None,
        }

        # Execute POST
        post_ok, http_status, response_json, error_msg = execute_post_request(
            token, args.netbox_url, endpoint, payload
        )

        item_result["http_status"] = http_status

        if not post_ok:
            item_result["status"] = "REAL_WRITE_FAILED"
            item_result["error_sanitized"] = error_msg
            item_result["finished_at"] = datetime.utcnow().isoformat() + "+00:00"
            executed_items.append(item_result)

            # Stop on first failure
            failed_at_item = item_id
            overall_status = "REAL_WRITE_FAILED"
            break

        # Extract ID from response
        response_id = response_json.get("id") if response_json else None
        item_result["response_id"] = response_id

        # Verify created resource
        if response_id:
            verify_ok, verify_msg = verify_created_resource(token, args.netbox_url, item, response_json)
            if verify_ok:
                item_result["verification_status"] = "verified"
                item_result["status"] = "REAL_WRITE_CREATED"
            else:
                item_result["verification_status"] = "failed"
                item_result["status"] = "REAL_WRITE_CREATED_NOT_VERIFIED"
        else:
            item_result["verification_status"] = "no_id"
            item_result["status"] = "REAL_WRITE_CREATED_NO_ID"

        item_result["finished_at"] = datetime.utcnow().isoformat() + "+00:00"
        executed_items.append(item_result)

    timestamp_end = datetime.utcnow().isoformat() + "+00:00"

    # Generate result JSON
    result_json = {
        "execution_id": execution_id,
        "execution_package_id": execution_package_id,
        "device": device,
        "device_id": device_id,
        "operator": args.operator,
        "started_at": timestamp_start,
        "finished_at": timestamp_end,
        "status": overall_status,
        "one_shot_execution": True,
        "retry_attempted": False,
        "rollback_attempted": False,
        "token_logged": False,
        "items": executed_items,
        "safety_confirmations": {
            "token_not_logged": True,
            "token_not_saved": True,
            "no_sync_called": True,
            "no_patch_delete": True,
            "no_equipment_access": True,
            "one_shot_only": True,
        },
        "next_phase": "FASE_2_54_POST_WRITE_VERIFICATION",
    }

    # Generate result markdown
    created_count = sum(1 for item in executed_items if "CREATED" in item.get("status", ""))
    failed_count = sum(1 for item in executed_items if "FAILED" in item.get("status", ""))

    result_md = f"""# Resultado da Execução de Escrita Real — {device}

## 1. Status

### {overall_status}

## 2. Resumo

- **Operador:** {args.operator}
- **Execution Package:** {execution_package_id}
- **Total itens:** {len(items)}
- **Executados:** {len(executed_items)}
- **Criados:** {created_count}
- **Falhados:** {failed_count}
- **Iniciado:** {timestamp_start}
- **Finalizado:** {timestamp_end}

## 3. Itens Executados

| Item ID | Approval ID | Object Key | Endpoint | HTTP | Status | Response ID | Verificação |
|---|---|---|---|---|---|---|---|
"""

    for item in executed_items:
        result_md += (
            f"| {item['item_id']} | {item['approval_id']} | {item['object_key']} | "
            f"{item['endpoint']} | {item['http_status']} | {item['status']} | "
            f"{item['response_id']} | {item['verification_status']} |\n"
        )

    result_md += """
## 4. Segurança

✓ Token não logado
✓ Token não salvo
✓ Sem /sync
✓ Sem PATCH/DELETE
✓ Sem acesso a equipamento
✓ Execução one-shot
✓ Sem retry automático

## 5. Próxima Fase

FASE 2.54 — Post-Write Verification
"""

    # Write results
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(result_json, f, indent=2)

    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(result_md, encoding="utf-8")

    print(f"✓ Execution result: {args.output_json}")
    print(f"✓ Execution report: {args.output_md}")
    print(f"✓ Status: {overall_status}")

    return 0 if overall_status == "REAL_WRITE_SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
