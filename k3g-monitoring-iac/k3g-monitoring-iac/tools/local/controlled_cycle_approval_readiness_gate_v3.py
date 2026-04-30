#!/usr/bin/env python3
"""FASE 4.78 — Cycle-003 Approval Readiness Gate."""

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
		"bearer",
	]
	found = []
	text_lower = text.lower()
	for keyword in forbidden:
		if keyword.lower() in text_lower:
			found.append(keyword)
	return list(set(found))


def validate_approval_readiness(
	*,
	cycle_id: str,
	device: str,
	device_id: str,
	approvals_dir: Path,
	week2_review: Path,
	output: Path,
	output_json: Path,
) -> dict[str, Any]:
	"""Validate approval readiness."""
	approvals_dir.mkdir(parents=True, exist_ok=True)

	# Load Week 2 review
	review = load_json(week2_review)
	review_decision = review.get("decision", "")

	# Scan for proposed ApprovalRecords
	proposed_files = list(approvals_dir.glob("AR-*.json"))
	approvals = []
	issues = []

	if len(proposed_files) == 0:
		decision = "NOT_READY_FOR_MANUAL_APPROVAL_REVIEW"
		reason = "No proposed ApprovalRecords found"
	else:
		# Validate each proposed ApprovalRecord
		for ar_file in proposed_files:
			ar = load_json(ar_file)

			# Validate cycle_id
			if ar.get("cycle_id") != cycle_id:
				issues.append(f"{ar_file.name}: cycle_id mismatch")
				continue

			# Validate status/state
			if ar.get("status") != "proposed":
				issues.append(f"{ar_file.name}: status is not proposed")
			if ar.get("state") != "proposed":
				issues.append(f"{ar_file.name}: state is not proposed")

			# Validate required fields
			if not ar.get("object_type"):
				issues.append(f"{ar_file.name}: object_type missing")
			if not ar.get("object_key"):
				issues.append(f"{ar_file.name}: object_key missing")
			if not ar.get("proposed_payload"):
				issues.append(f"{ar_file.name}: proposed_payload missing")

			# Validate review fields
			if not ar.get("review", {}).get("reviewed_by"):
				issues.append(f"{ar_file.name}: reviewer missing")
			if not ar.get("review", {}).get("reviewed_at"):
				issues.append(f"{ar_file.name}: reviewed_at missing")

			# Validate evidence_hash
			if not ar.get("evidence_hash"):
				issues.append(f"{ar_file.name}: evidence_hash missing")

			# Validate safety flags
			safety_flags = ar.get("safety_flags", {})
			required_flags = [
				"no_netbox_write",
				"no_apply_plan_created",
				"manual_review_required",
				"human_decision_required",
				"proposed_only",
			]
			for flag in required_flags:
				if not safety_flags.get(flag):
					issues.append(f"{ar_file.name}: {flag} not true")

			# Validate state_history
			state_history = ar.get("state_history", [])
			has_promoted = any(e.get("event") == "promoted_to_proposed" for e in state_history)
			if not has_promoted:
				issues.append(f"{ar_file.name}: promoted_to_proposed event missing")

			# Scan for secrets
			ar_text = json.dumps(ar, ensure_ascii=False)
			secrets = scan_for_secrets(ar_text)
			if secrets:
				issues.append(f"{ar_file.name}: secrets found: {', '.join(secrets)}")

			approvals.append(ar)

		# Determine decision
		if issues:
			decision = "NOT_READY_FOR_MANUAL_APPROVAL_REVIEW"
			reason = f"Validation issues found in {len(proposed_files)} record(s)"
		elif len(proposed_files) > 3:
			decision = "NOT_READY_FOR_MANUAL_APPROVAL_REVIEW"
			reason = f"Too many items ({len(proposed_files)} > 3)"
		else:
			decision = "READY_FOR_MANUAL_APPROVAL_REVIEW"
			reason = f"All {len(proposed_files)} proposed ApprovalRecord(s) valid"

	result = {
		"readiness_id": f"readiness-{cycle_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
		"cycle_id": cycle_id,
		"device": device,
		"device_id": device_id,
		"validated_at": datetime.now(timezone.utc).isoformat(),
		"decision": decision,
		"reason": reason,
		"approvals_count": len(proposed_files),
		"validation_issues": issues,
	}

	output_json.parent.mkdir(parents=True, exist_ok=True)
	output_json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

	# Markdown report
	lines = [
		f"# Approval Readiness Gate — {cycle_id.upper()}",
		"",
		f"## Decision: {decision}",
		"",
		f"- Device: {device} (ID: {device_id})",
		f"- Reason: {reason}",
		f"- Proposed ApprovalRecords: {len(proposed_files)}",
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
		"Manual approval review" if "READY" in decision else "Resolve validation issues",
		"",
		"---",
		f"Validated at {datetime.now(timezone.utc).isoformat()}",
	])

	output.parent.mkdir(parents=True, exist_ok=True)
	output.write_text("\n".join(lines), encoding="utf-8")

	return result


def main() -> int:
	"""Run FASE 4.78."""
	parser = argparse.ArgumentParser(description="FASE 4.78 — Approval Readiness Gate")
	parser.add_argument("--cycle-id", required=True)
	parser.add_argument("--device", required=True)
	parser.add_argument("--device-id", required=True)
	parser.add_argument("--approvals-dir", type=Path, required=True)
	parser.add_argument("--week2-review", type=Path, required=True)
	parser.add_argument("--output", type=Path, required=True)
	parser.add_argument("--output-json", type=Path, required=True)

	args = parser.parse_args()
	result = validate_approval_readiness(
		cycle_id=args.cycle_id,
		device=args.device,
		device_id=args.device_id,
		approvals_dir=args.approvals_dir,
		week2_review=args.week2_review,
		output=args.output,
		output_json=args.output_json,
	)

	print(f"✓ Approval readiness: {result.get('decision')}")
	print(f"✓ Report: {args.output}")
	return 0 if "READY" in result.get("decision") else 1


if __name__ == "__main__":
	raise SystemExit(main())
