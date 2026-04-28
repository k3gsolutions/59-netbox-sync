#!/usr/bin/env python3
"""Archive compliance report to history and update index.json."""

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Archive compliance report to history and update index."
    )
    parser.add_argument(
        "--report",
        required=True,
        help="Path to compliance report .md file",
    )
    parser.add_argument(
        "--device",
        help="Device name (auto-detected from report title if not provided)",
    )
    parser.add_argument(
        "--device-id",
        type=int,
        help="Device ID (optional, for index.json)",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Root directory (default: current dir)",
    )
    return parser.parse_args()


def extract_device_name_from_report(report_path):
    """Extract device name from report title: '# Relatório de Compliance — DEVICE-NAME'."""
    with open(report_path, "r", encoding="utf-8") as f:
        first_line = f.readline()

    # Match: # Relatório de Compliance — DEVICE-NAME
    match = re.search(r"# Relatório de Compliance — (.+)$", first_line)
    if match:
        name = match.group(1).strip()
        if name and name != "unknown":
            return name
    return None


def get_iso8601_timestamp():
    """Return current UTC time as ISO8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ensure_reports_structure(root):
    """Ensure reports/pilot-device-compliance/{current,history} exists."""
    base = Path(root) / "reports" / "pilot-device-compliance"
    base.mkdir(parents=True, exist_ok=True)
    (base / "current").mkdir(exist_ok=True)
    (base / "history").mkdir(exist_ok=True)
    return base


def load_index(index_path):
    """Load index.json or return default structure."""
    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "version": "1.1",
        "generated_at": get_iso8601_timestamp(),
        "devices": {},
        "retention_policy": {
            "keep_days": 90,
            "keep_count_per_device": None,
            "enabled": True,
        },
    }


def save_index(index_path, data):
    """Save index.json."""
    data["generated_at"] = get_iso8601_timestamp()
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def archive_report(report_path, device_name, device_id, root):
    """Archive report to history and update current."""
    report_path = Path(report_path).resolve()
    root = Path(root).resolve()

    if not report_path.exists():
        print(f"Error: report file not found: {report_path}", file=sys.stderr)
        return False

    if not device_name:
        device_name = extract_device_name_from_report(report_path)
        if not device_name:
            print("Error: could not detect device name from report", file=sys.stderr)
            print("       Use --device to specify", file=sys.stderr)
            return False

    # Ensure structure
    base = ensure_reports_structure(root)
    index_path = base / "index.json"

    # Read report
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Archive to history
    timestamp = get_iso8601_timestamp()
    device_history = base / "history" / device_name
    device_history.mkdir(parents=True, exist_ok=True)
    archived_path = device_history / f"{timestamp}-compliance-report.md"

    with open(archived_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✓ Archived: {archived_path}")

    # Update current
    current_path = base / "current" / f"{device_name}-compliance-report.md"
    shutil.copy(report_path, current_path)
    print(f"✓ Updated current: {current_path}")

    # Update index
    index = load_index(index_path)
    if device_name not in index["devices"]:
        index["devices"][device_name] = {
            "device_id": device_id,
            "last_report": timestamp,
            "reports_count": 1,
            "history_path": f"history/{device_name}",
        }
    else:
        index["devices"][device_name]["last_report"] = timestamp
        index["devices"][device_name]["reports_count"] = (
            index["devices"][device_name].get("reports_count", 0) + 1
        )
        if device_id:
            index["devices"][device_name]["device_id"] = device_id

    save_index(index_path, index)
    print(f"✓ Updated index: {index_path}")

    return True


def main():
    args = parse_args()

    if archive_report(
        args.report,
        args.device,
        args.device_id,
        args.root,
    ):
        print("\n✓ Report archived successfully")
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
