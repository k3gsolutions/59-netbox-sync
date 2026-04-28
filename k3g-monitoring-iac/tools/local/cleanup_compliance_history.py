#!/usr/bin/env python3
"""Clean up old compliance reports based on retention policy."""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Tuple


def load_index(index_path: Path) -> Dict:
    """Load index.json."""
    if not index_path.exists():
        return {"devices": {}, "retention_policy": {}}
    with open(index_path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_iso8601(timestamp_str: str) -> datetime:
    """Parse ISO8601 timestamp."""
    # Format: 2026-04-28T05:53:48Z
    timestamp_str = timestamp_str.rstrip("Z")
    return datetime.fromisoformat(timestamp_str).replace(tzinfo=timezone.utc)


def find_reports_to_delete(
    base_path: Path,
    keep_days: int = 90,
    keep_count: int = None,
) -> List[Tuple[str, Path]]:
    """Find reports that should be deleted based on retention policy."""
    to_delete = []
    now = datetime.now(timezone.utc)
    cutoff_date = now - timedelta(days=keep_days)

    history_path = base_path / "history"
    if not history_path.exists():
        return to_delete

    # Iterate over each device directory
    for device_dir in history_path.iterdir():
        if not device_dir.is_dir():
            continue

        device_name = device_dir.name
        reports = []

        # Find all reports for this device
        for report_file in device_dir.glob("*.md"):
            try:
                # Extract timestamp from filename: YYYY-MM-DDTHH:MM:SSZ-compliance-report.md
                timestamp_str = report_file.name.split("-compliance-report.md")[0]
                report_date = parse_iso8601(timestamp_str)
                reports.append((report_date, report_file))
            except Exception:
                # Skip files that don't match expected format
                pass

        if not reports:
            continue

        # Sort by date (newest first)
        reports.sort(reverse=True)

        # Mark old reports for deletion
        for i, (report_date, report_path) in enumerate(reports):
            # Check age-based retention
            if report_date < cutoff_date:
                to_delete.append((device_name, report_path))
                continue

            # Check count-based retention
            if keep_count is not None and i >= keep_count:
                to_delete.append((device_name, report_path))

    return to_delete


def main():
    parser = argparse.ArgumentParser(
        description="Clean up old compliance reports"
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Root directory (default: current)",
    )
    parser.add_argument(
        "--keep-days",
        type=int,
        default=90,
        help="Keep reports from last N days (default: 90)",
    )
    parser.add_argument(
        "--keep-count",
        type=int,
        help="Keep last N reports per device (optional)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete files (default: dry-run)",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    base_path = root / "reports" / "pilot-device-compliance"
    index_path = base_path / "index.json"

    if not base_path.exists():
        print(f"Error: base path not found: {base_path}", file=sys.stderr)
        return 1

    # Find reports to delete
    to_delete = find_reports_to_delete(
        base_path,
        keep_days=args.keep_days,
        keep_count=args.keep_count,
    )

    if not to_delete:
        print("✓ No reports to delete.")
        return 0

    # Print summary
    print(f"{'DRY RUN' if not args.apply else 'EXECUTING'}: cleanup compliance history")
    print(f"Keep-days: {args.keep_days}")
    if args.keep_count:
        print(f"Keep-count: {args.keep_count}")
    print()

    # Group by device
    by_device: Dict[str, List[Path]] = {}
    for device_name, report_path in to_delete:
        if device_name not in by_device:
            by_device[device_name] = []
        by_device[device_name].append(report_path)

    # Print and delete
    total_deleted = 0
    for device_name in sorted(by_device.keys()):
        reports = sorted(by_device[device_name])
        print(f"{device_name}: {len(reports)} report(s)")
        for report_path in reports:
            print(f"  - {report_path.name}")
            if args.apply:
                try:
                    report_path.unlink()
                    total_deleted += 1
                except Exception as e:
                    print(f"    ERROR: {e}", file=sys.stderr)

    print()
    if args.apply:
        print(f"✓ Deleted {total_deleted} report(s)")
        # Update index.json reports_count for each device
        try:
            index = load_index(index_path)
            for device_name in by_device.keys():
                if device_name in index.get("devices", {}):
                    history_dir = base_path / "history" / device_name
                    count = len(list(history_dir.glob("*.md")))
                    index["devices"][device_name]["reports_count"] = count
            with open(index_path, "w", encoding="utf-8") as f:
                json.dump(index, f, indent=2)
            print(f"✓ Updated {index_path}")
        except Exception as e:
            print(f"Warning: could not update index.json: {e}", file=sys.stderr)
    else:
        print(f"DRY RUN: would delete {len(to_delete)} report(s)")
        print("Re-run with --apply to actually delete")

    return 0


if __name__ == "__main__":
    sys.exit(main())
