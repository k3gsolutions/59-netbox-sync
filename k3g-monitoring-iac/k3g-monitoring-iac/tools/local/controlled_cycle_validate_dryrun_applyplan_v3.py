#!/usr/bin/env python3
"""FASE 4.81 — Cycle-003 Dry-Run ApplyPlan Validation."""

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
		"password",
		"secret",
		"api_key",
		"private_key",
		"bearer",
		"authorization",
	]
	# Fields to exclude from scanning
	excluded_fields = {"no_token_required", "token_required"}

	found = []
	text_lower = text.lower()

	# Replace excluded field names with placeholder before checking
	for field in excluded_fields:
		text_lower = text_lower.replace(field.lower(), "_excluded_")

	for keyword in forbidden:
		if keyword.lower() in text_lower:
			found.append(keyword)
	return list(set(found))


def validate_dryrun_applyplan(
	*,
	cycle_id: str,
	apply_plan: Path,
	device: str,
	device_id: str,
	output: Path,
	output_json: Path,
) -> dict[str, Any]:
	"""Validate dry-run ApplyPlan."""
	# Load ApplyPlan
	plan = load_json(apply_plan)

	issues = []

	# Validate basic structure
	if not plan:
		issues.append("ApplyPlan not found or unreadable")
	else:
		# Validate cycle_id
		if plan.get("cycle_id") != cycle_id:
			issues.append(f"cycle_id mismatch: {plan.get('cycle_id')} != {cycle_id}")

		# Validate device
		if plan.get("device") != device:
			issues.append(f"device mismatch: {plan.get('device')} != {device}")
		if plan.get("device_id") != device_id:
			issues.append(f"device_id mismatch: {plan.get('device_id')} != {device_id}")

		# Validate mode and status
		if plan.get("mode") != "dry_run":
			issues.append(f"mode not dry_run: {plan.get('mode')}")
		if plan.get("status") != "generated":
			issues.append(f"status not generated: {plan.get('status')}")

		# Validate items
		if not plan.get("items"):
			issues.append("items empty or missing")

		# Validate item count
		items_count = len(plan.get("items", []))
		if items_count > 3:
			issues.append(f"too many items ({items_count} > 3)")

		# Validate each item
		for idx, item in enumerate(plan.get("items", [])):
			if not item.get("approval_id"):
				issues.append(f"item {idx}: approval_id missing")
			if not item.get("object_type"):
				issues.append(f"item {idx}: object_type missing")
			if not item.get("object_key"):
				issues.append(f"item {idx}: object_key missing")
			if not item.get("proposed_payload"):
				issues.append(f"item {idx}: proposed_payload missing")
			if not item.get("evidence_hash"):
				issues.append(f"item {idx}: evidence_hash missing")
			if not item.get("expected_result"):
				issues.append(f"item {idx}: expected_result missing")
			if not item.get("rollback_hint"):
				issues.append(f"item {idx}: rollback_hint missing")

		# Validate safety flags
		safety_flags = plan.get("safety_flags", {})
		required_flags = {
			"dry_run_only": True,
			"no_netbox_write": True,
			"no_token_required": True,
			"no_apply_execution": True,
			"manual_execution_gate_required": True,
			"generated_from_approved_records": True,
		}
		for flag, expected_value in required_flags.items():
			if safety_flags.get(flag) != expected_value:
				issues.append(f"safety_flag {flag} not {expected_value}")

		# Validate execution policy
		exec_policy = plan.get("execution_policy", {})
		if exec_policy.get("can_execute_real_write") != False:
			issues.append("can_execute_real_write not false")
		if exec_policy.get("requires_next_gate") != True:
			issues.append("requires_next_gate not true")
		if exec_policy.get("max_items") != 3:
			issues.append(f"max_items not 3: {exec_policy.get('max_items')}")

		# Validate allowed/forbidden methods
		allowed_methods = exec_policy.get("allowed_methods", [])
		if "POST" not in allowed_methods:
			issues.append("POST not in allowed_methods")
		forbidden_methods = exec_policy.get("forbidden_methods", [])
		if "PATCH" not in forbidden_methods or "DELETE" not in forbidden_methods:
			issues.append("PATCH or DELETE not in forbidden_methods")

		# Validate forbidden targets
		forbidden_targets = exec_policy.get("forbidden_targets", [])
		required_targets = ["/sync", "equipment", "ssh", "netconf"]
		for target in required_targets:
			if target not in forbidden_targets:
				issues.append(f"target {target} not in forbidden_targets")

		# Scan for secrets
		plan_text = json.dumps(plan, ensure_ascii=False)
		secrets = scan_for_secrets(plan_text)
		if secrets:
			issues.append(f"secrets found: {', '.join(secrets)}")

	# Determine decision
	if not plan:
		decision = "CYCLE_DRYRUN_APPLYPLAN_INVALID"
		reason = "ApplyPlan not found"
	elif issues:
		decision = "CYCLE_DRYRUN_APPLYPLAN_INVALID"
		reason = f"Validation issues found"
	else:
		decision = "CYCLE_DRYRUN_APPLYPLAN_VALID"
		reason = "ApplyPlan valid for dry-run simulation"

	result = {
		"validation_id": f"validate-{cycle_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
		"cycle_id": cycle_id,
		"device": device,
		"device_id": device_id,
		"validated_at": datetime.now(timezone.utc).isoformat(),
		"decision": decision,
		"reason": reason,
		"apply_plan_id": plan.get("apply_plan_id") if plan else None,
		"items_count": len(plan.get("items", [])) if plan else 0,
		"validation_issues": issues,
	}

	output_json.parent.mkdir(parents=True, exist_ok=True)
	output_json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

	# Markdown report
	lines = [
		f"# Dry-Run ApplyPlan Validation — {cycle_id.upper()}",
		"",
		f"## Decision: {decision}",
		"",
		f"- Device: {device} (ID: {device_id})",
		f"- Reason: {reason}",
		f"- Items: {result['items_count']}/3",
		f"- ApplyPlan ID: {result['apply_plan_id'] or 'N/A'}",
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
		"Dry-run execution gate" if "VALID" in decision else "Resolve validation issues",
		"",
		"---",
		f"Validated at {result['validated_at']}",
	])

	output.parent.mkdir(parents=True, exist_ok=True)
	output.write_text("\n".join(lines), encoding="utf-8")

	return result


def main() -> int:
	"""Run FASE 4.81."""
	parser = argparse.ArgumentParser(description="FASE 4.81 — Dry-Run ApplyPlan Validation")
	parser.add_argument("--cycle-id", required=True)
	parser.add_argument("--apply-plan", type=Path, required=True)
	parser.add_argument("--device", required=True)
	parser.add_argument("--device-id", required=True)
	parser.add_argument("--output", type=Path, required=True)
	parser.add_argument("--output-json", type=Path, required=True)

	args = parser.parse_args()
	result = validate_dryrun_applyplan(
		cycle_id=args.cycle_id,
		apply_plan=args.apply_plan,
		device=args.device,
		device_id=args.device_id,
		output=args.output,
		output_json=args.output_json,
	)

	print(f"✓ ApplyPlan validation: {result.get('decision')}")
	print(f"✓ Report: {args.output}")
	return 0 if "VALID" in result.get("decision") else 1


if __name__ == "__main__":
	raise SystemExit(main())
