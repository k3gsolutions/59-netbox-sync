#!/usr/bin/env python3
"""Local operational readiness check for the Week 1 pending-item workflow."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def check_path(path: Path, label: str) -> bool:
    if path.exists():
        print(f"✓ {label}: {path}")
        return True
    print(f"✗ {label}: missing ({path})")
    return False


def main() -> int:
    print("=" * 60)
    print("Local Operational Readiness Check")
    print("=" * 60)

    checks = [
        check_path(ROOT / "webui" / "app.py", "Web UI app"),
        check_path(ROOT / "webui" / "services" / "response_forms.py", "Response forms service"),
        check_path(ROOT / "reports" / "pilot-device-compliance" / "week1-metadata-collection-template.csv", "Week 1 template"),
        check_path(ROOT / "reports" / "pilot-device-compliance" / "week1-response-validation.md", "Week 1 validation report"),
        check_path(ROOT / "docs" / "62-webui-response-form.md", "Pending-item UX doc"),
    ]

    csv_dir = ROOT / "reports" / "pilot-device-compliance" / "week1-responses"
    csv_ok = csv_dir.exists()
    print(f"{'✓' if csv_ok else '✗'} Week 1 response directory: {csv_dir}")
    checks.append(csv_ok)

    from webui.app import app

    route_paths = {getattr(route, "path", "") for route in app.routes}
    required_routes = {
        "/service-engagement/{device}/pending-items",
        "/service-engagement/{device}/pending-items/{safe_item_id}",
        "/service-engagement/{device}/pending-items/{safe_item_id}/response",
    }
    missing_routes = sorted(required_routes - route_paths)
    if missing_routes:
        print(f"✗ Missing routes: {', '.join(missing_routes)}")
        checks.append(False)
    else:
        print("✓ Pending-item routes present")
        checks.append(True)

    success = all(checks)
    print("=" * 60)
    print("Readiness:", "PASS" if success else "FAIL")
    print("=" * 60)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
