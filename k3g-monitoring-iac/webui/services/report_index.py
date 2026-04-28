"""Report index for read-only web UI."""

from pathlib import Path
from typing import Dict, Optional
import json


def load_index(root: Path) -> Optional[Dict]:
    """Load index.json if it exists."""
    index_path = root / "reports" / "pilot-device-compliance" / "index.json"

    if not index_path.exists():
        return None

    try:
        return json.loads(index_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def get_latest_report(root: Path) -> Optional[str]:
    """Get path to latest compliance report."""
    reports_dir = root / "reports" / "pilot-device-compliance"

    if not reports_dir.exists():
        return None

    # Find latest *.md file (excluding special files)
    candidates = [
        f for f in reports_dir.glob("*.md")
        if not f.name.startswith(".")
        and "comparison" not in f.name.lower()
        and "incident" not in f.name.lower()
    ]

    if not candidates:
        return None

    latest = max(candidates, key=lambda f: f.stat().st_mtime)
    return f"reports/pilot-device-compliance/{latest.name}"


def parse_report_metrics(content: str) -> Dict:
    """
    Parse metrics from report markdown.

    Look for tables and counts.
    """
    metrics = {
        "divergences": 0,
        "ready_for_review": 0,
        "missing_metadata": 0,
        "naming_failed": 0,
        "blocked": 0,
        "ignored": 0,
    }

    # Very basic parsing - look for common keywords
    for line in content.split("\n"):
        if "divergence" in line.lower() and "|" in line:
            try:
                parts = line.split("|")
                if len(parts) > 1 and parts[1].strip().isdigit():
                    metrics["divergences"] = int(parts[1].strip())
            except Exception:
                pass

    return metrics
