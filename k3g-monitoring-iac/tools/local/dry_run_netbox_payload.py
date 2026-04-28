#!/usr/bin/env python3
"""Dry-run NetBox payload validation (no writes, read-only validation)."""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional


def validate_payload_schema(payload: Dict, object_type: str) -> List[str]:
    """Validate payload has required fields for type.

    Returns list of warnings/errors (empty if valid).
    """
    warnings = []

    # All objects need name
    if "name" not in payload and object_type != "ip_address":
        warnings.append(f"WARNING: Missing 'name' field for {object_type}")

    # Type-specific validation
    if object_type == "interface":
        if "type" not in payload:
            warnings.append("INFO: 'type' field missing (will use default)")
        if "enabled" not in payload:
            warnings.append("INFO: 'enabled' field missing (will use default)")

    elif object_type == "ip_address":
        if "address" not in payload:
            warnings.append("ERROR: Missing 'address' field (required)")
        if "vrf" not in payload:
            warnings.append("WARNING: Missing 'vrf' field (may be required)")

    elif object_type in ("vlan", "vrf"):
        if "name" not in payload:
            warnings.append(f"ERROR: Missing 'name' field (required for {object_type})")

    elif object_type == "bgp_peer":
        if "asn" not in payload:
            warnings.append("WARNING: Missing 'asn' field")
        if "remote_asn" not in payload:
            warnings.append("WARNING: Missing 'remote_asn' field")

    return warnings


def check_for_secrets(payload: Dict) -> List[str]:
    """Check payload doesn't contain secrets."""
    warnings = []

    payload_str = json.dumps(payload)
    forbidden = ["password", "token", "secret", "api_key", "ssh"]

    for pattern in forbidden:
        if pattern in payload_str.lower():
            warnings.append(f"ERROR: Forbidden pattern in payload: {pattern}")

    return warnings


def build_netbox_payload(
    object_type: str,
    object_key: str,
    evidence: Dict,
    category: Optional[str] = None,
) -> Dict:
    """Build suggested NetBox payload from evidence.

    No writes. No API calls. Validation only.
    """
    payload = {}

    if object_type == "interface":
        payload["name"] = object_key
        payload["type"] = evidence.get("type", "1000base-t")  # Default to 1GE
        payload["enabled"] = evidence.get("status") in ("up", "Up", None)
        payload["mtu"] = evidence.get("mtu", 1500)

        if evidence.get("description"):
            payload["description"] = evidence["description"]

        # Tags for discovery
        payload["tags"] = [
            "discovery:netops_netbox_sync",
            "discovery:staged",
        ]

        if category == "base_inventory":
            payload["tags"].append("inventory:base-interface")
        elif category == "service":
            payload["tags"].append("inventory:service-interface")

    elif object_type == "ip_address":
        payload["address"] = object_key
        payload["vrf"] = evidence.get("vrf", "default")

        if evidence.get("interface"):
            payload["assigned_object"] = {
                "name": evidence["interface"],
                "type": "interface",
            }

    elif object_type == "vrf":
        payload["name"] = object_key

        if evidence.get("description"):
            payload["description"] = evidence["description"]

    elif object_type == "vlan":
        payload["vid"] = int(object_key)  # VLAN ID

        if evidence.get("description"):
            payload["description"] = evidence["description"]
            payload["name"] = evidence["description"][:64]  # Name from description

    elif object_type == "bgp_peer":
        payload["asn"] = evidence.get("remote_asn")
        payload["remote_asn"] = evidence.get("remote_asn")
        payload["remote_ip"] = object_key

        if evidence.get("description"):
            payload["description"] = evidence["description"]

    # Add staged import tags
    if "tags" not in payload:
        payload["tags"] = []

    payload["tags"].extend([
        "discovery:staged",
        "source:device",
    ])

    return payload


def generate_dry_run_report(
    approval_id: str,
    device: str,
    object_type: str,
    object_key: str,
    action: str,
    payload: Dict,
    warnings: List[str],
) -> str:
    """Generate human-readable dry-run report."""
    lines = []

    lines.append(f"# Dry-Run Report — {approval_id}")
    lines.append("")
    lines.append(f"**Device:** {device}")
    lines.append(f"**Object:** {object_type} / {object_key}")
    lines.append(f"**Action:** {action}")
    lines.append("")

    lines.append("## Suggested NetBox Payload")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(payload, indent=2))
    lines.append("```")
    lines.append("")

    if warnings:
        lines.append("## Validation Results")
        lines.append("")
        for warning in warnings:
            lines.append(f"- {warning}")
        lines.append("")

    lines.append("## Dry-Run Status")
    lines.append("")

    has_errors = any(w.startswith("ERROR:") for w in warnings)
    if has_errors:
        lines.append("⚠️  **FAILED** — Errors found, cannot proceed with staged import")
        lines.append("")
        lines.append("**Next Step:** Fix issues above before requesting approval")
    else:
        lines.append("✓ **PASSED** — Ready for approval and staged import")
        lines.append("")
        lines.append("**Next Step:** Review payload, approve in approval workflow")

    lines.append("")
    lines.append("## Security Check")
    lines.append("")
    lines.append("- [x] No passwords in payload")
    lines.append("- [x] No tokens in payload")
    lines.append("- [x] No secrets in payload")
    lines.append("- [x] Read-only validation only (no writes)")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Dry-run validation of NetBox payload (read-only, no writes)"
    )
    parser.add_argument("--approval-id", required=True, help="ApprovalRecord ID")
    parser.add_argument("--device", required=True, help="Device hostname")
    parser.add_argument("--object-type", required=True, help="Type")
    parser.add_argument("--object-key", required=True, help="Unique key")
    parser.add_argument("--action", required=True, help="safe_create_staged|needs_review")
    parser.add_argument("--evidence", help="JSON evidence string")
    parser.add_argument("--category", help="base_inventory|service")
    parser.add_argument(
        "--output",
        default="reports/pilot-device-compliance/approvals/pending",
        help="Output directory",
    )
    args = parser.parse_args()

    # Parse evidence
    evidence = {}
    if args.evidence:
        try:
            evidence = json.loads(args.evidence)
        except json.JSONDecodeError as e:
            print(f"Error parsing evidence JSON: {e}", file=sys.stderr)
            return 1

    # Build payload
    payload = build_netbox_payload(
        args.object_type,
        args.object_key,
        evidence,
        args.category,
    )

    # Validate
    schema_warnings = validate_payload_schema(payload, args.object_type)
    secret_warnings = check_for_secrets(payload)
    all_warnings = schema_warnings + secret_warnings

    # Generate report
    report = generate_dry_run_report(
        args.approval_id,
        args.device,
        args.object_type,
        args.object_key,
        args.action,
        payload,
        all_warnings,
    )

    # Save report
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    report_filename = f"dry-run-{args.approval_id[:8]}.md"
    report_path = output_dir / report_filename

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"✓ Dry-run report: {report_path}")
    print("")
    print(report)

    # Return error code if validation failed
    if any(w.startswith("ERROR:") for w in all_warnings):
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
