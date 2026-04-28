#!/usr/bin/env python3
"""Export compliance history to CSV."""

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Dict, List


def load_index(index_path: Path) -> Dict:
    """Load index.json."""
    if not index_path.exists():
        return {"devices": {}}
    with open(index_path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_report_metadata(report_path: Path) -> Dict:
    """Extract metadata from report Markdown file."""
    metadata = {
        "total_divergences": None,
        "highest_severity": None,
        "status": None,
        "netbox_loaded": None,
    }

    try:
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract total divergences
        match = re.search(r"Total de divergências: (\d+)", content)
        if match:
            metadata["total_divergences"] = int(match.group(1))

        # Extract highest severity
        match = re.search(r"Severidade mais alta: ([^\n]+)", content)
        if match:
            severity = match.group(1).strip()
            if severity and severity != "Nenhuma":
                metadata["highest_severity"] = severity

        # Extract status
        match = re.search(r"Status geral: ([^\n]+)", content)
        if match:
            metadata["status"] = match.group(1).strip()

        # Extract netbox loaded
        match = re.search(r"NetBox carregado: ([^\n]+)", content)
        if match:
            metadata["netbox_loaded"] = match.group(1).strip()

    except Exception:
        pass

    return metadata


def main():
    parser = argparse.ArgumentParser(
        description="Export compliance history to CSV"
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Root directory (default: current)",
    )
    parser.add_argument(
        "--output",
        default="compliance-history.csv",
        help="Output CSV file (default: compliance-history.csv)",
    )
    parser.add_argument(
        "--include-metadata",
        action="store_true",
        help="Include divergence count and severity from reports",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    base_path = root / "reports" / "pilot-device-compliance"
    index_path = base_path / "index.json"
    output_path = Path(args.output).resolve()

    if not index_path.exists():
        print(f"Error: index not found: {index_path}", file=sys.stderr)
        return 1

    index = load_index(index_path)
    devices = index.get("devices", {})

    if not devices:
        print("No devices in index.", file=sys.stderr)
        return 1

    # Prepare CSV rows
    rows = []
    for device_name, device_info in sorted(devices.items()):
        row = {
            "device": device_name,
            "device_id": device_info.get("device_id") or "",
            "last_report": device_info.get("last_report") or "",
            "reports_count": device_info.get("reports_count", 0),
        }

        # Add metadata from latest report if requested
        if args.include_metadata:
            history_dir = base_path / "history" / device_name
            if history_dir.exists():
                # Get latest report
                reports = sorted(
                    history_dir.glob("*.md"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
                if reports:
                    metadata = extract_report_metadata(reports[0])
                    row["total_divergences"] = metadata.get("total_divergences", "")
                    row["highest_severity"] = metadata.get("highest_severity", "")
                    row["status"] = metadata.get("status", "")
                    row["netbox_loaded"] = metadata.get("netbox_loaded", "")

        rows.append(row)

    # Determine fieldnames
    fieldnames = ["device", "device_id", "last_report", "reports_count"]
    if args.include_metadata:
        fieldnames.extend(["total_divergences", "highest_severity", "status", "netbox_loaded"])

    # Write CSV
    try:
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"✓ Exported {len(rows)} device(s) to: {output_path}")
        return 0
    except Exception as e:
        print(f"Error writing CSV: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
