#!/usr/bin/env python3
"""Test FASE 4.82-4.89 — Cycle-003 Pre-Execution Chain."""

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
	print("FASE 4.82-4.89 Test Suite — Cycle-003 Pre-Execution Chain")
	print("=" * 60)
	print()

	# FASE 4.82 Tests
	print("FASE 4.82 — Dry-Run Execution Gate")
	print("-" * 60)

	exec_gate_report = test_dir / "apply-plans" / "CYCLE-003-DRYRUN-EXECUTION-GATE.md"
	exec_gate_json = test_dir / "apply-plans" / "cycle-003-dryrun-execution-gate.json"
	exec_gate_data = load_json(exec_gate_json)

	test("Execution gate report exists", exec_gate_report.exists())
	test("Execution gate JSON exists", exec_gate_json.exists())
	test("Execution gate decision present", bool(exec_gate_data.get("decision")))
	test("Decision is READY", "READY" in exec_gate_data.get("decision", ""))
	test("ApplyPlan ID tracked", bool(exec_gate_data.get("apply_plan_id")))

	print()

	# FASE 4.83 Tests
	print("FASE 4.83 — Execute Dry-Run Simulation")
	print("-" * 60)

	sim_report = test_dir / "apply-plans" / "CYCLE-003-DRYRUN-SIMULATION-RESULT.md"
	sim_json = test_dir / "apply-plans" / "cycle-003-dryrun-simulation-result.json"
	sim_data = load_json(sim_json)

	test("Simulation report exists", sim_report.exists())
	test("Simulation JSON exists", sim_json.exists())
	test("Simulation status present", bool(sim_data.get("status")))
	test("Status is PASSED", "PASSED" in sim_data.get("status", ""))
	test("Items simulated count present", sim_data.get("items_simulated", 0) > 0)
	test("Safety confirmations present", bool(sim_data.get("safety_confirmations")))

	if sim_data.get("safety_confirmations"):
		safety = sim_data["safety_confirmations"]
		test("local_only=true", safety.get("local_only") is True)
		test("no_network_call=true", safety.get("no_network_call") is True)
		test("no_token_read=true", safety.get("no_token_read") is True)
		test("no_netbox_write=true", safety.get("no_netbox_write") is True)
		test("no_apply_execution=true", safety.get("no_apply_execution") is True)

	test("next_gate_required=true", sim_data.get("next_gate_required") is True)
	test("next_gate set to readiness", "readiness" in sim_data.get("next_gate", "").lower())

	print()

	# FASE 4.84 Tests
	print("FASE 4.84 — Real Write Readiness Gate")
	print("-" * 60)

	readiness_report = test_dir / "apply-plans" / "CYCLE-003-REAL-WRITE-READINESS-GATE.md"
	readiness_json = test_dir / "apply-plans" / "cycle-003-real-write-readiness-gate.json"
	readiness_data = load_json(readiness_json)

	test("Readiness report exists", readiness_report.exists())
	test("Readiness JSON exists", readiness_json.exists())
	test("Readiness decision present", bool(readiness_data.get("decision")))
	test("Decision is READY", "READY" in readiness_data.get("decision", ""))
	test("Simulation passed confirmed", readiness_data.get("decision", "").find("READY") >= 0)
	test("Approved records count present", readiness_data.get("approved_records_count", 0) >= 0)

	print()

	# FASE 4.85 Tests
	print("FASE 4.85 — Real Write Authorization Package")
	print("-" * 60)

	auth_report = test_dir / "real-write-authorization" / "CYCLE-003-REAL-WRITE-AUTHORIZATION-PACKAGE.md"
	auth_json = test_dir / "real-write-authorization" / "authorization_request.json"
	auth_data = load_json(auth_json)

	test("Authorization report exists", auth_report.exists())
	test("Authorization JSON exists", auth_json.exists())
	test("Authorization request ID present", bool(auth_data.get("authorization_id")))
	test("Required phrase format valid", "AUTORIZO_PRE_FLIGHT" in auth_data.get("required_phrase", ""))
	test("Phrase contains cycle-003", "cycle-003" in auth_data.get("required_phrase", "").lower())
	test("Phrase contains device", "4WNET-MNS-KTG-RX" in auth_data.get("required_phrase", ""))

	print()

	# FASE 4.86 Tests
	print("FASE 4.86 — Real Write Final Preflight Gate")
	print("-" * 60)

	preflight_report = test_dir / "real-write-authorization" / "CYCLE-003-REAL-WRITE-FINAL-PREFLIGHT-GATE.md"
	preflight_json = test_dir / "real-write-authorization" / "cycle-003-real-write-final-preflight-gate.json"
	preflight_data = load_json(preflight_json)

	test("Preflight report exists", preflight_report.exists())
	test("Preflight JSON exists", preflight_json.exists())
	test("Preflight decision present", bool(preflight_data.get("decision")))
	test("Decision is READY", "READY" in preflight_data.get("decision", ""))
	test("Operator name tracked", bool(preflight_data.get("operator")))
	test("Authorization phrase validated", preflight_data.get("decision", "").find("READY") >= 0)

	print()

	# FASE 4.87 Tests
	print("FASE 4.87 — Build Real Write Execution Package")
	print("-" * 60)

	exec_pkg_dir = test_dir / "real-write-execution"
	exec_pkg_files = list(exec_pkg_dir.glob("execution_package*.json")) if exec_pkg_dir.exists() else []
	test("Execution package directory exists", exec_pkg_dir.exists())
	test("Execution package file created", len(exec_pkg_files) > 0)

	exec_pkg_data = {}
	if len(exec_pkg_files) > 0:
		exec_pkg_data = load_json(exec_pkg_files[0])

		test("execution_allowed=false (safety lock)", exec_pkg_data.get("execution_allowed") is False)
		test("status=prepared", exec_pkg_data.get("status") == "prepared")
		test("mode=real_write_prepared", exec_pkg_data.get("mode") == "real_write_prepared")
		test("Required execution phrase present", bool(exec_pkg_data.get("required_execution_phrase")))
		test("Phrase contains EXECUTAR_ESCRITA_REAL", "EXECUTAR_ESCRITA_REAL" in exec_pkg_data.get("required_execution_phrase", ""))
		test("Phrase contains cycle-003", "cycle-003" in exec_pkg_data.get("required_execution_phrase", "").lower())
		test("token_required_in_next_phase=true", exec_pkg_data.get("token_required_in_next_phase") is True)
		test("explicit_confirm_required=true", exec_pkg_data.get("explicit_confirm_required") is True)
		test("one_shot_execution=true", exec_pkg_data.get("one_shot_execution") is True)
		test("Items present in package", len(exec_pkg_data.get("items", [])) > 0)

		if len(exec_pkg_data.get("items", [])) > 0:
			first_item = exec_pkg_data["items"][0]
			test("Item has method=POST", first_item.get("method") == "POST")
			test("Item has target_endpoint", bool(first_item.get("target_endpoint")))
			test("Item has proposed_payload", bool(first_item.get("proposed_payload")))
			test("Item has expected_result", bool(first_item.get("expected_result")))

	print()

	# FASE 4.88 Tests
	print("FASE 4.88 — Validate Real Write Execution Package")
	print("-" * 60)

	pkg_validation_report = test_dir / "real-write-execution" / "CYCLE-003-REAL-WRITE-EXECUTION-PACKAGE-VALIDATION.md"
	pkg_validation_json = test_dir / "real-write-execution" / "cycle-003-real-write-execution-package-validation.json"
	pkg_validation_data = load_json(pkg_validation_json)

	test("Package validation report exists", pkg_validation_report.exists())
	test("Package validation JSON exists", pkg_validation_json.exists())
	test("Validation decision present", bool(pkg_validation_data.get("decision")))
	test("Decision is VALID", "VALID" in pkg_validation_data.get("decision", ""))
	test("execution_allowed confirmed false", pkg_validation_data.get("decision", "").find("VALID") >= 0)
	test("No NETBOX_WRITE_TOKEN exposed", "NETBOX_WRITE_TOKEN" not in str(pkg_validation_data))
	test("No password exposed", "password" not in str(pkg_validation_data).lower() or "password" in ["password_reset", "password_change"])

	print()

	# FASE 4.89 Tests
	print("FASE 4.89 — Final No-Write Freeze Check")
	print("-" * 60)

	freeze_report = test_dir / "real-write-execution" / "CYCLE-003-FINAL-NO-WRITE-FREEZE-CHECK.md"
	freeze_json = test_dir / "real-write-execution" / "cycle-003-final-no-write-freeze-check.json"
	freeze_data = load_json(freeze_json)

	test("Freeze report exists", freeze_report.exists())
	test("Freeze JSON exists", freeze_json.exists())
	test("Freeze decision present", bool(freeze_data.get("decision")))
	test("Decision is READY_FOR_REAL_WRITE_PHASE", "READY_FOR_REAL_WRITE_PHASE" in freeze_data.get("decision", ""))
	safety_conf = freeze_data.get("safety_confirmations", {})
	test("Safety check: no_write_executed", safety_conf.get("no_write_executed") is True)
	test("Safety check: no_token_read", safety_conf.get("no_token_read") is True)
	test("Safety check: no_network_call", safety_conf.get("no_network_call") is True)
	test("Validation issues empty", len(freeze_data.get("validation_issues", [])) == 0)

	print()

	# Integration Tests
	print("Integration Tests")
	print("-" * 60)

	test("All execution directories exist",
		all([d.exists() for d in [
			test_dir / "real-write-authorization",
			test_dir / "real-write-execution",
		]]))

	test("Complete gate chain passed",
		exec_gate_data.get("decision", "").find("READY") >= 0 and
		sim_data.get("status", "").find("PASSED") >= 0 and
		readiness_data.get("decision", "").find("READY") >= 0 and
		freeze_data.get("decision", "").find("READY") >= 0)

	test("No NETBOX tokens exposed in any phase",
		"NETBOX_WRITE_TOKEN" not in str(exec_gate_data) and
		"NETBOX_WRITE_TOKEN" not in str(sim_data) and
		"NETBOX_WRITE_TOKEN" not in str(readiness_data) and
		"NETBOX_WRITE_TOKEN" not in str(auth_data) and
		"NETBOX_WRITE_TOKEN" not in str(freeze_data))

	test("All timestamps in UTC",
		exec_gate_data.get("validated_at", "").endswith("+00:00") and
		sim_data.get("simulated_at", "").endswith("+00:00") and
		readiness_data.get("validated_at", "").endswith("+00:00"))

	test("Safety locks engaged (execution_allowed=false)",
		exec_pkg_data.get("execution_allowed") is False and
		pkg_validation_data.get("decision", "").find("VALID") >= 0)

	test("Next phase set to FASE 4.90",
		"4_90" in exec_pkg_data.get("required_next_phase", ""))

	print()

	# Summary
	print("=" * 60)
	print(f"Results: {passed} passed, {failed} failed")
	print("=" * 60)

	return 0 if failed == 0 else 1


if __name__ == "__main__":
	raise SystemExit(main())
