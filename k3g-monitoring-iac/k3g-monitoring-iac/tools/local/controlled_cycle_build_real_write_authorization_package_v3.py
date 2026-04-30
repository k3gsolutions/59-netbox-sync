#!/usr/bin/env python3
"""FASE 4.85 — Real Write Authorization Package."""

import argparse, json, hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

def load_json(path: Path) -> dict:
	try: return json.loads(path.read_text(encoding="utf-8"))
	except: return {}

def build_auth_package(*, cycle_id: str, device: str, device_id: str, apply_plan: Path, output_dir: Path, report: Path) -> dict[str, Any]:
	plan = load_json(apply_plan)
	plan_id = plan.get("apply_plan_id", "unknown")
	auth_phrase = f"AUTORIZO_PRE_FLIGHT_ESCRITA_REAL_{cycle_id}_{device}_{plan_id}"

	auth_req = {
		"authorization_id": f"AUTH-{cycle_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
		"cycle_id": cycle_id,
		"device": device,
		"device_id": device_id,
		"apply_plan_id": plan_id,
		"required_phrase": auth_phrase,
		"generated_at": datetime.now(timezone.utc).isoformat(),
	}

	output_dir.mkdir(parents=True, exist_ok=True)
	auth_file = output_dir / "authorization_request.json"
	auth_file.write_text(json.dumps(auth_req, indent=2, ensure_ascii=False), encoding="utf-8")

	lines = [f"# Real Write Authorization Package — {cycle_id.upper()}", "", "## Authorization Request Generated", "", f"- Authorization ID: {auth_req['authorization_id']}", f"- Device: {device}", f"- Required Phrase: {auth_phrase}", "", "---", f"Generated at {auth_req['generated_at']}"]
	report.parent.mkdir(parents=True, exist_ok=True)
	report.write_text("\n".join(lines), encoding="utf-8")

	return {"authorization_id": auth_req["authorization_id"], "cycle_id": cycle_id, "device": device, "required_phrase": auth_phrase}

def main() -> int:
	parser = argparse.ArgumentParser()
	parser.add_argument("--cycle-id", required=True)
	parser.add_argument("--device", required=True)
	parser.add_argument("--device-id", required=True)
	parser.add_argument("--apply-plan", type=Path, required=True)
	parser.add_argument("--output-dir", type=Path, required=True)
	parser.add_argument("--report", type=Path, required=True)
	args = parser.parse_args()
	result = build_auth_package(cycle_id=args.cycle_id, device=args.device, device_id=args.device_id, apply_plan=args.apply_plan, output_dir=args.output_dir, report=args.report)
	print(f"✓ Authorization package: {result['authorization_id']}")
	return 0

if __name__ == "__main__": raise SystemExit(main())
