#!/usr/bin/env python3
"""Analyze service candidate readiness (read-only, no API writes)."""

import argparse
import json
import sys
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def load_import_plan(file_path: str) -> Dict:
    """Load ImportPlan JSON."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise ValueError(f"File not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")


def is_base_interface_name(name: str) -> bool:
    """Check if interface is base infrastructure (not subinterface/service)."""
    if not name:
        return False

    # Exclude subinterfaces
    if "." in name:
        return False

    # Exclude virtual service
    if re.match(r"^(Vlan|Virtual|irb|lo\d|null|NULL)", name, re.IGNORECASE):
        return False

    # Include base patterns
    base_patterns = [
        r"^(Eth-Trunk|Ethernet|GigabitEthernet|FastEthernet|TenGigabitEthernet)",
        r"^(10GE|25GE|40GE|100GE)",
        r"^(ae|bundle-ether)",
        r"^(Management|mgmt|mgt)",
    ]

    return any(re.match(p, name, re.IGNORECASE) for p in base_patterns)


def classify_readiness(item: Dict) -> Tuple[str, List[str]]:
    """Classify service candidate readiness."""
    errors = []
    object_type = item.get("object_type")
    object_key = item.get("object_key", "")
    evidence = item.get("evidence", {})

    # Reject base_inventory
    if is_base_interface_name(object_key):
        return "ignored", ["Not a service candidate (base infrastructure)"]

    # For interfaces
    if object_type == "interface":
        # Check fields
        if not object_key:
            errors.append("Missing object_key")

        # Subinterfaces need parent and VLAN
        if "." in object_key:
            parts = object_key.split(".")
            if len(parts) == 2:
                base, vlan = parts
                if not vlan.isdigit():
                    return "naming_failed", [f"VLAN part '{vlan}' not numeric"]
                if not is_base_interface_name(base):
                    return "naming_failed", [f"Base '{base}' not recognized"]
            else:
                errors.append(f"Invalid subinterface format: {object_key}")

        # Check for required metadata
        if not evidence.get("service_type"):
            errors.append("Missing service_type")
        if not evidence.get("tenant"):
            errors.append("Missing tenant")

        # Check description pattern (optional but recommended)
        description = evidence.get("description", "").strip()
        if description:
            # SERVICE_SLUG pattern
            pattern = r"^(customer-internet|customer-l2vpn|customer-l3vpn|customer-transport|carrier-transit|carrier-peering|ix-public|cdn-cache|infra-backbone|infra-management):[a-z0-9-]{2,32}:NB-[0-9]+(:[\w-]+)?$"
            if not re.match(pattern, description, re.IGNORECASE):
                # Not necessarily failed, just note it
                pass

    elif object_type == "bgp_peer":
        # BGP requires remote_as, remote_address, description
        if not evidence.get("remote_as"):
            errors.append("Missing remote_as")
        if not evidence.get("remote_address"):
            errors.append("Missing remote_address")
        if not evidence.get("description"):
            errors.append("Missing description")

    elif object_type == "ip_address":
        # IP requires address and interface/vrf
        if not evidence.get("address"):
            errors.append("Missing address")
        if not evidence.get("interface") and not evidence.get("vrf"):
            errors.append("Missing interface or vrf")

    # Classify based on errors
    if not errors:
        return "ready_for_review", []

    if any("Missing" in e for e in errors):
        return "missing_metadata", errors

    if any("naming" in e.lower() for e in errors):
        return "naming_failed", errors

    return "blocked", errors


def render_report(
    device: str,
    classifications: Dict[str, List[Dict]],
) -> str:
    """Render readiness report as Markdown."""
    lines = []

    lines.append(f"# Service Candidate Readiness — {device}")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now(timezone.utc).isoformat()}")
    lines.append("")

    # Summary
    total = sum(len(items) for items in classifications.values())
    lines.append("## 1. Resumo")
    lines.append("")
    lines.append(f"- Total service candidates: {total}")
    lines.append(f"- ready_for_review: {len(classifications.get('ready_for_review', []))}")
    lines.append(f"- missing_metadata: {len(classifications.get('missing_metadata', []))}")
    lines.append(f"- naming_failed: {len(classifications.get('naming_failed', []))}")
    lines.append(f"- ambiguous: {len(classifications.get('ambiguous', []))}")
    lines.append(f"- blocked: {len(classifications.get('blocked', []))}")
    lines.append(f"- ignored: {len(classifications.get('ignored', []))}")
    lines.append("")

    # Ready for review
    ready = classifications.get("ready_for_review", [])
    lines.append("## 2. Ready for Review")
    lines.append("")
    if ready:
        lines.append("| # | Type | Key | Service Type | Tenant |")
        lines.append("|---|------|-----|--------------|--------|")
        for i, item in enumerate(ready, 1):
            evidence = item.get("evidence", {})
            lines.append(f"| {i} | {item.get('object_type')} | {item.get('object_key')} | {evidence.get('service_type', '?')} | {evidence.get('tenant', '?')} |")
        lines.append("")
    else:
        lines.append("Nenhum item ready.")
        lines.append("")

    # Missing metadata
    missing = classifications.get("missing_metadata", [])
    lines.append("## 3. Missing Required Metadata")
    lines.append("")
    if missing:
        for item in missing:
            key = item.get("object_key")
            reasons = item.get("reasons", [])
            lines.append(f"- **{key}** ({item.get('object_type')})")
            for reason in reasons:
                lines.append(f"  - {reason}")
        lines.append("")
    else:
        lines.append("Nenhum item missing metadata.")
        lines.append("")

    # Naming failed
    naming = classifications.get("naming_failed", [])
    lines.append("## 4. Naming Failed")
    lines.append("")
    if naming:
        for item in naming:
            key = item.get("object_key")
            reasons = item.get("reasons", [])
            lines.append(f"- **{key}** ({item.get('object_type')})")
            for reason in reasons:
                lines.append(f"  - {reason}")
        lines.append("")
    else:
        lines.append("Nenhum item naming_failed.")
        lines.append("")

    # Blocked
    blocked = classifications.get("blocked", [])
    lines.append("## 5. Blocked")
    lines.append("")
    if blocked:
        for item in blocked:
            key = item.get("object_key")
            reasons = item.get("reasons", [])
            lines.append(f"- **{key}** ({item.get('object_type')})")
            for reason in reasons:
                lines.append(f"  - {reason}")
        lines.append("")
    else:
        lines.append("Nenhum item bloqueado.")
        lines.append("")

    # Ignored
    ignored = classifications.get("ignored", [])
    lines.append("## 6. Ignored")
    lines.append("")
    if ignored:
        lines.append(f"{len(ignored)} items ignorados (base_inventory ou fora de escopo).")
    else:
        lines.append("Nenhum item ignorado.")
    lines.append("")

    # Notes
    lines.append("## 7. Observações")
    lines.append("")
    lines.append("- ✅ Análise read-only (nenhuma API write)")
    lines.append("- ✅ Nenhum token write usado")
    lines.append("- ✅ Nenhuma escrita NetBox")
    lines.append("- ✅ Nenhuma configuração em equipamento")
    lines.append("- ✅ Próxima fase: enriquecimento manual ou aprovação de items ready_for_review")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze service candidate readiness (read-only, no API writes)"
    )
    parser.add_argument("--import-plan", required=True, help="ImportPlan JSON file")
    parser.add_argument("--output", required=True, help="Output Markdown file")
    parser.add_argument("--device", required=True, help="Device name")
    args = parser.parse_args()

    try:
        # Load ImportPlan
        import_plan = load_import_plan(args.import_plan)

        # Extract service candidates
        items = import_plan.get("items", [])
        print(f"Processing {len(items)} items...")
        print("")

        # Classify each item
        classifications = {
            "ready_for_review": [],
            "missing_metadata": [],
            "naming_failed": [],
            "ambiguous": [],
            "blocked": [],
            "ignored": [],
        }

        for item in items:
            readiness, reasons = classify_readiness(item)
            classifications[readiness].append({
                "object_type": item.get("object_type"),
                "object_key": item.get("object_key"),
                "evidence": item.get("evidence"),
                "reasons": reasons,
            })

        print("Classification results:")
        for category, items_list in classifications.items():
            print(f"  {category}: {len(items_list)}")
        print("")

        # Render report
        report = render_report(args.device, classifications)

        # Save report
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"✓ Report saved: {output_path}")
        print("")
        print(report)

        return 0

    except ValueError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
