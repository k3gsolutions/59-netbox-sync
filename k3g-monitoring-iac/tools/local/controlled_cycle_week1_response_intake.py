#!/usr/bin/env python3
"""FASE 4.5 — Controlled Operation Cycle Week 1 Response Intake.

Collect and classify responses received from teams during Week 1.
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


def count_responses(responses_dir: Path) -> Dict[str, Any]:
    """Count responses by status and team."""
    counts = {
        "total_files": 0,
        "total_items": 0,
        "by_team": {
            "service": {"count": 0, "items": []},
            "network_ops": {"count": 0, "items": []},
            "bgp": {"count": 0, "items": []},
        },
        "by_status": {
            "responded": 0,
            "still_pending": 0,
            "invalid_format": 0,
        },
    }

    if not responses_dir.exists():
        return counts

    for response_file in responses_dir.glob("*.json"):
        counts["total_files"] += 1
        try:
            response_data = json.loads(response_file.read_text())
            team = response_data.get("team", "unknown")
            if team in counts["by_team"]:
                counts["by_team"][team]["count"] += 1
                counts["by_team"][team]["items"].append(response_data.get("item_id", "unknown"))
            counts["total_items"] += 1
            counts["by_status"]["responded"] += 1
        except Exception:
            counts["by_status"]["invalid_format"] += 1

    return counts


def evaluate_intake(counts: Dict[str, Any], max_items: int) -> str:
    """Evaluate intake readiness."""
    if counts["total_items"] >= max_items:
        return "WEEK1_INTAKE_READY"

    if counts["total_items"] > 0:
        return "WEEK1_INTAKE_PARTIAL"

    return "WEEK1_INTAKE_BLOCKED"


def generate_intake_markdown(
    cycle_id: str,
    device: str,
    decision: str,
    counts: Dict[str, Any],
) -> str:
    """Generate intake markdown report."""
    timestamp = datetime.utcnow().isoformat() + "+00:00"

    emoji = {
        "WEEK1_INTAKE_READY": "✓",
        "WEEK1_INTAKE_PARTIAL": "⚠",
        "WEEK1_INTAKE_BLOCKED": "✗",
    }.get(decision, "?")

    service_items = ", ".join(counts["by_team"]["service"]["items"]) or "none"
    netops_items = ", ".join(counts["by_team"]["network_ops"]["items"]) or "none"
    bgp_items = ", ".join(counts["by_team"]["bgp"]["items"]) or "none"

    md = f"""# {cycle_id} — Week 1 Response Intake

## 1. Decision

### {emoji} {decision}

Total responses: {counts["total_items"]}
Status: {decision}

## 2. Responses by Team

### Service Team
- Count: {counts["by_team"]["service"]["count"]}
- Items: {service_items}

### Network Ops
- Count: {counts["by_team"]["network_ops"]["count"]}
- Items: {netops_items}

### BGP Team
- Count: {counts["by_team"]["bgp"]["count"]}
- Items: {bgp_items}

## 3. Status Summary

- **Responded:** {counts["by_status"]["responded"]}
- **Still Pending:** {counts["by_status"]["still_pending"]}
- **Invalid Format:** {counts["by_status"]["invalid_format"]}

## 4. Next Steps

"""
    if decision == "WEEK1_INTAKE_READY":
        md += "All responses received. Proceed to Week 1 Validation."
    elif decision == "WEEK1_INTAKE_PARTIAL":
        md += "Some responses received. Waiting for remaining teams."
    else:
        md += "No responses yet. Teams should submit via Web UI or local response files."

    md += f"""

---

**Cycle ID:** {cycle_id}
**Device:** {device}
**Decision:** {decision}
**Intake At:** {timestamp}
"""

    return md


def main() -> int:
    """Run FASE 4.5."""
    parser = argparse.ArgumentParser(
        description="FASE 4.5 — Controlled Operation Cycle Week 1 Response Intake"
    )
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--cycle-dir", type=Path, required=True)
    parser.add_argument("--responses-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)

    args = parser.parse_args()

    # Load scope to get max_items
    scope_file = args.cycle_dir / f"{args.cycle_id.upper()}-SCOPE.json"
    scope = load_json_safe(scope_file)
    max_items = scope.get("max_items", 3)

    # Count responses
    counts = count_responses(args.responses_dir)
    decision = evaluate_intake(counts, max_items)

    # Generate markdown
    markdown = generate_intake_markdown(args.cycle_id, args.device, decision, counts)

    # Generate JSON
    intake_json = {
        "cycle_id": args.cycle_id,
        "device": args.device,
        "device_id": args.device_id,
        "decision": decision,
        "evaluated_at": datetime.utcnow().isoformat() + "+00:00",
        "response_counts": counts,
        "max_items_required": max_items,
        "ready_for_validation": "READY" in decision,
    }

    # Write outputs
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(intake_json, f, indent=2)

    print(f"✓ Week 1 intake decision: {decision}")
    print(f"✓ Total responses: {counts['total_items']}")
    print(f"✓ Report: {args.output}")
    print(f"✓ JSON: {args.output_json}")

    return 0 if "READY" in decision or "PARTIAL" in decision else 1


if __name__ == "__main__":
    raise SystemExit(main())
