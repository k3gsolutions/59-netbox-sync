#!/usr/bin/env python3
"""FASE 4.37 — Controlled Operation Cycle Week 1 Validation (v2)."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tools.local.controlled_cycle_week1_common import (
    EXPECTED_TEAMS,
    TEAM_LABELS,
    classify_record,
    contains_blocked_terms,
    detect_secret_hits,
    load_response_items,
    normalize_team,
    object_key_is_safe,
)
from webui.services.controlled_operation import load_json_safe
from webui.services.validators import validate_status


def _load_policy_registry(policy_dir: Path) -> bool:
    if not policy_dir.exists():
        return False
    required = [
        "discovery-elements.yaml",
        "dependency-map.yaml",
        "naming-conventions.yaml",
        "snmp-policy.yaml",
        "interface-policy.yaml",
        "vrf-policy.yaml",
        "bgp-policy.yaml",
        "route-policy-policy.yaml",
        "ip-prefix-policy.yaml",
        "community-policy.yaml",
        "as-path-policy.yaml",
        "comments-policy.yaml",
        "compliance-severity-policy.yaml",
    ]
    return all((policy_dir / name).exists() for name in required)


def _validate_record(record: Dict[str, Any]) -> tuple[str, List[str]]:
    status = str(record.get("status") or "").strip()
    status_ok, status_error = validate_status(status)
    issues: List[str] = []
    if not status_ok:
        issues.append(status_error or "status invalid")
        return "blocked", issues

    classification, record_issues, _ = classify_record(record)
    issues.extend(record_issues)

    if contains_blocked_terms(record.get("notes"), record.get("evidence"), record.get("owner")):
        issues.append("blocked keyword found")
    if not object_key_is_safe(record.get("object_key", "")):
        issues.append("object_key unsafe")

    if classification in {"blocked", "rejected"}:
        return classification, issues
    if classification == "needs_clarification":
        return "needs_clarification", issues
    if status == "validated" and not issues:
        return "validated", issues
    if not issues:
        return "ready_for_week2_review", issues
    return "needs_clarification", issues


def main() -> int:
    parser = argparse.ArgumentParser(description="FASE 4.37 — Cycle Week 1 Validation")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--cycle-dir", type=Path, required=True)
    parser.add_argument("--responses-dir", type=Path, required=True)
    parser.add_argument("--policy-registry", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()

    scope_file = args.cycle_dir / f"{args.cycle_id.upper()}-SCOPE.json"
    status_file = args.cycle_dir / f"{args.cycle_id.upper()}-STATUS.md"
    week1_dir = args.cycle_dir / "week1"
    week1_status_file = week1_dir / f"{args.cycle_id.upper()}-WEEK1-STATUS.md"
    policy_ready = _load_policy_registry(args.policy_registry)
    scope = load_json_safe(scope_file) if scope_file.exists() else {}
    max_items = int(scope.get("max_items") or 3)
    items = load_response_items(args.responses_dir)

    validated: List[Dict[str, Any]] = []
    ready_for_week2_review: List[Dict[str, Any]] = []
    needs_clarification: List[Dict[str, Any]] = []
    blocked: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    still_pending: List[Dict[str, Any]] = []
    per_team = {team: {"total": 0, "validated": 0, "pending": 0, "clarification": 0, "blocked": 0, "rejected": 0} for team in EXPECTED_TEAMS}

    if not items:
        still_pending.extend(
            {
                "team": team,
                "object_key": f"cycle-002-{team}",
                "object_type": "n/a",
                "reason": "no response file",
            }
            for team in EXPECTED_TEAMS
        )

    for record in items:
        team = normalize_team(record.get("team"), record.get("source_name", ""))
        if team not in per_team:
            blocked.append({
                "team": team or "unknown",
                "object_key": record.get("object_key") or "unknown",
                "object_type": record.get("object_type") or "unknown",
                "reason": "team outside scope",
            })
            continue

        per_team[team]["total"] += 1
        classification, issues = _validate_record(record)
        row = {
            "team": team,
            "object_key": record.get("object_key") or record.get("item_id") or "unknown",
            "object_type": record.get("object_type") or "unknown",
            "status": classification,
            "updated_by": record.get("updated_by") or "unknown",
            "updated_at": record.get("updated_at") or record.get("reviewed_at") or "unknown",
            "evidence": record.get("evidence") or "",
            "notes": record.get("notes") or "",
            "source_file": record.get("source_name"),
            "issues": issues,
        }
        if classification == "validated":
            validated.append(row)
            per_team[team]["validated"] += 1
        elif classification == "ready_for_week2_review":
            ready_for_week2_review.append(row)
            per_team[team]["validated"] += 1
        elif classification == "needs_clarification":
            needs_clarification.append(row)
            per_team[team]["clarification"] += 1
        elif classification == "blocked":
            blocked.append(row)
            per_team[team]["blocked"] += 1
        elif classification == "rejected":
            rejected.append(row)
            per_team[team]["rejected"] += 1
        else:
            still_pending.append(row)
            per_team[team]["pending"] += 1

    total_items = len(validated) + len(ready_for_week2_review) + len(needs_clarification) + len(blocked) + len(rejected) + len(still_pending)
    if blocked or rejected:
        decision = "WEEK1_VALIDATION_BLOCKED"
    elif validated or ready_for_week2_review:
        if needs_clarification or still_pending:
            decision = "WEEK1_VALIDATION_PASSED_WITH_RESTRICTIONS"
        else:
            decision = "WEEK1_VALIDATION_PASSED"
    else:
        decision = "WEEK1_VALIDATION_BLOCKED"

    now = datetime.now(timezone.utc).isoformat()
    report_lines = [
        f"# {args.cycle_id.upper()} — Week 1 Validation",
        "",
        "## 1. Decision",
        f"**{decision}**",
        "",
        "## 2. Resumo",
        "",
        f"- Total: {total_items}",
        f"- Validadas: {len(validated)}",
        f"- Prontas para revisão da Semana 2: {len(ready_for_week2_review)}",
        f"- Precisam de esclarecimento: {len(needs_clarification)}",
        f"- Bloqueadas: {len(blocked)}",
        f"- Rejeitadas: {len(rejected)}",
        f"- Ainda pendentes: {len(still_pending)}",
        f"- Registry ready: {policy_ready}",
        "",
        "## 3. Resultado por Time",
        "",
        "| Time | Total | Validadas | Pendentes | Esclarecimento | Bloqueadas | Rejeitadas |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for team in EXPECTED_TEAMS:
        report_lines.append(
            f"| {TEAM_LABELS[team]} | {per_team[team]['total']} | {per_team[team]['validated']} | {per_team[team]['pending']} | {per_team[team]['clarification']} | {per_team[team]['blocked']} | {per_team[team]['rejected']} |"
        )

    report_lines.extend([
        "",
        "## 4. Itens prontos para Semana 2",
        "",
        "| Object Type | Object Key | Time | Responsável | Evidência | Status |",
        "|---|---|---|---|---|---|",
    ])
    for row in validated + ready_for_week2_review:
        report_lines.append(
            f"| {row['object_type']} | {row['object_key']} | {TEAM_LABELS[row['team']]} | {row['updated_by']} | {row['evidence']} | {row['status']} |"
        )
    if not (validated or ready_for_week2_review):
        report_lines.append("| - | - | - | - | - | - |")

    report_lines.extend([
        "",
        "## 5. Itens que não avançam",
        "",
        "| Object Type | Object Key | Motivo | Próxima ação |",
        "|---|---|---|---|",
    ])
    for row in needs_clarification + blocked + rejected + still_pending:
        reason = "; ".join(row.get("issues", [])) if row.get("issues") else row.get("reason", "pending")
        next_action = "Responder" if row in still_pending else "Corrigir" if row in needs_clarification else "Bloqueado" if row in blocked else "Revisar" if row in rejected else "Verificar"
        report_lines.append(
            f"| {row['object_type']} | {row['object_key']} | {reason} | {next_action} |"
        )
    if not (needs_clarification or blocked or rejected or still_pending):
        report_lines.append("| - | - | - | - |")

    report_lines.extend([
        "",
        "## 6. Próximo passo",
        "",
        "Preparar Week 2 review board." if decision != "WEEK1_VALIDATION_BLOCKED" else "Resolver bloqueios antes de preparar Week 2.",
        "",
        "---",
        "",
        f"**Device:** {args.device}",
        f"**Device ID:** {args.device_id}",
        f"**Policy registry:** {args.policy_registry}",
        f"**Generated at:** {now}",
    ])
    report = "\n".join(report_lines)

    output_json = {
        "cycle_id": args.cycle_id,
        "device": args.device,
        "device_id": args.device_id,
        "decision": decision,
        "generated_at": now,
        "policy_registry": str(args.policy_registry),
        "summary": {
            "total": total_items,
            "validated": len(validated),
            "ready_for_week2_review": len(ready_for_week2_review),
            "needs_clarification": len(needs_clarification),
            "blocked": len(blocked),
            "rejected": len(rejected),
            "still_pending": len(still_pending),
        },
        "validated": validated,
        "ready_for_week2_review": ready_for_week2_review,
        "needs_clarification": needs_clarification,
        "blocked": blocked,
        "rejected": rejected,
        "still_pending": still_pending,
        "policy_ready": policy_ready,
        "sensitive_hits": detect_secret_hits(args.responses_dir),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(output_json, indent=2), encoding="utf-8")

    if week1_status_file.exists():
        week1_status_file.write_text(
            "\n".join(
                [
                    f"# {args.cycle_id.upper()} — Week 1 Status",
                    "",
                    "## Status Atual",
                    decision,
                    "",
                    "## Summary",
                    f"- Validated: {len(validated)}",
                    f"- Ready for Week 2 review: {len(ready_for_week2_review)}",
                    f"- Needs clarification: {len(needs_clarification)}",
                    f"- Blocked: {len(blocked)}",
                    f"- Rejected: {len(rejected)}",
                    f"- Still pending: {len(still_pending)}",
                    "",
                    "## Next Step",
                    "Prepare Week 2 review." if decision != "WEEK1_VALIDATION_BLOCKED" else "Resolve blockers first.",
                ]
            ),
            encoding="utf-8",
        )

    status_file.write_text(
        "\n".join(
            [
                f"# {args.cycle_id.upper()} — Status do Ciclo",
                "",
                "## Status Atual",
                decision,
                "",
                "## Gate",
                f"- Decision: {decision}",
                f"- Reason: Week 1 validation evaluated",
                f"- Previous cycle: cycle-001",
                f"- Checked at: {now}",
                "",
                "## Guardrails",
                f"- Scope: {'present' if scope_file.exists() else 'missing'}",
                f"- Week 1 dir: {'present' if week1_dir.exists() else 'missing'}",
                f"- Responses dir: {'present' if args.responses_dir.exists() else 'missing'}",
                f"- Audit dir: {'present' if (week1_dir / 'audit').exists() else 'missing'}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    print(f"✓ Week 1 validation decision: {decision}")
    print(f"✓ Report: {args.output}")
    print(f"✓ JSON: {args.output_json}")
    return 0 if decision != "WEEK1_VALIDATION_BLOCKED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
