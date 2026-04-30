#!/usr/bin/env python3
"""FASE 4.38 — Cycle-002 Week 1 local response seed."""

from __future__ import annotations

import argparse
import csv
import json
import re
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tools.local.controlled_cycle_week1_common import (
    TEAM_LABELS,
    classify_record,
    contains_blocked_terms,
    object_key_is_safe,
    normalize_object_type,
    normalize_team,
    _clean,
    detect_secret_hits,
)
from webui.services.controlled_operation import load_json_safe
from webui.services.response_forms import CSV_HEADER
from webui.services.validators import (
    validate_bgp_response,
    validate_ip_response,
    validate_subinterface_response,
)


def _load_template_rows(cycle_dir: Path) -> List[Dict[str, str]]:
    template = cycle_dir.parent.parent / "pilot-device-compliance" / "week1-metadata-collection-template.csv"
    rows: List[Dict[str, str]] = []
    if not template.exists():
        return rows
    with template.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row:
                rows.append({k: (v or "").strip() for k, v in row.items()})
    return rows


def _safe_item_id(device: str, object_key: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", object_key.lower()).strip("-")
    digest = hashlib.sha1(f"{device}:{object_key}".encode("utf-8")).hexdigest()[:8]
    return f"{base[:48] or 'item'}-{digest}"


def _team_slug(team: str) -> str:
    normalized = (team or "").strip().lower().replace("_", "-")
    if "service" in normalized:
        return "service-team"
    if "network" in normalized or "ops" in normalized:
        return "network-ops"
    if "bgp" in normalized:
        return "bgp-team"
    return normalized or "unknown-team"


def _csv_filename(team_slug: str) -> str:
    return {
        "service-team": "service-team-response.csv",
        "network-ops": "network-ops-response.csv",
        "bgp-team": "bgp-team-response.csv",
    }.get(team_slug, f"{team_slug}-response.csv")


def _responses_dir(cycle_dir: Path) -> Path:
    responses_dir = cycle_dir / "week1" / "responses"
    responses_dir.mkdir(parents=True, exist_ok=True)
    return responses_dir


def _audit_dir(cycle_dir: Path) -> Path:
    audit_dir = cycle_dir / "week1" / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    return audit_dir


def _load_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    rows: List[Dict[str, str]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append({k: (v or "").strip() for k, v in row.items()})
    return rows


def _write_response_row(cycle_dir: Path, team_slug: str, row: Dict[str, str]) -> Path:
    responses_dir = _responses_dir(cycle_dir)
    csv_path = responses_dir / _csv_filename(team_slug)
    rows = _load_csv_rows(csv_path)
    replaced = False
    for idx, existing in enumerate(rows):
        if existing.get("object_key") == row["object_key"]:
            rows[idx] = row
            replaced = True
            break
    if not replaced:
        rows.append(row)

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_HEADER, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return csv_path


def _append_audit(cycle_dir: Path, team_slug: str, item: Dict[str, str], payload: Dict[str, str], issues: List[str]) -> Path:
    audit_path = _audit_dir(cycle_dir) / f"{team_slug}-response-audit.json"
    entries: List[Dict[str, Any]] = []
    if audit_path.exists():
        try:
            loaded = json.loads(audit_path.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                entries = loaded
        except Exception:
            entries = []

    entries.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cycle_id": "cycle-002",
        "device": item.get("device", ""),
        "device_id": item.get("device_id", ""),
        "team": team_slug,
        "object_type": item.get("object_type", ""),
        "object_key": item.get("object_key", ""),
        "updated_by": payload.get("updated_by", ""),
        "response_status": payload.get("status", ""),
        "changed_fields": [
            field for field in CSV_HEADER
            if field not in {"updated_at"} and (str(item.get(field, "")).strip() != str(payload.get(field, "")).strip())
        ],
        "validation_result": {
            "valid": not issues,
            "issues": issues,
        },
    })
    audit_path.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")
    return audit_path


def _resolve_scope_item(cycle_dir: Path, team_slug: str, object_type: str, object_key: str) -> Dict[str, str]:
    template_rows = _load_template_rows(cycle_dir)
    for row in template_rows:
        row_team = _team_slug(row.get("responsible_team", ""))
        row_type = normalize_object_type(row.get("object_type"), row_team, row.get("source_name", ""))
        if row_team == team_slug and row_type == object_type and row.get("object_key") == object_key:
            return {
                "device": row.get("device", ""),
                "device_id": "1890",
                "responsible_team": row.get("responsible_team", ""),
                "responsible_team_slug": row_team,
                "object_type": object_type,
                "object_key": object_key,
            }
    raise KeyError("object_key outside scope")


def _validate_payload(object_type: str, payload: Dict[str, str]) -> tuple[bool, List[str]]:
    if contains_blocked_terms(json.dumps(payload, sort_keys=True)):
        return False, ["blocked keyword found"]

    if object_type == "subinterface":
        return validate_subinterface_response(payload)
    if object_type == "ip_address":
        return validate_ip_response(payload)
    if object_type == "bgp_peer":
        return validate_bgp_response(payload)
    return False, [f"unsupported object_type: {object_type}"]


def _build_row(item: Dict[str, str], payload: Dict[str, str]) -> Dict[str, str]:
    row = {field: "" for field in CSV_HEADER}
    row["device"] = item.get("device", "")
    row["object_type"] = item.get("object_type", "")
    row["object_key"] = item.get("object_key", "")
    row["responsible_team"] = item.get("responsible_team", "")
    for field in CSV_HEADER:
        if field in {"device", "object_type", "object_key", "responsible_team", "updated_at"}:
            continue
        row[field] = str(payload.get(field, "") or "").strip()
    row["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return row


def _summary_for_cycle(cycle_dir: Path) -> Dict[str, Any]:
    responses_dir = _responses_dir(cycle_dir)
    items: List[Dict[str, Any]] = []
    for csv_path in sorted(responses_dir.glob("*.csv")):
        team_slug = _team_slug(csv_path.stem)
        rows = _load_csv_rows(csv_path)
        for row in rows:
            record = dict(row)
            record["team"] = team_slug
            classification, issues, _ = classify_record(record)
            items.append({
                "team": team_slug,
                "object_key": row.get("object_key", ""),
                "object_type": row.get("object_type", ""),
                "status": row.get("status", ""),
                "classification": classification,
                "issues": issues,
                "source_file": csv_path.name,
            })
    team_counts = {
        team: sum(1 for item in items if item["team"] == team)
        for team in ("service", "network_ops", "bgp")
    }
    valid_count = sum(1 for item in items if item["classification"] in {"validated", "ready_for_week2_review"})
    if valid_count == 0:
        decision = "WEEK1_RESPONSE_BLOCKED"
    elif len(team_counts) == 3 and all(team_counts.values()):
        decision = "WEEK1_RESPONSE_READY"
    else:
        decision = "WEEK1_RESPONSE_READY_WITH_RESTRICTIONS"
    return {
        "decision": decision,
        "team_counts": team_counts,
        "items": items,
        "valid_count": valid_count,
        "responses_dir": str(responses_dir),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="FASE 4.38 — Cycle-002 Week 1 Response Seed")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--cycle-dir", type=Path, required=True)
    parser.add_argument("--team", required=True)
    parser.add_argument("--object-type", required=True)
    parser.add_argument("--object-key", required=True)
    parser.add_argument("--response-status", required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--notes", required=True)
    parser.add_argument("--updated-by", default="uat")
    parser.add_argument("--tenant", default="")
    parser.add_argument("--service-type", default="")
    parser.add_argument("--criticality", default="")
    parser.add_argument("--interface", default="")
    parser.add_argument("--vrf", default="")
    parser.add_argument("--relation-type", default="")
    parser.add_argument("--service-relation", default="")
    parser.add_argument("--remote-asn", default="")
    parser.add_argument("--remote-bgp-group", default="")
    parser.add_argument("--policy-intent", default="")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    cycle_dir = args.cycle_dir
    scope_file = cycle_dir / "CYCLE-002-SCOPE.json"
    status_file = cycle_dir / "CYCLE-002-STATUS.md"
    week1_status_file = cycle_dir / "week1" / "CYCLE-002-WEEK1-STATUS.md"

    blockers: List[str] = []
    if args.cycle_id != "cycle-002":
        blockers.append("cycle_id must be cycle-002")
    if args.device != "4WNET-MNS-KTG-RX":
        blockers.append("device mismatch")
    if str(args.device_id) != "1890":
        blockers.append("device_id mismatch")
    if not scope_file.exists():
        blockers.append("scope missing")

    team_slug = _team_slug(args.team)
    object_type = normalize_object_type(args.object_type, team_slug, args.object_key)
    if not object_type:
        blockers.append("invalid object_type")
    if not object_key_is_safe(args.object_key):
        blockers.append("object_key unsafe")
    if contains_blocked_terms(
        args.updated_by,
        args.owner,
        args.evidence,
        args.notes,
        args.tenant,
        args.service_type,
        args.criticality,
        args.interface,
        args.vrf,
        args.relation_type,
        args.service_relation,
        args.remote_asn,
        args.remote_bgp_group,
        args.policy_intent,
    ):
        blockers.append("blocked keyword found")

    try:
        item = _resolve_scope_item(cycle_dir, team_slug, object_type or "", args.object_key)
    except KeyError as exc:
        blockers.append(str(exc))
        item = {}

    payload = {
        "status": args.response_status,
        "owner": args.owner,
        "evidence": args.evidence,
        "notes": args.notes,
        "updated_by": args.updated_by,
        "tenant": args.tenant,
        "service_type": args.service_type,
        "criticality": args.criticality,
        "interface": args.interface,
        "vrf": args.vrf,
        "relation_type": args.relation_type,
        "service_relation": args.service_relation,
        "remote_asn": args.remote_asn,
        "remote_bgp_group": args.remote_bgp_group,
        "policy_intent": args.policy_intent,
        "object_key": args.object_key,
    }
    if object_type == "ip_address":
        payload.setdefault("relation_type", args.relation_type or "infrastructure")
    if object_type == "subinterface":
        payload.setdefault("tenant", args.tenant or "Cliente Piloto 002")
        payload.setdefault("service_type", args.service_type or "customer-internet")
        payload.setdefault("criticality", args.criticality or "gold")
    if object_type == "bgp_peer":
        payload.setdefault("remote_asn", args.remote_asn or "65000")
        payload.setdefault("remote_bgp_group", args.remote_bgp_group or "UAT-GROUP")
        payload.setdefault("policy_intent", args.policy_intent or "UAT policy intent for peer validation")
        payload.setdefault("criticality", args.criticality or "silver")

    valid = False
    issues: List[str] = []
    if not blockers and item:
        valid, issues = _validate_payload(object_type or "", payload)
        if not valid:
            blockers.extend(issues)

    responses_dir = cycle_dir / "week1" / "responses"
    audit_dir = cycle_dir / "week1" / "audit"
    responses_dir.mkdir(parents=True, exist_ok=True)
    audit_dir.mkdir(parents=True, exist_ok=True)

    csv_path = None
    audit_path = None
    if not blockers and item:
        row = _build_row(item, payload)
        csv_path = _write_response_row(cycle_dir, team_slug, row)
        audit_path = _append_audit(cycle_dir, team_slug, item, payload, issues)

    summary = _summary_for_cycle(cycle_dir)
    decision = summary["decision"] if not blockers else "WEEK1_RESPONSE_BLOCKED"
    if blockers and csv_path is None:
        csv_path = responses_dir / _csv_filename(team_slug)
    report_path = args.output_dir / "CYCLE-002-WEEK1-RESPONSE-SEED.md"
    json_path = args.output_dir / "cycle-002-week1-response-seed.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    report_lines = [
        f"# {args.cycle_id.upper()} — Week 1 Response Seed",
        "",
        "## 1. Decision",
        f"**{decision}**",
        "",
        "## 2. Seeded Response",
        f"- Team: {item.get('responsible_team', args.team) if item else args.team}",
        f"- Object Type: {object_type}",
        f"- Object Key: {args.object_key}",
        f"- Status: {args.response_status}",
        f"- Updated By: {args.updated_by}",
        f"- CSV: {csv_path.relative_to(cycle_dir.parent.parent) if csv_path and csv_path.exists() else 'n/a'}",
        f"- Audit: {audit_path.relative_to(cycle_dir.parent.parent) if audit_path and audit_path.exists() else 'n/a'}",
        "",
        "## 3. Current Response State",
        f"- Valid items: {summary['valid_count']}",
        f"- Service files: {summary['team_counts']['service']}",
        f"- Network Ops files: {summary['team_counts']['network_ops']}",
        f"- BGP files: {summary['team_counts']['bgp']}",
        "",
        "## 4. Next Step",
        "Re-run Week 1 intake and validation.",
        "",
        "---",
        f"**Device:** {args.device}",
        f"**Device ID:** {args.device_id}",
        f"**Sensitive hits:** {len(detect_secret_hits(responses_dir))}",
    ]
    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    output = {
        "cycle_id": args.cycle_id,
        "device": args.device,
        "device_id": args.device_id,
        "team": team_slug,
        "object_type": object_type,
        "object_key": args.object_key,
        "decision": decision,
        "blocked": blockers,
        "validated": valid,
        "issues": issues,
        "csv_path": str(csv_path.relative_to(cycle_dir.parent.parent)) if csv_path and csv_path.exists() else None,
        "audit_path": str(audit_path.relative_to(cycle_dir.parent.parent)) if audit_path and audit_path.exists() else None,
        "summary": summary,
        "sensitive_hits": detect_secret_hits(responses_dir),
    }
    json_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    if not blockers:
        status_value = "WEEK1_RESPONSE_READY" if decision == "WEEK1_RESPONSE_READY" else "WEEK1_RESPONSE_READY_WITH_RESTRICTIONS"
    else:
        status_value = "WEEK1_RESPONSE_BLOCKED"

    status_md = [
        f"# {args.cycle_id.upper()} — Week 1 Status",
        "",
        "## Status Atual",
        status_value,
        "",
        "## Summary",
        f"- Response ready: {summary['decision']}",
        f"- Service files: {summary['team_counts']['service']}",
        f"- Network Ops files: {summary['team_counts']['network_ops']}",
        f"- BGP files: {summary['team_counts']['bgp']}",
        f"- Sensitive hits: {len(detect_secret_hits(responses_dir))}",
        "",
        "## Next Step",
        "Re-run intake and validation.",
    ]
    week1_status_file.parent.mkdir(parents=True, exist_ok=True)
    week1_status_file.write_text("\n".join(status_md), encoding="utf-8")

    status_file.write_text(
        "\n".join(
            [
                f"# {args.cycle_id.upper()} — Status do Ciclo",
                "",
                "## Status Atual",
                status_value,
                "",
                "## Gate",
                f"- Decision: {decision}",
                f"- Reason: Week 1 response seed evaluated",
                f"- Previous cycle: cycle-001",
                f"- Checked at: {datetime.now(timezone.utc).isoformat()}",
                "",
                "## Guardrails",
                f"- Scope: {'present' if scope_file.exists() else 'missing'}",
                f"- Responses dir: {'present' if responses_dir.exists() else 'missing'}",
                f"- Audit dir: {'present' if audit_dir.exists() else 'missing'}",
            ]
        ),
        encoding="utf-8",
    )

    print(f"✓ Week 1 response seed decision: {decision}")
    print(f"✓ Report: {report_path}")
    print(f"✓ JSON: {json_path}")
    return 0 if decision != "WEEK1_RESPONSE_BLOCKED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
