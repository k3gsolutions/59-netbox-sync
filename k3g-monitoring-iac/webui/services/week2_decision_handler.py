"""Week 2 review decision handling — local governance without NetBox."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Week2Decision:
    """Week 2 review human decision."""

    item_id: str
    reviewer: str
    decision: str  # approve_for_approval_record, request_changes, reject, defer, block
    reason: Optional[str] = None
    notes: Optional[str] = None
    reviewed_at: str = ""
    approval_record_allowed: bool = False

    def __post_init__(self) -> None:
        """Set reviewed_at if not set."""
        if not self.reviewed_at:
            self.reviewed_at = datetime.utcnow().isoformat() + "Z"

    def validate(self) -> tuple[bool, str]:
        """Validate decision. Returns (valid, message)."""
        if not self.reviewer:
            return False, "reviewer required"
        if not self.decision:
            return False, "decision required"
        if self.decision not in [
            "approve_for_approval_record",
            "request_changes",
            "reject",
            "defer",
            "block",
        ]:
            return False, f"unknown decision: {self.decision}"

        # Decision-specific rules
        if self.decision == "approve_for_approval_record":
            if not self.approval_record_allowed:
                return False, "approval_record_allowed must be true for approve"
            if not self.reason and not self.notes:
                return False, "reason or notes required for approve"
        elif self.decision == "request_changes":
            if not self.notes:
                return False, "notes required for request_changes"
        elif self.decision == "reject":
            if not self.reason:
                return False, "reason required for reject"
        elif self.decision == "block":
            if not self.reason:
                return False, "reason required for block"
        elif self.decision == "defer":
            if not self.notes:
                return False, "notes required for defer"

        return True, ""


def save_decision(
    decision: Week2Decision,
    review_dir: Path,
) -> tuple[bool, str]:
    """Save decision to CSV + audit JSON. Returns (success, message)."""
    # Validate
    valid, msg = decision.validate()
    if not valid:
        return False, msg

    review_dir.mkdir(parents=True, exist_ok=True)

    # Save to CSV
    csv_path = review_dir / "week2-review-decisions.csv"
    fieldnames = [
        "item_id",
        "reviewer",
        "decision",
        "reason",
        "notes",
        "reviewed_at",
        "approval_record_allowed",
    ]

    # Read existing, update, write
    rows = []
    if csv_path.exists():
        with open(csv_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader) if reader else []

    # Find and update or append
    found = False
    for row in rows:
        if row.get("item_id") == decision.item_id:
            row["reviewer"] = decision.reviewer
            row["decision"] = decision.decision
            row["reason"] = decision.reason or ""
            row["notes"] = decision.notes or ""
            row["reviewed_at"] = decision.reviewed_at
            row["approval_record_allowed"] = str(decision.approval_record_allowed)
            found = True
            break

    if not found:
        rows.append(asdict(decision))

    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # Save audit JSON
    audit_dir = review_dir / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_file = audit_dir / f"decision-{decision.item_id}-{datetime.utcnow().isoformat()}.json"

    audit_data = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "decision": asdict(decision),
        "security": {
            "no_netbox_write": True,
            "no_token": True,
            "no_apply": True,
            "no_approval_record_auto": True,
        },
    }
    audit_file.write_text(json.dumps(audit_data, indent=2), encoding="utf-8")

    return True, f"Decision saved for {decision.item_id}"


def load_decisions(review_dir: Path) -> List[Dict[str, Any]]:
    """Load existing decisions from CSV."""
    csv_path = review_dir / "week2-review-decisions.csv"
    if not csv_path.exists():
        return []

    rows = []
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader) if reader else []
    return rows


def get_item_decision(item_id: str, review_dir: Path) -> Optional[Dict[str, Any]]:
    """Get existing decision for item."""
    decisions = load_decisions(review_dir)
    for d in decisions:
        if d.get("item_id") == item_id:
            return d
    return None
