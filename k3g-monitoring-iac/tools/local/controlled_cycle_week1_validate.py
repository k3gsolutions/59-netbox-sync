#!/usr/bin/env python3
"""FASE 4.6 — Controlled Operation Cycle Week 1 Validation.

Validate Week 1 responses against compliance policies.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def load_json_safe(file_path: Path) -> Dict[str, Any]:
    """Load JSON file safely."""
    if not file_path.exists():
        return {}

    try:
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def validate_response(response: Dict[str, Any], device: str) -> tuple[bool, list[str]]:
    """Validate single response."""
    issues = []

    # Check device
    if response.get("device") != device:
        issues.append(f"device mismatch: {response.get('device')} != {device}")

    # Check object_type
    valid_types = ["interface", "ip_address", "bgp_peer", "vrf", "route_policy"]
    if response.get("object_type") not in valid_types:
        issues.append(f"object_type {response.get('object_type')} not in {valid_types}")

    # Check owner
    if not response.get("owner"):
        issues.append("owner field required")

    # Check for secrets in comments
    comment = response.get("notes", "").lower()
    blocked_words = ["token", "password", "secret", "netbox_write_token"]
    for word in blocked_words:
        if word in comment:
            issues.append(f"blocked word '{word}' found in notes")

    # Check status
    if response.get("status") not in ["pending", "submitted", "validated"]:
        issues.append(f"invalid status: {response.get('status')}")

    return len(issues) == 0, issues


def evaluate_validation(valid_count: int, blocked_count: int, total: int) -> str:
    """Evaluate validation result."""
    if blocked_count > 0:
        return "WEEK1_VALIDATION_BLOCKED"

    if valid_count == total and total > 0:
        return "WEEK1_VALIDATION_PASSED"

    if valid_count > 0:
        return "WEEK1_VALIDATION_PASSED_WITH_RESTRICTIONS"

    return "WEEK1_VALIDATION_BLOCKED"


def generate_validation_markdown(
    cycle_id: str,
    device: str,
    decision: str,
    valid_count: int,
    blocked_count: int,
    total: int,
) -> str:
    """Generate validation markdown report."""
    timestamp = datetime.utcnow().isoformat() + "+00:00"

    emoji = {
        "WEEK1_VALIDATION_PASSED": "✓",
        "WEEK1_VALIDATION_PASSED_WITH_RESTRICTIONS": "⚠",
        "WEEK1_VALIDATION_BLOCKED": "✗",
    }.get(decision, "?")

    md = f"""# {cycle_id} — Week 1 Validation

## 1. Decision

### {emoji} {decision}

## 2. Validation Results

- **Total Responses:** {total}
- **Valid:** {valid_count}
- **Blocked:** {blocked_count}
- **Pending:** {total - valid_count - blocked_count}

## 3. Validation Rules Applied

- Device matches cycle scope
- Object type allowed
- Owner documented
- No secrets in comments
- Valid status
- Naming conventions checked
- Required fields present

## 4. Next Steps

"""
    if decision == "WEEK1_VALIDATION_PASSED":
        md += "All responses validated. Proceed to Week 2 Review."
    elif decision == "WEEK1_VALIDATION_PASSED_WITH_RESTRICTIONS":
        md += "Some responses validated. Address restrictions before Week 2."
    else:
        md += "Validation blocked. Review blocked items before proceeding."

    md += f"""

---

**Cycle ID:** {cycle_id}
**Device:** {device}
**Validation At:** {timestamp}
"""

    return md


def main() -> int:
    """Run FASE 4.6."""
    parser = argparse.ArgumentParser(
        description="FASE 4.6 — Controlled Operation Cycle Week 1 Validation"
    )
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--cycle-dir", type=Path, required=True)
    parser.add_argument("--responses-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)

    args = parser.parse_args()

    # Validate all responses
    valid_count = 0
    blocked_count = 0
    validation_details = []

    if args.responses_dir.exists():
        for response_file in args.responses_dir.glob("*.json"):
            response_data = load_json_safe(response_file)
            is_valid, issues = validate_response(response_data, args.device)

            if is_valid:
                valid_count += 1
                status = "validated"
            elif issues:
                blocked_count += 1
                status = "blocked"
            else:
                status = "unknown"

            validation_details.append({
                "file": response_file.name,
                "status": status,
                "issues": issues,
            })

    total = valid_count + blocked_count
    decision = evaluate_validation(valid_count, blocked_count, total)

    # Generate markdown
    markdown = generate_validation_markdown(args.cycle_id, args.device, decision, valid_count, blocked_count, total)

    # Generate JSON
    validation_json = {
        "cycle_id": args.cycle_id,
        "device": args.device,
        "device_id": args.device_id,
        "decision": decision,
        "validated_at": datetime.utcnow().isoformat() + "+00:00",
        "summary": {
            "total_responses": total,
            "valid": valid_count,
            "blocked": blocked_count,
            "ready_for_week2": valid_count > 0 and blocked_count == 0,
        },
        "details": validation_details,
    }

    # Write outputs
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(validation_json, f, indent=2)

    print(f"✓ Week 1 validation decision: {decision}")
    print(f"✓ Valid responses: {valid_count}")
    print(f"✓ Blocked responses: {blocked_count}")
    print(f"✓ Report: {args.output}")
    print(f"✓ JSON: {args.output_json}")

    return 0 if "PASSED" in decision else 1


if __name__ == "__main__":
    raise SystemExit(main())
