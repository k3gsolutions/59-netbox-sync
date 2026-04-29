#!/usr/bin/env python3
"""
Validate Week 1 metadata collection responses from service teams.

Read template, check for responses, validate, and classify readiness.
Zero NetBox API calls, zero writes.

Usage:
    python3 validate_week1_responses.py \
        --template <path/to/template.csv> \
        --responses-dir <path/to/week1-responses> \
        --output <path/to/output.md> \
        --device <device_name>
"""

import argparse
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


def parse_args():
    parser = argparse.ArgumentParser(
        description="Validate Week 1 metadata responses"
    )
    parser.add_argument("--template", required=True, help="Template CSV file")
    parser.add_argument("--responses-dir", required=True, help="Responses directory")
    parser.add_argument("--output", required=True, help="Output markdown file")
    parser.add_argument("--device", required=True, help="Device name")
    return parser.parse_args()


def load_template(template_file: str) -> List[Dict]:
    """Load template CSV."""
    items = []
    with open(template_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            items.append(row)
    return items


def find_responses(responses_dir: str) -> Dict[str, Dict]:
    """Find response files in responses directory."""
    responses = {
        "service_team": None,
        "network_ops": None,
        "bgp_team": None,
    }

    response_path = Path(responses_dir)
    if not response_path.exists():
        return responses

    for f in response_path.glob("*.csv"):
        if "service" in f.name.lower():
            responses["service_team"] = str(f)
        elif "network" in f.name.lower() or "ops" in f.name.lower():
            responses["network_ops"] = str(f)
        elif "bgp" in f.name.lower():
            responses["bgp_team"] = str(f)

    return responses


def validate_response(item: Dict, response: Dict) -> Tuple[str, str]:
    """
    Validate response against template item.
    Return (status, reason).
    """
    object_type = item.get("object_type", "").lower()
    object_key = item.get("object_key", "")

    # Check if all required fields filled
    if object_type == "subinterface":
        required = ["tenant", "service_type", "criticality", "owner"]
        missing = [f for f in required if not response.get(f, "").strip()]
        if missing:
            return ("needs_clarification", f"Missing: {', '.join(missing)}")
        return ("validated", "All required fields present")

    elif object_type == "ip_address":
        relation_type = response.get("relation_type", "").strip()
        detected_interface = response.get("detected_interface", "").strip()
        detected_vrf = response.get("detected_vrf", "").strip()
        required = ["owner", "evidence", "relation_type"]
        missing = [f for f in required if not response.get(f, "").strip()]
        if not response.get("interface", "").strip() and not detected_interface:
            missing.append("interface")
        if not response.get("vrf", "").strip() and not detected_vrf:
            missing.append("vrf")
        if relation_type == "service" and not response.get("service_relation", "").strip():
            missing.append("service_relation")
        if relation_type == "unknown" and not response.get("notes", "").strip():
            missing.append("notes")
        if missing:
            return ("needs_clarification", f"Missing: {', '.join(missing)}")
        return ("validated", "All required fields present")

    elif object_type == "bgp_peer":
        required = ["remote_asn", "remote_bgp_group", "owner"]
        missing = [f for f in required if not response.get(f, "").strip()]
        if missing:
            return ("needs_clarification", f"Missing: {', '.join(missing)}")
        return ("validated", "All required fields present")

    return ("unknown", "Unknown object type")


def classify_items(template: List[Dict], responses: Dict[str, Dict]) -> Dict:
    """Classify all items by readiness."""
    classified = {
        "validated": [],
        "needs_clarification": [],
        "blocked": [],
        "rejected": [],
        "still_pending": [],
    }

    for item in template:
        object_key = item.get("object_key", "")
        object_type = item.get("object_type", "").lower()
        team = item.get("responsible_team", "").lower()

        # Check if response exists
        response_file = None
        if "service" in team:
            response_file = responses.get("service_team")
        elif "network" in team or "ops" in team:
            response_file = responses.get("network_ops")
        elif "bgp" in team:
            response_file = responses.get("bgp_team")

        if not response_file:
            classified["still_pending"].append({
                "object_key": object_key,
                "object_type": object_type,
                "team": team,
                "reason": "No response file found",
            })
            continue

        # Load response file and find matching item
        try:
            with open(response_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                found = False
                for row in reader:
                    if row.get("object_key") == object_key or object_key in str(row):
                        status, reason = validate_response(item, row)
                        classified[status].append({
                            "object_key": object_key,
                            "object_type": object_type,
                            "team": team,
                            "reason": reason,
                            "response": row,
                        })
                        found = True
                        break

                if not found:
                    classified["still_pending"].append({
                        "object_key": object_key,
                        "object_type": object_type,
                        "team": team,
                        "reason": "Not found in response file",
                    })
        except Exception as e:
            classified["blocked"].append({
                "object_key": object_key,
                "object_type": object_type,
                "team": team,
                "reason": f"Error reading response: {str(e)}",
            })

    return classified


def generate_report(device: str, template: List[Dict], classified: Dict) -> str:
    """Generate markdown report."""
    timestamp = datetime.utcnow().isoformat() + "+00:00"

    report = f"""# Week 1 Response Validation — {device}

**Device:** {device}
**Generated:** {timestamp}
**Status:** Response intake + validation

---

## 1. Summary

| Status | Count |
|--------|-------|
| Validated | {len(classified['validated'])} |
| Needs Clarification | {len(classified['needs_clarification'])} |
| Still Pending | {len(classified['still_pending'])} |
| Blocked | {len(classified['blocked'])} |
| Rejected | {len(classified['rejected'])} |
| **TOTAL** | **{len(template)}** |

---

## 2. Validated (Ready for Week 2 Review)

Items with all required fields present and valid:

"""
    if classified['validated']:
        report += "| Object Key | Type | Team | Status |\n"
        report += "|------------|------|------|--------|\n"
        for item in classified['validated']:
            report += f"| {item['object_key']} | {item['object_type']} | {item['team']} | ✓ |\n"
    else:
        report += "No validated items yet.\n"

    report += "\n---\n\n"
    report += "## 3. Needs Clarification\n\n"
    report += "Items missing required fields or with incomplete responses:\n\n"

    if classified['needs_clarification']:
        report += "| Object Key | Type | Team | Issue |\n"
        report += "|------------|------|------|-------|\n"
        for item in classified['needs_clarification']:
            report += f"| {item['object_key']} | {item['object_type']} | {item['team']} | {item['reason']} |\n"
    else:
        report += "No clarification needed.\n"

    report += "\n---\n\n"
    report += "## 4. Still Pending\n\n"
    report += "Items without responses yet:\n\n"

    if classified['still_pending']:
        report += "| Object Key | Type | Team |\n"
        report += "|------------|------|------|\n"
        for item in classified['still_pending']:
            report += f"| {item['object_key']} | {item['object_type']} | {item['team']} |\n"
    else:
        report += "All items have responses.\n"

    report += "\n---\n\n"
    report += "## 5. Next Steps\n\n"
    report += f"- **Validated:** {len(classified['validated'])} item(s) ready for Week 2 review\n"
    report += f"- **Needs Clarification:** {len(classified['needs_clarification'])} item(s) — request updates from teams\n"
    report += f"- **Still Pending:** {len(classified['still_pending'])} item(s) — follow up with teams\n\n"
    report += "### Week 2 (2026-05-09+) Tasks:\n"
    report += "1. Review validated items\n"
    report += "2. Return needs_clarification items to teams for update\n"
    report += "3. Follow up on still_pending items\n"
    report += "4. Create ApprovalRecords ONLY for validated items\n"
    report += "5. Do NOT approve automatically — manual review required\n\n"

    report += "---\n\n"
    report += "**Notes:**\n"
    report += "- Zero API calls to NetBox\n"
    report += "- Zero writes to inventory\n"
    report += "- No ApprovalRecords created (Week 2 task)\n"
    report += "- All responses require manual review\n"

    return report


def main():
    args = parse_args()

    # Load template
    template = load_template(args.template)
    print(f"✓ Loaded {len(template)} items from template")

    # Find responses
    responses = find_responses(args.responses_dir)
    print(f"  Service Team: {responses['service_team'] or 'NOT FOUND'}")
    print(f"  Network Ops: {responses['network_ops'] or 'NOT FOUND'}")
    print(f"  BGP Team: {responses['bgp_team'] or 'NOT FOUND'}")

    # Classify items
    classified = classify_items(template, responses)
    print(f"\n✓ Classification complete:")
    print(f"  Validated: {len(classified['validated'])}")
    print(f"  Needs Clarification: {len(classified['needs_clarification'])}")
    print(f"  Still Pending: {len(classified['still_pending'])}")
    print(f"  Blocked: {len(classified['blocked'])}")
    print(f"  Rejected: {len(classified['rejected'])}")

    # Generate report
    report = generate_report(args.device, template, classified)

    # Write report
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n✓ Report saved: {args.output}")


if __name__ == "__main__":
    main()
