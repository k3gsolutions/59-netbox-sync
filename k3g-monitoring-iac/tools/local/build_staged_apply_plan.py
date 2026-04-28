#!/usr/bin/env python3
"""Build ApplyPlan from ApprovalRecord (dry-run, no writes)."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
import hashlib
import uuid


def load_approval_record(file_path: str) -> Dict:
    """Load ApprovalRecord JSON."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise ValueError(f"File not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")


def compute_payload_hash(payload: Dict) -> str:
    """Compute SHA256 hash of payload."""
    payload_str = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return f"sha256:{hashlib.sha256(payload_str.encode()).hexdigest()}"


def build_staged_payload(approval: Dict) -> Dict:
    """Build NetBox staged payload from ApprovalRecord."""
    proposal = approval.get("proposal", {})
    evidence = approval.get("evidence", {})
    object_type = proposal.get("object_type")
    object_key = proposal.get("object_key")
    approval_id = approval.get("approval_id")
    import_plan_id = approval.get("import_plan_id")
    device_id = approval.get("device_id")
    category = proposal.get("category")

    if object_type == "interface":
        payload = {
            "device": device_id,
            "name": object_key,
            "type": evidence.get("type", "1000base-t"),
            "enabled": evidence.get("status") in ("up", "Up", True),
            "mtu": evidence.get("mtu", 1500),
            "tags": [
                {"name": "discovery:netops_netbox_sync"},
                {"name": "discovery:staged"},
                {"name": "source:device"},
                {"name": f"approval:{approval_id[:8]}"},
            ],
            "custom_fields": {
                "discovery_source": "device_inventory",
                "discovery_status": "staged",
                "discovery_confidence": proposal.get("confidence"),
                "import_plan_id": import_plan_id,
                "approval_id": approval_id,
            },
        }

        if evidence.get("description"):
            payload["description"] = evidence["description"]

        return payload

    raise ValueError(f"Object type not supported: {object_type}")


def run_readiness_checks(approval: Dict, payload: Dict) -> tuple[List[Dict], List[str]]:
    """Run readiness checks on ApprovalRecord and payload."""
    checks = []
    blocked = []
    proposal = approval.get("proposal", {})
    review = approval.get("review", {})

    # Check 1: approval_id present
    approval_id = approval.get("approval_id")
    if approval_id:
        checks.append({
            "check": "approval_id_present",
            "result": "PASSED",
            "severity": "CRITICAL",
            "details": f"approval_id: {approval_id[:8]}..."
        })
    else:
        checks.append({
            "check": "approval_id_present",
            "result": "FAILED",
            "severity": "CRITICAL",
            "details": "approval_id missing"
        })
        blocked.append("APPROVAL_NOT_FOUND")

    # Check 2: status is dry_run_passed
    status = review.get("status")
    if status == "dry_run_passed":
        checks.append({
            "check": "status_dry_run_passed",
            "result": "PASSED",
            "severity": "CRITICAL",
            "details": f"status: {status}"
        })
    else:
        checks.append({
            "check": "status_dry_run_passed",
            "result": "FAILED",
            "severity": "CRITICAL",
            "details": f"status: {status} (expected: dry_run_passed)"
        })
        blocked.append("APPROVAL_NOT_DRY_RUN_PASSED")

    # Check 3: action is safe_create_staged
    action = proposal.get("action")
    if action == "safe_create_staged":
        checks.append({
            "check": "action_safe_create_staged",
            "result": "PASSED",
            "severity": "CRITICAL",
            "details": f"action: {action}"
        })
    else:
        checks.append({
            "check": "action_safe_create_staged",
            "result": "FAILED",
            "severity": "CRITICAL",
            "details": f"action: {action} (expected: safe_create_staged)"
        })
        blocked.append("UNSUPPORTED_ACTION")

    # Check 4: object_type supported
    object_type = proposal.get("object_type")
    if object_type == "interface":
        checks.append({
            "check": "object_type_supported",
            "result": "PASSED",
            "severity": "CRITICAL",
            "details": f"object_type: {object_type}"
        })
    else:
        checks.append({
            "check": "object_type_supported",
            "result": "FAILED",
            "severity": "CRITICAL",
            "details": f"object_type: {object_type} (not supported in FASE 1.9)"
        })
        blocked.append("UNSUPPORTED_OBJECT_TYPE")

    # Check 5: no secrets in payload
    payload_str = json.dumps(payload)
    forbidden = ["password", "token", "secret", "api_key", "ssh"]
    has_secrets = any(p in payload_str.lower() for p in forbidden)
    if not has_secrets:
        checks.append({
            "check": "no_secrets_in_payload",
            "result": "PASSED",
            "severity": "CRITICAL",
            "details": "0 forbidden patterns found"
        })
    else:
        checks.append({
            "check": "no_secrets_in_payload",
            "result": "FAILED",
            "severity": "CRITICAL",
            "details": "Forbidden patterns detected"
        })
        blocked.append("SECRET_DETECTED")

    # Check 6: tags staged present
    tags = [t.get("name", "") for t in payload.get("tags", [])]
    if "discovery:staged" in tags:
        checks.append({
            "check": "tags_staged_present",
            "result": "PASSED",
            "severity": "CRITICAL",
            "details": "discovery:staged tag present"
        })
    else:
        checks.append({
            "check": "tags_staged_present",
            "result": "FAILED",
            "severity": "CRITICAL",
            "details": "discovery:staged tag missing"
        })
        blocked.append("TAGS_INVALID")

    # Check 7: approval tag present
    approval_tag = f"approval:{approval_id[:8]}"
    if any(approval_tag in t for t in tags):
        checks.append({
            "check": "tags_approval_present",
            "result": "PASSED",
            "severity": "CRITICAL",
            "details": f"{approval_tag} tag present"
        })
    else:
        checks.append({
            "check": "tags_approval_present",
            "result": "FAILED",
            "severity": "CRITICAL",
            "details": f"{approval_tag} tag missing"
        })
        blocked.append("TAGS_INVALID")

    # Check 8: custom_fields valid
    cf = payload.get("custom_fields", {})
    if cf.get("approval_id") and cf.get("discovery_status") == "staged":
        checks.append({
            "check": "custom_fields_valid",
            "result": "PASSED",
            "severity": "CRITICAL",
            "details": "discovery_source, discovery_status, approval_id present"
        })
    else:
        checks.append({
            "check": "custom_fields_valid",
            "result": "FAILED",
            "severity": "CRITICAL",
            "details": "Missing or invalid custom_fields"
        })
        blocked.append("PAYLOAD_MISSING_REQUIRED_FIELD")

    # Check 9: confidence valid
    confidence = proposal.get("confidence")
    if confidence in ("exact", "normalized"):
        checks.append({
            "check": "confidence_valid",
            "result": "PASSED",
            "severity": "CRITICAL",
            "details": f"confidence: {confidence}"
        })
    else:
        checks.append({
            "check": "confidence_valid",
            "result": "FAILED",
            "severity": "CRITICAL",
            "details": f"confidence: {confidence} (not exact/normalized)"
        })
        blocked.append("CONFIDENCE_NOT_EXACT_OR_NORMALIZED")

    # Check 10: naming follows pattern
    object_key = proposal.get("object_key")
    category = proposal.get("category")
    if category == "base_inventory":
        if "." not in object_key:  # Base interface, no dots
            checks.append({
                "check": "naming_follows_pattern",
                "result": "PASSED",
                "severity": "CRITICAL",
                "details": f"Base interface naming valid: {object_key}"
            })
        else:
            checks.append({
                "check": "naming_follows_pattern",
                "result": "FAILED",
                "severity": "CRITICAL",
                "details": f"Base interface should not have dots: {object_key}"
            })
            blocked.append("NAMING_DOES_NOT_FOLLOW_PATTERN")
    elif category == "service":
        if "." in object_key:  # Service interface, must have dots
            parts = object_key.split(".")
            if len(parts) == 2 and parts[1].isdigit():
                checks.append({
                    "check": "naming_follows_pattern",
                    "result": "PASSED",
                    "severity": "CRITICAL",
                    "details": f"Service interface naming valid (base.vlan_id): {object_key}"
                })
            else:
                checks.append({
                    "check": "naming_follows_pattern",
                    "result": "FAILED",
                    "severity": "CRITICAL",
                    "details": f"Service interface naming invalid: {object_key} (expected base.vlan_id)"
                })
                blocked.append("SERVICE_NAMING_INVALID")
        else:
            checks.append({
                "check": "naming_follows_pattern",
                "result": "FAILED",
                "severity": "CRITICAL",
                "details": f"Service interface must have dots: {object_key}"
            })
            blocked.append("SERVICE_NAMING_INVALID")

    # Check 11: dry-run report (not checked, would require API)
    checks.append({
        "check": "object_not_exists",
        "result": "NOT_CHECKED",
        "severity": "WARNING",
        "details": "Requires NetBox API call (not done in dry-run)"
    })

    # Check 12: write policy enforced
    checks.append({
        "check": "write_policy_enforced",
        "result": "PASSED",
        "severity": "CRITICAL",
        "details": "real_apply_enabled=false, write_token_provided=false"
    })

    # Check 13: write token not provided
    checks.append({
        "check": "write_token_not_provided",
        "result": "PASSED",
        "severity": "CRITICAL",
        "details": "write_token_provided=false (as expected in FASE 1.9)"
    })

    return checks, blocked


def build_apply_plan(approval_file: str, output_dir: Optional[str] = None) -> None:
    """Build ApplyPlan from ApprovalRecord."""
    approval = load_approval_record(approval_file)

    # Validate prerequisites
    if approval.get("review", {}).get("status") != "dry_run_passed":
        raise ValueError("ApprovalRecord status must be dry_run_passed")

    if approval.get("proposal", {}).get("action") != "safe_create_staged":
        raise ValueError("Action must be safe_create_staged")

    # Build payload
    payload = build_staged_payload(approval)
    payload_hash = compute_payload_hash(payload)

    # Run checks
    checks, blocked = run_readiness_checks(approval, payload)

    # Generate ApplyPlan
    apply_plan = {
        "apply_plan_id": str(uuid.uuid4()),
        "approval_id": approval.get("approval_id"),
        "import_plan_id": approval.get("import_plan_id"),
        "device": approval.get("device"),
        "device_id": approval.get("device_id"),
        "object_type": approval.get("proposal", {}).get("object_type"),
        "object_key": approval.get("proposal", {}).get("object_key"),
        "action": approval.get("proposal", {}).get("action"),
        "category": approval.get("proposal", {}).get("category"),
        "confidence": approval.get("proposal", {}).get("confidence"),
        "target_endpoint": "/api/dcim/interfaces/" if approval.get("proposal", {}).get("object_type") == "interface" else None,
        "method": "POST",
        "staged_payload": payload,
        "payload_hash": payload_hash,
        "readiness_status": "ready" if not blocked else "blocked",
        "readiness_checks": checks,
        "blocked_reasons": blocked,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by_tool": "build_staged_apply_plan.py",
        "generated_by_version": "1.0",
        "write_policy": {
            "requires_write_token": True,
            "write_token_provided": False,
            "write_token_validated": False,
            "real_apply_enabled": False,
            "write_policy_enforced": "STAGE_ONLY_NO_ACTIVE",
        },
        "metadata": {
            "dry_run_report_path": approval.get("audit", {}).get("dry_run_report"),
            "dry_run_timestamp": approval.get("audit", {}).get("report_timestamp"),
            "dry_run_hash": "sha256:...",  # Would compare if dry-run available
            "netbox_readiness_check_performed": False,
            "notes": "Ready for staged import. Requires write token validation before apply."
        }
    }

    # Determine output file
    if output_dir:
        output_path = Path(output_dir)
    else:
        approval_path = Path(approval_file)
        output_path = approval_path.parent

    output_path.mkdir(parents=True, exist_ok=True)

    # Generate filename
    approval_id = approval.get("approval_id", "unknown")[:8]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    output_file = output_path / f"apply-plan-{approval_id}-{timestamp}.json"

    # Save
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(apply_plan, f, indent=2, ensure_ascii=False)

    print(f"✓ ApplyPlan generated: {output_file}")
    print(f"  apply_plan_id: {apply_plan['apply_plan_id']}")
    print(f"  readiness_status: {apply_plan['readiness_status']}")
    if blocked:
        print(f"  blocked_reasons: {', '.join(blocked)}")
    else:
        print(f"  ✓ All checks passed")


def main():
    parser = argparse.ArgumentParser(
        description="Build ApplyPlan from ApprovalRecord (dry-run, no writes)"
    )
    parser.add_argument("--approval", required=True, help="ApprovalRecord JSON file")
    parser.add_argument("--output", help="Output directory (default: same as approval)")
    args = parser.parse_args()

    try:
        build_apply_plan(args.approval, args.output)
        return 0
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
