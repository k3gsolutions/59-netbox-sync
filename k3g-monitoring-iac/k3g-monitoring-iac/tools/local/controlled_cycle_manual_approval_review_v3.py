#!/usr/bin/env python3
"""FASE 4.79 — Cycle-003 Manual Approval Decision."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict:
	"""Load JSON safely."""
	try:
		return json.loads(path.read_text(encoding="utf-8"))
	except Exception:
		return {}


def scan_for_secrets(text: str) -> list[str]:
	"""Scan for secret keywords."""
	forbidden = [
		"NETBOX_WRITE_TOKEN",
		"token",
		"password",
		"secret",
		"api_key",
		"private_key",
		"bearer",
	]
	found = []
	text_lower = text.lower()
	for keyword in forbidden:
		if keyword.lower() in text_lower:
			found.append(keyword)
	return list(set(found))


def review_approval_record(
	*,
	cycle_id: str,
	approval_record: Path,
	decision: str,
	reviewer: str,
	reason: str,
	output_dir: Path,
	report: Path,
	output_json: Path,
) -> dict[str, Any]:
	"""Review and decide on approval record."""
	output_dir.mkdir(parents=True, exist_ok=True)

	# Load approval record
	record = load_json(approval_record)
	issues = []

	# Validate record exists
	if not record:
		issues.append("approval record not found or unreadable")
		result = {
			"review_id": f"approval-review-{cycle_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
			"cycle_id": cycle_id,
			"decision": "CYCLE_APPROVAL_REVIEW_BLOCKED",
			"reason": "Record not found",
			"validation_issues": issues,
		}
	else:
		# Validate basic fields
		if record.get("cycle_id") != cycle_id:
			issues.append(f"cycle_id mismatch: {record.get('cycle_id')} != {cycle_id}")
		if record.get("status") not in ["proposed", "pending"]:
			issues.append(f"status not proposed/pending: {record.get('status')}")
		if record.get("state") not in ["proposed", "pending"]:
			issues.append(f"state not proposed/pending: {record.get('state')}")

		# Validate reviewer and reason
		if not reviewer or not reviewer.strip():
			issues.append("reviewer missing")
		if not reason or not reason.strip():
			issues.append("reason missing")

		# Scan for secrets
		record_text = json.dumps(record, ensure_ascii=False)
		secrets = scan_for_secrets(record_text)
		if secrets:
			issues.append(f"secrets found: {', '.join(secrets)}")

		# Validate safety flags
		safety_flags = record.get("safety_flags", {})
		if not safety_flags.get("no_netbox_write"):
			issues.append("no_netbox_write not true")
		if not safety_flags.get("manual_review_required"):
			issues.append("manual_review_required not true")
		if not safety_flags.get("proposed_only"):
			issues.append("proposed_only not true")

		# Determine decision
		if decision == "approve":
			if issues:
				final_decision = "CYCLE_APPROVAL_REVIEW_BLOCKED"
				final_reason = f"Validation issues: {'; '.join(issues)}"
			else:
				# Create approved copy
				approved_record = record.copy()
				approved_record["status"] = "approved"
				approved_record["state"] = "approved"
				approved_record["approved_by"] = reviewer
				approved_record["approved_at"] = datetime.now(timezone.utc).isoformat()
				approved_record["approval_reason"] = reason

				# Add to state_history
				if "state_history" not in approved_record:
					approved_record["state_history"] = []
				approved_record["state_history"].append({
					"event": "cycle_manual_approval_reviewed",
					"timestamp": datetime.now(timezone.utc).isoformat(),
					"actor": reviewer,
				})
				approved_record["state_history"].append({
					"event": "approved_for_cycle_dryrun_applyplan",
					"timestamp": datetime.now(timezone.utc).isoformat(),
					"actor": reviewer,
				})

				# Write approved record
				approval_id = record.get("approval_id", "AR-unknown")
				approved_file = output_dir / f"{approval_id}.json"
				approved_file.write_text(json.dumps(approved_record, indent=2, ensure_ascii=False), encoding="utf-8")

				final_decision = "CYCLE_APPROVAL_REVIEW_APPROVED"
				final_reason = f"Approved by {reviewer}"
		else:
			# For reject/defer/block
			final_decision = "CYCLE_APPROVAL_REVIEW_BLOCKED"
			final_reason = f"Decision: {decision} — {reason}"

		result = {
			"review_id": f"approval-review-{cycle_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
			"cycle_id": cycle_id,
			"approval_id": record.get("approval_id"),
			"decision": final_decision,
			"reason": final_reason,
			"reviewer": reviewer,
			"reviewed_at": datetime.now(timezone.utc).isoformat(),
			"validation_issues": issues,
		}

	output_json.parent.mkdir(parents=True, exist_ok=True)
	output_json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

	# Markdown report
	lines = [
		f"# Manual Approval Review — {cycle_id.upper()}",
		"",
		f"## Decision: {result['decision']}",
		"",
		f"- Reviewer: {reviewer}",
		f"- Reason: {result['reason']}",
		f"- Reviewed at: {result['reviewed_at']}",
		"",
	]

	if result.get("validation_issues"):
		lines.extend([
			"## Validation Issues",
			"",
		])
		for issue in result["validation_issues"]:
			lines.append(f"- {issue}")
		lines.append("")

	lines.extend([
		"## Next Step",
		"Generate dry-run ApplyPlan" if "APPROVED" in result["decision"] else "Resolve issues",
		"",
		"---",
		f"Reviewed at {result['reviewed_at']}",
	])

	report.parent.mkdir(parents=True, exist_ok=True)
	report.write_text("\n".join(lines), encoding="utf-8")

	return result


def main() -> int:
	"""Run FASE 4.79."""
	parser = argparse.ArgumentParser(description="FASE 4.79 — Manual Approval Review")
	parser.add_argument("--cycle-id", required=True)
	parser.add_argument("--approval-record", type=Path, required=True)
	parser.add_argument("--decision", choices=["approve", "reject", "request_changes", "defer", "block"], required=True)
	parser.add_argument("--reviewer", required=True)
	parser.add_argument("--reason", required=True)
	parser.add_argument("--output-dir", type=Path, required=True)
	parser.add_argument("--report", type=Path, required=True)
	parser.add_argument("--output-json", type=Path, required=True)

	args = parser.parse_args()
	result = review_approval_record(
		cycle_id=args.cycle_id,
		approval_record=args.approval_record,
		decision=args.decision,
		reviewer=args.reviewer,
		reason=args.reason,
		output_dir=args.output_dir,
		report=args.report,
		output_json=args.output_json,
	)

	print(f"✓ Approval review: {result.get('decision')}")
	print(f"✓ Report: {args.report}")
	return 0 if "BLOCKED" not in result.get("decision") else 1


if __name__ == "__main__":
	raise SystemExit(main())
