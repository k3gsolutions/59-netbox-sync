"""Artifact scanner for read-only web UI."""

import json
from pathlib import Path
from typing import List, Dict, Optional


DENYLIST = {
    "payload.local.json",
    "secrets.json",
    "token",
    "password",
}

DENYLIST_PATTERNS = [
    "payload.local",
    "-raw",
    "raw-",
    "_raw_",
]

ALLOWED_EXTENSIONS = {".md", ".json", ".txt"}


def normalize_report_path(path: str) -> Optional[str]:
    """
    Normalize report path to be relative to reports/ directory.

    Accepts:
    - pilot-device-compliance/file.md
    - reports/pilot-device-compliance/file.md
    - /reports/pilot-device-compliance/file.md

    Returns:
    - pilot-device-compliance/file.md (relative to reports/)
    - None if path is invalid
    """
    if not path:
        return None

    # Remove leading/trailing whitespace
    path = path.strip()

    # Block absolute paths
    if path.startswith("/"):
        path = path.lstrip("/")

    # Block path traversal
    if ".." in path:
        return None

    # Remove 'reports/' prefix if present
    if path.startswith("reports/"):
        path = path[8:]  # len("reports/") = 8

    # Remove trailing slashes
    path = path.rstrip("/")

    # Reject empty result
    if not path:
        return None

    return path


def safe_resolve_path(base: Path, requested_path: str) -> Optional[Path]:
    """
    Safely resolve a path to prevent traversal attacks.

    Returns None if path is unsafe.
    """
    try:
        # Remove leading/trailing slashes
        requested_path = requested_path.strip("/")

        # Block path traversal
        if ".." in requested_path:
            return None

        # Block denylist
        for denied in DENYLIST:
            if denied in requested_path.lower():
                return None

        # Block patterns
        for pattern in DENYLIST_PATTERNS:
            if pattern in requested_path.lower():
                return None

        # Resolve and check it's within base
        resolved = (base / requested_path).resolve()
        base_resolved = base.resolve()

        if not str(resolved).startswith(str(base_resolved)):
            return None

        return resolved
    except Exception:
        return None


def list_reports(root: Path) -> List[Dict]:
    """List all compliance reports."""
    reports_dir = root / "reports" / "pilot-device-compliance"

    if not reports_dir.exists():
        return []

    reports = []
    for md_file in reports_dir.glob("*.md"):
        try:
            mtime = md_file.stat().st_mtime
            reports.append({
                "name": md_file.name,
                "path": f"reports/pilot-device-compliance/{md_file.name}",
                "mtime": mtime,
            })
        except Exception:
            pass

    return sorted(reports, key=lambda x: x["mtime"], reverse=True)


def list_devices(root: Path) -> List[Dict]:
    """List devices with history."""
    history_dir = root / "reports" / "pilot-device-compliance" / "history"

    devices = {}

    if history_dir.exists():
        for device_file in history_dir.glob("*.json"):
            try:
                device_name = device_file.stem
                devices[device_name] = {
                    "name": device_name,
                    "path": f"reports/pilot-device-compliance/history/{device_file.name}",
                    "mtime": device_file.stat().st_mtime,
                }
            except Exception:
                pass

    return sorted(devices.values(), key=lambda x: x["mtime"], reverse=True)


def list_approvals(root: Path) -> List[Dict]:
    """List approval records."""
    approvals_dir = root / "reports" / "pilot-device-compliance" / "approvals"

    approvals = []

    if not approvals_dir.exists():
        return approvals

    for status_dir in approvals_dir.iterdir():
        if not status_dir.is_dir():
            continue

        status = status_dir.name  # pending, approved, rejected, applied

        for json_file in status_dir.glob("*.json"):
            try:
                approvals.append({
                    "name": json_file.name,
                    "status": status,
                    "path": f"reports/pilot-device-compliance/approvals/{status}/{json_file.name}",
                    "mtime": json_file.stat().st_mtime,
                })
            except Exception:
                pass

    return sorted(approvals, key=lambda x: x["mtime"], reverse=True)


def list_apply_plans(root: Path) -> List[Dict]:
    """List apply plans."""
    approvals_dir = root / "reports" / "pilot-device-compliance" / "approvals"

    apply_plans = []

    if not approvals_dir.exists():
        return apply_plans

    for status_dir in approvals_dir.iterdir():
        if not status_dir.is_dir():
            continue

        for json_file in status_dir.glob("apply-plan-*.json"):
            try:
                apply_plans.append({
                    "name": json_file.name,
                    "path": f"reports/pilot-device-compliance/approvals/{status_dir.name}/{json_file.name}",
                    "mtime": json_file.stat().st_mtime,
                })
            except Exception:
                pass

    return sorted(apply_plans, key=lambda x: x["mtime"], reverse=True)


def list_batch_results(root: Path) -> List[Dict]:
    """List batch apply results."""
    applied_dir = root / "reports" / "pilot-device-compliance" / "approvals" / "applied"

    results = []

    if not applied_dir.exists():
        return results

    for md_file in applied_dir.glob("batch-apply-result-*.md"):
        try:
            results.append({
                "name": md_file.name,
                "path": f"reports/pilot-device-compliance/approvals/applied/{md_file.name}",
                "mtime": md_file.stat().st_mtime,
            })
        except Exception:
            pass

    return sorted(results, key=lambda x: x["mtime"], reverse=True)


def list_incidents(root: Path) -> List[Dict]:
    """List incident reports."""
    incidents_dir = root / "reports" / "pilot-device-compliance" / "incidents"

    incidents = []

    if not incidents_dir.exists():
        return incidents

    for md_file in incidents_dir.glob("*.md"):
        try:
            incidents.append({
                "name": md_file.name,
                "path": f"reports/pilot-device-compliance/incidents/{md_file.name}",
                "mtime": md_file.stat().st_mtime,
            })
        except Exception:
            pass

    return sorted(incidents, key=lambda x: x["mtime"], reverse=True)


def list_comparisons(root: Path) -> List[Dict]:
    """List device comparisons."""
    comparisons_dir = root / "reports" / "pilot-device-compliance" / "comparisons"

    comparisons = []

    if not comparisons_dir.exists():
        return comparisons

    for md_file in comparisons_dir.glob("*.md"):
        try:
            comparisons.append({
                "name": md_file.name,
                "path": f"reports/pilot-device-compliance/comparisons/{md_file.name}",
                "mtime": md_file.stat().st_mtime,
            })
        except Exception:
            pass

    return sorted(comparisons, key=lambda x: x["mtime"], reverse=True)
