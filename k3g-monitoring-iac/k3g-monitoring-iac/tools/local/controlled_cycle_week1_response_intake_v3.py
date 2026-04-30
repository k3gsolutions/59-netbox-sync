#!/usr/bin/env python3
"""FASE 4.73 — Cycle-003 Week 1 Response Intake."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict:
	"""Load JSON safely."""
	try:
		return json.loads(path.read_text(encoding="utf-8"))
	except Exception:
		return {}


def intake_week1_responses(
	*,
	cycle_id: str,
	device: str,
	device_id: str,
	responses_dir: Path,
	output: Path,
	output_json: Path,
) -> dict[str, Any]:
	"""Intake Week 1 responses from teams."""
	responses_dir.mkdir(parents=True, exist_ok=True)

	# Scan responses directory
	response_files = list(responses_dir.glob("*.json")) + list(responses_dir.glob("*.csv"))
	response_count = len(response_files)

	issues = []

	# Check: at least one response
	if response_count == 0:
		issues.append("no responses collected yet")
		decision = "WEEK1_INTAKE_BLOCKED"
		reason = "Responses directory empty"
	elif response_count < 3:
		decision = "WEEK1_INTAKE_PARTIAL"
		reason = f"Partial responses ({response_count} file(s))"
	else:
		decision = "WEEK1_INTAKE_READY"
		reason = f"All responses collected ({response_count} file(s))"

	# Load responses
	responses = []
	for resp_file in sorted(response_files):
		try:
			if resp_file.suffix == ".json":
				data = load_json(resp_file)
				responses.append({
					"file": resp_file.name,
					"size_bytes": resp_file.stat().st_size,
					"type": "json",
					"loaded": True,
					"teams": data.get("teams", []),
				})
			else:
				responses.append({
					"file": resp_file.name,
					"size_bytes": resp_file.stat().st_size,
					"type": "csv",
					"loaded": True,
				})
		except Exception as e:
			responses.append({
				"file": resp_file.name,
				"error": str(e),
				"loaded": False,
			})

	result = {
		"intake_id": f"week1-intake-{cycle_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
		"cycle_id": cycle_id,
		"device": device,
		"device_id": device_id,
		"intake_at": datetime.now(timezone.utc).isoformat(),
		"decision": decision,
		"reason": reason,
		"response_files": response_count,
		"responses": responses,
	}

	output_json.parent.mkdir(parents=True, exist_ok=True)
	output_json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

	# Markdown report
	lines = [
		f"# Week 1 Response Intake — {cycle_id.upper()}",
		"",
		f"## Decision: {decision}",
		"",
		f"- Device: {device} (ID: {device_id})",
		f"- Reason: {reason}",
		f"- Response files: {response_count}",
		"",
	]

	if responses:
		lines.extend([
			"## Responses Received",
			"",
			"| File | Size | Type | Status |",
			"|------|------|------|--------|",
		])
		for resp in responses:
			status = "✓" if resp.get("loaded") else "✗"
			lines.append(f"| {resp['file']} | {resp.get('size_bytes', 0)} bytes | {resp.get('type', 'unknown')} | {status} |")
		lines.append("")

	lines.extend([
		"## Next Step",
		"Week 1 Validation" if decision != "WEEK1_INTAKE_BLOCKED" else "Wait for responses or block intake",
		"",
		"---",
		f"Intake at {datetime.now(timezone.utc).isoformat()}",
	])

	output.parent.mkdir(parents=True, exist_ok=True)
	output.write_text("\n".join(lines), encoding="utf-8")

	return result


def main() -> int:
	"""Run FASE 4.73."""
	parser = argparse.ArgumentParser(description="FASE 4.73 — Week 1 Response Intake")
	parser.add_argument("--cycle-id", required=True)
	parser.add_argument("--device", required=True)
	parser.add_argument("--device-id", required=True)
	parser.add_argument("--responses-dir", type=Path, required=True)
	parser.add_argument("--output", type=Path, required=True)
	parser.add_argument("--output-json", type=Path, required=True)

	args = parser.parse_args()
	result = intake_week1_responses(
		cycle_id=args.cycle_id,
		device=args.device,
		device_id=args.device_id,
		responses_dir=args.responses_dir,
		output=args.output,
		output_json=args.output_json,
	)

	print(f"✓ Week 1 intake: {result.get('decision')}")
	print(f"✓ Report: {args.output}")
	return 0 if result.get("decision") != "WEEK1_INTAKE_BLOCKED" else 1


if __name__ == "__main__":
	raise SystemExit(main())
