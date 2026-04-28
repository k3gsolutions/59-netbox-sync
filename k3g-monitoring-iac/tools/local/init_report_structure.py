#!/usr/bin/env python3
"""Initialize compliance report directory structure and index.json."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Initialize compliance report structure"
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Root directory (default: current)",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    base = root / "reports" / "pilot-device-compliance"

    # Create directories
    for d in [base / "current", base / "history"]:
        d.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created: {d}")

    # Create .gitignore
    gitignore = base / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(
            "payload*.json\n*raw*.json\n*secret*.json\n*.local.json\n"
            "__pycache__/\n*.pyc\n.pytest_cache/\n"
        )
        print(f"✓ Created: {gitignore}")

    # Create index.json if not exists
    index_path = base / "index.json"
    if not index_path.exists():
        index = {
            "version": "1.1",
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "devices": {},
            "retention_policy": {
                "keep_days": 90,
                "keep_count_per_device": None,
                "enabled": True,
            },
        }
        with open(index_path, "w") as f:
            json.dump(index, f, indent=2)
        print(f"✓ Created: {index_path}")
    else:
        print(f"ℹ Exists: {index_path}")

    print("\n✓ Structure initialized")
    return 0


if __name__ == "__main__":
    sys.exit(main())
