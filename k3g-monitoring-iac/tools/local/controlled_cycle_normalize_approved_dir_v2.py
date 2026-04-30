#!/usr/bin/env python3
"""Normalize Cycle-002 approved-dir layout without deleting source files."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--approved-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()

    compat_dir = args.approved_dir / "approved"
    args.approved_dir.mkdir(parents=True, exist_ok=True)
    compat_dir.mkdir(parents=True, exist_ok=True)

    copied = []
    for src in sorted(compat_dir.glob("*.json")):
        dst = args.approved_dir / src.name
        if not dst.exists():
            shutil.copy2(src, dst)
            copied.append(dst.name)

    report = "\n".join([
        f"# {args.cycle_id.upper()} Approved Dir Normalization",
        "",
        f"- root: {args.approved_dir}",
        f"- compat: {compat_dir}",
        f"- copied: {len(copied)}",
        f"- copied_files: {', '.join(copied) if copied else 'none'}",
        "",
        "## Safety",
        "- No deletion",
        "- No NetBox write",
        "- No ApplyPlan",
    ])
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    payload = {
        "cycle_id": args.cycle_id,
        "root_dir": str(args.approved_dir),
        "compat_dir": str(compat_dir),
        "copied": copied,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "no_netbox_write": True,
        "no_apply_plan_created": True,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"✓ Normalized approved dir: {len(copied)} copied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
