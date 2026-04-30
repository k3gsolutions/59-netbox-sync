#!/usr/bin/env python3
"""FASE 4.84 — Cycle-003 Real Write Readiness Gate."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

def load_json(path: Path) -> dict:
	try: return json.loads(path.read_text(encoding="utf-8"))
	except: return {}

def validate_real_write_readiness(*, cycle_id: str, apply_plan: Path, simulation_result: Path, approved_dir: Path, output: Path, output_json: Path) -> dict[str, Any]:
	plan = load_json(apply_plan)
	sim = load_json(simulation_result)
	issues = []

	if not plan: issues.append("ApplyPlan not found")
	elif plan.get("cycle_id") != cycle_id: issues.append("cycle_id mismatch")
	elif plan.get("mode") != "dry_run": issues.append("mode not dry_run")
	elif plan.get("execution_policy", {}).get("can_execute_real_write") != False: issues.append("can_execute_real_write not false")

	if not sim: issues.append("simulation result not found")
	elif "PASSED" not in sim.get("status", ""): issues.append("simulation not passed")

	approved_records = list(approved_dir.glob("AR-*.json"))
	if not approved_records: issues.append("no approved records")
	else:
		for ar_file in approved_records:
			ar = load_json(ar_file)
			if ar.get("status") != "approved": issues.append(f"{ar_file.name}: status not approved")

	decision = "CYCLE_READY_FOR_REAL_WRITE_REVIEW" if not issues else "CYCLE_NOT_READY_FOR_REAL_WRITE"
	result = {
		"gate_id": f"rw-readiness-{cycle_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
		"cycle_id": cycle_id,
		"validated_at": datetime.now(timezone.utc).isoformat(),
		"decision": decision,
		"reason": "; ".join(issues) if issues else "Real write readiness confirmed",
		"apply_plan_id": plan.get("apply_plan_id"),
		"validation_issues": issues,
	}

	output_json.parent.mkdir(parents=True, exist_ok=True)
	output_json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

	lines = [f"# Real Write Readiness Gate — {cycle_id.upper()}", "", f"## Decision: {decision}", "", f"- Reason: {result['reason']}", "", "---", f"Validated at {result['validated_at']}"]
	output.parent.mkdir(parents=True, exist_ok=True)
	output.write_text("\n".join(lines), encoding="utf-8")
	return result

def main() -> int:
	parser = argparse.ArgumentParser()
	parser.add_argument("--cycle-id", required=True)
	parser.add_argument("--apply-plan", type=Path, required=True)
	parser.add_argument("--simulation-result", type=Path, required=True)
	parser.add_argument("--approved-dir", type=Path, required=True)
	parser.add_argument("--output", type=Path, required=True)
	parser.add_argument("--output-json", type=Path, required=True)
	args = parser.parse_args()
	result = validate_real_write_readiness(
		cycle_id=args.cycle_id, apply_plan=args.apply_plan, simulation_result=args.simulation_result,
		approved_dir=args.approved_dir, output=args.output, output_json=args.output_json
	)
	print(f"✓ Real write readiness: {result.get('decision')}")
	return 0 if "READY" in result.get("decision") else 1

if __name__ == "__main__": raise SystemExit(main())
