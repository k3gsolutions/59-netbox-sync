#!/usr/bin/env python3
"""FASE 4.82 — Cycle-003 Dry-Run Execution Gate."""

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


def validate_dryrun_execution_gate(
	*,
	cycle_id: str,
	apply_plan: Path,
	validation_report: Path,
	output: Path,
	output_json: Path,
) -> dict[str, Any]:
	"""Validate dry-run execution gate."""
	plan = load_json(apply_plan)
	issues = []

	# Validate ApplyPlan
	if not plan:
		issues.append("ApplyPlan not found")
	else:
		if plan.get("cycle_id") != cycle_id:
			issues.append(f"cycle_id mismatch: {plan.get('cycle_id')} != {cycle_id}")
		if plan.get("mode") != "dry_run":
			issues.append(f"mode not dry_run: {plan.get('mode')}")
		if plan.get("status") not in ["generated", "validated"]:
			issues.append(f"status not generated/validated: {plan.get('status')}")

		# Validate safety flags
		flags = plan.get("safety_flags", {})
		for flag in ["dry_run_only", "no_netbox_write", "no_token_required", "no_apply_execution", "manual_execution_gate_required", "generated_from_approved_records"]:
			if not flags.get(flag):
				issues.append(f"safety_flag {flag} not true")

		# Validate execution policy
		policy = plan.get("execution_policy", {})
		if policy.get("can_execute_real_write") != False:
			issues.append("can_execute_real_write not false")
		if policy.get("requires_next_gate") != True:
			issues.append("requires_next_gate not true")

		# Validate methods/targets
		if "POST" not in policy.get("allowed_methods", []):
			issues.append("POST not in allowed_methods")
		for forbidden in ["PATCH", "DELETE"]:
			if forbidden not in policy.get("forbidden_methods", []):
				issues.append(f"{forbidden} not in forbidden_methods")
		for target in ["/sync", "equipment", "ssh", "netconf"]:
			if target not in policy.get("forbidden_targets", []):
				issues.append(f"{target} not in forbidden_targets")

		# Validate items
		if not plan.get("items"):
			issues.append("items empty")
		if len(plan.get("items", [])) > 3:
			issues.append(f"too many items ({len(plan.get('items', []))} > 3)")

	# Validate validation report
	if not validation_report.exists():
		issues.append("validation report not found")
	else:
		report_text = validation_report.read_text(encoding="utf-8")
		if "CYCLE_DRYRUN_APPLYPLAN_INVALID" in report_text:
			issues.append("validation report shows INVALID")
		elif "CYCLE_DRYRUN_APPLYPLAN_VALID" not in report_text:
			issues.append("validation report does not show VALID")

	# Determine decision
	if issues:
		decision = "CYCLE_DRYRUN_EXECUTION_BLOCKED"
		reason = f"Validation issues: {'; '.join(issues[:3])}"
	else:
		decision = "CYCLE_DRYRUN_EXECUTION_READY"
		reason = "ApplyPlan and validation passed, ready for simulation"

	result = {
		"gate_id": f"dryrun-exec-gate-{cycle_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
		"cycle_id": cycle_id,
		"validated_at": datetime.now(timezone.utc).isoformat(),
		"decision": decision,
		"reason": reason,
		"apply_plan_id": plan.get("apply_plan_id") if plan else None,
		"validation_issues": issues,
	}

	output_json.parent.mkdir(parents=True, exist_ok=True)
	output_json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

	lines = [
		f"# Dry-Run Execution Gate — {cycle_id.upper()}",
		"",
		f"## Decision: {decision}",
		"",
		f"- Reason: {reason}",
		f"- ApplyPlan ID: {result['apply_plan_id'] or 'N/A'}",
		"",
		"## Next Step",
		"Dry-run simulation" if "READY" in decision else "Resolve validation issues",
		"",
		"---",
		f"Validated at {result['validated_at']}",
	]

	output.parent.mkdir(parents=True, exist_ok=True)
	output.write_text("\n".join(lines), encoding="utf-8")

	return result


def main() -> int:
	"""Run FASE 4.82."""
	parser = argparse.ArgumentParser(description="FASE 4.82 — Dry-Run Execution Gate")
	parser.add_argument("--cycle-id", required=True)
	parser.add_argument("--apply-plan", type=Path, required=True)
	parser.add_argument("--validation-report", type=Path, required=True)
	parser.add_argument("--output", type=Path, required=True)
	parser.add_argument("--output-json", type=Path, required=True)

	args = parser.parse_args()
	result = validate_dryrun_execution_gate(
		cycle_id=args.cycle_id,
		apply_plan=args.apply_plan,
		validation_report=args.validation_report,
		output=args.output,
		output_json=args.output_json,
	)

	print(f"✓ Dryrun execution gate: {result.get('decision')}")
	return 0 if "READY" in result.get("decision") else 1


if __name__ == "__main__":
	raise SystemExit(main())
