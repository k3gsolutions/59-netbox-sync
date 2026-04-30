#!/usr/bin/env python3
"""FASE 4.88 — Validate Real Write Execution Package."""

import argparse, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

def load_json(path: Path) -> dict:
	try: return json.loads(path.read_text(encoding="utf-8"))
	except: return {}

def validate_exec_package(*, cycle_id: str, execution_package: Path, output: Path, output_json: Path) -> dict[str, Any]:
	pkg = load_json(execution_package)
	issues = []

	if not pkg: issues.append("Package not found")
	else:
		if pkg.get("cycle_id") != cycle_id: issues.append("cycle_id mismatch")
		if pkg.get("status") != "prepared": issues.append("status not prepared")
		if pkg.get("execution_allowed") != False: issues.append("execution_allowed not false")
		if pkg.get("token_required_in_next_phase") != True: issues.append("token_required_in_next_phase not true")
		if not pkg.get("required_execution_phrase"): issues.append("required_execution_phrase missing")
		if not pkg.get("items"): issues.append("items empty")
		if len(pkg.get("items", [])) > 3: issues.append("too many items")

		for item in pkg.get("items", []):
			if item.get("method") != "POST": issues.append(f"item {item.get('item_id')}: method not POST")

	decision = "CYCLE_REAL_WRITE_EXECUTION_PACKAGE_VALID" if not issues else "CYCLE_REAL_WRITE_EXECUTION_PACKAGE_INVALID"
	result = {
		"validation_id": f"exec-pkg-val-{cycle_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
		"cycle_id": cycle_id,
		"validated_at": datetime.now(timezone.utc).isoformat(),
		"decision": decision,
		"reason": "; ".join(issues) if issues else "Execution package valid",
		"execution_package_id": pkg.get("execution_package_id") if pkg else None,
		"items_count": len(pkg.get("items", [])) if pkg else 0,
		"validation_issues": issues,
	}

	output_json.parent.mkdir(parents=True, exist_ok=True)
	output_json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

	lines = [f"# Real Write Execution Package Validation — {cycle_id.upper()}", "", f"## Decision: {decision}", "", f"- Package ID: {result['execution_package_id']}", f"- Items: {result['items_count']}/3", f"- Reason: {result['reason']}", "", "---", f"Validated at {result['validated_at']}"]
	output.parent.mkdir(parents=True, exist_ok=True)
	output.write_text("\n".join(lines), encoding="utf-8")
	return result

def main() -> int:
	parser = argparse.ArgumentParser()
	parser.add_argument("--cycle-id", required=True)
	parser.add_argument("--execution-package", type=Path, required=True)
	parser.add_argument("--output", type=Path, required=True)
	parser.add_argument("--output-json", type=Path, required=True)
	args = parser.parse_args()
	result = validate_exec_package(cycle_id=args.cycle_id, execution_package=args.execution_package, output=args.output, output_json=args.output_json)
	print(f"✓ Package validation: {result.get('decision')}")
	return 0 if "VALID" in result.get("decision") else 1

if __name__ == "__main__": raise SystemExit(main())
