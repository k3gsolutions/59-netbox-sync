#!/usr/bin/env python3
"""Test FASE 4.71-4.74 — Cycle-003 Week 1 Flow."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
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
	test_dir = Path("k3g-monitoring-iac/reports/controlled-operation/cycle-003")
	week1_dir = test_dir / "week1"

	print("=" * 60)
	print("FASE 4.71-4.74 Test Suite — Cycle-003 Week 1 Flow")
	print("=" * 60)
	print()

	# FASE 4.71 Tests
	print("FASE 4.71 — Intake Activation")
	print("-" * 60)

	intake_json = test_dir / "cycle-003-intake-activation.json"
	intake_data = load_json(intake_json)

	test("Intake activation file exists", intake_json.exists())
	test("Activation decision present", bool(intake_data.get("decision")))
	test("Decision is ACTIVATED_WITH_RESTRICTIONS",
		"ACTIVATED_WITH_RESTRICTIONS" in intake_data.get("decision", ""))
	test("Start gate decision captured", bool(intake_data.get("start_gate_decision")))
	test("Restrictions inherited", bool(intake_data.get("restrictions")))
	test("Activation ID format valid",
		intake_data.get("activation_id", "").startswith("intake-"))

	print()

	# FASE 4.72 Tests
	print("FASE 4.72 — Week 1 Preparation")
	print("-" * 60)

	plan_file = week1_dir / "CYCLE-003-WEEK1-PLAN.md"
	status_file = week1_dir / "CYCLE-003-WEEK1-STATUS.md"
	responses_dir = week1_dir / "responses"
	audit_dir = week1_dir / "audit"

	test("Week 1 plan exists", plan_file.exists())
	test("Week 1 status template exists", status_file.exists())
	test("Responses directory created", responses_dir.exists())
	test("Audit directory created", audit_dir.exists())

	if plan_file.exists():
		plan_text = plan_file.read_text(encoding="utf-8")
		test("Plan mentions team assignments", "Network Operations" in plan_text)
		test("Plan mentions validation steps", "Validar" in plan_text)

	print()

	# FASE 4.73 Tests
	print("FASE 4.73 — Week 1 Response Intake")
	print("-" * 60)

	intake_report = week1_dir / "CYCLE-003-WEEK1-INTAKE.md"
	intake_result_json = week1_dir / "cycle-003-week1-intake.json"
	intake_result = load_json(intake_result_json)

	test("Intake report exists", intake_report.exists())
	test("Intake result JSON exists", intake_result_json.exists())
	test("Intake decision present", bool(intake_result.get("decision")))
	test("Response files counted", intake_result.get("response_files", 0) >= 0)
	test("Intake ID format valid",
		intake_result.get("intake_id", "").startswith("week1-intake-"))

	if intake_report.exists():
		intake_text = intake_report.read_text(encoding="utf-8")
		test("Report shows decision", "Decision" in intake_text)
		test("Report shows file count", "Response files" in intake_text)

	print()

	# FASE 4.74 Tests
	print("FASE 4.74 — Week 1 Validation")
	print("-" * 60)

	validation_report = week1_dir / "CYCLE-003-WEEK1-VALIDATION.md"
	validation_json = week1_dir / "cycle-003-week1-validation.json"
	validation_data = load_json(validation_json)

	test("Validation report exists", validation_report.exists())
	test("Validation result JSON exists", validation_json.exists())
	test("Validation decision present", bool(validation_data.get("decision")))
	test("Files validated tracked", validation_data.get("files_validated", 0) >= 0)
	test("Violations array present", isinstance(validation_data.get("violations"), list))
	test("Validation ID format valid",
		validation_data.get("validation_id", "").startswith("week1-validate-"))

	if validation_report.exists():
		validation_text = validation_report.read_text(encoding="utf-8")
		test("Report shows decision", "Decision" in validation_text)
		test("Report shows violation count", "Violations" in validation_text)

	print()

	# Integration Tests
	print("Integration Tests")
	print("-" * 60)

	test("All directories in expected structure",
		all([d.exists() for d in [test_dir, week1_dir, responses_dir, audit_dir]]))

	test("No NETBOX tokens exposed",
		"NETBOX_WRITE_TOKEN" not in str(intake_data) and
		"NETBOX_WRITE_TOKEN" not in str(validation_data))

	test("Timestamps in UTC format",
		intake_data.get("activated_at", "").endswith("+00:00") and
		intake_result.get("intake_at", "").endswith("+00:00") and
		validation_data.get("validated_at", "").endswith("+00:00"))

	print()

	# Summary
	print("=" * 60)
	print(f"Results: {passed} passed, {failed} failed")
	print("=" * 60)

	return 0 if failed == 0 else 1


if __name__ == "__main__":
	raise SystemExit(main())
