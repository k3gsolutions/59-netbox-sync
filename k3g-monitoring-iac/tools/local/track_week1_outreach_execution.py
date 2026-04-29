#!/usr/bin/env python3
"""
Track Week 1 Outreach Execution (FASE 2.16).

Generates status snapshot of outreach distribution and responses.

Zero NetBox writes. No tokens. Local file I/O only.

Usage:
    python3 track_week1_outreach_execution.py \\
        --device <device> \\
        --outreach-dir <path> \\
        --responses-dir <path> \\
        --output <path> \\
        --deadline <date> \\
        --reminder-date <date>
"""

import argparse
from datetime import datetime
from pathlib import Path
import csv


def parse_args():
    parser = argparse.ArgumentParser(
        description="Track Week 1 outreach execution"
    )
    parser.add_argument("--device", required=True, help="Device name")
    parser.add_argument("--outreach-dir", required=True, help="Outreach directory")
    parser.add_argument("--responses-dir", required=True, help="Responses directory")
    parser.add_argument("--output", required=True, help="Output snapshot file")
    parser.add_argument("--deadline", required=True, help="Deadline (YYYY-MM-DD)")
    parser.add_argument("--reminder-date", required=True, help="Reminder date (YYYY-MM-DD)")
    return parser.parse_args()


def count_response_rows(csv_file: str) -> int:
    """Count non-empty rows in CSV."""
    try:
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            return len([r for r in rows if r and any(r.values())])
    except (FileNotFoundError, csv.Error):
        return 0


def determine_status(dist_log_path: str, response_count: int, expected: int, deadline_str: str) -> str:
    """Determine team status."""
    now = datetime.utcnow()
    deadline = datetime.fromisoformat(deadline_str)

    # Check if distribution log exists and has entry for team
    if not Path(dist_log_path).exists():
        return "not_sent"

    # Check response count
    if response_count == 0:
        if now > deadline:
            return "overdue"
        return "response_missing"
    elif response_count == expected:
        return "complete"
    else:
        if now > deadline:
            return "overdue"
        return "partial_response"


def generate_snapshot(device: str, outreach_dir: str, responses_dir: str, deadline: str, reminder_date: str) -> str:
    """Generate status snapshot."""
    now = datetime.utcnow().isoformat() + "+00:00"

    outreach_path = Path(outreach_dir)
    responses_path = Path(responses_dir)

    # Count responses
    service_count = count_response_rows(str(responses_path / "service-team-response.csv"))
    ops_count = count_response_rows(str(responses_path / "network-ops-response.csv"))
    bgp_count = count_response_rows(str(responses_path / "bgp-team-response.csv"))

    # Determine statuses
    service_status = "not_sent" if service_count == 0 else "complete" if service_count == 5 else "partial_response"
    ops_status = "not_sent" if ops_count == 0 else "complete" if ops_count == 1 else "partial_response"
    bgp_status = "not_sent" if bgp_count == 0 else "complete" if bgp_count == 1 else "partial_response"

    total_received = sum([service_count, ops_count, bgp_count])
    pending = (5 - service_count) + (1 - ops_count) + (1 - bgp_count)
    partial = (1 if 0 < service_count < 5 else 0) + (1 if 0 < ops_count < 1 else 0) + (1 if 0 < bgp_count < 1 else 0)

    snapshot = f"""# Week 1 Outreach Status Snapshot — {device}

**Generated:** {now}
**Device:** {device} (device_id: 1890)
**Deadline:** {deadline}
**Reminder Date:** {reminder_date}

---

## 1. Summary

| Metric | Value |
|--------|-------|
| Total Teams | 3 |
| Responses Received | {service_count + ops_count + bgp_count} |
| Pending Items | {pending} |
| Partial Responses | {partial} |
| Status | Mixed |

---

## 2. Status by Team

| Team | Expected | Received | Status | Next Action |
|---|---:|---:|---|---|
| Service Team | 5 | {service_count} | {service_status} | {"✅ Complete" if service_status == "complete" else "📬 Awaiting" if service_status == "not_sent" else "⚠️ Clarification"} |
| Network Ops | 1 | {ops_count} | {ops_status} | {"✅ Complete" if ops_status == "complete" else "📬 Awaiting" if ops_status == "not_sent" else "⚠️ Clarification"} |
| BGP Team | 1 | {bgp_count} | {bgp_status} | {"✅ Complete" if bgp_status == "complete" else "📬 Awaiting" if bgp_status == "not_sent" else "⚠️ Clarification"} |

---

## 3. Workflow Status

- **not_sent:** Message not yet sent
- **response_missing:** Message sent, no response received yet
- **partial_response:** Some items responded, some pending
- **complete:** All items received and valid
- **overdue:** Deadline passed, no response
- **escalation_required:** Director notification sent

---

## 4. Next Steps

1. Check distribution log: outreach/execution/outreach-distribution-log.md
2. If status=response_missing and date>=reminder-date: send reminder
3. If status=overdue: escalate to director
4. Update log with each action
5. Re-run this snapshot to track progress

---

**Status:** Ready for review and action.

"""

    return snapshot


def main():
    args = parse_args()

    # Generate snapshot
    snapshot = generate_snapshot(
        args.device,
        args.outreach_dir,
        args.responses_dir,
        args.deadline,
        args.reminder_date
    )

    # Write snapshot
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(snapshot)

    print(f"✓ Status snapshot generated: {output_path}")
    print(f"✓ Review at: {output_path}")


if __name__ == "__main__":
    main()
