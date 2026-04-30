#!/usr/bin/env python3
"""FASE 4.36 — Controlled Operation Cycle Week 1 Response Intake (v2)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tools.local.controlled_cycle_week1_common import (
    EXPECTED_TEAMS,
    TEAM_LABELS,
    classify_by_team,
    classify_record,
    detect_secret_hits,
    load_response_items,
    normalize_team,
)
from webui.services.controlled_operation import load_json_safe


def _records_by_team(items: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    bucket = {team: [] for team in EXPECTED_TEAMS}
    for item in items:
        team = normalize_team(item.get("team"), item.get("source_name", ""))
        if team in bucket:
            bucket[team].append(item)
    return bucket


def main() -> int:
    parser = argparse.ArgumentParser(description="FASE 4.36 — Cycle Week 1 Response Intake")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--cycle-dir", type=Path, required=True)
    parser.add_argument("--responses-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()

    scope_file = args.cycle_dir / f"{args.cycle_id.upper()}-SCOPE.json"
    status_file = args.cycle_dir / f"{args.cycle_id.upper()}-STATUS.md"
    week1_dir = args.cycle_dir / "week1"
    week1_status_file = week1_dir / f"{args.cycle_id.upper()}-WEEK1-STATUS.md"

    scope = load_json_safe(scope_file) if scope_file.exists() else {}
    expected_max_items = int(scope.get("max_items") or 3)
    responses = load_response_items(args.responses_dir)
    by_team = _records_by_team(responses)
    team_rows = {team: [] for team in EXPECTED_TEAMS}
    team_status = {team: "still_pending" for team in EXPECTED_TEAMS}
    team_details = {team: {"file_count": 0, "issues": [], "records": []} for team in EXPECTED_TEAMS}

    for team in EXPECTED_TEAMS:
        team_records = by_team.get(team, [])
        team_details[team]["file_count"] = len(team_records)
        if not team_records:
            continue

        valid_records = []
        issues: List[str] = []
        for record in team_records:
            classification, record_issues, _ = classify_record(record)
            team_rows[team].append({
                "object_key": record.get("object_key") or record.get("item_id") or "unknown",
                "object_type": record.get("object_type") or "unknown",
                "status": classification,
                "source_file": record.get("source_name"),
            })
            if classification in {"blocked", "rejected"}:
                issues.extend(record_issues)
            elif classification == "needs_clarification":
                issues.extend(record_issues)
            else:
                valid_records.append(record)
                team_status[team] = "responded"
        if issues:
            team_status[team] = "missing_required_fields" if any("required" in issue.lower() or "missing" in issue.lower() for issue in issues) else "invalid_format"
        if not team_records:
            team_status[team] = "still_pending"
        team_details[team]["issues"] = issues
        team_details[team]["records"] = valid_records

    responded = sum(1 for team in EXPECTED_TEAMS if team_status[team] == "responded")
    invalid = sum(1 for team in EXPECTED_TEAMS if team_status[team] == "invalid_format")
    missing = sum(1 for team in EXPECTED_TEAMS if team_status[team] == "missing_required_fields")
    still_pending = sum(1 for team in EXPECTED_TEAMS if team_status[team] == "still_pending")

    if still_pending == 0 and invalid == 0 and missing == 0:
        decision = "WEEK1_INTAKE_READY"
    elif responded > 0:
        decision = "WEEK1_INTAKE_PARTIAL"
    else:
        decision = "WEEK1_INTAKE_BLOCKED"

    now = datetime.now(timezone.utc).isoformat()
    report_lines = [
        f"# {args.cycle_id.upper()} — Week 1 Response Intake",
        "",
        "## 1. Decision",
        f"**{decision}**",
        "",
        "## 2. Team Intake",
        "",
        "| Time | Status | Arquivos | Observações |",
        "|---|---|---:|---|",
    ]
    for team in EXPECTED_TEAMS:
        notes = "; ".join(team_details[team]["issues"]) if team_details[team]["issues"] else "ok"
        report_lines.append(
            f"| {TEAM_LABELS[team]} | {team_status[team]} | {team_details[team]['file_count']} | {notes} |"
        )

    report_lines.extend([
        "",
        "## 3. Respostas Localizadas",
        "",
    ])
    for team in EXPECTED_TEAMS:
        report_lines.append(f"### {TEAM_LABELS[team]}")
        if team_rows[team]:
            report_lines.append("| Object Key | Object Type | Status | Arquivo |")
            report_lines.append("|---|---|---|---|")
            for row in team_rows[team]:
                report_lines.append(
                    f"| {row['object_key']} | {row['object_type']} | {row['status']} | {row['source_file']} |"
                )
        else:
            report_lines.append("- Nenhuma resposta localizada.")
        report_lines.append("")

    report_lines.extend([
        "## 4. Próximo passo",
        "",
        "Responder itens restantes." if decision != "WEEK1_INTAKE_READY" else "Avançar para validação Week 1.",
        "",
        "---",
        "",
        f"**Device:** {args.device}",
        f"**Device ID:** {args.device_id}",
        f"**Total responses:** {len(responses)}",
        f"**Expected max items:** {expected_max_items}",
        f"**Generated at:** {now}",
    ])
    report = "\n".join(report_lines)

    output_json = {
        "cycle_id": args.cycle_id,
        "device": args.device,
        "device_id": args.device_id,
        "decision": decision,
        "evaluated_at": now,
        "expected_max_items": expected_max_items,
        "summary": {
            "responded": responded,
            "still_pending": still_pending,
            "invalid_format": invalid,
            "missing_required_fields": missing,
            "total_teams": len(EXPECTED_TEAMS),
        },
        "teams": {
            team: {
                "status": team_status[team],
                "file_count": team_details[team]["file_count"],
                "issues": team_details[team]["issues"],
                "records": team_rows[team],
            }
            for team in EXPECTED_TEAMS
        },
        "responses_dir": str(args.responses_dir),
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
                    f"- Responded: {responded}",
                    f"- Still pending: {still_pending}",
                    f"- Invalid format: {invalid}",
                    f"- Missing required fields: {missing}",
                    "",
                    "## Next Step",
                    "Proceed to validation." if decision != "WEEK1_INTAKE_BLOCKED" else "Resolve blockers first.",
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
                f"- Reason: Week 1 response intake evaluated",
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

    print(f"✓ Week 1 intake decision: {decision}")
    print(f"✓ Report: {args.output}")
    print(f"✓ JSON: {args.output_json}")
    return 0 if decision != "WEEK1_INTAKE_BLOCKED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
