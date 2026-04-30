#!/usr/bin/env python3
"""Test FASE 4.75-4.78 — Cycle-003 Week 2 Approval Flow."""

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
	print("FASE 4.75-4.78 Test Suite — Cycle-003 Week 2 Approval Flow")
	print("=" * 60)
	print()

	# FASE 4.75 Tests
	print("FASE 4.75 — Week 2 Preparation")
	print("-" * 60)

	week2_dir = test_dir / "week2"
	plan_file = week2_dir / "CYCLE-003-WEEK2-PLAN.md"
	board_file = week2_dir / "CYCLE-003-WEEK2-REVIEW-BOARD.md"
	decisions_file = week2_dir / "CYCLE-003-WEEK2-DECISIONS.csv"
	status_file = week2_dir / "CYCLE-003-WEEK2-STATUS.md"
	approval_drafts = week2_dir / "approval-drafts"
	audit_dir = week2_dir / "audit"

	test("Week 2 plan exists", plan_file.exists())
	test("Week 2 review board exists", board_file.exists())
	test("Week 2 decisions CSV exists", decisions_file.exists())
	test("Week 2 status exists", status_file.exists())
	test("Approval drafts dir created", approval_drafts.exists())
	test("Audit dir created", audit_dir.exists())

	if plan_file.exists():
		plan_text = plan_file.read_text(encoding="utf-8")
		test("Plan mentions review board", "Review Board" in plan_text)
		test("Plan mentions approval decisions", "approve_for_approval_record" in plan_text)

	print()

	# FASE 4.76 Tests
	print("FASE 4.76 — Week 2 Human Review")
	print("-" * 60)

	review_report = week2_dir / "CYCLE-003-WEEK2-HUMAN-REVIEW.md"
	review_json = week2_dir / "cycle-003-week2-human-review.json"
	review_data = load_json(review_json)

	test("Review report exists", review_report.exists())
	test("Review JSON exists", review_json.exists())
	test("Review decision present", bool(review_data.get("decision")))
	test("Decision is PASSED", "PASSED" in review_data.get("decision", ""))
	test("Reviewed count tracked", review_data.get("decisions_reviewed", 0) > 0)
	test("Approved count tracked", review_data.get("decisions_approved", 0) > 0)

	if review_report.exists():
		review_text = review_report.read_text(encoding="utf-8")
		test("Report shows decision", "Decision" in review_text)
		test("Report shows review counts", "Reviewed" in review_text)

	print()

	# FASE 4.77 Tests
	print("FASE 4.77 — Promote to Proposed ApprovalRecords")
	print("-" * 60)

	approvals_dir = test_dir / "approvals"
	pending_dir = approvals_dir / "pending"
	promotion_report = approvals_dir / "CYCLE-003-PROPOSED-APPROVALS.md"
	promotion_json = approvals_dir / "cycle-003-proposed-approvals.json"
	promotion_data = load_json(promotion_json)

	test("Promotion report exists", promotion_report.exists())
	test("Promotion JSON exists", promotion_json.exists())
	test("Promotion decision present", bool(promotion_data.get("decision")))
	test("Decision is CREATED", "CREATED" in promotion_data.get("decision", ""))
	test("Approvals created count tracked", promotion_data.get("approvals_created", 0) > 0)
	test("Pending dir created", pending_dir.exists())

	# Check proposed ApprovalRecords
	proposed_records = list(pending_dir.glob("AR-*.json"))
	test("Proposed ApprovalRecords exist", len(proposed_records) > 0)

	if len(proposed_records) > 0:
		first_record = load_json(proposed_records[0])
		test("Status is proposed", first_record.get("status") == "proposed")
		test("State is proposed", first_record.get("state") == "proposed")
		test("Safety flags present", bool(first_record.get("safety_flags")))
		test("no_netbox_write flag true", first_record.get("safety_flags", {}).get("no_netbox_write") is True)
		test("manual_review_required flag true", first_record.get("safety_flags", {}).get("manual_review_required") is True)
		test("proposed_only flag true", first_record.get("safety_flags", {}).get("proposed_only") is True)
		test("State history present", bool(first_record.get("state_history")))
		test("promoted_to_proposed event in history",
			any(e.get("event") == "promoted_to_proposed" for e in first_record.get("state_history", [])))

	if promotion_report.exists():
		promotion_text = promotion_report.read_text(encoding="utf-8")
		test("Report shows approvals created", "ApprovalRecords" in promotion_text)

	print()

	# FASE 4.78 Tests
	print("FASE 4.78 — Approval Readiness Gate")
	print("-" * 60)

	readiness_report = approvals_dir / "CYCLE-003-APPROVAL-READINESS-GATE.md"
	readiness_json = approvals_dir / "cycle-003-approval-readiness-gate.json"
	readiness_data = load_json(readiness_json)

	test("Readiness report exists", readiness_report.exists())
	test("Readiness JSON exists", readiness_json.exists())
	test("Readiness decision present", bool(readiness_data.get("decision")))
	test("Decision is READY", "READY" in readiness_data.get("decision", ""))
	test("Approvals count tracked", readiness_data.get("approvals_count", 0) > 0)

	if readiness_report.exists():
		readiness_text = readiness_report.read_text(encoding="utf-8")
		test("Report shows decision", "Decision" in readiness_text)
		test("Report mentions manual approval review", "Manual approval" in readiness_text)

	print()

	# Integration Tests
	print("Integration Tests")
	print("-" * 60)

	test("All Week 2 directories exist",
		all([d.exists() for d in [week2_dir, approval_drafts, audit_dir, approvals_dir, pending_dir]]))

	test("No NETBOX tokens exposed",
		"NETBOX_WRITE_TOKEN" not in str(review_data) and
		"NETBOX_WRITE_TOKEN" not in str(promotion_data) and
		"NETBOX_WRITE_TOKEN" not in str(readiness_data))

	test("No apply/sync/retry keywords",
		"apply_plan" not in str(promotion_data).lower() and
		"/sync" not in str(promotion_data))

	test("All timestamps in UTC",
		review_data.get("reviewed_at", "").endswith("+00:00") and
		promotion_data.get("promoted_at", "").endswith("+00:00") and
		readiness_data.get("validated_at", "").endswith("+00:00"))

	print()

	# Summary
	print("=" * 60)
	print(f"Results: {passed} passed, {failed} failed")
	print("=" * 60)

	return 0 if failed == 0 else 1


if __name__ == "__main__":
	raise SystemExit(main())
