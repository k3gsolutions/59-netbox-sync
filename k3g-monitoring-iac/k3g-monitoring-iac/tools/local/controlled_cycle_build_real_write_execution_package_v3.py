#!/usr/bin/env python3
"""FASE 4.87 — Build Real Write Execution Package."""

import argparse, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

def load_json(path: Path) -> dict:
	try: return json.loads(path.read_text(encoding="utf-8"))
	except: return {}

def build_exec_package(*, cycle_id: str, authorization_request: Path, apply_plan: Path, output_dir: Path, report: Path) -> dict[str, Any]:
	auth_req = load_json(authorization_request)
	plan = load_json(apply_plan)

	exec_pkg_id = f"EXEC-{cycle_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
	exec_phrase = f"EXECUTAR_ESCRITA_REAL_{cycle_id}_{plan.get('device', 'unknown')}_{exec_pkg_id}"

	items = []
	for item in plan.get("items", []):
		items.append({
			"item_id": item.get("item_id"),
			"approval_id": item.get("approval_id"),
			"object_type": item.get("object_type"),
			"object_key": item.get("object_key"),
			"method": item.get("method"),
			"target_endpoint": item.get("target_endpoint"),
			"proposed_payload": item.get("proposed_payload"),
			"rollback_hint": item.get("rollback_hint"),
			"expected_result": item.get("expected_result"),
		})

	exec_pkg = {
		"execution_package_id": exec_pkg_id,
		"cycle_id": cycle_id,
		"device": plan.get("device"),
		"device_id": plan.get("device_id"),
		"apply_plan_id": plan.get("apply_plan_id"),
		"authorization_id": auth_req.get("authorization_id"),
		"generated_at": datetime.now(timezone.utc).isoformat(),
		"status": "prepared",
		"mode": "real_write_prepared",
		"execution_allowed": False,
		"token_required_in_next_phase": True,
		"explicit_confirm_required": True,
		"one_shot_execution": True,
		"max_items": 3,
		"items": items,
		"safety_confirmations": {
			"no_write_executed": True,
			"no_token_read": True,
			"no_network_call": True,
			"package_only": True,
			"real_write_not_executed": True,
		},
		"required_next_phase": "FASE_4_90_CYCLE003_EXECUTE_REAL_WRITE_ONCE",
		"required_execution_phrase": exec_phrase,
	}

	output_dir.mkdir(parents=True, exist_ok=True)
	pkg_file = output_dir / "execution_package.json"
	pkg_file.write_text(json.dumps(exec_pkg, indent=2, ensure_ascii=False), encoding="utf-8")

	lines = [f"# Real Write Execution Package — {cycle_id.upper()}", "", f"## Package ID: {exec_pkg_id}", f"## Status: prepared", f"## Execution Allowed: false", "", f"- Items: {len(items)}", f"- Mode: real_write_prepared", f"- Required Phrase: {exec_phrase}", "", "---", f"Generated at {exec_pkg['generated_at']}"]
	report.parent.mkdir(parents=True, exist_ok=True)
	report.write_text("\n".join(lines), encoding="utf-8")

	return {"execution_package_id": exec_pkg_id, "cycle_id": cycle_id, "items_count": len(items), "execution_allowed": False}

def main() -> int:
	parser = argparse.ArgumentParser()
	parser.add_argument("--cycle-id", required=True)
	parser.add_argument("--authorization-request", type=Path, required=True)
	parser.add_argument("--apply-plan", type=Path, required=True)
	parser.add_argument("--output-dir", type=Path, required=True)
	parser.add_argument("--report", type=Path, required=True)
	args = parser.parse_args()
	result = build_exec_package(cycle_id=args.cycle_id, authorization_request=args.authorization_request, apply_plan=args.apply_plan, output_dir=args.output_dir, report=args.report)
	print(f"✓ Execution package: {result['execution_package_id']}")
	print(f"✓ Execution allowed: {result['execution_allowed']}")
	return 0

if __name__ == "__main__": raise SystemExit(main())
