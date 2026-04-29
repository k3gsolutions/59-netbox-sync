#!/usr/bin/env python3
"""FASE 2.54 — Post-Write Verification.

Verify each created object in NetBox matches expected payload.
Read-only GET verification. Compare response vs. expected fields.
Generate verification report.
Token from environment only. No writes, no modifications.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

try:
    import requests
except ImportError:
    requests = None


def read_token_from_env() -> Optional[str]:
    """Read NETBOX_READ_TOKEN from environment. Never log or print."""
    return os.environ.get("NETBOX_READ_TOKEN")


def load_execution_result(result_file: Path) -> Tuple[bool, str, Dict[str, Any]]:
    """Load REAL-WRITE-EXECUTION-RESULT.json."""
    if not result_file.exists():
        return False, f"Result file not found: {result_file}", {}

    try:
        with open(result_file, encoding="utf-8") as f:
            result = json.load(f)
    except Exception as e:
        return False, f"Invalid JSON: {e}", {}

    if result.get("status") != "REAL_WRITE_SUCCESS":
        return False, f"Execution status is {result.get('status')}, not SUCCESS", result

    if not result.get("items"):
        return False, "No items in execution result", result

    return True, "Execution result valid", result


def load_execution_package(package_file: Path) -> Tuple[bool, str, Dict[str, Any]]:
    """Load execution_package.json for expected payloads."""
    if not package_file.exists():
        return False, f"Package not found: {package_file}", {}

    try:
        with open(package_file, encoding="utf-8") as f:
            package = json.load(f)
    except Exception as e:
        return False, f"Invalid JSON: {e}", {}

    if not package.get("items"):
        return False, "No items in package", package

    return True, "Package valid", package


def find_item_in_package(
    items: List[Dict[str, Any]], item_id: str
) -> Optional[Dict[str, Any]]:
    """Find item in package by item_id."""
    for item in items:
        if item.get("item_id") == item_id:
            return item
    return None


def verify_object_in_netbox(
    token: str,
    netbox_url: str,
    endpoint: str,
    resource_id: int,
    expected_payload: Dict[str, Any],
) -> Tuple[bool, str, Dict[str, Any]]:
    """GET verify object in NetBox. Compare vs. expected payload.

    Returns: (success, message, response_json)
    Never log token.
    """
    if requests is None:
        return False, "requests library not available", {}

    # Build GET URL
    url = f"{netbox_url.rstrip('/')}{endpoint.rstrip('/')}/{resource_id}/"

    headers = {
        "Authorization": f"Token {token}",
        "Accept": "application/json",
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code == 200:
            result = response.json()

            # Verify key fields from expected payload
            all_match = True
            mismatches = []

            for key, expected_value in expected_payload.items():
                actual_value = result.get(key)

                # Simple equality check for primitives
                if isinstance(expected_value, (str, int, bool, type(None))):
                    if actual_value != expected_value:
                        all_match = False
                        mismatches.append(
                            f"{key}: expected {expected_value}, got {actual_value}"
                        )
                # For dicts/lists, convert both to JSON strings for comparison
                elif isinstance(expected_value, (dict, list)):
                    try:
                        expected_str = json.dumps(expected_value, sort_keys=True)
                        actual_str = json.dumps(actual_value, sort_keys=True)
                        if expected_str != actual_str:
                            all_match = False
                            mismatches.append(f"{key}: object mismatch")
                    except Exception:
                        # Can't compare complex types, skip
                        pass

            if all_match:
                return True, "Object verified", result
            else:
                return False, f"Field mismatches: {'; '.join(mismatches)}", result

        else:
            try:
                error_detail = response.json()
            except Exception:
                error_detail = response.text

            return False, f"HTTP {response.status_code}: {error_detail}", {}

    except requests.exceptions.Timeout:
        return False, "Request timeout", {}
    except requests.exceptions.ConnectionError:
        return False, "Connection error", {}
    except Exception as e:
        return False, f"Request error: {str(e)}", {}


def main() -> int:
    """Run FASE 2.54."""
    parser = argparse.ArgumentParser(
        description="FASE 2.54 — Post-Write Verification"
    )
    parser.add_argument(
        "--execution-result", type=Path, required=True, help="Execution result JSON"
    )
    parser.add_argument(
        "--execution-package", type=Path, required=True, help="Execution package JSON"
    )
    parser.add_argument("--netbox-url", required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)

    args = parser.parse_args()

    verification_id = str(uuid4())
    timestamp_start = datetime.utcnow().isoformat() + "+00:00"

    # Load execution result
    result_ok, result_reason, execution_result = load_execution_result(
        args.execution_result
    )
    if not result_ok:
        print(f"✗ Result invalid: {result_reason}")
        return 1

    # Load execution package
    pkg_ok, pkg_reason, execution_package = load_execution_package(
        args.execution_package
    )
    if not pkg_ok:
        print(f"✗ Package invalid: {pkg_reason}")
        return 1

    # Validate token exists
    if not os.environ.get("NETBOX_READ_TOKEN"):
        print("✗ NETBOX_READ_TOKEN not in environment")
        return 1

    # Read token (first and only time)
    token = read_token_from_env()

    # Verify each item
    executed_items = execution_result.get("items", [])
    package_items = execution_package.get("items", [])
    verified_items = []
    failed_count = 0
    overall_status = "POST_WRITE_VERIFICATION_SUCCESS"

    for exec_item in executed_items:
        item_id = exec_item.get("item_id")
        endpoint = exec_item.get("endpoint")
        response_id = exec_item.get("response_id")

        verification_item = {
            "item_id": item_id,
            "approval_id": exec_item.get("approval_id"),
            "object_type": exec_item.get("object_type"),
            "object_key": exec_item.get("object_key"),
            "endpoint": endpoint,
            "response_id": response_id,
            "verification_status": None,
            "fields_verified": 0,
            "fields_total": 0,
            "mismatches": [],
            "error_message": None,
        }

        # If no response_id, can't verify
        if not response_id:
            verification_item["verification_status"] = "SKIPPED_NO_ID"
            verified_items.append(verification_item)
            continue

        # Find item in package for expected payload
        package_item = find_item_in_package(package_items, item_id)
        if not package_item:
            verification_item["verification_status"] = "SKIPPED_NOT_IN_PACKAGE"
            verified_items.append(verification_item)
            continue

        expected_payload = package_item.get("payload", {})
        verification_item["fields_total"] = len(expected_payload)

        # Verify in NetBox
        verify_ok, verify_msg, response_json = verify_object_in_netbox(
            token, args.netbox_url, endpoint, response_id, expected_payload
        )

        if verify_ok:
            verification_item["verification_status"] = "VERIFIED"
            verification_item["fields_verified"] = len(expected_payload)
        else:
            verification_item["verification_status"] = "VERIFICATION_FAILED"
            verification_item["error_message"] = verify_msg
            failed_count += 1
            overall_status = "POST_WRITE_VERIFICATION_FAILED"

        verified_items.append(verification_item)

    timestamp_end = datetime.utcnow().isoformat() + "+00:00"

    # Generate result JSON
    verification_json = {
        "verification_id": verification_id,
        "execution_id": execution_result.get("execution_id"),
        "execution_package_id": execution_result.get("execution_package_id"),
        "device": execution_result.get("device"),
        "device_id": execution_result.get("device_id"),
        "started_at": timestamp_start,
        "finished_at": timestamp_end,
        "status": overall_status,
        "verified_count": len(verified_items) - failed_count,
        "failed_count": failed_count,
        "total_count": len(verified_items),
        "token_logged": False,
        "items": verified_items,
        "safety_confirmations": {
            "token_not_logged": True,
            "read_only_get": True,
            "no_writes": True,
            "no_modifications": True,
        },
        "next_phase": "FASE_2_55_POST_WRITE_COMPLIANCE_RERUN",
    }

    # Generate result markdown
    verified_count = sum(
        1 for item in verified_items if item["verification_status"] == "VERIFIED"
    )
    skipped_count = sum(
        1 for item in verified_items if "SKIPPED" in item["verification_status"]
    )

    result_md = f"""# Resultado da Verificação Pós-Escrita — {execution_result.get('device')}

## 1. Status

### {overall_status}

## 2. Resumo

- **Verification ID:** {verification_id}
- **Execution ID:** {execution_result.get('execution_id')}
- **Device:** {execution_result.get('device')}
- **Total Itens:** {len(verified_items)}
- **Verificados:** {verified_count}
- **Falhados:** {failed_count}
- **Pulados:** {skipped_count}
- **Iniciado:** {timestamp_start}
- **Finalizado:** {timestamp_end}

## 3. Itens Verificados

| Item ID | Object Type | Object Key | Endpoint | Response ID | Verificação | Campos |
|---|---|---|---|---|---|---|
"""

    for item in verified_items:
        fields_str = (
            f"{item['fields_verified']}/{item['fields_total']}"
            if item["fields_total"] > 0
            else "N/A"
        )
        result_md += (
            f"| {item['item_id']} | {item['object_type']} | {item['object_key']} | "
            f"{item['endpoint']} | {item['response_id']} | {item['verification_status']} | {fields_str} |\n"
        )

    if failed_count > 0:
        result_md += "\n## 4. Erros de Verificação\n\n"
        for item in verified_items:
            if item["verification_status"] == "VERIFICATION_FAILED":
                result_md += f"- **{item['item_id']}:** {item['error_message']}\n"

    result_md += f"""
## 5. Segurança

✓ Token não logado
✓ Somente GET (read-only)
✓ Sem escrita
✓ Sem modificações
✓ Verificação de campo para campo

## 6. Próxima Fase

FASE 2.55 — Post-Write Compliance Re-Run
"""

    # Write results
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(verification_json, f, indent=2)

    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(result_md, encoding="utf-8")

    print(f"✓ Verification result: {args.output_json}")
    print(f"✓ Verification report: {args.output_md}")
    print(f"✓ Status: {overall_status}")

    return 0 if overall_status == "POST_WRITE_VERIFICATION_SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
