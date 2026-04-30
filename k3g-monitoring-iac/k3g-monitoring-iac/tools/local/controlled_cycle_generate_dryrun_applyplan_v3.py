#!/usr/bin/env python3
"""FASE 4.80 — Cycle-003 Dry-Run ApplyPlan Generation."""

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


def generate_dryrun_applyplan(
	*,
	cycle_id: str,
	device: str,
	device_id: str,
	approved_dir: Path,
	approval_review: Path,
	output_dir: Path,
	report: Path,
	output_json: Path,
) -> dict[str, Any]:
	"""Generate dry-run ApplyPlan from approved records."""
	approved_dir.mkdir(parents=True, exist_ok=True)
	output_dir.mkdir(parents=True, exist_ok=True)

	# Load approval review
	review = load_json(approval_review)

	# Scan for approved records
	approved_records = list(approved_dir.glob("AR-*.json"))

	issues = []
	items = []

	if len(approved_records) == 0:
		issues.append("no approved ApprovalRecords found")
	else:
		# Load each approved record
		for ar_file in approved_records:
			ar = load_json(ar_file)

			# Validate approved status
			if ar.get("status") != "approved":
				issues.append(f"{ar_file.name}: status not approved")
				continue
			if ar.get("state") != "approved":
				issues.append(f"{ar_file.name}: state not approved")
				continue

			# Build item
			item = {
				"item_id": f"item-{len(items) + 1}",
				"approval_id": ar.get("approval_id"),
				"object_type": ar.get("object_type"),
				"object_key": ar.get("object_key"),
				"action": "create",
				"method": "POST",
				"target_endpoint": "/api/ipam/ip-addresses/",
				"proposed_payload": ar.get("proposed_payload"),
				"expected_result": ar.get("review", {}).get("status"),
				"rollback_hint": f"Delete {ar.get('object_key')} if created",
				"evidence_hash": ar.get("evidence_hash"),
			}
			items.append(item)

	# Determine decision
	if issues:
		decision = "CYCLE_DRYRUN_APPLYPLAN_BLOCKED"
		reason = f"Validation issues: {'; '.join(issues)}"
	elif len(items) == 0:
		decision = "CYCLE_DRYRUN_APPLYPLAN_BLOCKED"
		reason = "No items to generate ApplyPlan"
	elif len(items) > 3:
		decision = "CYCLE_DRYRUN_APPLYPLAN_BLOCKED"
		reason = f"Too many items ({len(items)} > 3)"
	else:
		decision = "CYCLE_DRYRUN_APPLYPLAN_GENERATED"
		reason = f"Generated ApplyPlan with {len(items)} item(s)"

	# Create ApplyPlan
	apply_plan_id = f"APPLYPLAN-{cycle_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
	apply_plan = {
		"apply_plan_id": apply_plan_id,
		"cycle_id": cycle_id,
		"device": device,
		"device_id": device_id,
		"mode": "dry_run",
		"status": "generated",
		"generated_at": datetime.now(timezone.utc).isoformat(),
		"source_approval_records": [ar.get("approval_id") for ar in [load_json(f) for f in approved_records]],
		"items": items,
		"safety_flags": {
			"dry_run_only": True,
			"no_netbox_write": True,
			"no_token_required": True,
			"no_apply_execution": True,
			"manual_execution_gate_required": True,
			"generated_from_approved_records": True,
		},
		"execution_policy": {
			"can_execute_real_write": False,
			"requires_next_gate": True,
			"next_gate": "FASE_4_81_CYCLE003_DRYRUN_VALIDATION",
			"max_items": 3,
			"allowed_methods": ["POST"],
			"forbidden_methods": ["PATCH", "DELETE"],
			"forbidden_targets": ["/sync", "equipment", "ssh", "netconf"],
		},
	}

	# Write ApplyPlan if generated
	if decision == "CYCLE_DRYRUN_APPLYPLAN_GENERATED":
		plan_file = output_dir / f"{apply_plan_id}.json"
		plan_file.write_text(json.dumps(apply_plan, indent=2, ensure_ascii=False), encoding="utf-8")

	result = {
		"generation_id": f"gen-{cycle_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
		"cycle_id": cycle_id,
		"device": device,
		"device_id": device_id,
		"generated_at": datetime.now(timezone.utc).isoformat(),
		"decision": decision,
		"reason": reason,
		"apply_plan_id": apply_plan_id if decision == "CYCLE_DRYRUN_APPLYPLAN_GENERATED" else None,
		"items_count": len(items),
		"validation_issues": issues,
	}

	output_json.parent.mkdir(parents=True, exist_ok=True)
	output_json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

	# Markdown report
	lines = [
		f"# Dry-Run ApplyPlan Generation — {cycle_id.upper()}",
		"",
		f"## Decision: {decision}",
		"",
		f"- Device: {device} (ID: {device_id})",
		f"- Reason: {reason}",
		f"- Items: {len(items)}/3",
		f"- ApplyPlan ID: {apply_plan_id if decision == 'CYCLE_DRYRUN_APPLYPLAN_GENERATED' else 'N/A'}",
		"",
	]

	if items:
		lines.extend([
			"## Items",
			"",
			"| Item ID | Approval ID | Object Type | Object Key |",
			"|---------|-------------|-------------|------------|",
		])
		for item in items:
			lines.append(f"| {item['item_id']} | {item['approval_id']} | {item['object_type']} | {item['object_key']} |")
		lines.append("")

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
		"Dry-run ApplyPlan validation" if "GENERATED" in decision else "Resolve issues",
		"",
		"---",
		f"Generated at {result['generated_at']}",
	])

	report.parent.mkdir(parents=True, exist_ok=True)
	report.write_text("\n".join(lines), encoding="utf-8")

	return result


def main() -> int:
	"""Run FASE 4.80."""
	parser = argparse.ArgumentParser(description="FASE 4.80 — Dry-Run ApplyPlan Generation")
	parser.add_argument("--cycle-id", required=True)
	parser.add_argument("--device", required=True)
	parser.add_argument("--device-id", required=True)
	parser.add_argument("--approved-dir", type=Path, required=True)
	parser.add_argument("--approval-review", type=Path, required=True)
	parser.add_argument("--output-dir", type=Path, required=True)
	parser.add_argument("--report", type=Path, required=True)
	parser.add_argument("--output-json", type=Path, required=True)

	args = parser.parse_args()
	result = generate_dryrun_applyplan(
		cycle_id=args.cycle_id,
		device=args.device,
		device_id=args.device_id,
		approved_dir=args.approved_dir,
		approval_review=args.approval_review,
		output_dir=args.output_dir,
		report=args.report,
		output_json=args.output_json,
	)

	print(f"✓ ApplyPlan generation: {result.get('decision')}")
	print(f"✓ Items: {result['items_count']}")
	return 0 if "GENERATED" in result.get("decision") else 1


if __name__ == "__main__":
	raise SystemExit(main())
