#!/usr/bin/env python3
"""FASE 4.89 — Final No-Write Freeze Check."""

import argparse, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

def load_json(path: Path) -> dict:
	try: return json.loads(path.read_text(encoding="utf-8"))
	except: return {}

def final_freeze_check(*, cycle_id: str, execution_package: Path, package_validation: Path, output: Path, output_json: Path) -> dict[str, Any]:
	pkg = load_json(execution_package)
	val = load_json(package_validation)
	issues = []

	# Validate package validation passed
	val_text = package_validation.read_text(encoding="utf-8") if package_validation.exists() else ""
	if "INVALID" in val_text: issues.append("package validation invalid")
	elif "VALID" not in val_text: issues.append("package validation not passed")

	# Validate package
	if not pkg: issues.append("execution package not found")
	else:
		if pkg.get("execution_allowed") != False: issues.append("execution_allowed not false")
		if not pkg.get("required_execution_phrase"): issues.append("required_execution_phrase missing")

		# Check for secrets
		pkg_text = json.dumps(pkg, ensure_ascii=False)
		forbidden = ["NETBOX_WRITE_TOKEN", "token", "password", "secret"]
		for word in forbidden:
			if word.lower() in pkg_text.lower() and "no_token" not in pkg_text.lower()[pkg_text.lower().find(word.lower()):]:
				issues.append(f"potential secret: {word}")

	decision = "CYCLE_READY_FOR_REAL_WRITE_PHASE" if not issues else "CYCLE_NOT_READY_FOR_REAL_WRITE_PHASE"
	result = {
		"freeze_id": f"freeze-{cycle_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
		"cycle_id": cycle_id,
		"checked_at": datetime.now(timezone.utc).isoformat(),
		"decision": decision,
		"reason": "; ".join(issues) if issues else "Final freeze check passed - no write possible",
		"execution_package_id": pkg.get("execution_package_id") if pkg else None,
		"safety_confirmations": {
			"no_write_executed": True,
			"no_token_read": True,
			"no_network_call": True,
		},
		"validation_issues": issues,
	}

	output_json.parent.mkdir(parents=True, exist_ok=True)
	output_json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

	lines = [f"# Final No-Write Freeze Check — {cycle_id.upper()}", "", f"## Decision: {decision}", "", f"- Package ID: {result['execution_package_id']}", f"- Reason: {result['reason']}", "", "## Safety Confirmations", "- no_write_executed: ✓", "- no_token_read: ✓", "- no_network_call: ✓", "", "---", f"Checked at {result['checked_at']}"]
	output.parent.mkdir(parents=True, exist_ok=True)
	output.write_text("\n".join(lines), encoding="utf-8")
	return result

def main() -> int:
	parser = argparse.ArgumentParser()
	parser.add_argument("--cycle-id", required=True)
	parser.add_argument("--execution-package", type=Path, required=True)
	parser.add_argument("--package-validation", type=Path, required=True)
	parser.add_argument("--output", type=Path, required=True)
	parser.add_argument("--output-json", type=Path, required=True)
	args = parser.parse_args()
	result = final_freeze_check(cycle_id=args.cycle_id, execution_package=args.execution_package, package_validation=args.package_validation, output=args.output, output_json=args.output_json)
	print(f"✓ Final freeze: {result.get('decision')}")
	return 0 if "READY" in result.get("decision") else 1

if __name__ == "__main__": raise SystemExit(main())
