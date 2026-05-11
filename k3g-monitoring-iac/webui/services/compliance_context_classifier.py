"""Operational context classifier for parsed compliance inventory.

Local only. No NetBox writes. No device writes. No sync/apply/approval side effects.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .compliance_jobs import JOBS_BASE


CONTEXTS: dict[str, dict[str, Any]] = {
    "security_access": {
        "label": "Seguranca e Acessos",
        "description": "ACL, SNMP, SSH, AAA e usuarios locais quando aparecem na coleta.",
        "optional": False,
    },
    "interfaces": {
        "label": "Interfaces e Subinterfaces",
        "description": "Interfaces fisicas, Eth-Trunk, VLANIF, subinterfaces, MTU, estado e servico associado.",
        "optional": False,
    },
    "vpns": {
        "label": "VPNs",
        "description": "L2VC, VSI, VPLS, VPWS e bindings detectados.",
        "optional": False,
    },
    "tunnels": {
        "label": "Tuneis",
        "description": "Existencia de tuneis e onde estao atrelados quando a coleta permite inferir.",
        "optional": True,
    },
    "bgp": {
        "label": "BGP",
        "description": "Peerings, filtros, route-policy, ASN remoto, descricao e estado.",
        "optional": False,
    },
    "mpls": {
        "label": "MPLS",
        "description": "Ativacao e features MPLS detectadas.",
        "optional": True,
    },
    "ospf": {
        "label": "OSPF",
        "description": "Processos, areas, interfaces e features OSPF detectadas.",
        "optional": True,
    },
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _safe_job_dir(job_id: str, jobs_base: Optional[Path] = None) -> Path:
    return (jobs_base or JOBS_BASE) / job_id


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_parsed_inventory_files(job_id: str, jobs_base: Optional[Path] = None) -> list[dict[str, Any]]:
    job_dir = _safe_job_dir(job_id, jobs_base)
    inventories: list[dict[str, Any]] = []
    for path in sorted((job_dir / "collection-results").glob("devices/*/parsed/parsed-inventory.json")):
        inventory = _load_json(path)
        if inventory:
            inventories.append({"path": path, "inventory": inventory})
    return inventories


def _command_text(parsed_inventory: dict[str, Any]) -> str:
    chunks: list[str] = []
    for command in parsed_inventory.get("commands") or []:
        chunks.append(str(command.get("command_name") or ""))
    for item in (parsed_inventory.get("system") or {}).get("config_includes") or []:
        chunks.append(str(item.get("include_filter") or ""))
        chunks.extend(str(line) for line in item.get("matches") or [])
    for interface in parsed_inventory.get("interfaces") or []:
        chunks.append(str(interface.get("name") or ""))
        chunks.append(str(interface.get("description") or ""))
    return "\n".join(chunks)


def _interface_type(name: str) -> str:
    lowered = name.lower()
    if "." in name:
        return "subinterface"
    if lowered.startswith("eth-trunk"):
        return "eth_trunk"
    if lowered.startswith("vlanif"):
        return "vlanif"
    if lowered.startswith("tunnel"):
        return "tunnel"
    if lowered.startswith(("loopback", "virtual-", "null")):
        return "logical"
    return "physical"


def _normalize_interface(item: dict[str, Any]) -> dict[str, Any]:
    name = str(item.get("name") or "")
    description = item.get("description")
    service = None
    if description and re.search(r"(?:SVC|CID|CUST|MPLS|INET|IX|CLI)\b", str(description), re.I):
        service = str(description)
    return {
        "name": name,
        "type": _interface_type(name),
        "description": description,
        "mtu": item.get("mtu"),
        "physical": item.get("physical"),
        "protocol": item.get("protocol"),
        "service_association": service,
        "source": "parsed_inventory.interfaces",
    }


def _detect_lines(text: str, patterns: list[str]) -> list[str]:
    matches: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if any(re.search(pattern, stripped, re.I) for pattern in patterns):
            matches.append(stripped)
    return matches


def classify_device_contexts(parsed_inventory: dict[str, Any], source_path: str = "") -> dict[str, Any]:
    """Classify one parsed device inventory into operational contexts."""
    command_text = _command_text(parsed_inventory)
    contexts: list[dict[str, Any]] = []

    snmp = parsed_inventory.get("snmp") or {}
    security_items: list[dict[str, Any]] = []
    if snmp:
        security_items.append({"type": "snmp", "name": snmp.get("sys_name") or "snmp-agent", "attributes": snmp, "source": "parsed_inventory.snmp"})
    for item in (parsed_inventory.get("system") or {}).get("config_includes") or []:
        include_filter = str(item.get("include_filter") or "").lower()
        if any(token in include_filter for token in ("ssh", "stelnet", "snmp-agent", "acl", "aaa", "local-user")):
            security_items.append(
                {
                    "type": include_filter or "access_config",
                    "name": include_filter or "access_config",
                    "attributes": {"matches_count": len(item.get("matches") or []), "include_filter": item.get("include_filter")},
                    "source": "parsed_inventory.system.config_includes",
                }
            )
    contexts.append(_context("security_access", security_items))

    interfaces = [_normalize_interface(item) for item in parsed_inventory.get("interfaces") or []]
    seen = {item["name"] for item in interfaces}
    for item in parsed_inventory.get("ipv4_interfaces") or []:
        name = str(item.get("name") or "")
        if name and name not in seen:
            interfaces.append(_normalize_interface(item))
            seen.add(name)
    for item in parsed_inventory.get("ipv6_interfaces") or []:
        name = str(item.get("name") or "")
        if name and name not in seen:
            interfaces.append(_normalize_interface(item))
            seen.add(name)
    contexts.append(_context("interfaces", interfaces))

    vpn_lines = _detect_lines(command_text, [r"\bl2vc\b", r"\bvsi\b", r"\bvpls\b", r"\bvpws\b", r"\bvpn-instance\b"])
    contexts.append(_context("vpns", [{"type": "vpn_reference", "name": line, "source": "parsed_or_command_context"} for line in vpn_lines]))

    tunnel_interfaces = [item for item in interfaces if item.get("type") == "tunnel"]
    tunnel_lines = _detect_lines(command_text, [r"\btunnel\b"])
    tunnel_items = tunnel_interfaces + [
        {"type": "tunnel_reference", "name": line, "binding": _infer_binding(line), "source": "parsed_or_command_context"} for line in tunnel_lines
    ]
    contexts.append(_context("tunnels", tunnel_items))

    bgp_items: list[dict[str, Any]] = []
    for peer in parsed_inventory.get("bgp_peers") or []:
        bgp_items.append(
            {
                "type": "bgp_peer",
                "name": peer.get("peer_ip"),
                "remote_asn": peer.get("remote_asn") or peer.get("asn"),
                "description": peer.get("description"),
                "state": peer.get("state"),
                "import_policy": peer.get("import_policy"),
                "export_policy": peer.get("export_policy"),
                "source": "parsed_inventory.bgp_peers",
            }
        )
    for name, value in (parsed_inventory.get("route_policies") or {}).items():
        bgp_items.append({"type": "route_policy", "name": name, "attributes": value, "source": "parsed_inventory.route_policies"})
    for name, value in (parsed_inventory.get("ip_prefixes") or {}).items():
        bgp_items.append({"type": "ip_prefix", "name": name, "attributes": value, "source": "parsed_inventory.ip_prefixes"})
    for name, value in (parsed_inventory.get("ipv6_prefixes") or {}).items():
        bgp_items.append({"type": "ip_prefix", "name": name, "attributes": value, "source": "parsed_inventory.ipv6_prefixes"})
    community_lines = _detect_lines(command_text, [r"community-filter", r"community-list"])
    bgp_items.extend({"type": "community_filter", "name": line, "source": "parsed_or_command_context"} for line in community_lines)
    contexts.append(_context("bgp", bgp_items))

    mpls_lines = _detect_lines(command_text, [r"\bmpls\b", r"\bl2vpn\b", r"\bl2vc\b", r"\bvsi\b"])
    contexts.append(_context("mpls", [{"type": "mpls_feature", "name": line, "source": "parsed_or_command_context"} for line in mpls_lines]))

    ospf_lines = _detect_lines(command_text, [r"\bospf\b", r"\barea\s+\d+"])
    contexts.append(_context("ospf", [{"type": "ospf_reference", "name": line, "source": "parsed_or_command_context"} for line in ospf_lines]))

    return {
        "device_id": parsed_inventory.get("device_id"),
        "name": parsed_inventory.get("name"),
        "profile": parsed_inventory.get("profile"),
        "source_path": source_path,
        "contexts": contexts,
    }


def _context(context_id: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    meta = CONTEXTS[context_id]
    return {
        "context_id": context_id,
        "label": meta["label"],
        "description": meta["description"],
        "optional": bool(meta["optional"]),
        "present": bool(items),
        "items_count": len(items),
        "items": items,
    }


def _infer_binding(line: str) -> str | None:
    match = re.search(r"(?:interface|binding|bind|source)\s+(\S+)", line, re.I)
    return match.group(1) if match else None


def classify_job_contexts(job_id: str, jobs_base: Optional[Path] = None) -> dict[str, Any]:
    """Generate analysis/context-inventory.json for all parsed devices."""
    job_dir = _safe_job_dir(job_id, jobs_base)
    devices = [
        classify_device_contexts(item["inventory"], str(item["path"]))
        for item in _load_parsed_inventory_files(job_id, jobs_base)
    ]
    summary = {
        "devices": len(devices),
        "contexts": {
            context_id: {
                "label": meta["label"],
                "optional": bool(meta["optional"]),
                "present_devices": sum(1 for device in devices for ctx in device["contexts"] if ctx["context_id"] == context_id and ctx["present"]),
                "items_total": sum(int(ctx["items_count"]) for device in devices for ctx in device["contexts"] if ctx["context_id"] == context_id),
            }
            for context_id, meta in CONTEXTS.items()
        },
    }
    payload = {
        "job_id": job_id,
        "generated_at": _now(),
        "layer": "post_parser_pre_compare",
        "safety": _safety(),
        "summary": summary,
        "devices": devices,
        "files": {"context_inventory": str(job_dir / "analysis" / "context-inventory.json")},
    }
    _dump_json(job_dir / "analysis" / "context-inventory.json", payload)
    return payload


def _safety() -> dict[str, bool]:
    return {
        "netbox_write": False,
        "sync_called": False,
        "apply_plan_created": False,
        "approval_record_created": False,
        "ssh_write": False,
        "config_mode": False,
        "netconf_write": False,
        "snmp_write": False,
    }
