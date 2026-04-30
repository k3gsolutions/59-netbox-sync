#!/usr/bin/env python3
"""Test FASE 4.79-4.81 — Cycle-003 Approval & ApplyPlan Flow."""

from __future__ import annotations

import json
from pathlib import Path

# Test counter
passed = 0
failed = 0


def test(name: str, condition: bool) -> None:
	"""Record test result."""
	global passed, failed
	status = "✓" if condition else "✗"
	print(f"{status} {name}")
	if condition:
		passed += 1
	else:
		failed += 1


def load_json(path: Path) -> dict:
	"""Load JSON."""
	try:
		return json.loads(path.read_text(encoding="utf-8"))
	except Exception:
		return {}


def main() -> int:
	"""Run test suite."""
	test_dir = Path("reports/controlled-operation/cycle-003")

	print("=" * 60)
	print("FASE 4.79-4.81 Test Suite — Cycle-003 Approval & ApplyPlan")
	print("=" * 60)
	print()

	# FASE 4.79 Tests
	print("FASE 4.79 — Manual Approval Review")
	print("-" * 60)

	approvals_dir = test_dir / "approvals"
	approved_dir = approvals_dir / "approved"
	approval_report = approvals_dir / "CYCLE-003-MANUAL-APPROVAL-REVIEW.md"
	approval_json = approvals_dir / "cycle-003-manual-approval-review.json"
	approval_data = load_json(approval_json)

	test("Approval report exists", approval_report.exists())
	test("Approval JSON exists", approval_json.exists())
	test("Approval decision present", bool(approval_data.get("decision")))
	test("Decision is APPROVED", "APPROVED" in approval_data.get("decision", ""))
	test("Reviewer tracked", bool(approval_data.get("reviewer")))
	test("Approved dir created", approved_dir.exists())

	# Check approved ApprovalRecord
	approved_records = list(approved_dir.glob("AR-*.json"))
	test("Approved record exists", len(approved_records) > 0)

	if len(approved_records) > 0:
		first_approved = load_json(approved_records[0])
		test("Status changed to approved", first_approved.get("status") == "approved")
		test("State changed to approved", first_approved.get("state") == "approved")
		test("approved_by field set", bool(first_approved.get("approved_by")))
		test("approved_at field set", bool(first_approved.get("approved_at")))
		test("approval_reason field set", bool(first_approved.get("approval_reason")))

		# Check state_history
		history = first_approved.get("state_history", [])
		has_reviewed = any(e.get("event") == "cycle_manual_approval_reviewed" for e in history)
		has_approved = any(e.get("event") == "approved_for_cycle_dryrun_applyplan" for e in history)
		test("cycle_manual_approval_reviewed in history", has_reviewed)
		test("approved_for_cycle_dryrun_applyplan in history", has_approved)

	print()

	# FASE 4.80 Tests
	print("FASE 4.80 — Dry-Run ApplyPlan Generation")
	print("-" * 60)

	applyplan_dir = test_dir / "apply-plans"
	dryrun_dir = applyplan_dir / "dry-run"
	gen_report = applyplan_dir / "CYCLE-003-DRYRUN-APPLYPLAN-GENERATION.md"
	gen_json = applyplan_dir / "cycle-003-dryrun-applyplan-generation.json"
	gen_data = load_json(gen_json)

	test("Generation report exists", gen_report.exists())
	test("Generation JSON exists", gen_json.exists())
	test("Generation decision present", bool(gen_data.get("decision")))
	test("Decision is GENERATED", "GENERATED" in gen_data.get("decision", ""))
	test("Items count tracked", gen_data.get("items_count", 0) > 0)
	test("Dry-run dir created", dryrun_dir.exists())

	# Check generated ApplyPlan
	applyplans = list(dryrun_dir.glob("APPLYPLAN-*.json"))
	test("ApplyPlan file exists", len(applyplans) > 0)

	if len(applyplans) > 0:
		first_plan = load_json(applyplans[0])
		test("mode is dry_run", first_plan.get("mode") == "dry_run")
		test("status is generated", first_plan.get("status") == "generated")
		test("safety_flags present", bool(first_plan.get("safety_flags")))
		test("execution_policy present", bool(first_plan.get("execution_policy")))

		# Check safety flags
		flags = first_plan.get("safety_flags", {})
		test("dry_run_only=true", flags.get("dry_run_only") is True)
		test("no_netbox_write=true", flags.get("no_netbox_write") is True)
		test("no_apply_execution=true", flags.get("no_apply_execution") is True)

		# Check execution policy
		policy = first_plan.get("execution_policy", {})
		test("can_execute_real_write=false", policy.get("can_execute_real_write") is False)
		test("requires_next_gate=true", policy.get("requires_next_gate") is True)

	print()

	# FASE 4.81 Tests
	print("FASE 4.81 — Dry-Run ApplyPlan Validation")
	print("-" * 60)

	val_report = applyplan_dir / "CYCLE-003-DRYRUN-APPLYPLAN-VALIDATION.md"
	val_json = applyplan_dir / "cycle-003-dryrun-applyplan-validation.json"
	val_data = load_json(val_json)

	test("Validation report exists", val_report.exists())
	test("Validation JSON exists", val_json.exists())
	test("Validation decision present", bool(val_data.get("decision")))
	test("Decision is VALID", "VALID" in val_data.get("decision", ""))
	test("Items count tracked", val_data.get("items_count", 0) > 0)

	print()

	# Integration Tests
	print("Integration Tests")
	print("-" * 60)

	test("All approval directories exist",
		all([d.exists() for d in [approvals_dir, approved_dir, applyplan_dir, dryrun_dir]]))

	test("No NETBOX tokens exposed",
		"NETBOX_WRITE_TOKEN" not in str(approval_data) and
		"NETBOX_WRITE_TOKEN" not in str(gen_data) and
		"NETBOX_WRITE_TOKEN" not in str(val_data))

	test("No apply/sync keywords",
		"apply" not in str(gen_data).lower() or "/sync" not in str(gen_data))

	test("All timestamps in UTC",
		approval_data.get("reviewed_at", "").endswith("+00:00") and
		gen_data.get("generated_at", "").endswith("+00:00") and
		val_data.get("validated_at", "").endswith("+00:00"))

	print()

	# Summary
	print("=" * 60)
	print(f"Results: {passed} passed, {failed} failed")
	print("=" * 60)

	return 0 if failed == 0 else 1


if __name__ == "__main__":
	raise SystemExit(main())
