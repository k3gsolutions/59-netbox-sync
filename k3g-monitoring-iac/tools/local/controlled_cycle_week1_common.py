#!/usr/bin/env python3
"""Shared helpers for controlled Cycle-002 Week 1 operations."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from webui.services.controlled_operation import load_json_safe, load_text_safe, scan_sensitive_terms
from webui.services.validators import (
    validate_bgp_response,
    validate_bgp_metadata_registry,
    validate_interface_name_registry,
    validate_ip_response,
    validate_ip_address_relation_registry,
    validate_subinterface_response,
    validate_vrf_name_registry,
)

EXPECTED_TEAMS = ["service", "network_ops", "bgp"]
TEAM_LABELS = {
    "service": "Equipe de Serviços",
    "network_ops": "Network Ops",
    "bgp": "Equipe BGP",
}
TEAM_ALIASES = {
    "service": {"service", "service_team", "service-team", "service team", "subinterface"},
    "network_ops": {"network_ops", "network-ops", "network ops", "ops", "ip_address"},
    "bgp": {"bgp", "bgp_team", "bgp-team", "bgp team", "bgp_peer"},
}
OBJECT_TYPE_ALIASES = {
    "service": "subinterface",
    "service_interface": "subinterface",
    "subinterface": "subinterface",
    "network_ops": "ip_address",
    "ip_address": "ip_address",
    "ip mapping": "ip_address",
    "bgp": "bgp_peer",
    "bgp_peer": "bgp_peer",
}
BLOCKED_WORDS = ("token", "password", "secret", "netbox_write_token", "private key", "bearer", "authorization")


def _clean(value: Any) -> str:
    return str(value or "").strip()


def normalize_team(value: Any, source_name: str = "") -> Optional[str]:
    candidate = _clean(value).lower().replace("-", "_").replace(" ", "_")
    for team, aliases in TEAM_ALIASES.items():
        if candidate in aliases:
            return team
    lowered = source_name.lower()
    if "service" in lowered:
        return "service"
    if "network" in lowered or "ops" in lowered:
        return "network_ops"
    if "bgp" in lowered:
        return "bgp"
    return None


def normalize_object_type(value: Any, team: str = "", source_name: str = "") -> Optional[str]:
    candidate = _clean(value).lower().replace("-", "_").replace(" ", "_")
    if candidate in OBJECT_TYPE_ALIASES:
        return OBJECT_TYPE_ALIASES[candidate]
    if team == "service":
        return "subinterface"
    if team == "network_ops":
        return "ip_address"
    if team == "bgp":
        return "bgp_peer"
    lowered = source_name.lower()
    if "service" in lowered:
        return "subinterface"
    if "network" in lowered or "ip" in lowered:
        return "ip_address"
    if "bgp" in lowered:
        return "bgp_peer"
    return None


def contains_blocked_terms(*values: Any) -> bool:
    text = " ".join(_clean(value).lower() for value in values if _clean(value))
    return any(word in text for word in BLOCKED_WORDS)


def object_key_is_safe(object_key: str) -> bool:
    key = _clean(object_key)
    if not key:
        return False
    if key in {".", ".."}:
        return False
    if "\\" in key or ".." in key:
        return False
    if key.startswith("/") or key.startswith("./") or key.startswith("../"):
        return False
    return True


def load_response_items(responses_dir: Path) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    if not responses_dir.exists():
        return items

    for path in sorted(responses_dir.iterdir()):
        if not path.is_file() or path.suffix.lower() not in {".json", ".csv"}:
            continue

        try:
            if path.suffix.lower() == ".json":
                payload = load_json_safe(path)
                if isinstance(payload, list):
                    rows: Iterable[Any] = payload
                elif isinstance(payload, dict):
                    rows = [payload]
                else:
                    rows = []
                for row in rows:
                    if isinstance(row, dict):
                        items.append(_normalize_record(row, path))
            else:
                with path.open("r", encoding="utf-8", newline="") as handle:
                    reader = csv.DictReader(handle)
                    for row in reader:
                        items.append(_normalize_record(row, path))
        except Exception as exc:
            items.append({
                "source_file": str(path),
                "source_name": path.name,
                "format": "invalid",
                "parse_error": str(exc),
            })

    return items


def _normalize_record(row: Dict[str, Any], source_path: Path) -> Dict[str, Any]:
    team = normalize_team(
        row.get("team") or row.get("responsible_team") or row.get("responsible_team_slug") or row.get("owner_team"),
        source_path.name,
    )
    object_type = normalize_object_type(
        row.get("object_type") or row.get("type") or row.get("item_type"),
        team or "",
        source_path.name,
    )
    record = dict(row)
    record.update({
        "source_file": str(source_path),
        "source_name": source_path.name,
        "team": team,
        "object_type": object_type,
        "object_key": _clean(row.get("object_key") or row.get("item_id") or row.get("key")),
        "status": _clean(row.get("status") or row.get("response_status") or row.get("validation_status")),
        "updated_by": _clean(row.get("updated_by") or row.get("reviewed_by")),
        "updated_at": _clean(row.get("updated_at") or row.get("reviewed_at")),
    })
    return record


def team_required_fields(team: str) -> List[str]:
    if team == "service":
        return ["tenant", "service_type", "criticality", "owner", "evidence"]
    if team == "network_ops":
        return ["owner", "evidence", "relation_type"]
    if team == "bgp":
        return ["remote_asn", "remote_bgp_group", "policy_intent", "owner", "criticality", "evidence"]
    return []


def classify_record(record: Dict[str, Any]) -> Tuple[str, List[str], List[Dict[str, Any]]]:
    team = record.get("team") or normalize_team(record.get("responsible_team"), record.get("source_name", ""))
    object_type = record.get("object_type") or normalize_object_type(record.get("object_type"), team or "", record.get("source_name", ""))
    status = _clean(record.get("status")).lower()
    issues: List[str] = []
    violations: List[Dict[str, Any]] = []

    if not team:
        issues.append("team missing")
        return "blocked", issues, violations
    if not object_type:
        issues.append("object_type missing")
        return "blocked", issues, violations

    object_key = _clean(record.get("object_key"))
    if not object_key_is_safe(object_key):
        issues.append("object_key unsafe")

    if contains_blocked_terms(json.dumps(record, sort_keys=True)):
        issues.append("blocked keyword found")

    if status in {"blocked", "rejected"}:
        if not _clean(record.get("notes")):
            issues.append("notes required")
        return status, issues, violations
    if status == "needs_clarification":
        if not _clean(record.get("notes")):
            issues.append("notes required")
        return "needs_clarification", issues, violations

    if status not in {"answered", "validated", "ready_for_week2_review"}:
        issues.append(f"unsupported status: {status or 'missing'}")
        return "blocked", issues, violations

    if object_type == "subinterface":
        ok, errors = validate_subinterface_response(record)
        if not ok:
            issues.extend(errors)
        if _clean(record.get("tenant")) and len(_clean(record.get("tenant"))) > 100:
            issues.append("tenant too long")
        if _clean(record.get("service_type")) and contains_blocked_terms(record.get("service_type")):
            issues.append("service_type contains blocked keyword")
        if _clean(record.get("criticality")) and contains_blocked_terms(record.get("criticality")):
            issues.append("criticality contains blocked keyword")
        if _clean(record.get("owner")) and contains_blocked_terms(record.get("owner")):
            issues.append("owner contains blocked keyword")
        if _clean(record.get("evidence")) and contains_blocked_terms(record.get("evidence")):
            issues.append("evidence contains blocked keyword")
        if _clean(record.get("interface")):
            valid, err = validate_interface_name_registry(record.get("interface"), required=False)
            if not valid and err:
                issues.append(f"interface: {err}")
        if _clean(record.get("vrf")):
            valid, err = validate_vrf_name_registry(record.get("vrf"), required=False)
            if not valid and err:
                issues.append(f"vrf: {err}")
    elif object_type == "ip_address":
        ok, errors = validate_ip_response(record)
        if not ok:
            issues.extend(errors)
        for violation in validate_ip_address_relation_registry(record):
            violations.append(violation)
            if violation.get("severity") in {"blocker", "error"}:
                issues.append(f"{violation.get('rule_id')}: {violation.get('message_pt')}")
        if _clean(record.get("interface")):
            valid, err = validate_interface_name_registry(record.get("interface"), required=False)
            if not valid and err:
                issues.append(f"interface: {err}")
        if _clean(record.get("vrf")):
            valid, err = validate_vrf_name_registry(record.get("vrf"), required=False)
            if not valid and err:
                issues.append(f"vrf: {err}")
    elif object_type == "bgp_peer":
        ok, errors = validate_bgp_response(record)
        if not ok:
            issues.extend(errors)
        for violation in validate_bgp_metadata_registry(record):
            violations.append(violation)
            if violation.get("severity") in {"blocker", "error"}:
                issues.append(f"{violation.get('rule_id')}: {violation.get('message_pt')}")
    else:
        issues.append(f"unsupported object_type: {object_type}")

    if status == "validated" and not issues:
        return "validated", issues, violations
    if not issues:
        return "ready_for_week2_review", issues, violations
    return "needs_clarification" if any(item.startswith("missing") or "required" in item.lower() for item in issues) else "blocked", issues, violations


def classify_by_team(items: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    bucket: Dict[str, List[Dict[str, Any]]] = {team: [] for team in EXPECTED_TEAMS}
    for item in items:
        team = item.get("team") or normalize_team(item.get("responsible_team"), item.get("source_name", ""))
        if team in bucket:
            bucket[team].append(item)
    return bucket


def detect_secret_hits(responses_dir: Path) -> List[str]:
    return scan_sensitive_terms(responses_dir)
