#!/usr/bin/env python3
"""FASE 4.76 — Cycle-003 Week 2 Human Review."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_csv(path: Path) -> list[dict]:
	"""Load CSV safely."""
	try:
		with open(path, "r", encoding="utf-8") as f:
			return list(csv.DictReader(f))
	except Exception:
		return []


def review_week2(
	*,
	cycle_id: str,
	device: str,
	device_id: str,
	cycle_dir: Path,
	week2_dir: Path,
	output: Path,
	output_json: Path,
) -> dict[str, Any]:
	"""Review Week 2 decisions."""
	week2_dir.mkdir(parents=True, exist_ok=True)

	# Load decisions CSV
	decisions_file = week2_dir / f"{cycle_id.upper()}-WEEK2-DECISIONS.csv"
	decisions = load_csv(decisions_file)

	issues = []
	reviewed_count = 0
	pending_count = 0
	approved_count = 0

	# Validate each decision
	for idx, decision_row in enumerate(decisions):
		decision = decision_row.get("decision", "").strip()
		reviewed_by = decision_row.get("reviewed_by", "").strip()
		reviewed_at = decision_row.get("reviewed_at", "").strip()
		approval_record_allowed = decision_row.get("approval_record_allowed", "false").lower() == "true"
		reason = decision_row.get("reason", "").strip()

		# Check if reviewed
		if decision == "pending_review":
			pending_count += 1
			continue

		reviewed_count += 1

		# Validate required fields
		if not reviewed_by:
			issues.append(f"Row {idx}: reviewer missing")
		if not reviewed_at:
			issues.append(f"Row {idx}: reviewed_at missing")
		if not reason:
			issues.append(f"Row {idx}: reason missing")

		# Validate approval_record_allowed logic
		if decision == "approve_for_approval_record" and not approval_record_allowed:
			issues.append(f"Row {idx}: approval_for_approval_record but approval_record_allowed=false")
		elif decision != "approve_for_approval_record" and approval_record_allowed:
			issues.append(f"Row {idx}: approval_record_allowed=true but decision is {decision}")

		# Count approvals
		if decision == "approve_for_approval_record":
			approved_count += 1

	# Determine decision
	if pending_count > 0 and reviewed_count == 0:
		status_decision = "WEEK2_REVIEW_BLOCKED"
		status_reason = f"All decisions pending; no reviews completed"
	elif issues:
		status_decision = "WEEK2_REVIEW_PASSED_WITH_RESTRICTIONS"
		status_reason = f"Reviewed {reviewed_count}, but validation issues found"
	elif reviewed_count == 0:
		status_decision = "WEEK2_REVIEW_BLOCKED"
		status_reason = "No decisions reviewed"
	else:
		status_decision = "WEEK2_REVIEW_PASSED"
		status_reason = f"Reviewed {reviewed_count}; {approved_count} approved for ApprovalRecord"

	result = {
		"review_id": f"week2-review-{cycle_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
		"cycle_id": cycle_id,
		"device": device,
		"device_id": device_id,
		"reviewed_at": datetime.now(timezone.utc).isoformat(),
		"decision": status_decision,
		"reason": status_reason,
		"decisions_total": len(decisions),
		"decisions_pending": pending_count,
		"decisions_reviewed": reviewed_count,
		"decisions_approved": approved_count,
		"validation_issues": issues,
	}

	output_json.parent.mkdir(parents=True, exist_ok=True)
	output_json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

	# Markdown report
	lines = [
		f"# Week 2 Human Review — {cycle_id.upper()}",
		"",
		f"## Decision: {status_decision}",
		"",
		f"- Device: {device} (ID: {device_id})",
		f"- Reason: {status_reason}",
		f"- Total decisions: {len(decisions)}",
		f"- Pending: {pending_count}",
		f"- Reviewed: {reviewed_count}",
		f"- Approved for ApprovalRecord: {approved_count}",
		"",
	]

	if issues:
		lines.extend([
			"## Validation Issues",
			"",
		])
		for issue in issues:
			lines.append(f"- {issue}")
		lines.append("")

	lines.extend([
		"## Next Step",
		"Promote to ApprovalRecords" if "PASSED" in status_decision and approved_count > 0 else "Resolve pending reviews or validation issues",
		"",
		"---",
		f"Reviewed at {datetime.now(timezone.utc).isoformat()}",
	])

	output.parent.mkdir(parents=True, exist_ok=True)
	output.write_text("\n".join(lines), encoding="utf-8")

	return result


def main() -> int:
	"""Run FASE 4.76."""
	parser = argparse.ArgumentParser(description="FASE 4.76 — Week 2 Human Review")
	parser.add_argument("--cycle-id", required=True)
	parser.add_argument("--device", required=True)
	parser.add_argument("--device-id", required=True)
	parser.add_argument("--cycle-dir", type=Path, required=True)
	parser.add_argument("--week2-dir", type=Path, required=True)
	parser.add_argument("--output", type=Path, required=True)
	parser.add_argument("--output-json", type=Path, required=True)

	args = parser.parse_args()
	result = review_week2(
		cycle_id=args.cycle_id,
		device=args.device,
		device_id=args.device_id,
		cycle_dir=args.cycle_dir,
		week2_dir=args.week2_dir,
		output=args.output,
		output_json=args.output_json,
	)

	print(f"✓ Week 2 review: {result.get('decision')}")
	print(f"✓ Report: {args.output}")
	return 0 if "BLOCKED" not in result.get("decision") else 1


if __name__ == "__main__":
	raise SystemExit(main())
