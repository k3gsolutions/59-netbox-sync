"""Huawei NE8000 local parser baseline.

Local only. No NetBox. No SSH/SNMP/NETCONF. No writes outside reports/.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .compliance_jobs import JOBS_BASE, load_compliance_job


PARSER_NAME = "huawei-ne8000-baseline"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dump_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _safe_job_dir(job_id: str, jobs_base: Optional[Path] = None) -> Path:
    return (jobs_base or JOBS_BASE) / job_id


def _reports_root() -> Path:
    return JOBS_BASE.parents[1]


def _report_path(path: Path) -> str:
    try:
        return str(path.relative_to(_reports_root()))
    except Exception:
        return str(path)


def _lines(text: str) -> list[str]:
    return [line.rstrip() for line in (text or "").splitlines()]


def _compact_nonempty(lines: list[str]) -> list[str]:
    return [line.strip() for line in lines if line and line.strip()]


def _strip_command_prefix(command_name: str) -> str:
    return (command_name or "").strip().lower()


def _split_key_value(line: str) -> tuple[str, str] | None:
    if ":" in line:
        left, right = line.split(":", 1)
        return left.strip(), right.strip()
    if "=" in line:
        left, right = line.split("=", 1)
        return left.strip(), right.strip()
    return None


def parse_display_version(text: str) -> dict[str, Any]:
    lines = _lines(text)
    result: dict[str, Any] = {
        "raw_line_count": len(_compact_nonempty(lines)),
        "lines": _compact_nonempty(lines),
        "version": None,
        "system_name": None,
        "platform": None,
        "hardware": None,
        "uptime": None,
        "serial_number": None,
    }
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        lowered = stripped.lower()
        if result["version"] is None:
            match = re.search(r"\bversion\s+([A-Za-z0-9._-]+(?:\s+[A-Za-z0-9._-]+)*)", stripped, re.I)
            if match:
                result["version"] = match.group(1).strip()
        if result["system_name"] is None:
            match = re.search(r"(?:sysname|system name)\s*[:=]\s*(.+)$", stripped, re.I)
            if match:
                result["system_name"] = match.group(1).strip()
        if result["platform"] is None:
            match = re.search(r"\b(NE8000[\w.-]*)\b", stripped, re.I)
            if match:
                result["platform"] = match.group(1).strip()
        if result["hardware"] is None and any(token in lowered for token in ("board", "hardware", "chassis", "device type")):
            result["hardware"] = stripped
        if result["uptime"] is None and "uptime" in lowered:
            result["uptime"] = stripped
        if result["serial_number"] is None:
            match = re.search(r"(?:serial number|sn)\s*[:=]\s*(.+)$", stripped, re.I)
            if match:
                result["serial_number"] = match.group(1).strip()
    return result


def parse_display_device(text: str) -> dict[str, Any]:
    lines = _lines(text)
    components: list[dict[str, Any]] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.lower().startswith(("slot", "board", "card", "device")):
            parts = re.split(r"\s{2,}|\t+", stripped)
            components.append(
                {
                    "line": stripped,
                    "parts": parts,
                }
            )
    return {
        "raw_line_count": len(_compact_nonempty(lines)),
        "lines": _compact_nonempty(lines),
        "components": components,
    }


def _parse_brief_rows(text: str, expected_columns: int = 4) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in _lines(text):
        stripped = line.strip()
        if not stripped:
            continue
        lowered = stripped.lower()
        if lowered.startswith(("interface", "ifname", "phy", "protocol", "---")):
            continue
        parts = re.split(r"\s{2,}|\t+", stripped)
        if len(parts) < expected_columns:
            parts = re.split(r"\s+", stripped)
        if len(parts) < expected_columns:
            continue
        rows.append({"columns": parts, "line": stripped})
    return rows


def parse_display_interface_brief(text: str) -> dict[str, Any]:
    rows = _parse_brief_rows(text, expected_columns=3)
    interfaces: list[dict[str, Any]] = []
    for row in rows:
        columns = row["columns"]
        interfaces.append(
            {
                "name": columns[0],
                "physical": columns[1] if len(columns) > 1 else None,
                "protocol": columns[2] if len(columns) > 2 else None,
                "description": " ".join(columns[3:]).strip() if len(columns) > 3 else None,
                "line": row["line"],
            }
        )
    return {"interfaces": interfaces, "raw_line_count": len(_compact_nonempty(_lines(text)))}


def parse_display_ip_interface_brief(text: str) -> dict[str, Any]:
    rows = _parse_brief_rows(text, expected_columns=4)
    interfaces: list[dict[str, Any]] = []
    for row in rows:
        columns = row["columns"]
        interfaces.append(
            {
                "name": columns[0],
                "ip_address": columns[1] if len(columns) > 1 else None,
                "physical": columns[2] if len(columns) > 2 else None,
                "protocol": columns[3] if len(columns) > 3 else None,
                "description": " ".join(columns[4:]).strip() if len(columns) > 4 else None,
                "line": row["line"],
            }
        )
    return {"ipv4_interfaces": interfaces, "raw_line_count": len(_compact_nonempty(_lines(text)))}


def parse_display_ipv6_interface_brief(text: str) -> dict[str, Any]:
    rows = _parse_brief_rows(text, expected_columns=4)
    interfaces: list[dict[str, Any]] = []
    for row in rows:
        columns = row["columns"]
        interfaces.append(
            {
                "name": columns[0],
                "ipv6_address": columns[1] if len(columns) > 1 else None,
                "physical": columns[2] if len(columns) > 2 else None,
                "protocol": columns[3] if len(columns) > 3 else None,
                "description": " ".join(columns[4:]).strip() if len(columns) > 4 else None,
                "line": row["line"],
            }
        )
    return {"ipv6_interfaces": interfaces, "raw_line_count": len(_compact_nonempty(_lines(text)))}


def parse_display_bgp_peer(text: str) -> dict[str, Any]:
    peers: list[dict[str, Any]] = []
    for line in _lines(text):
        stripped = line.strip()
        if not stripped:
            continue
        lowered = stripped.lower()
        if lowered.startswith(("peer", "bgp", "---", "address", "neighbor")):
            continue
        parts = re.split(r"\s+", stripped)
        if len(parts) < 2:
            continue
        if not re.match(r"^\d{1,3}(?:\.\d{1,3}){3}$", parts[0]) and not re.match(r"^[A-Fa-f0-9:.]+$", parts[0]):
            continue
        peers.append(
            {
                "peer_ip": parts[0],
                "asn": parts[1] if len(parts) > 1 else None,
                "state": " ".join(parts[2:]).strip() if len(parts) > 2 else None,
                "line": stripped,
            }
        )
    return {"bgp_peers": peers, "raw_line_count": len(_compact_nonempty(_lines(text)))}


def parse_display_route_policy(text: str) -> dict[str, Any]:
    route_policies: dict[str, dict[str, Any]] = {}
    current_name: str | None = None
    current_node: dict[str, Any] | None = None
    for line in _lines(text):
        stripped = line.strip()
        if not stripped:
            continue
        start = re.match(r"^route-policy\s+(\S+)\s+(permit|deny)\s+node\s+(\d+)", stripped, re.I)
        if start:
            current_name = start.group(1)
            current_node = {
                "node": int(start.group(3)),
                "action": start.group(2).lower(),
                "statements": [],
                "line": stripped,
            }
            route_policies.setdefault(current_name, {"name": current_name, "nodes": []})["nodes"].append(current_node)
            continue
        if current_node and re.match(r"^(if-match|apply|description)\b", stripped, re.I):
            current_node["statements"].append(stripped)
    return {"route_policies": route_policies, "raw_line_count": len(_compact_nonempty(_lines(text)))}


def parse_display_ip_ip_prefix(text: str) -> dict[str, Any]:
    prefix_lists: dict[str, dict[str, Any]] = {}
    for line in _lines(text):
        stripped = line.strip()
        if not stripped:
            continue
        match = re.match(r"^ip\s+ip-prefix\s+(\S+)\s+index\s+(\d+)\s+(permit|deny)\s+(.+)$", stripped, re.I)
        if not match:
            continue
        name = match.group(1)
        entry = {
            "index": int(match.group(2)),
            "action": match.group(3).lower(),
            "value": match.group(4).strip(),
            "line": stripped,
        }
        prefix_lists.setdefault(name, {"name": name, "entries": []})["entries"].append(entry)
    return {"ip_prefixes": prefix_lists, "raw_line_count": len(_compact_nonempty(_lines(text)))}


def parse_display_ipv6_prefix(text: str) -> dict[str, Any]:
    prefix_lists: dict[str, dict[str, Any]] = {}
    for line in _lines(text):
        stripped = line.strip()
        if not stripped:
            continue
        match = re.match(r"^ipv6\s+prefix\s+(\S+)\s+index\s+(\d+)\s+(permit|deny)\s+(.+)$", stripped, re.I)
        if not match:
            continue
        name = match.group(1)
        entry = {
            "index": int(match.group(2)),
            "action": match.group(3).lower(),
            "value": match.group(4).strip(),
            "line": stripped,
        }
        prefix_lists.setdefault(name, {"name": name, "entries": []})["entries"].append(entry)
    return {"ipv6_prefixes": prefix_lists, "raw_line_count": len(_compact_nonempty(_lines(text)))}


def parse_display_snmp_agent_sys_info(text: str) -> dict[str, Any]:
    info: dict[str, Any] = {
        "sys_name": None,
        "contact": None,
        "location": None,
        "engine_id": None,
        "versions": [],
        "lines": _compact_nonempty(_lines(text)),
    }
    for line in _lines(text):
        stripped = line.strip()
        if not stripped:
            continue
        lowered = stripped.lower()
        if info["sys_name"] is None:
            match = re.search(r"(?:sysname|system name)\s*[:=]\s*(.+)$", stripped, re.I)
            if match:
                info["sys_name"] = match.group(1).strip()
        if info["contact"] is None and "contact" in lowered:
            match = _split_key_value(stripped)
            if match:
                info["contact"] = match[1]
        if info["location"] is None and "location" in lowered:
            match = _split_key_value(stripped)
            if match:
                info["location"] = match[1]
        if info["engine_id"] is None and "engine" in lowered:
            match = _split_key_value(stripped)
            if match:
                info["engine_id"] = match[1]
        if "version" in lowered and stripped not in info["versions"]:
            info["versions"].append(stripped)
    return info


def parse_display_current_configuration_include(command_name: str, text: str) -> dict[str, Any]:
    command = (command_name or "").strip()
    include_match = re.search(r"\|\s*include\s+(.+)$", command, re.I)
    include_filter = include_match.group(1).strip() if include_match else ""
    lines = _compact_nonempty(_lines(text))
    sensitive_terms = {
        "password",
        "cipher",
        "simple",
        "authentication",
        "local-user",
        "snmp-agent community",
        "radius",
        "tacacs",
        "key-chain",
        "private-key",
        "secret",
    }
    if include_filter:
        filtered = [line for line in lines if include_filter.lower() in line.lower()]
    else:
        filtered = lines
    sanitized: list[str] = []
    for line in filtered:
        lowered = line.lower()
        if any(term in lowered for term in sensitive_terms):
            continue
        sanitized.append(line)
    return {
        "include_filter": include_filter,
        "matches": sanitized,
        "filtered_sensitive_count": len(filtered) - len(sanitized),
        "raw_line_count": len(lines),
    }


def parse_redacted_command_file(command_name: str, text: str) -> dict[str, Any]:
    command = (command_name or "").strip()
    lowered = command.lower()
    payload: dict[str, Any] = {
        "command_name": command,
        "parser": PARSER_NAME,
        "parsed": {},
        "warnings": [],
        "skipped": False,
    }

    if not (text or "").strip():
        payload["warnings"].append(f"{command or 'unknown command'} output is empty")
        return payload

    try:
        if lowered.startswith("display version"):
            payload["parsed"] = {"display_version": parse_display_version(text)}
        elif lowered.startswith("display device"):
            payload["parsed"] = {"display_device": parse_display_device(text)}
        elif lowered.startswith("display interface brief"):
            payload["parsed"] = {"display_interface_brief": parse_display_interface_brief(text)}
        elif lowered.startswith("display ip interface brief"):
            payload["parsed"] = {"display_ip_interface_brief": parse_display_ip_interface_brief(text)}
        elif lowered.startswith("display ipv6 interface brief"):
            payload["parsed"] = {"display_ipv6_interface_brief": parse_display_ipv6_interface_brief(text)}
        elif lowered.startswith("display bgp peer") or lowered.startswith("display bgp vpnv4") or lowered.startswith("display bgp vpnv6"):
            payload["parsed"] = {"display_bgp_peer": parse_display_bgp_peer(text)}
        elif lowered.startswith("display route-policy"):
            payload["parsed"] = {"display_route_policy": parse_display_route_policy(text)}
        elif lowered.startswith("display ip ip-prefix"):
            payload["parsed"] = {"display_ip_ip_prefix": parse_display_ip_ip_prefix(text)}
        elif lowered.startswith("display ipv6 prefix"):
            payload["parsed"] = {"display_ipv6_prefix": parse_display_ipv6_prefix(text)}
        elif lowered.startswith("display snmp-agent sys-info"):
            payload["parsed"] = {"display_snmp_agent_sys_info": parse_display_snmp_agent_sys_info(text)}
        elif lowered.startswith("display current-configuration") and "| include" in lowered:
            payload["parsed"] = {"display_current_configuration_include": parse_display_current_configuration_include(command, text)}
        else:
            payload["skipped"] = True
            payload["warnings"].append(f"{command or 'unknown command'} skipped")
    except Exception as exc:  # pragma: no cover - defensive fallback
        payload["warnings"].append(f"{command or 'unknown command'} parse error: {exc}")
        payload["skipped"] = True

    return payload


def _merge_parsed_payload(device_result: dict[str, Any], parsed_result: dict[str, Any]) -> None:
    parsed = parsed_result.get("parsed") or {}
    if "display_version" in parsed:
        device_result["system"].update(parsed["display_version"])
    if "display_device" in parsed:
        device_result["system"].setdefault("device", parsed["display_device"])
    if "display_snmp_agent_sys_info" in parsed:
        device_result["snmp"].update(parsed["display_snmp_agent_sys_info"])
    if "display_interface_brief" in parsed:
        device_result["interfaces"].extend((parsed["display_interface_brief"] or {}).get("interfaces") or [])
    if "display_ip_interface_brief" in parsed:
        device_result["ipv4_interfaces"].extend((parsed["display_ip_interface_brief"] or {}).get("ipv4_interfaces") or [])
    if "display_ipv6_interface_brief" in parsed:
        device_result["ipv6_interfaces"].extend((parsed["display_ipv6_interface_brief"] or {}).get("ipv6_interfaces") or [])
    if "display_bgp_peer" in parsed:
        device_result["bgp_peers"].extend((parsed["display_bgp_peer"] or {}).get("bgp_peers") or [])
    if "display_route_policy" in parsed:
        route_policies = (parsed["display_route_policy"] or {}).get("route_policies") or {}
        for name, data in route_policies.items():
            device_result["route_policies"][name] = data
    if "display_ip_ip_prefix" in parsed:
        prefixes = (parsed["display_ip_ip_prefix"] or {}).get("ip_prefixes") or {}
        for name, data in prefixes.items():
            device_result["ip_prefixes"][name] = data
    if "display_ipv6_prefix" in parsed:
        prefixes = (parsed["display_ipv6_prefix"] or {}).get("ipv6_prefixes") or {}
        for name, data in prefixes.items():
            device_result["ipv6_prefixes"][name] = data
    if "display_current_configuration_include" in parsed:
        snippets = parsed["display_current_configuration_include"]
        if snippets.get("matches"):
            device_result["system"].setdefault("config_includes", []).append(
                {
                    "include_filter": snippets.get("include_filter"),
                    "matches": snippets.get("matches"),
                }
            )


def _load_device_file_pairs(device_dir: Path) -> list[dict[str, Any]]:
    pairs: list[dict[str, Any]] = []
    redacted_dir = device_dir / "redacted"
    raw_dir = device_dir / "raw"

    source_dir = redacted_dir if any(path.is_file() and path.suffix == ".txt" for path in redacted_dir.glob("*")) else raw_dir
    if not source_dir.exists():
        return pairs

    for txt_path in sorted(source_dir.glob("*.txt")):
        if txt_path.name == ".gitkeep":
            continue
        meta_path = source_dir / f"{txt_path.stem}.meta.json"
        command_name = txt_path.stem.replace("_", " ")
        meta: dict[str, Any] = {}
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                meta = {}
        command_name = str(meta.get("command") or command_name).strip()
        try:
            text = txt_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            text = ""
        pairs.append(
            {
                "command_name": command_name,
                "text": text,
                "source": "redacted" if source_dir == redacted_dir else "raw",
                "text_path": str(txt_path),
                "meta_path": str(meta_path) if meta_path.exists() else "",
                "meta": meta,
            }
        )
    return pairs


def parse_device_collection(device_dir: str | Path, jobs_base: Optional[Path] = None) -> dict[str, Any]:
    device_dir = Path(device_dir)
    if not device_dir.exists():
        raise KeyError("device collection directory not found")

    results_dir = device_dir.parent.parent
    job_dir = results_dir.parent
    job_id = job_dir.name
    job = load_compliance_job(job_id, jobs_base)
    device_id = device_dir.name

    parser_manifest = list((job.get("parser_manifest") or {}).get("devices") or [])
    plan_devices = list((job.get("collection_plan") or {}).get("devices") or [])
    device_meta = next((item for item in parser_manifest if str(item.get("device_id")) == device_id), None)
    if not device_meta:
        device_meta = next((item for item in plan_devices if str(item.get("device_id")) == device_id), {})

    device_result: dict[str, Any] = {
        "device_id": device_meta.get("device_id") if device_meta else device_id,
        "name": device_meta.get("name") if device_meta else device_id,
        "profile": device_meta.get("profile") if device_meta else "default-readonly",
        "parsed_at": _now(),
        "parser": PARSER_NAME,
        "summary": {
            "interfaces_count": 0,
            "ipv4_interfaces_count": 0,
            "ipv6_interfaces_count": 0,
            "bgp_peers_count": 0,
            "route_policies_count": 0,
            "ip_prefixes_count": 0,
            "ipv6_prefixes_count": 0,
            "warnings_count": 0,
        },
        "system": {},
        "interfaces": [],
        "ipv4_interfaces": [],
        "ipv6_interfaces": [],
        "bgp_peers": [],
        "route_policies": {},
        "ip_prefixes": {},
        "ipv6_prefixes": {},
        "snmp": {},
        "warnings": [],
        "skipped": [],
        "commands": [],
        "files": {},
    }

    command_pairs = _load_device_file_pairs(device_dir)
    if not command_pairs:
        device_result["warnings"].append("no raw or redacted command files found")

    for pair in command_pairs:
        parsed = parse_redacted_command_file(pair["command_name"], pair["text"])
        device_result["commands"].append(
            {
                "command_name": pair["command_name"],
                "source": pair["source"],
                "text_path": pair["text_path"],
                "meta_path": pair["meta_path"],
                "warnings": parsed.get("warnings") or [],
                "skipped": bool(parsed.get("skipped")),
            }
        )
        _merge_parsed_payload(device_result, parsed)
        device_result["warnings"].extend(parsed.get("warnings") or [])
        if parsed.get("skipped"):
            device_result["skipped"].append(pair["command_name"])

    device_result["summary"].update(
        {
            "interfaces_count": len(device_result["interfaces"]),
            "ipv4_interfaces_count": len(device_result["ipv4_interfaces"]),
            "ipv6_interfaces_count": len(device_result["ipv6_interfaces"]),
            "bgp_peers_count": len(device_result["bgp_peers"]),
            "route_policies_count": len(device_result["route_policies"]),
            "ip_prefixes_count": len(device_result["ip_prefixes"]),
            "ipv6_prefixes_count": len(device_result["ipv6_prefixes"]),
            "warnings_count": len(device_result["warnings"]),
        }
    )

    parsed_dir = device_dir / "parsed"
    parsed_dir.mkdir(parents=True, exist_ok=True)
    inventory_json = parsed_dir / "parsed-inventory.json"
    inventory_md = parsed_dir / "PARSED-INVENTORY.md"
    device_result["files"] = {
        "parsed_inventory_json": str(inventory_json),
        "parsed_inventory_markdown": str(inventory_md),
        "parsed_inventory_json_report_path": _report_path(inventory_json),
        "parsed_inventory_report_path": _report_path(inventory_md),
    }
    _dump_json(inventory_json, device_result)

    markdown_lines = [
        "# PARSED-INVENTORY",
        "",
        f"## Job ID\n`{job_id}`",
        "",
        f"## Device\n`{device_result['name']}`",
        "",
        f"## Parser\n`{PARSER_NAME}`",
        "",
        "## Summary",
    ]
    for key, value in device_result["summary"].items():
        markdown_lines.append(f"- {key}: {value}")
    markdown_lines.extend(
        [
            "",
            "## Warnings",
        ]
    )
    if device_result["warnings"]:
        markdown_lines.extend([f"- {warning}" for warning in device_result["warnings"]])
    else:
        markdown_lines.append("- none")
    markdown_lines.extend(
        [
            "",
            "## Skipped",
        ]
    )
    if device_result["skipped"]:
        markdown_lines.extend([f"- {item}" for item in device_result["skipped"]])
    else:
        markdown_lines.append("- none")
    inventory_md.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")

    return device_result


def parse_job_collection(job_id: str, jobs_base: Optional[Path] = None) -> dict[str, Any]:
    job = load_compliance_job(job_id, jobs_base)
    job_dir = _safe_job_dir(job_id, jobs_base)
    results_dir = job_dir / "collection-results"
    parser_manifest = job.get("parser_manifest") or {}
    raw_validation = job.get("raw_output_safety_validation") or {}

    if not parser_manifest:
        raise ValueError("parser manifest missing")
    if raw_validation.get("decision") == "RAW_OUTPUT_SAFETY_INVALID":
        raise ValueError("raw output safety validation invalid")

    manifest_devices = list(parser_manifest.get("devices") or [])
    if not manifest_devices:
        raise ValueError("no devices available for parsing")

    device_results: list[dict[str, Any]] = []
    any_warnings = False
    any_skipped = False

    for device in manifest_devices:
        device_id = str(device.get("device_id") or device.get("id") or "unknown")
        device_dir = results_dir / "devices" / device_id
        parsed = parse_device_collection(device_dir, jobs_base)
        device_results.append(parsed)
        any_warnings = any_warnings or bool(parsed.get("warnings"))
        any_skipped = any_skipped or bool(parsed.get("skipped"))

    summary = {
        "devices_count": len(device_results),
        "interfaces_count": sum(int(device.get("summary", {}).get("interfaces_count") or 0) for device in device_results),
        "ipv4_interfaces_count": sum(int(device.get("summary", {}).get("ipv4_interfaces_count") or 0) for device in device_results),
        "ipv6_interfaces_count": sum(int(device.get("summary", {}).get("ipv6_interfaces_count") or 0) for device in device_results),
        "bgp_peers_count": sum(int(device.get("summary", {}).get("bgp_peers_count") or 0) for device in device_results),
        "route_policies_count": sum(int(device.get("summary", {}).get("route_policies_count") or 0) for device in device_results),
        "ip_prefixes_count": sum(int(device.get("summary", {}).get("ip_prefixes_count") or 0) for device in device_results),
        "ipv6_prefixes_count": sum(int(device.get("summary", {}).get("ipv6_prefixes_count") or 0) for device in device_results),
        "warnings_count": sum(int(device.get("summary", {}).get("warnings_count") or 0) for device in device_results),
        "skipped_count": sum(len(device.get("skipped") or []) for device in device_results),
    }

    status = "PARSER_COMPLETED"
    if any_warnings or any_skipped:
        status = "PARSER_COMPLETED_WITH_WARNINGS"

    payload = {
        "job_id": job_id,
        "parser": PARSER_NAME,
        "parsed_at": _now(),
        "status": status,
        "decision": status,
        "operator": "",
        "simulation_only": True,
        "device_connection_started": False,
        "netbox_write": False,
        "sync_called": False,
        "approval_record_created": False,
        "apply_plan_created": False,
        "summary": summary,
        "warnings": [warning for device in device_results for warning in (device.get("warnings") or [])],
        "skipped": [item for device in device_results for item in (device.get("skipped") or [])],
        "devices": device_results,
        "checked_at": _now(),
    }

    parser_result_json = results_dir / "parser-result.json"
    parser_result_md = results_dir / "PARSER-RESULT.md"
    _dump_json(parser_result_json, payload)

    lines = [
        "# PARSER-RESULT",
        "",
        f"## Job ID\n`{job_id}`",
        "",
        f"## Decision\n`{status}`",
        "",
        "## Summary",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Devices",
        ]
    )
    for device in device_results:
        lines.extend(
            [
                "",
                f"### {device.get('name')}",
                f"- device_id: {device.get('device_id')}",
                f"- profile: {device.get('profile')}",
                f"- parser: {device.get('parser')}",
                f"- warnings_count: {device.get('summary', {}).get('warnings_count', 0)}",
                f"- parsed_inventory_markdown: {device.get('files', {}).get('parsed_inventory_report_path')}",
                f"- parsed_inventory_json: {device.get('files', {}).get('parsed_inventory_json_report_path')}",
            ]
        )
    lines.extend(
        [
            "",
            "## Safety",
            "- simulation_only=true",
            "- device_connection_started=false",
            "- netbox_write=false",
            "- sync_called=false",
            "- approval_record_created=false",
            "- apply_plan_created=false",
        ]
    )
    parser_result_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "job_id": job_id,
        "parser": PARSER_NAME,
        "status": status,
        "decision": status,
        "summary": summary,
        "files": {
            "parser_result": str(parser_result_json),
            "parser_result_markdown": str(parser_result_md),
            "parser_result_report_path": _report_path(parser_result_md),
        },
        "parser_result": payload,
    }
