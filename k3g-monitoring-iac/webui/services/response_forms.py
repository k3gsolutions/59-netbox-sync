"""Pending-item response helpers for the local Web UI."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Any

from .validators import (
    CRITICALITIES,
    SERVICE_TYPES,
    STATUSES,
    contains_blocked_keywords,
    validate_criticality,
    validate_evidence,
    validate_interface,
    validate_notes,
    validate_owner,
    validate_policy_intent,
    validate_remote_asn,
    validate_remote_bgp_group,
    validate_relation_type,
    validate_service_relation,
    validate_service_type,
    validate_status,
    validate_tenant,
    validate_vrf,
)

try:
    from .convention_validator import (
        load_policy_registry,
        validate_comment,
        validate_bgp_metadata,
        validate_ip_address_relation,
        _make_registry_blocker,
    )
    HAS_CONVENTION_VALIDATOR = True
except (ImportError, Exception):
    HAS_CONVENTION_VALIDATOR = False
    _make_registry_blocker = None  # type: ignore

RESPONSES_ROOT_NAME = "week1-responses"
AUDIT_DIR_NAME = "audit"

CSV_HEADER = [
    "device",
    "object_type",
    "object_key",
    "responsible_team",
    "status",
    "tenant",
    "service_type",
    "criticality",
    "owner",
    "evidence",
    "interface",
    "vrf",
    "service_relation",
    "remote_asn",
    "remote_bgp_group",
    "policy_intent",
    "notes",
    "updated_at",
    "updated_by",
    "relation_type",
]

TEAM_FILE_STEMS = {
    "service-team": "service-team-response.csv",
    "network-ops": "network-ops-response.csv",
    "bgp-team": "bgp-team-response.csv",
}

TEAM_LABELS = {
    "service-team": "Service Team",
    "network-ops": "Network Ops",
    "bgp-team": "BGP Team",
}

OBJECT_FIELD_SETS = {
    "subinterface": [
        "tenant",
        "service_type",
        "criticality",
        "owner",
        "evidence",
        "notes",
        "status",
    ],
    "ip_address": [
        "interface",
        "vrf",
        "relation_type",
        "service_relation",
        "owner",
        "evidence",
        "notes",
        "status",
    ],
    "bgp_peer": [
        "remote_asn",
        "remote_bgp_group",
        "policy_intent",
        "owner",
        "criticality",
        "evidence",
        "notes",
        "status",
    ],
}

MODAL_STATUS_CHOICES = ["answered", "needs_clarification", "blocked", "rejected"]
RELATION_TYPE_CHOICES = ["service", "infrastructure", "loopback", "management", "backbone", "unknown"]

BLOCKED_VALUES = (
    "token",
    "password",
    "secret",
    "netbox_write_token",
    "private key",
    "bearer",
    "authorization",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _team_slug(team: str) -> str:
    normalized = (team or "").strip().lower().replace("_", "-")
    if normalized in TEAM_LABELS:
        return normalized
    if "service" in normalized:
        return "service-team"
    if "network" in normalized or "ops" in normalized:
        return "network-ops"
    if "bgp" in normalized:
        return "bgp-team"
    return re.sub(r"[^a-z0-9-]+", "-", normalized).strip("-") or "unknown-team"


def _team_label(team: str) -> str:
    return TEAM_LABELS.get(_team_slug(team), team or "Unknown Team")


def _csv_filename(team: str) -> str:
    return TEAM_FILE_STEMS.get(_team_slug(team), f"{_team_slug(team)}-response.csv")


def _audit_filename(team: str) -> str:
    return f"{_team_slug(team)}-response-audit.json"


def _responses_dir(reports_root: Path) -> Path:
    responses_dir = reports_root / "reports" / "pilot-device-compliance" / RESPONSES_ROOT_NAME
    responses_dir.mkdir(parents=True, exist_ok=True)
    return responses_dir


def _audit_dir(reports_root: Path) -> Path:
    audit_dir = _responses_dir(reports_root) / AUDIT_DIR_NAME
    audit_dir.mkdir(parents=True, exist_ok=True)
    return audit_dir


def _normalize_object_key(object_key: str) -> str:
    return (object_key or "").strip()


def _is_safe_object_key(object_key: str) -> bool:
    if not object_key:
        return False
    lowered = object_key.lower()
    if ".." in lowered:
        return False
    if "/" in object_key or "\\" in object_key:
        return False
    return True


def _safe_item_id(device: str, object_key: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", object_key.lower()).strip("-")
    if not base:
        base = "item"
    digest = hashlib.sha1(f"{device}:{object_key}".encode("utf-8")).hexdigest()[:8]
    return f"{base[:48]}-{digest}"


def _stringify(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _blocked_reason_map(payload: Dict[str, object]) -> Optional[str]:
    for key, value in payload.items():
        if isinstance(value, str) and contains_blocked_keywords(value):
            return f"{key} contains blocked keywords"
    return None


def _extract_text_values(text: str) -> Dict[str, str]:
    value = (text or "").strip()
    lowered = value.lower()
    detected_interface = ""
    detected_vrf = ""
    status_hint = "needs_mapping"

    interface_candidates = []
    explicit_patterns = [
        r"assigned_interface[:=\s]+([A-Za-z0-9_./\-]+)",
        r"assigned_object_name[:=\s]+([A-Za-z0-9_./\-]+)",
        r"source_interface[:=\s]+([A-Za-z0-9_./\-]+)",
    ]
    for pattern in explicit_patterns:
        for match in re.finditer(pattern, value, re.IGNORECASE):
            candidate = match.group(1)
            if candidate and candidate not in interface_candidates:
                interface_candidates.append(candidate)

    interface_patterns = [
        r"(Eth-Trunk\d+(?:\.\d+)?)",
        r"(GigabitEthernet\d+/\d+/\d+(?:\.\d+)?)",
        r"(10GE\d+/\d+/\d+)",
        r"(LoopBack\d+)",
        r"(Vlanif\d+)",
    ]
    for pattern in interface_patterns:
        for match in re.finditer(pattern, value, re.IGNORECASE):
            candidate = match.group(1)
            if candidate and candidate not in interface_candidates:
                interface_candidates.append(candidate)

    if interface_candidates:
        detected_interface = interface_candidates[0]

    vrf_patterns = [
        r"vrf[:=\s]+([a-zA-Z0-9_\-]+)",
        r"vpn_instance[:=\s]+([a-zA-Z0-9_\-]+)",
        r"assigned_vrf[:=\s]+([a-zA-Z0-9_\-]+)",
        r"source_vrf[:=\s]+([a-zA-Z0-9_\-]+)",
    ]
    for pattern in vrf_patterns:
        match = re.search(pattern, value, re.IGNORECASE)
        if match:
            detected_vrf = match.group(1)
            break

    if detected_interface and detected_vrf:
        status_hint = "confirm_detected_mapping"
    elif detected_interface or detected_vrf:
        status_hint = "confirm_detected_mapping"

    if len(set(interface_candidates)) > 1 or "multiple" in lowered or "ambiguous" in lowered or "either" in lowered:
        status_hint = "ambiguous_mapping"

    return {
        "detected_interface": detected_interface,
        "detected_vrf": detected_vrf,
        "status_hint": status_hint,
    }


def _load_csv_rows(csv_path: Path) -> List[Dict[str, str]]:
    if not csv_path.exists():
        return []
    rows: List[Dict[str, str]] = []
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row:
                rows.append({k: (v or "").strip() for k, v in row.items()})
    return rows


def _find_existing_row(rows: Iterable[Dict[str, str]], object_key: str) -> Optional[Dict[str, str]]:
    for row in rows:
        if row.get("object_key") == object_key:
            return row
    return None


def _response_row_by_team(reports_root: Path, team: str) -> Tuple[Path, List[Dict[str, str]]]:
    responses_dir = _responses_dir(reports_root)
    csv_path = responses_dir / _csv_filename(team)
    return csv_path, _load_csv_rows(csv_path)


def _load_template_rows(reports_root: Path) -> List[Dict[str, str]]:
    template = reports_root / "reports" / "pilot-device-compliance" / "week1-metadata-collection-template.csv"
    if not template.exists():
        return []
    rows: List[Dict[str, str]] = []
    with template.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row:
                rows.append({k: (v or "").strip() for k, v in row.items()})
    return rows


def _load_status_summary(reports_root: Path) -> Dict[str, Dict[str, int]]:
    summary = {
        "pending": {},
        "answered": {},
        "needs_clarification": {},
        "blocked": {},
        "rejected": {},
    }
    template_rows = _load_template_rows(reports_root)
    for row in template_rows:
        team = _team_slug(row.get("responsible_team", ""))
        summary["pending"][team] = summary["pending"].get(team, 0) + 1
    return summary


def build_unified_csv_row(item: Dict[str, str], payload: Dict[str, object]) -> Dict[str, str]:
    """Build the unified CSV row expected by Week 1 validation."""
    row = {field: "" for field in CSV_HEADER}
    row["device"] = _stringify(item.get("device"))
    row["object_type"] = _stringify(item.get("object_type"))
    row["object_key"] = _stringify(item.get("object_key"))
    row["responsible_team"] = _stringify(item.get("responsible_team"))
    row["status"] = _stringify(payload.get("status"))
    row["tenant"] = _stringify(payload.get("tenant"))
    row["service_type"] = _stringify(payload.get("service_type"))
    row["criticality"] = _stringify(payload.get("criticality"))
    row["owner"] = _stringify(payload.get("owner"))
    row["evidence"] = _stringify(payload.get("evidence"))
    row["interface"] = _stringify(payload.get("interface"))
    row["vrf"] = _stringify(payload.get("vrf"))
    row["service_relation"] = _stringify(payload.get("service_relation"))
    row["remote_asn"] = _stringify(payload.get("remote_asn"))
    row["remote_bgp_group"] = _stringify(payload.get("remote_bgp_group"))
    row["policy_intent"] = _stringify(payload.get("policy_intent"))
    row["notes"] = _stringify(payload.get("notes"))
    row["updated_at"] = _utc_now()
    row["updated_by"] = _stringify(payload.get("updated_by"))
    row["relation_type"] = _stringify(payload.get("relation_type"))
    return row


def _validate_payload_common(item: Dict[str, str], payload: Dict[str, object]) -> List[str]:
    errors: List[str] = []

    object_key = _stringify(item.get("object_key"))
    if not object_key:
        errors.append("object_key: required")

    if "object_key" in payload:
        submitted_object_key = _stringify(payload.get("object_key"))
        if submitted_object_key != object_key:
            errors.append("object_key: immutable and must match pending item")
        elif not _is_safe_object_key(submitted_object_key):
            errors.append("object_key: unsafe value")

    updated_by = _stringify(payload.get("updated_by"))
    if not updated_by:
        errors.append("updated_by: required")
    elif contains_blocked_keywords(updated_by):
        errors.append("updated_by: contains blocked keywords")

    blocked_reason = _blocked_reason_map(payload)
    if blocked_reason:
        errors.append(blocked_reason)

    return errors


def _collect_convention_violations(item: Dict[str, str], payload: Dict[str, object]) -> List[Dict[str, Any]]:
    """Collect convention violations from policy registry.

    If registry is unavailable, returns REGISTRY-001 blocker violation
    to prevent silent fallback to hardcoded patterns.
    """
    violations: List[Dict[str, Any]] = []

    if not HAS_CONVENTION_VALIDATOR:
        # Registry unavailable = blocker violation, not silent allow
        return [_make_registry_blocker("REGISTRY-001")] if _make_registry_blocker else []

    object_type = _stringify(item.get("object_type")).lower()
    responsible_team = _team_slug(item.get("responsible_team", ""))

    # Validate notes/evidence fields via convention_validator
    notes = _stringify(payload.get("notes"))
    if notes:
        result = validate_comment(notes, max_len=1024)
        if not result.get("valid"):
            violations.append(result)

    evidence = _stringify(payload.get("evidence"))
    if evidence:
        result = validate_comment(evidence, max_len=1024)
        if not result.get("valid"):
            violations.append(result)

    # BGP metadata validation
    if object_type == "bgp_peer" or responsible_team == "bgp-team":
        bgp_data = {
            "remote_asn": payload.get("remote_asn"),
            "owner": payload.get("owner"),
            "policy_intent": payload.get("policy_intent"),
            "service_type": payload.get("service_type"),
            "criticality": payload.get("criticality"),
            "notes": notes,
        }
        bgp_violations = validate_bgp_metadata(bgp_data)
        violations.extend(bgp_violations)

    # IP address relation validation
    if object_type == "ip_address" or responsible_team == "network-ops":
        ip_data = {
            "relation_type": payload.get("relation_type"),
            "service_relation": payload.get("service_relation"),
            "notes": notes,
        }
        ip_violations = validate_ip_address_relation(ip_data)
        violations.extend(ip_violations)

    return violations


def validate_response_payload(item: Dict[str, str], payload: Dict[str, object]) -> Tuple[bool, List[str], List[Dict[str, Any]]]:
    """Validate a response payload for a pending item.

    Returns:
        Tuple[valid: bool, errors: List[str], convention_violations: List[Dict]]
    """
    errors = _validate_payload_common(item, payload)

    object_type = _stringify(item.get("object_type")).lower()
    responsible_team = _team_slug(item.get("responsible_team", ""))
    status = _stringify(payload.get("status"))

    valid_statuses = set(MODAL_STATUS_CHOICES)
    if status not in valid_statuses:
        errors.append(f"status: invalid value ({status})")
        return False, errors, []

    if status == "answered":
        if object_type == "subinterface" or responsible_team == "service-team":
            valid, err = validate_tenant(_stringify(payload.get("tenant")), required=True)
            if not valid:
                errors.append(f"tenant: {err}")

            valid, err = validate_service_type(_stringify(payload.get("service_type")), required=True)
            if not valid:
                errors.append(f"service_type: {err}")

            valid, err = validate_criticality(_stringify(payload.get("criticality")), required=True)
            if not valid:
                errors.append(f"criticality: {err}")

            valid, err = validate_owner(_stringify(payload.get("owner")), required=True)
            if not valid:
                errors.append(f"owner: {err}")

            valid, err = validate_evidence(_stringify(payload.get("evidence")), required=True)
            if not valid:
                errors.append(f"evidence: {err}")

        elif object_type == "ip_address" or responsible_team == "network-ops":
            relation_type = _stringify(payload.get("relation_type"))
            valid, err = validate_relation_type(relation_type, required=True)
            if not valid:
                errors.append(f"relation_type: {err}")

            valid, err = validate_owner(_stringify(payload.get("owner")), required=True)
            if not valid:
                errors.append(f"owner: {err}")

            valid, err = validate_evidence(_stringify(payload.get("evidence")), required=True)
            if not valid:
                errors.append(f"evidence: {err}")

            interface_value = _stringify(payload.get("interface"))
            detected_interface = _stringify(item.get("detected_interface"))
            if not interface_value and not detected_interface:
                errors.append("interface: Interface required")
            elif interface_value:
                valid, err = validate_interface(interface_value, required=True)
                if not valid:
                    errors.append(f"interface: {err}")

            vrf_value = _stringify(payload.get("vrf"))
            detected_vrf = _stringify(item.get("detected_vrf"))
            if not vrf_value and not detected_vrf:
                errors.append("vrf: VRF required")
            elif vrf_value:
                valid, err = validate_vrf(vrf_value, required=True)
                if not valid:
                    errors.append(f"vrf: {err}")

            if relation_type == "service":
                valid, err = validate_service_relation(_stringify(payload.get("service_relation")), required=True)
                if not valid:
                    errors.append(f"service_relation: {err}")
            if relation_type == "unknown" and not _stringify(payload.get("notes")):
                errors.append("notes: required")

        elif object_type == "bgp_peer" or responsible_team == "bgp-team":
            valid, err = validate_remote_asn(_stringify(payload.get("remote_asn")), required=True)
            if not valid:
                errors.append(f"remote_asn: {err}")

            valid, err = validate_remote_bgp_group(_stringify(payload.get("remote_bgp_group")), required=True)
            if not valid:
                errors.append(f"remote_bgp_group: {err}")

            valid, err = validate_policy_intent(_stringify(payload.get("policy_intent")), required=True)
            if not valid:
                errors.append(f"policy_intent: {err}")

            valid, err = validate_owner(_stringify(payload.get("owner")), required=True)
            if not valid:
                errors.append(f"owner: {err}")

            valid, err = validate_criticality(_stringify(payload.get("criticality")), required=True)
            if not valid:
                errors.append(f"criticality: {err}")

            valid, err = validate_evidence(_stringify(payload.get("evidence")), required=True)
            if not valid:
                errors.append(f"evidence: {err}")
        else:
            errors.append(f"object_type: unsupported value ({object_type})")
    notes = _stringify(payload.get("notes"))
    if status in {"blocked", "rejected", "needs_clarification"} and not notes:
        errors.append("notes: required")
    if _stringify(payload.get("relation_type")) == "unknown" and not notes:
        errors.append("notes: required")
    if notes:
        valid, err = validate_notes(notes)
        if not valid:
            errors.append(f"notes: {err}")

    # Collect convention violations (advisories, not blocking)
    convention_violations = _collect_convention_violations(item, payload)

    return len(errors) == 0, errors, convention_violations


def save_response_csv(team: str, item: Dict[str, str], payload: Dict[str, object], root: Path) -> Path:
    """Save or update the team CSV without duplicating object_key."""
    responses_dir = _responses_dir(root)
    csv_path = responses_dir / _csv_filename(team)
    rows = _load_csv_rows(csv_path)
    new_row = build_unified_csv_row(item, payload)

    replaced = False
    for index, row in enumerate(rows):
        if row.get("object_key") == new_row["object_key"]:
            rows[index] = new_row
            replaced = True
            break
    if not replaced:
        rows.append(new_row)

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_HEADER, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    return csv_path


def save_response_audit(team: str, item: Dict[str, str], payload: Dict[str, object], root: Path) -> Path:
    """Append an audit record for the local response change."""
    audit_dir = _audit_dir(root)
    audit_path = audit_dir / _audit_filename(team)
    existing_entries: List[Dict[str, object]] = []
    if audit_path.exists():
        try:
            loaded = json.loads(audit_path.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                existing_entries = loaded
        except Exception:
            existing_entries = []

    changed_fields = []
    for field in CSV_HEADER:
        if field in {"updated_at", "updated_by"}:
            continue
        old_value = _stringify(item.get(field))
        new_value = _stringify(payload.get(field))
        if field == "responsible_team":
            new_value = _stringify(item.get(field))
        if old_value != new_value and new_value:
            changed_fields.append(field)

    validation_result = {
        "valid": True,
        "status": _stringify(payload.get("status")),
        "errors": [],
    }

    if "validation_errors" in payload and isinstance(payload["validation_errors"], list):
        validation_result["errors"] = [str(err) for err in payload["validation_errors"]]
        validation_result["valid"] = len(validation_result["errors"]) == 0

    entry = {
        "timestamp": _utc_now(),
        "updated_by": _stringify(payload.get("updated_by")),
        "team": _team_slug(team),
        "object_type": _stringify(item.get("object_type")),
        "object_key": _stringify(item.get("object_key")),
        "previous_status": _stringify(item.get("status")) or "pending",
        "new_status": _stringify(payload.get("status")),
        "changed_fields": changed_fields,
        "validation_result": validation_result,
    }

    existing_entries.append(entry)
    audit_path.write_text(json.dumps(existing_entries, indent=2, ensure_ascii=False), encoding="utf-8")
    return audit_path


def load_pending_items(device: str) -> List[Dict[str, object]]:
    """Load current pending items from the local template and response CSVs."""
    root = Path(__file__).resolve().parents[2]
    template_rows = _load_template_rows(root)
    items: List[Dict[str, object]] = []

    response_maps: Dict[str, Dict[str, Dict[str, str]]] = {}
    for team in TEAM_LABELS:
        _, rows = _response_row_by_team(root, team)
        response_maps[team] = {
            row.get("object_key", ""): row
            for row in rows
            if row.get("object_key")
        }

    for row in template_rows:
        row_device = _stringify(row.get("device"))
        if row_device and row_device != device:
            continue

        team_slug = _team_slug(row.get("responsible_team", ""))
        object_key = _stringify(row.get("object_key"))
        current_row = response_maps.get(team_slug, {}).get(object_key, {})

        current_status = _stringify(current_row.get("status") or row.get("status") or "pending")
        if current_status not in {"pending", *MODAL_STATUS_CHOICES}:
            current_status = "pending"

        if current_status == "answered":
            missing_fields: List[str] = []
        else:
            missing_fields = [
                field.strip()
                for field in _stringify(row.get("missing_fields")).split(",")
                if field.strip()
            ]

        detections = {"detected_interface": "", "detected_vrf": "", "status_hint": "needs_mapping"}
        if _stringify(row.get("object_type")).lower() == "ip_address":
            detection_source = " ".join(
                filter(
                    None,
                    [
                        _stringify(row.get("evidence")),
                        _stringify(row.get("notes")),
                        _stringify(row.get("service_relation")),
                        _stringify(row.get("assigned_object_name")),
                        _stringify(row.get("assigned_interface")),
                        _stringify(row.get("vrf")),
                        _stringify(row.get("vpn_instance")),
                        _stringify(row.get("source_interface")),
                        _stringify(row.get("source_vrf")),
                        _stringify(row.get("object_key")),
                    ],
                )
            )
            detections = _extract_text_values(detection_source)

        item = {
            "device": row_device or device,
            "object_type": _stringify(row.get("object_type")),
            "object_key": object_key,
            "responsible_team": _team_label(team_slug),
            "responsible_team_slug": team_slug,
            "missing_fields": missing_fields,
            "current_status": current_status,
            "safe_item_id": _safe_item_id(row_device or device, object_key),
            "updated_at": _stringify(current_row.get("updated_at")),
            "updated_by": _stringify(current_row.get("updated_by")),
            "csv_status": _stringify(current_row.get("status")),
            "tenant": _stringify(current_row.get("tenant")),
            "service_type": _stringify(current_row.get("service_type")),
            "criticality": _stringify(current_row.get("criticality")),
            "owner": _stringify(current_row.get("owner")),
            "evidence": _stringify(current_row.get("evidence")),
            "interface": _stringify(current_row.get("interface")),
            "vrf": _stringify(current_row.get("vrf")),
            "service_relation": _stringify(current_row.get("service_relation")),
            "remote_asn": _stringify(current_row.get("remote_asn")),
            "remote_bgp_group": _stringify(current_row.get("remote_bgp_group")),
            "policy_intent": _stringify(current_row.get("policy_intent")),
            "notes": _stringify(current_row.get("notes")),
            "relation_type": _stringify(current_row.get("relation_type")),
            "detected_interface": _stringify(current_row.get("detected_interface")) or detections.get("detected_interface", ""),
            "detected_vrf": _stringify(current_row.get("detected_vrf")) or detections.get("detected_vrf", ""),
            "status_hint": _stringify(current_row.get("status_hint")) or detections.get("status_hint", ""),
            "csv_path": str((_responses_dir(root) / _csv_filename(team_slug)).relative_to(root)),
        }
        if item["object_type"].lower() == "ip_address":
            if not item["detected_interface"] or not item["detected_vrf"]:
                item["status_hint"] = item["status_hint"] or "needs_mapping"
            else:
                item["status_hint"] = item["status_hint"] or "confirm_detected_mapping"
            if item["status_hint"] == "needs_mapping" and item["detected_interface"]:
                item["status_hint"] = "confirm_detected_mapping"
        items.append(item)

    items.sort(key=lambda row: (row["responsible_team"], row["object_type"], row["object_key"]))
    return items


def get_pending_item(device: str, safe_item_id: str) -> Dict[str, object]:
    """Return a single pending item by safe_item_id."""
    if not safe_item_id or not re.match(r"^[a-z0-9-]+-[a-f0-9]{8}$", safe_item_id):
        raise KeyError("Unknown item")

    for item in load_pending_items(device):
        if item.get("safe_item_id") == safe_item_id:
            schema = build_pending_item_schema(item)
            return {
                "item": item,
                "schema": schema,
                "team": item.get("responsible_team_slug"),
            }

    raise KeyError("Unknown item")


def build_pending_item_schema(item: Dict[str, object]) -> Dict[str, object]:
    """Build the dynamic form schema for the modal."""
    object_type = _stringify(item.get("object_type")).lower()
    team = _team_slug(_stringify(item.get("responsible_team_slug") or item.get("responsible_team")))

    fields: List[Dict[str, object]] = [
        {
            "name": "updated_by",
            "label": "Updated By",
            "type": "text",
            "required": True,
            "value": item.get("updated_by", ""),
        }
    ]
    if object_type == "subinterface" or team == "service-team":
        fields.extend([
            {"name": "tenant", "label": "Tenant", "type": "text", "required": False, "value": item.get("tenant", "")},
            {
                "name": "service_type",
                "label": "Service Type",
                "type": "select",
                "required": False,
                "choices": sorted(SERVICE_TYPES),
                "value": item.get("service_type", ""),
            },
            {
                "name": "criticality",
                "label": "Criticality",
                "type": "select",
                "required": False,
                "choices": sorted(CRITICALITIES),
                "value": item.get("criticality", ""),
            },
            {"name": "owner", "label": "Owner", "type": "text", "required": False, "value": item.get("owner", "")},
            {"name": "evidence", "label": "Evidence", "type": "textarea", "required": False, "value": item.get("evidence", "")},
            {"name": "notes", "label": "Notes", "type": "textarea", "required": False, "value": item.get("notes", "")},
            {
                "name": "status",
                "label": "Status",
                "type": "select",
                "required": True,
                "choices": MODAL_STATUS_CHOICES,
                "value": item.get("current_status", "answered"),
            },
        ])
    elif object_type == "ip_address" or team == "network-ops":
        detected_interface = _stringify(item.get("detected_interface"))
        detected_vrf = _stringify(item.get("detected_vrf"))
        fields.extend([
            {"name": "ip_address", "label": "IP Address", "type": "text", "required": False, "readonly": True, "value": item.get("object_key", "")},
            {"name": "detected_interface", "label": "Detected Interface", "type": "text", "required": False, "readonly": True, "value": detected_interface},
            {"name": "detected_vrf", "label": "Detected VRF", "type": "text", "required": False, "readonly": True, "value": detected_vrf},
            {"name": "interface", "label": "Interface", "type": "text", "required": False, "value": item.get("interface", "") or detected_interface},
            {"name": "vrf", "label": "VRF", "type": "text", "required": False, "value": item.get("vrf", "") or detected_vrf},
            {"name": "relation_type", "label": "Relation Type", "type": "select", "required": True, "choices": RELATION_TYPE_CHOICES, "value": item.get("relation_type", "")},
            {"name": "service_relation", "label": "Service Relation", "type": "text", "required": False, "value": item.get("service_relation", ""), "help": "Required only when relation_type=service"},
            {"name": "owner", "label": "Owner", "type": "text", "required": False, "value": item.get("owner", "")},
            {"name": "evidence", "label": "Evidence", "type": "textarea", "required": False, "value": item.get("evidence", "")},
            {"name": "notes", "label": "Notes", "type": "textarea", "required": False, "value": item.get("notes", "")},
            {
                "name": "status",
                "label": "Status",
                "type": "select",
                "required": True,
                "choices": MODAL_STATUS_CHOICES,
                "value": item.get("current_status", "answered"),
            },
        ])
    else:
        fields.extend([
            {"name": "remote_asn", "label": "Remote ASN", "type": "number", "required": False, "value": item.get("remote_asn", "")},
            {
                "name": "remote_bgp_group",
                "label": "Remote BGP Group",
                "type": "text",
                "required": False,
                "value": item.get("remote_bgp_group", ""),
            },
            {"name": "policy_intent", "label": "Policy Intent", "type": "textarea", "required": False, "value": item.get("policy_intent", "")},
            {"name": "owner", "label": "Owner", "type": "text", "required": False, "value": item.get("owner", "")},
            {
                "name": "criticality",
                "label": "Criticality",
                "type": "select",
                "required": False,
                "choices": sorted(CRITICALITIES),
                "value": item.get("criticality", ""),
            },
            {"name": "evidence", "label": "Evidence", "type": "textarea", "required": False, "value": item.get("evidence", "")},
            {"name": "notes", "label": "Notes", "type": "textarea", "required": False, "value": item.get("notes", "")},
            {
                "name": "status",
                "label": "Status",
                "type": "select",
                "required": True,
                "choices": MODAL_STATUS_CHOICES,
                "value": item.get("current_status", "answered"),
            },
        ])

    return {
        "team": team,
        "object_type": object_type,
        "fields": fields,
        "status_choices": MODAL_STATUS_CHOICES,
        "relation_type_choices": RELATION_TYPE_CHOICES,
    }


def update_edit_audit_log(
    team: str,
    object_key: str,
    fields_changed: List[str],
    status: str,
    reports_root: Path,
) -> Tuple[bool, str]:
    """Compatibility wrapper for older audit log references."""
    try:
        audit_dir = _audit_dir(reports_root)
        log_file = audit_dir / "edit-audit-log.md"
        entry = f"""## {_utc_now()}

- Team: {_team_slug(team)}
- Object: {object_key}
- Fields Changed: {', '.join(fields_changed)}
- Validation: {status}
- Source: webui_form

"""
        with log_file.open("a", encoding="utf-8") as handle:
            handle.write(entry)
        return True, str(log_file)
    except Exception as exc:
        return False, str(exc)


def load_response_csv(team: str, reports_root: Path) -> List[Dict[str, str]]:
    """Compatibility helper used by older code paths."""
    csv_path = _responses_dir(reports_root) / _csv_filename(team)
    return _load_csv_rows(csv_path)


def get_latest_response(team: str, reports_root: Path) -> Optional[Dict[str, str]]:
    """Compatibility helper used by older code paths."""
    rows = load_response_csv(team, reports_root)
    return rows[-1] if rows else None
