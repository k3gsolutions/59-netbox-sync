#!/usr/bin/env python3
"""Build a local execution log for the real Week 1 response flow."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from webui.services.local_pipeline import parse_week1_validation_summary


REPORTS_ROOT = ROOT / "reports" / "pilot-device-compliance"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Week 1 real execution status")
    parser.add_argument("--device", required=True)
    parser.add_argument("--responses-dir", required=True)
    parser.add_argument("--validation", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def _read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _team_label(value: str) -> str:
    normalized = value.strip().lower()
    if "service" in normalized:
        return "Equipe de Serviços"
    if "network" in normalized or "ops" in normalized:
        return "Network Ops"
    if "bgp" in normalized:
        return "Equipe BGP"
    return value.strip() or "N/A"


def _team_key(value: str) -> str:
    normalized = value.strip().lower()
    if "service" in normalized:
        return "service-team"
    if "network" in normalized or "ops" in normalized:
        return "network-ops"
    if "bgp" in normalized:
        return "bgp-team"
    return normalized or "unknown"


def _active_csv_files(responses_dir: Path) -> List[Path]:
    files = []
    if not responses_dir.exists():
        return files
    for path in sorted(responses_dir.glob("*.csv")):
        if path.name.endswith(".csv"):
            files.append(path)
    return files


def _template_team_counts() -> Dict[str, int]:
    template = REPORTS_ROOT / "week1-metadata-collection-template.csv"
    counts: Dict[str, int] = defaultdict(int)
    if not template.exists():
        return {}
    with template.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            counts[_team_key(row.get("responsible_team", ""))] += 1
    return dict(counts)


def _build_rows(responses_dir: Path) -> Dict[str, List[Dict[str, str]]]:
    rows_by_team: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for csv_path in _active_csv_files(responses_dir):
        rows = _read_csv(csv_path)
        for row in rows:
            rows_by_team[_team_key(row.get("responsible_team", ""))].append(row)
    return dict(rows_by_team)


def _audit_files(responses_dir: Path) -> List[Path]:
    audit_dir = responses_dir / "audit"
    if not audit_dir.exists():
        return []
    return sorted(path for path in audit_dir.glob("*.json") if path.is_file())


def _render_report(device: str, validation_path: Path, responses_dir: Path) -> str:
    validation = parse_week1_validation_summary(validation_path)
    team_counts = _template_team_counts()
    rows_by_team = _build_rows(responses_dir)
    audit_files = _audit_files(responses_dir)

    overall_state = "em andamento"
    if validation["validated"] == 0 and validation["still_pending"] == 0 and validation["needs_clarification"] == 0 and validation["blocked"] == 0 and validation["rejected"] == 0:
        overall_state = "limpo"
    elif validation["still_pending"] == 0 and validation["needs_clarification"] == 0 and validation["blocked"] == 0 and validation["rejected"] == 0 and validation["validated"] > 0:
        overall_state = "pronto para Semana 2"
    elif validation["needs_clarification"] or validation["blocked"] or validation["rejected"]:
        overall_state = "com restrições"

    lines = [
        f"# Execução Real da Semana 1 — {device}",
        "",
        "## 1. Objetivo",
        "Registrar a execução real das respostas dos times pela Web UI.",
        "",
        "## 2. Estado inicial",
        "- GO_REAL_WEEK1_CLEAN",
        "- UAT arquivado",
        "- Pendências reais iniciadas limpas",
        "- Web UI em PT-BR",
        "- Nenhuma escrita NetBox",
        "",
        "## 3. Pendências por time",
        "",
        "| Time | Total | Respondidas | Pendentes | Status |",
        "|---|---:|---:|---:|---|",
    ]

    for team_key in ["service-team", "network-ops", "bgp-team"]:
        team_name = _team_label(team_key)
        total = team_counts.get(team_key, 0)
        responded = len(rows_by_team.get(team_key, []))
        pending = max(total - responded, 0)
        status = "em andamento" if pending else "concluído"
        lines.append(f"| {team_name} | {total} | {responded} | {pending} | {status} |")

    lines.extend(
        [
            "",
            "## 4. Respostas registradas",
            "",
            "| Data | Time | Object Type | Object Key | Status | Responsável | Evidência | Arquivo CSV |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )

    for csv_path in _active_csv_files(responses_dir):
        rows = _read_csv(csv_path)
        for row in rows:
            lines.append(
                "| {updated_at} | {team} | {object_type} | {object_key} | {status} | {updated_by} | {evidence} | {csv} |".format(
                    updated_at=row.get("updated_at", ""),
                    team=_team_label(row.get("responsible_team", "")),
                    object_type=row.get("object_type", ""),
                    object_key=row.get("object_key", ""),
                    status=row.get("status", ""),
                    updated_by=row.get("updated_by", ""),
                    evidence=row.get("evidence", ""),
                    csv=csv_path.name,
                )
            )

    lines.extend(
        [
            "",
            "## 5. Auditoria local",
            "",
            f"- CSVs gerados: {', '.join(path.name for path in _active_csv_files(responses_dir))}",
            f"- Audit JSON gerados: {', '.join(path.name for path in audit_files) if audit_files else 'nenhum'}",
            f"- Última validação local: {validation['validated']} validadas / {validation['still_pending']} ainda pendentes / {validation['needs_clarification']} precisam de esclarecimento / {validation['blocked']} bloqueadas / {validation['rejected']} rejeitadas",
            f"- Estado operacional: {overall_state}",
            "",
            "## 6. Confirmações de segurança",
            "- Nenhuma escrita NetBox.",
            "- Nenhum apply.",
            "- Nenhum /sync.",
            "- Nenhum ApprovalRecord automático.",
            "- Nenhum ApplyPlan automático.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = _parse_args()
    responses_dir = Path(args.responses_dir)
    validation_path = Path(args.validation)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(_render_report(args.device, validation_path, responses_dir), encoding="utf-8")
    print(f"✓ Execution log saved: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
