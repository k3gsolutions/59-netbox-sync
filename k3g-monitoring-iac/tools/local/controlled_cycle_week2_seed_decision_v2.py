#!/usr/bin/env python3
"""FASE 4.44 - Cycle-002 Week 2 Decision Test Seed.

Seed one local Week 2 decision for controlled testing.
No NetBox write. No token. No ApplyPlan.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def safe_text(value: Any) -> str:
    return str(value or "").strip()


def truthy(value: Any) -> bool:
    return safe_text(value).lower() in {"true", "1", "yes", "y"}


def load_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: List[Dict[str, str]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def sanitize(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", safe_text(value))


def draft_path(drafts_dir: Path, item_id: str) -> Path:
    return drafts_dir / f"approval-draft-{sanitize(item_id)}.json"


def has_secret(text: str) -> bool:
    lowered = safe_text(text).lower()
    blocked = ["netbox_write_token", "authorization: token", "token=", "password=", "secret=", "api_key", "private key", "bearer"]
    return any(term in lowered for term in blocked)


def main() -> int:
    parser = argparse.ArgumentParser(description="FASE 4.44 - Cycle-002 Week 2 Decision Test Seed")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--week2-dir", type=Path, required=True)
    parser.add_argument("--decision", required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--approval-record-allowed", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()

    decisions_csv = args.week2_dir / f"{args.cycle_id.upper()}-WEEK2-DECISIONS.csv"
    drafts_dir = args.week2_dir / "approval-drafts"
    audit_dir = args.week2_dir / "audit"
    backup_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    if args.cycle_id != "cycle-002":
        print("✗ cycle_id must be cycle-002")
        return 1
    if args.device_id != "1890":
        print("✗ device_id must be 1890")
        return 1
    if args.decision != "approve_for_approval_record":
        print("✗ only approve_for_approval_record is allowed for this seed")
        return 1
    if not truthy(args.approval_record_allowed):
        print("✗ approval_record_allowed must be true")
        return 1
    if not args.reviewer or not args.reason:
        print("✗ reviewer and reason are required")
        return 1
    if has_secret(args.reviewer) or has_secret(args.reason):
        print("✗ secret keyword found in reviewer/reason")
        return 1
    if not decisions_csv.exists():
        print(f"✗ decisions csv missing: {decisions_csv}")
        return 1
    if not drafts_dir.exists():
        print(f"✗ drafts dir missing: {drafts_dir}")
        return 1

    rows = load_csv(decisions_csv)
    if not rows:
        print("✗ decisions csv empty")
        return 1

    target_index = None
    for index, row in enumerate(rows):
        if safe_text(row.get("decision")).lower() in {"pending_review", "pending", ""}:
            target_index = index
            break
    if target_index is None:
        print("✗ no pending_review item found")
        return 1

    target = rows[target_index]
    item_id = safe_text(target.get("item_id") or target.get("object_key"))
    if not item_id:
        print("✗ target item_id missing")
        return 1
    draft_file = draft_path(drafts_dir, item_id)
    if not draft_file.exists():
        print(f"✗ draft missing: {draft_file.name}")
        return 1

    before_text = decisions_csv.read_text(encoding="utf-8")
    backup_path = decisions_csv.with_name(f"{decisions_csv.name}.bak.{backup_stamp}")
    backup_path.write_text(before_text, encoding="utf-8")

    now = datetime.now(timezone.utc).isoformat()
    target["decision"] = "approve_for_approval_record"
    target["reviewer"] = args.reviewer
    target["reviewed_at"] = now
    target["approval_record_allowed"] = "true"
    target["reason"] = args.reason
    if not safe_text(target.get("notes")):
        target["notes"] = args.reason

    fieldnames = list(rows[0].keys())
    if "approval_record_allowed" not in fieldnames:
        fieldnames.append("approval_record_allowed")
    if "reason" not in fieldnames:
        fieldnames.append("reason")
    if "notes" not in fieldnames:
        fieldnames.append("notes")

    write_csv(decisions_csv, rows, fieldnames)

    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_path = audit_dir / f"decision-seed-{backup_stamp}.json"
    audit_payload = {
        "cycle_id": args.cycle_id,
        "device": args.device,
        "device_id": args.device_id,
        "seeded_item_id": item_id,
        "seeded_draft": draft_file.name,
        "decision": "approve_for_approval_record",
        "reviewer": args.reviewer,
        "reviewed_at": now,
        "reason": args.reason,
        "approval_record_allowed": True,
        "backup_path": backup_path.name,
        "no_netbox_write": True,
        "no_apply_plan_created": True,
    }
    audit_path.write_text(json.dumps(audit_payload, indent=2), encoding="utf-8")

    report_lines = [
        f"# {args.cycle_id.upper()} Week 2 Decision Seed",
        "",
        "## Result",
        "- decision seeded: approve_for_approval_record",
        f"- seeded item: {item_id}",
        f"- reviewer: {args.reviewer}",
        f"- reviewed_at: {now}",
        f"- backup: {backup_path.name}",
        f"- audit: {audit_path.name}",
        "",
        "## Safety",
        "- No NetBox write",
        "- No ApplyPlan",
        "- No ApprovalRecord created",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(report_lines), encoding="utf-8")
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(audit_payload, indent=2), encoding="utf-8")

    print(f"✓ Seeded decision for {item_id}")
    print(f"✓ Backup: {backup_path}")
    print(f"✓ Audit: {audit_path}")
    print(f"✓ Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
