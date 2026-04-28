#!/usr/bin/env python3
"""Create local ApprovalRecord from ImportPlan item (read-only, no NetBox writes)."""

import argparse
import hashlib
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional


def generate_approval_id() -> str:
    """Generate UUID for approval record."""
    return str(uuid.uuid4())


def calculate_hash(content: str) -> str:
    """Calculate SHA256 hash of content."""
    return "sha256:" + hashlib.sha256(content.encode()).hexdigest()


def create_approval_record(
    device: str,
    device_id: int,
    object_type: str,
    object_key: str,
    action: str,
    code: str,
    category: Optional[str],
    reason: str,
    confidence: str,
    naming_compliant: bool,
    evidence: Dict,
    report_path: str,
    report_timestamp: str,
    import_plan_id: Optional[str] = None,
) -> Dict:
    """Create ApprovalRecord (no writes, no secrets, audit-ready).

    Args:
        device: Device hostname
        device_id: NetBox DCIM ID
        object_type: Type (interface, ip_address, vrf, vlan, bgp_peer, etc)
        object_key: Unique key (Eth-Trunk0, 10.0.0.1/24, etc)
        action: safe_create_staged | needs_review | blocked | ignore
        code: Divergence code (INTERFACE_MISSING_IN_NETBOX, etc)
        category: base_inventory | service | None
        reason: Classification reason
        confidence: exact | normalized | possible | ambiguous | none
        naming_compliant: Boolean
        evidence: Evidence dict from divergence
        report_path: Path to compliance report
        report_timestamp: ISO8601 timestamp of report
        import_plan_id: ID of source ImportPlan (optional)

    Returns:
        ApprovalRecord dict (ready to persist as JSON)

    Raises:
        ValueError: If action is blocked/ignore or invalid state
    """
    # Validation: cannot approve blocked or ignore items
    if action in ("blocked", "ignore"):
        raise ValueError(
            f"Cannot create approval for action={action}. "
            "Items must be safe_create_staged or needs_review."
        )

    # Validation: service items must have valid naming
    if category == "service" and not naming_compliant:
        raise ValueError(
            f"Service interface {object_key} has invalid naming. "
            "Must follow base.vlan_id pattern (e.g., Eth-Trunk0.1580)."
        )

    # Validation: no secrets in evidence
    evidence_str = json.dumps(evidence)
    forbidden = ["password", "token", "secret", "api_key", "ssh_password"]
    for pattern in forbidden:
        if pattern in evidence_str.lower():
            raise ValueError(f"Forbidden pattern in evidence: {pattern}")

    # Generate IDs and hashes
    approval_id = generate_approval_id()
    import_plan_id = import_plan_id or str(uuid.uuid4())
    evidence_hash = calculate_hash(evidence_str)

    now = datetime.now(timezone.utc).isoformat() + "Z"

    record = {
        "approval_id": approval_id,
        "import_plan_id": import_plan_id,
        "device": device,
        "device_id": device_id,
        "generated_at": now,
        "proposal": {
            "object_type": object_type,
            "object_key": object_key,
            "code": code,
            "action": action,
            "category": category,
            "confidence": confidence,
            "naming_compliant": naming_compliant,
            "reason": reason,
            "preferred_next_step": (
                "Revisar payload sugerido e aplicar staged import"
                if action == "safe_create_staged"
                else "Revisar evidência e solicitar mudanças ou rejeitar"
            ),
        },
        "evidence": evidence,
        "review": {
            "status": "proposed",
            "reviewed_by": None,
            "reviewed_at": None,
            "decision": None,
            "comment": None,
            "changes_requested": [],
            "expected_netbox_payload": None,
        },
        "audit": {
            "created_at": now,
            "updated_at": now,
            "created_by": "approval-engine",
            "report_path": report_path,
            "report_timestamp": report_timestamp,
            "evidence_hash": evidence_hash,
            "import_plan_hash": None,
        },
        "future_staging": {
            "dry_run_id": None,
            "dry_run_status": None,
            "dry_run_passed_at": None,
            "applied_at": None,
            "applied_by": None,
            "staged_import_id": None,
            "deployment_timestamp": None,
        },
        "metadata": {
            "version": "1.0",
            "source": "ImportPlan",
            "priority": "normal",
            "requires_2fa": False,
            "requires_2_approvers": False,
            "sla_hours": 24,
            "ttl_days": 90,
        },
    }

    return record


def save_approval_record(record: Dict, output_dir: Path) -> Path:
    """Save ApprovalRecord to JSON file."""
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    device = record["device"]
    approval_id = record["approval_id"][:8]  # Short prefix
    timestamp = record["generated_at"].replace(":", "").replace("-", "").split("Z")[0]

    filename = f"approval-{device}-{approval_id}-{timestamp}.json"
    filepath = output_dir / filename

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)

    return filepath


def main():
    parser = argparse.ArgumentParser(
        description="Create local ApprovalRecord from ImportPlan item (read-only)"
    )
    parser.add_argument("--device", required=True, help="Device hostname")
    parser.add_argument("--device-id", type=int, required=True, help="NetBox DCIM ID")
    parser.add_argument("--object-type", required=True, help="Type (interface, ip_address, etc)")
    parser.add_argument("--object-key", required=True, help="Unique key (Eth-Trunk0, etc)")
    parser.add_argument(
        "--action",
        required=True,
        choices=["safe_create_staged", "needs_review"],
        help="Action classification",
    )
    parser.add_argument("--code", required=True, help="Divergence code")
    parser.add_argument("--category", help="base_inventory | service")
    parser.add_argument("--reason", required=True, help="Classification reason")
    parser.add_argument(
        "--confidence",
        required=True,
        choices=["exact", "normalized", "possible", "ambiguous", "none"],
        help="Confidence level",
    )
    parser.add_argument(
        "--naming-compliant",
        action="store_true",
        help="Set if naming is compliant",
    )
    parser.add_argument("--evidence", help="JSON evidence string")
    parser.add_argument("--report-path", required=True, help="Path to compliance report")
    parser.add_argument("--report-timestamp", required=True, help="ISO8601 report timestamp")
    parser.add_argument(
        "--import-plan-id", help="Source ImportPlan ID (optional)"
    )
    parser.add_argument(
        "--output",
        default="reports/pilot-device-compliance/approvals/pending",
        help="Output directory (default: pending/)",
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

    # Create record
    try:
        record = create_approval_record(
            device=args.device,
            device_id=args.device_id,
            object_type=args.object_type,
            object_key=args.object_key,
            action=args.action,
            code=args.code,
            category=args.category,
            reason=args.reason,
            confidence=args.confidence,
            naming_compliant=args.naming_compliant,
            evidence=evidence,
            report_path=args.report_path,
            report_timestamp=args.report_timestamp,
            import_plan_id=args.import_plan_id,
        )
    except ValueError as e:
        print(f"Error creating record: {e}", file=sys.stderr)
        return 1

    # Save
    try:
        filepath = save_approval_record(record, args.output)
        print(f"✓ Created: {filepath}")
        print(f"  ID: {record['approval_id']}")
        print(f"  Status: {record['review']['status']}")
        return 0
    except Exception as e:
        print(f"Error saving record: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
