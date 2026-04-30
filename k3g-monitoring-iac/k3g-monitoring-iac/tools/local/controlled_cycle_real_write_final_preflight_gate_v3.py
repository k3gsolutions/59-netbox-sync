#!/usr/bin/env python3
"""FASE 4.86 — Real Write Final Preflight Gate."""

import argparse, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

def load_json(path: Path) -> dict:
	try: return json.loads(path.read_text(encoding="utf-8"))
	except: return {}

def final_preflight(*, authorization_request: Path, operator: str, authorization_phrase: str, output: Path, output_json: Path) -> dict[str, Any]:
	auth_req = load_json(authorization_request)

	decision = "CYCLE_NOT_READY_FOR_REAL_WRITE_EXECUTION"
	reason = "Authorization phrase mismatch or validation failed"

	if auth_req and auth_req.get("required_phrase") == authorization_phrase:
		decision = "CYCLE_READY_FOR_REAL_WRITE_EXECUTION_PACKAGE"
		reason = "Authorization phrase validated"

	result = {
		"preflight_id": f"preflight-{auth_req.get('cycle_id', 'unknown')}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
		"cycle_id": auth_req.get("cycle_id"),
		"operator": operator,
		"validated_at": datetime.now(timezone.utc).isoformat(),
		"decision": decision,
		"reason": reason,
	}

	output_json.parent.mkdir(parents=True, exist_ok=True)
	output_json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

	lines = [f"# Real Write Final Preflight Gate", "", f"## Decision: {decision}", "", f"- Operator: {operator}", f"- Reason: {reason}", "", "---", f"Validated at {result['validated_at']}"]
	output.parent.mkdir(parents=True, exist_ok=True)
	output.write_text("\n".join(lines), encoding="utf-8")
	return result

def main() -> int:
	parser = argparse.ArgumentParser()
	parser.add_argument("--authorization-request", type=Path, required=True)
	parser.add_argument("--operator", required=True)
	parser.add_argument("--authorization-phrase", required=True)
	parser.add_argument("--output", type=Path, required=True)
	parser.add_argument("--output-json", type=Path, required=True)
	args = parser.parse_args()
	result = final_preflight(authorization_request=args.authorization_request, operator=args.operator, authorization_phrase=args.authorization_phrase, output=args.output, output_json=args.output_json)
	print(f"✓ Preflight: {result.get('decision')}")
	return 0 if "READY" in result.get("decision") else 1

if __name__ == "__main__": raise SystemExit(main())
