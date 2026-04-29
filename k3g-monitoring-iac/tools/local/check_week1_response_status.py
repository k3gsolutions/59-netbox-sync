#!/usr/bin/env python3
"""
Check Week 1 Response Status (FASE 2.15 — optional tracking).

Scans week1-responses directory for incoming CSVs.
Counts responses per team.
Updates week1-response-tracker.md with status.

Zero NetBox writes. No tokens. Local only.

Usage:
    python3 check_week1_response_status.py \\
        --responses-dir <path/to/week1-responses> \\
        --outreach-dir <path/to/outreach> \\
        --deadline <date>
"""

import argparse
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple


def parse_args():
    parser = argparse.ArgumentParser(
        description="Check Week 1 response status"
    )
    parser.add_argument("--responses-dir", required=True, help="Responses directory")
    parser.add_argument("--outreach-dir", required=True, help="Outreach directory")
    parser.add_argument("--deadline", required=True, help="Deadline date (YYYY-MM-DD)")
    return parser.parse_args()


def count_csv_responses(csv_file: str) -> Tuple[int, List[str]]:
    """Count non-empty rows in CSV (excluding header)."""
    try:
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictFieldnames(f)
            next(reader, None)  # Skip header
            rows = list(reader)
            object_keys = [row.get("object_key", "") for row in rows if row and row.get("object_key")]
            return len(object_keys), object_keys
    except (FileNotFoundError, csv.Error):
        return 0, []


def check_status(responses_dir: str, expected_items: Dict[str, int], deadline: str) -> Dict:
    """Check response status for each team."""
    responses_path = Path(responses_dir)
    status = {
        "service_team": {"responded": 0, "total": expected_items.get("subinterfaces", 0), "items": []},
        "network_ops": {"responded": 0, "total": expected_items.get("ip_addresses", 0), "items": []},
        "bgp_team": {"responded": 0, "total": expected_items.get("bgp_peers", 0), "items": []},
    }

    # Check service-team-response.csv
    service_file = responses_path / "service-team-response.csv"
    if service_file.exists():
        count, items = count_csv_responses(str(service_file))
        status["service_team"]["responded"] = count
        status["service_team"]["items"] = items
        status["service_team"]["status"] = "complete" if count == status["service_team"]["total"] else "partial" if count > 0 else "not_started"
    else:
        status["service_team"]["status"] = "not_started"

    # Check network-ops-response.csv
    ops_file = responses_path / "network-ops-response.csv"
    if ops_file.exists():
        count, items = count_csv_responses(str(ops_file))
        status["network_ops"]["responded"] = count
        status["network_ops"]["items"] = items
        status["network_ops"]["status"] = "complete" if count == status["network_ops"]["total"] else "partial" if count > 0 else "not_started"
    else:
        status["network_ops"]["status"] = "not_started"

    # Check bgp-team-response.csv
    bgp_file = responses_path / "bgp-team-response.csv"
    if bgp_file.exists():
        count, items = count_csv_responses(str(bgp_file))
        status["bgp_team"]["responded"] = count
        status["bgp_team"]["items"] = items
        status["bgp_team"]["status"] = "complete" if count == status["bgp_team"]["total"] else "partial" if count > 0 else "not_started"
    else:
        status["bgp_team"]["status"] = "not_started"

    # Check if overdue
    now = datetime.utcnow()
    deadline_dt = datetime.fromisoformat(deadline)
    is_overdue = now > deadline_dt

    return {
        "status": status,
        "is_overdue": is_overdue,
        "checked_at": now.isoformat() + "+00:00"
    }


def generate_status_report(responses_dir: str, outreach_dir: str, deadline: str) -> str:
    """Generate status report."""
    # Extract expected items
    tracker_file = Path(outreach_dir) / "week1-response-tracker.md"
    if not tracker_file.exists():
        return "ERROR: week1-response-tracker.md not found"

    # Parse tracker to get expected counts
    expected = {
        "subinterfaces": 5,  # Hardcoded for now, could parse from tracker
        "ip_addresses": 1,
        "bgp_peers": 1,
    }

    # Check status
    result = check_status(responses_dir, expected, deadline)

    # Generate report
    timestamp = result["checked_at"]
    report = f"""# Week 1 Response Status Report

**Checked:** {timestamp}
**Deadline:** {deadline}
**Overdue:** {'Yes' if result['is_overdue'] else 'No'}

---

## Summary

| Team | Responded | Total | Status |
|------|-----------|-------|--------|
| Service Team | {result['status']['service_team']['responded']} | {result['status']['service_team']['total']} | {result['status']['service_team']['status']} |
| Network Ops | {result['status']['network_ops']['responded']} | {result['status']['network_ops']['total']} | {result['status']['network_ops']['status']} |
| BGP Team | {result['status']['bgp_team']['responded']} | {result['status']['bgp_team']['total']} | {result['status']['bgp_team']['status']} |

---

## Details

### Service Team
- Status: {result['status']['service_team']['status']}
- Responded: {result['status']['service_team']['responded']}/{result['status']['service_team']['total']}
- Items: {', '.join(result['status']['service_team']['items']) if result['status']['service_team']['items'] else 'None'}

### Network Ops
- Status: {result['status']['network_ops']['status']}
- Responded: {result['status']['network_ops']['responded']}/{result['status']['network_ops']['total']}
- Items: {', '.join(result['status']['network_ops']['items']) if result['status']['network_ops']['items'] else 'None'}

### BGP Team
- Status: {result['status']['bgp_team']['status']}
- Responded: {result['status']['bgp_team']['responded']}/{result['status']['bgp_team']['total']}
- Items: {', '.join(result['status']['bgp_team']['items']) if result['status']['bgp_team']['items'] else 'None'}

---

## Next Steps

"""

    if result['is_overdue']:
        report += "⚠️ **OVERDUE**: Deadline has passed. Escalate non-responders.\n"
    else:
        report += "✅ Awaiting responses until deadline.\n"

    return report


def main():
    args = parse_args()

    responses_path = Path(args.responses_dir)
    if not responses_path.exists():
        print(f"⚠ Responses directory not found: {args.responses_dir}")
        responses_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory")

    outreach_path = Path(args.outreach_dir)
    if not outreach_path.exists():
        print(f"❌ Outreach directory not found: {args.outreach_dir}")
        return

    # Check status
    print(f"✓ Checking response status...")
    report = generate_status_report(args.responses_dir, args.outreach_dir, args.deadline)

    # Save report
    report_file = outreach_path / "week1-response-status.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"✓ Status report saved: {report_file}")
    print(f"\nReport preview:")
    print(report[:500])


if __name__ == "__main__":
    main()
