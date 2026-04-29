#!/usr/bin/env python3
"""Manage Week 1 UAT response artifacts locally."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


ROOT = Path(__file__).resolve().parents[2]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage Week 1 UAT responses")
    parser.add_argument("--responses-dir", required=True)
    parser.add_argument("--mode", required=True, choices=["report", "archive", "keep-as-real", "reset"])
    parser.add_argument("--output", required=False)
    parser.add_argument("--confirm-reset-uat", action="store_true")
    parser.add_argument("--confirm-keep-as-real", action="store_true")
    parser.add_argument("--confirm-archive-uat", action="store_true")
    return parser.parse_args()


def _read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _csv_fieldnames(rows: List[Dict[str, str]]) -> List[str]:
    fieldnames: List[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    return fieldnames


def _write_csv_rows(path: Path, rows: List[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = _csv_fieldnames(rows)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def _is_uat_row(row: Dict[str, str]) -> bool:
    values = " ".join((row.get(key, "") or "") for key in row)
    lowered = values.lower()
    return (
        row.get("updated_by", "").strip().lower() == "uat"
        or "uat" in lowered
    )


def _split_csv_rows(rows: List[Dict[str, str]]) -> tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    real_rows: List[Dict[str, str]] = []
    uat_rows: List[Dict[str, str]] = []
    for row in rows:
        if _is_uat_row(row):
            uat_rows.append(row)
        else:
            real_rows.append(row)
    return real_rows, uat_rows


def _split_audit_entries(entries: List[Dict[str, object]]) -> tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    real_entries: List[Dict[str, object]] = []
    uat_entries: List[Dict[str, object]] = []
    for entry in entries:
        if str(entry.get("updated_by", "")).strip().lower() == "uat":
            uat_entries.append(entry)
        else:
            real_entries.append(entry)
    return real_entries, uat_entries


def _detect_uat_files(responses_dir: Path) -> List[Dict[str, object]]:
    audit_dir = responses_dir / "audit"
    files: List[Dict[str, object]] = []
    for csv_path in sorted(responses_dir.glob("*.csv")):
        rows = _read_csv_rows(csv_path)
        if not rows:
            continue
        uat_rows = [row for row in rows if _is_uat_row(row)]
        if uat_rows:
            files.append(
                {
                    "type": "csv",
                    "path": csv_path,
                    "rows": len(rows),
                    "uat_rows": len(uat_rows),
                    "all_uat": len(uat_rows) == len(rows),
                }
            )
    if audit_dir.exists():
        for audit_path in sorted(audit_dir.glob("*.json")):
            try:
                payload = json.loads(audit_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(payload, list):
                continue
            uat_entries = [entry for entry in payload if str(entry.get("updated_by", "")).strip().lower() == "uat"]
            if uat_entries:
                files.append(
                    {
                        "type": "audit",
                        "path": audit_path,
                        "rows": len(payload),
                        "uat_rows": len(uat_entries),
                        "all_uat": len(uat_entries) == len(payload),
                    }
                )
    return files


def _render_report(device_state: str, files: List[Dict[str, object]], title: str) -> str:
    lines = [
        f"# {title}",
        "",
        f"**Generated:** {_utc_now()}",
        f"**State:** {device_state}",
        "",
        "## Detected UAT Artifacts",
        "",
    ]
    if not files:
        lines.append("No UAT artifacts detected.")
    else:
        lines.append("| File | Type | Rows | UAT Rows | All UAT |")
        lines.append("|---|---|---:|---:|---|")
        for item in files:
            lines.append(
                f"| {item['path'].name} | {item['type']} | {item['rows']} | {item['uat_rows']} | {'yes' if item['all_uat'] else 'no'} |"
            )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"- {device_state}",
            "",
            "## Safety",
            "",
            "- No NetBox writes",
            "- No apply",
            "- No /sync",
            "- No ApprovalRecord auto-create",
            "- No ApplyPlan auto-create",
        ]
    )
    return "\n".join(lines) + "\n"


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _archive_uat_files(responses_dir: Path, files: List[Dict[str, object]], confirm: bool) -> Dict[str, object]:
    if not confirm:
        return {"success": False, "error": "missing --confirm-archive-uat"}
    archive_root = responses_dir / "uat-archive" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive_root.mkdir(parents=True, exist_ok=True)
    archived = []
    for item in files:
        src = item["path"]
        if item["type"] == "csv":
            rows = _read_csv_rows(src)
            real_rows, uat_rows = _split_csv_rows(rows)
            if not uat_rows:
                continue
            archive_file = archive_root / src.name
            _write_csv_rows(archive_file, uat_rows)
            archived.append(str(archive_file))
            if real_rows:
                _write_csv_rows(src, real_rows)
            else:
                src.unlink()
        elif item["type"] == "audit":
            try:
                payload = json.loads(src.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(payload, list):
                continue
            real_entries, uat_entries = _split_audit_entries(payload)
            if not uat_entries:
                continue
            archive_file = archive_root / src.name
            archive_file.write_text(json.dumps(uat_entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            archived.append(str(archive_file))
            if real_entries:
                src.write_text(json.dumps(real_entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            else:
                src.unlink()
    return {"success": True, "archive_dir": str(archive_root), "archived": archived}


def _reset_uat_files(files: List[Dict[str, object]], confirm: bool) -> Dict[str, object]:
    if not confirm:
        return {"success": False, "error": "missing --confirm-reset-uat"}
    removed = []
    for item in files:
        src = item["path"]
        if item["type"] == "csv" and src.exists():
            rows = _read_csv_rows(src)
            real_rows, uat_rows = _split_csv_rows(rows)
            if not uat_rows:
                continue
            if real_rows:
                _write_csv_rows(src, real_rows)
            else:
                src.unlink()
            removed.append(str(src))
        elif item["type"] == "audit" and src.exists():
            try:
                payload = json.loads(src.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(payload, list):
                continue
            real_entries, uat_entries = _split_audit_entries(payload)
            if not uat_entries:
                continue
            if real_entries:
                src.write_text(json.dumps(real_entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            else:
                src.unlink()
            removed.append(str(src))
    return {"success": True, "removed": removed}


def main() -> int:
    args = _parse_args()
    responses_dir = Path(args.responses_dir)
    files = _detect_uat_files(responses_dir)

    has_active_uat = bool(files)
    state_report = "GO_WITH_RESTRICTIONS_UAT_PRESENT" if has_active_uat else "GO_REAL_WEEK1_CLEAN"
    readiness_report = "GO_REAL_WEEK1_WITH_EXISTING_RESPONSES" if has_active_uat and args.mode == "keep-as-real" else state_report

    report_output = Path(args.output) if args.output else ROOT / "reports" / "pilot-device-compliance" / "WEEK1-UAT-RESPONSE-AUDIT.md"
    readiness_output = ROOT / "reports" / "pilot-device-compliance" / "WEEK1-REAL-READINESS-AFTER-UAT.md"

    if args.mode == "report":
        _write_text(report_output, _render_report(state_report, files, "WEEK1 UAT Response Audit"))
        _write_text(readiness_output, _render_report(readiness_report, files, "Week 1 Real Readiness After UAT"))
        print(f"✓ UAT report saved: {report_output}")
        print(f"✓ Readiness report saved: {readiness_output}")
        return 0

    if args.mode == "archive":
        result = _archive_uat_files(responses_dir, files, args.confirm_archive_uat)
        if not result.get("success"):
            print(result["error"])
            return 1
        _write_text(report_output, _render_report("GO_REAL_WEEK1_CLEAN", [], "WEEK1 UAT Response Audit"))
        _write_text(readiness_output, _render_report("GO_REAL_WEEK1_CLEAN", [], "Week 1 Real Readiness After UAT"))
        print(f"✓ Archived UAT artifacts to: {result['archive_dir']}")
        return 0

    if args.mode == "reset":
        result = _reset_uat_files(files, args.confirm_reset_uat)
        if not result.get("success"):
            print(result["error"])
            return 1
        _write_text(report_output, _render_report("GO_REAL_WEEK1_CLEAN", [], "WEEK1 UAT Response Audit"))
        _write_text(readiness_output, _render_report("GO_REAL_WEEK1_CLEAN", [], "Week 1 Real Readiness After UAT"))
        print("✓ UAT artifacts removed")
        return 0

    if args.mode == "keep-as-real":
        if not args.confirm_keep_as_real:
            print("missing --confirm-keep-as-real")
            return 1
        _write_text(report_output, _render_report("KEEP_AS_REAL", files, "WEEK1 UAT Response Audit"))
        _write_text(readiness_output, _render_report(readiness_report, files, "Week 1 Real Readiness After UAT"))
        print("✓ UAT artifacts marked as keep-as-real")
        return 0

    print("unknown mode")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
