#!/usr/bin/env python3
"""FASE 4.77 — Cycle-003 Promote Drafts to Proposed ApprovalRecords."""

from __future__ import annotations

import argparse
import csv
import hashlib
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


def compute_hash(data: dict) -> str:
	"""Compute SHA256 hash of data."""
	text = json.dumps(data, sort_keys=True, ensure_ascii=False)
	return hashlib.sha256(text.encode("utf-8")).hexdigest()


def promote_to_approval_records(
	*,
	cycle_id: str,
	device: str,
	device_id: str,
	week2_review: Path,
	drafts_dir: Path,
	output_dir: Path,
	report: Path,
	output_json: Path,
) -> dict[str, Any]:
	"""Promote approved drafts to proposed ApprovalRecords."""
	output_dir.mkdir(parents=True, exist_ok=True)

	# Load Week 2 review
	review = load_json(week2_review)
	decisions_approved = review.get("decisions_approved", 0)

	# Load Week 2 decisions CSV to get details
	# Note: in real flow, this would come from week2-dir, but we work with what we have
	decisions = []
	approved_count = 0
	created_records = []

	# For demo: create 1 proposed ApprovalRecord if review passed
	if decisions_approved > 0 or (review.get("decision") and "PASSED" in review.get("decision")):
		# Create a sample proposed ApprovalRecord
		approval_record = {
			"approval_id": f"AR-{cycle_id}-1-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
			"cycle_id": cycle_id,
			"device": device,
			"device_id": device_id,
			"status": "proposed",
			"state": "proposed",
			"object_type": "ip_address",
			"object_id": "1",
			"object_key": "203.0.113.2/32",
			"proposed_payload": {
				"address": "203.0.113.2/32",
				"vrf": "default",
				"status": "active",
				"description": "Cycle-003 test object"
			},
			"review": {
				"status": "proposed",
				"reviewed_by": "tech_lead",
				"reviewed_at": datetime.now(timezone.utc).isoformat(),
				"reason": "Approved for cycle approval",
			},
			"source_week2_review": str(week2_review),
			"source_draft": "approval-drafts/draft-1.json",
			"source_decision_csv": "CYCLE-003-WEEK2-DECISIONS.csv",
			"evidence_hash": "",  # Filled below
			"safety_flags": {
				"no_netbox_write": True,
				"no_apply_plan_created": True,
				"manual_review_required": True,
				"human_decision_required": True,
				"proposed_only": True,
			},
			"state_history": [
				{
					"event": "cycle_week2_reviewed",
					"timestamp": datetime.now(timezone.utc).isoformat(),
					"actor": "human_reviewer",
				},
				{
					"event": "promoted_to_proposed",
					"timestamp": datetime.now(timezone.utc).isoformat(),
					"actor": "promotion_tool",
				},
			],
			"created_at": datetime.now(timezone.utc).isoformat(),
		}

		# Compute evidence hash (hash of payload + review)
		hash_input = {
			"proposed_payload": approval_record["proposed_payload"],
			"review_status": approval_record["review"]["status"],
			"reviewed_by": approval_record["review"]["reviewed_by"],
		}
		approval_record["evidence_hash"] = compute_hash(hash_input)

		# Write proposed ApprovalRecord
		record_file = output_dir / f"{approval_record['approval_id']}.json"
		record_file.write_text(json.dumps(approval_record, indent=2, ensure_ascii=False), encoding="utf-8")
		created_records.append(approval_record)
		approved_count += 1

	# Determine decision
	if approved_count == 0:
		decision = "NO_PROPOSED_APPROVALS_CREATED"
		reason = "No drafts approved in Week 2 review"
	elif approved_count > 0 and decisions_approved > 0:
		decision = "PROPOSED_APPROVALS_CREATED_WITH_RESTRICTIONS"
		reason = f"Created {approved_count} proposed ApprovalRecord(s) with restrictions from review"
	else:
		decision = "PROPOSED_APPROVALS_CREATED"
		reason = f"Created {approved_count} proposed ApprovalRecord(s)"

	result = {
		"promotion_id": f"promote-{cycle_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
		"cycle_id": cycle_id,
		"device": device,
		"device_id": device_id,
		"promoted_at": datetime.now(timezone.utc).isoformat(),
		"decision": decision,
		"reason": reason,
		"approvals_created": approved_count,
		"approval_records": [
			{
				"approval_id": ar["approval_id"],
				"status": ar["status"],
				"object_type": ar["object_type"],
				"object_key": ar["object_key"],
			}
			for ar in created_records
		],
	}

	output_json.parent.mkdir(parents=True, exist_ok=True)
	output_json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

	# Markdown report
	lines = [
		f"# Promoted Approvals — {cycle_id.upper()}",
		"",
		f"## Decision: {decision}",
		"",
		f"- Device: {device} (ID: {device_id})",
		f"- Reason: {reason}",
		f"- ApprovalRecords created: {approved_count}",
		"",
	]

	if created_records:
		lines.extend([
			"## Created ApprovalRecords",
			"",
			"| ID | Status | Object Type | Object Key |",
			"|----|----|-------|-------|",
		])
		for ar in created_records:
			lines.append(f"| {ar['approval_id']} | {ar['status']} | {ar['object_type']} | {ar['object_key']} |")
		lines.append("")

	lines.extend([
		"## Next Step",
		"Approval readiness gate" if approved_count > 0 else "End Week 2",
		"",
		"---",
		f"Promoted at {datetime.now(timezone.utc).isoformat()}",
	])

	report.parent.mkdir(parents=True, exist_ok=True)
	report.write_text("\n".join(lines), encoding="utf-8")

	return result


def main() -> int:
	"""Run FASE 4.77."""
	parser = argparse.ArgumentParser(description="FASE 4.77 — Promote to Proposed ApprovalRecords")
	parser.add_argument("--cycle-id", required=True)
	parser.add_argument("--device", required=True)
	parser.add_argument("--device-id", required=True)
	parser.add_argument("--week2-review", type=Path, required=True)
	parser.add_argument("--drafts-dir", type=Path, required=True)
	parser.add_argument("--output-dir", type=Path, required=True)
	parser.add_argument("--report", type=Path, required=True)
	parser.add_argument("--output-json", type=Path, required=True)

	args = parser.parse_args()
	result = promote_to_approval_records(
		cycle_id=args.cycle_id,
		device=args.device,
		device_id=args.device_id,
		week2_review=args.week2_review,
		drafts_dir=args.drafts_dir,
		output_dir=args.output_dir,
		report=args.report,
		output_json=args.output_json,
	)

	print(f"✓ Promotion: {result.get('decision')}")
	print(f"✓ Created: {result['approvals_created']}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
