#!/usr/bin/env python3
"""FASE 4.74 — Cycle-003 Week 1 Validation."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict:
	"""Load JSON safely."""
	try:
		return json.loads(path.read_text(encoding="utf-8"))
	except Exception:
		return {}


def validate_interface_name(name: str) -> tuple[bool, str]:
	"""Validate interface naming conventions."""
	patterns = [
		r"^Eth-Trunk\d+$",  # Eth-Trunk0, Eth-Trunk1, etc.
		r"^GigabitEthernet\d+/\d+/\d+$",  # GigabitEthernet0/0/1
		r"^10GE\d+/\d+/\d+$",  # 10GE0/0/1
		r"^LoopBack\d+$",  # LoopBack0, LoopBack1
		r"^NULL\d+$",  # NULL0
		r"^Vlanif\d+$",  # Vlanif100, Vlanif200
		r"^Eth-Trunk\d+\.\d+$",  # Eth-Trunk0.1, sub-interface
		r"^GigabitEthernet\d+/\d+/\d+\.\d+$",  # GigabitEthernet0/0/1.1
	]
	for pattern in patterns:
		if re.match(pattern, name):
			return True, f"Interface '{name}' valid"
	return False, f"Interface '{name}' does not match naming conventions"


def validate_vrf_name(name: str) -> tuple[bool, str]:
	"""Validate VRF naming."""
	if re.match(r"^[A-Za-z0-9_\-]{1,32}$", name):
		return True, f"VRF '{name}' valid"
	return False, f"VRF '{name}' invalid"


def validate_bgp_asn(asn: str | int) -> tuple[bool, str]:
	"""Validate BGP AS number."""
	try:
		asn_int = int(asn)
		if 1 <= asn_int <= 4294967295:
			return True, f"ASN {asn} valid"
		return False, f"ASN {asn} out of range (1-4294967295)"
	except ValueError:
		return False, f"ASN {asn} not numeric"


def validate_route_policy_name(name: str) -> tuple[bool, str]:
	"""Validate route-policy naming."""
	pattern = r"^AS\d+-[A-Z0-9]+-[A-Z0-9]+-\w+-IPv[46]-(Import|Export)$"
	if re.match(pattern, name):
		return True, f"Route-policy '{name}' valid"
	return False, f"Route-policy '{name}' does not match AS*-*-*-*-IPv4/6-(Import|Export)"


def validate_response_payload(payload: dict) -> list[dict[str, Any]]:
	"""Validate response payload structure."""
	violations = []

	# Check teams
	teams = payload.get("teams", [])
	if not isinstance(teams, list):
		violations.append({
			"rule": "PAYLOAD-001",
			"severity": "error",
			"message": "teams field must be array",
		})
		return violations

	for team_idx, team in enumerate(teams):
		team_name = team.get("name", f"team_{team_idx}")

		# Check team name
		if not team.get("name"):
			violations.append({
				"rule": "PAYLOAD-002",
				"severity": "warning",
				"message": f"Team {team_idx}: name missing",
			})

		# Check team elements
		elements = team.get("elements", [])
		if not isinstance(elements, list):
			violations.append({
				"rule": "PAYLOAD-003",
				"severity": "error",
				"message": f"Team {team_name}: elements must be array",
			})
			continue

		for elem_idx, elem in enumerate(elements):
			elem_type = elem.get("type", "unknown")

			# Interface validation
			if elem_type == "interface":
				iface_name = elem.get("name")
				if iface_name:
					valid, msg = validate_interface_name(iface_name)
					if not valid:
						violations.append({
							"rule": "IFACE-001",
							"severity": "warning",
							"message": f"{team_name}[{elem_idx}]: {msg}",
						})

			# VRF validation
			elif elem_type == "vrf":
				vrf_name = elem.get("name")
				if vrf_name:
					valid, msg = validate_vrf_name(vrf_name)
					if not valid:
						violations.append({
							"rule": "VRF-001",
							"severity": "warning",
							"message": f"{team_name}[{elem_idx}]: {msg}",
						})

			# BGP peer validation
			elif elem_type == "bgp_peer":
				asn = elem.get("remote_asn")
				if asn:
					valid, msg = validate_bgp_asn(asn)
					if not valid:
						violations.append({
							"rule": "BGP-001",
							"severity": "error",
							"message": f"{team_name}[{elem_idx}]: {msg}",
						})

				policy_name = elem.get("import_policy")
				if policy_name:
					valid, msg = validate_route_policy_name(policy_name)
					if not valid:
						violations.append({
							"rule": "RTPOL-001",
							"severity": "warning",
							"message": f"{team_name}[{elem_idx}]: {msg}",
						})

	return violations


def validate_week1_responses(
	*,
	cycle_id: str,
	device: str,
	device_id: str,
	responses_dir: Path,
	output: Path,
	output_json: Path,
) -> dict[str, Any]:
	"""Validate Week 1 responses against Compliance Policy Registry."""
	responses_dir.mkdir(parents=True, exist_ok=True)

	# Scan response files
	response_files = list(responses_dir.glob("*.json"))

	all_violations = []
	validated_count = 0
	error_count = 0

	for resp_file in sorted(response_files):
		payload = load_json(resp_file)
		violations = validate_response_payload(payload)
		all_violations.extend(violations)
		validated_count += 1

	# Count violations by severity
	error_violations = [v for v in all_violations if v.get("severity") == "error"]
	warning_violations = [v for v in all_violations if v.get("severity") == "warning"]

	# Determine decision
	if len(response_files) == 0:
		decision = "WEEK1_VALIDATION_BLOCKED"
		reason = "No responses to validate"
	elif error_violations:
		decision = "WEEK1_VALIDATION_BLOCKED"
		reason = f"{len(error_violations)} validation error(s) found"
	elif warning_violations:
		decision = "WEEK1_VALIDATION_PASSED_WITH_RESTRICTIONS"
		reason = f"Passed with {len(warning_violations)} warning(s)"
	else:
		decision = "WEEK1_VALIDATION_PASSED"
		reason = "All validations passed"

	result = {
		"validation_id": f"week1-validate-{cycle_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
		"cycle_id": cycle_id,
		"device": device,
		"device_id": device_id,
		"validated_at": datetime.now(timezone.utc).isoformat(),
		"decision": decision,
		"reason": reason,
		"files_validated": validated_count,
		"violations_total": len(all_violations),
		"violations_errors": len(error_violations),
		"violations_warnings": len(warning_violations),
		"violations": all_violations,
	}

	output_json.parent.mkdir(parents=True, exist_ok=True)
	output_json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

	# Markdown report
	lines = [
		f"# Week 1 Validation — {cycle_id.upper()}",
		"",
		f"## Decision: {decision}",
		"",
		f"- Device: {device} (ID: {device_id})",
		f"- Reason: {reason}",
		f"- Files validated: {validated_count}",
		f"- Violations: {len(all_violations)} ({len(error_violations)} error, {len(warning_violations)} warning)",
		"",
	]

	if all_violations:
		lines.extend([
			"## Violations",
			"",
			"| Rule | Severity | Message |",
			"|------|----------|---------|",
		])
		for viol in all_violations:
			lines.append(f"| {viol['rule']} | {viol['severity']} | {viol['message']} |")
		lines.append("")

	lines.extend([
		"## Next Step",
		"Proceed to Week 2 Review" if decision != "WEEK1_VALIDATION_BLOCKED" else "Resolve validation errors",
		"",
		"---",
		f"Validated at {datetime.now(timezone.utc).isoformat()}",
	])

	output.parent.mkdir(parents=True, exist_ok=True)
	output.write_text("\n".join(lines), encoding="utf-8")

	return result


def main() -> int:
	"""Run FASE 4.74."""
	parser = argparse.ArgumentParser(description="FASE 4.74 — Week 1 Validation")
	parser.add_argument("--cycle-id", required=True)
	parser.add_argument("--device", required=True)
	parser.add_argument("--device-id", required=True)
	parser.add_argument("--responses-dir", type=Path, required=True)
	parser.add_argument("--output", type=Path, required=True)
	parser.add_argument("--output-json", type=Path, required=True)

	args = parser.parse_args()
	result = validate_week1_responses(
		cycle_id=args.cycle_id,
		device=args.device,
		device_id=args.device_id,
		responses_dir=args.responses_dir,
		output=args.output,
		output_json=args.output_json,
	)

	print(f"✓ Week 1 validation: {result.get('decision')}")
	print(f"✓ Report: {args.output}")
	return 0 if result.get("decision") != "WEEK1_VALIDATION_BLOCKED" else 1


if __name__ == "__main__":
	raise SystemExit(main())
