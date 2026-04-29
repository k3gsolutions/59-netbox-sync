#!/usr/bin/env python3
"""Generate final real Week 1 validation and Week 2 gate."""

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
    parser = argparse.ArgumentParser(description="Generate final real Week 1 validation")
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--validation", required=True)
    parser.add_argument("--candidates", required=True)
    parser.add_argument("--responses-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--gate-output", default=str(REPORTS_ROOT / "week2-activation-gate.md"))
    return parser.parse_args()


def _read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _team_key(value: str) -> str:
    normalized = value.strip().lower()
    if "service" in normalized:
        return "service-team"
    if "network" in normalized or "ops" in normalized:
        return "network-ops"
    if "bgp" in normalized:
        return "bgp-team"
    return normalized or "unknown"


def _team_label(value: str) -> str:
    key = _team_key(value)
    return {
        "service-team": "Equipe de Serviços",
        "network-ops": "Network Ops",
        "bgp-team": "Equipe BGP",
    }.get(key, value.strip() or "N/A")


def _template_counts() -> Dict[str, int]:
    template = REPORTS_ROOT / "week1-metadata-collection-template.csv"
    counts: Dict[str, int] = defaultdict(int)
    with template.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            counts[_team_key(row.get("responsible_team", ""))] += 1
    return dict(counts)


def _active_rows(responses_dir: Path) -> Dict[str, List[Dict[str, str]]]:
    rows: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for path in sorted(responses_dir.glob("*.csv")):
        for row in _read_csv(path):
            rows[_team_key(row.get("responsible_team", ""))].append(row)
    return dict(rows)


def _write_gate(path: Path, device: str, decision: str, summary: Dict[str, int | str], restrictions: List[str], next_step: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = [
        f"# Week 2 Activation Gate — {device}",
        "",
        f"**Generated:** {_utc_now()}",
        f"**Decision:** {decision}",
        "",
        "## Summary",
        "",
        f"- Validated: {summary.get('validated', 0)}",
        f"- Ready for Review: {summary.get('ready_for_review', 0)}",
        f"- Still Pending: {summary.get('still_pending', 0)}",
        f"- Needs Clarification: {summary.get('needs_clarification', 0)}",
        f"- Blocked: {summary.get('blocked', 0)}",
        f"- Rejected: {summary.get('rejected', 0)}",
        "",
        "## Restrictions",
        "",
    ]
    if restrictions:
        content.extend([f"- {item}" for item in restrictions])
    else:
        content.append("- Nenhuma restrição adicional.")
    content.extend(
        [
            "",
            "## Next Step",
            "",
            next_step,
            "",
            "## Safety",
            "",
            "- Local only",
            "- No NetBox writes",
            "- No ApprovalRecord auto-create",
            "- No ApplyPlan",
        ]
    )
    path.write_text("\n".join(content) + "\n", encoding="utf-8")


def _prepare_week2(device: str, validation: Path, candidates: Path, responses_dir: Path) -> bool:
    import subprocess
    import sys

    proc = subprocess.run(
        [
            sys.executable,
            "tools/local/prepare_week2_review.py",
            "--device",
            device,
            "--device-id",
            "1890",
            "--validation",
            str(validation),
            "--candidates",
            str(candidates),
            "--responses-dir",
            str(responses_dir),
            "--output-dir",
            str(REPORTS_ROOT / "week2-review"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0


def _render_report(device: str, summary: Dict[str, int | str], team_counts: Dict[str, int], rows_by_team: Dict[str, List[Dict[str, str]]], decision: str) -> str:
    lines = [
        f"# Validação Final Real da Semana 1 — {device}",
        "",
        "## 1. Resumo",
        "",
        f"- total de pendências: {summary.get('total', 0)}",
        f"- validadas: {summary.get('validated', 0)}",
        f"- ainda pendentes: {summary.get('still_pending', 0)}",
        f"- precisam de esclarecimento: {summary.get('needs_clarification', 0)}",
        f"- bloqueadas: {summary.get('blocked', 0)}",
        f"- rejeitadas: {summary.get('rejected', 0)}",
        "",
        "## 2. Resultado por time",
        "",
        "| Time | Total | Validadas | Pendentes | Esclarecimento | Bloqueadas | Rejeitadas |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]

    for key in ["service-team", "network-ops", "bgp-team"]:
        total = team_counts.get(key, 0)
        responded = len(rows_by_team.get(key, []))
        pending = max(total - responded, 0)
        # The local CSVs represent answered rows only, so validation buckets stay summary-wide.
        validation_count = responded
        clarification = 0 if responded else pending
        blocked = 0
        rejected = 0
        lines.append(
            f"| {_team_label(key)} | {total} | {validation_count} | {pending} | {clarification} | {blocked} | {rejected} |"
        )

    lines.extend(
        [
            "",
            "## 3. Itens prontos para Semana 2",
            "",
            "| Object Type | Object Key | Time | Responsável | Evidência | Status |",
            "|---|---|---|---|---|---|",
        ]
    )

    for key, rows in rows_by_team.items():
        for row in rows:
            lines.append(
                "| {object_type} | {object_key} | {team} | {owner} | {evidence} | {status} |".format(
                    object_type=row.get("object_type", ""),
                    object_key=row.get("object_key", ""),
                    team=_team_label(key),
                    owner=row.get("updated_by", row.get("owner", "")),
                    evidence=row.get("evidence", ""),
                    status=row.get("status", ""),
                )
            )

    lines.extend(
        [
            "",
            "## 4. Itens que não avançam",
            "",
            "| Object Type | Object Key | Motivo | Próxima ação |",
            "|---|---|---|---|",
        ]
    )

    if int(summary.get("still_pending", 0)) or int(summary.get("needs_clarification", 0)) or int(summary.get("blocked", 0)) or int(summary.get("rejected", 0)):
        lines.append(
            f"| pending | pending | Ainda há itens sem fechamento | Solicitar complemento/validação |"
        )
    else:
        lines.append("| none | none | Nenhum | Nenhuma |")

    lines.extend(
        [
            "",
            "## 5. Decisão",
            "",
            decision,
            "",
            "## 6. Segurança",
            "",
            "- Nenhuma escrita NetBox.",
            "- Nenhum apply.",
            "- Nenhum /sync.",
            "- Nenhum ApprovalRecord automático.",
            "- Nenhum ApplyPlan criado.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = _parse_args()
    device = args.device
    validation = Path(args.validation)
    candidates = Path(args.candidates)
    responses_dir = Path(args.responses_dir)
    output = Path(args.output)
    gate_output = Path(args.gate_output)

    summary = parse_week1_validation_summary(validation)
    team_counts = _template_counts()
    rows_by_team = _active_rows(responses_dir)

    if summary["validated"] > 0 and summary["still_pending"] == 0 and summary["needs_clarification"] == 0 and summary["blocked"] == 0 and summary["rejected"] == 0:
        decision = "GO_WEEK2_REVIEW"
        next_step = "Semana 2 liberada para revisão humana."
        restrictions: List[str] = []
    elif summary["validated"] > 0:
        decision = "GO_WEEK2_REVIEW_WITH_RESTRICTIONS"
        next_step = "Semana 2 preparada com restrições. Revisar pendências antes de aprovar qualquer item."
        restrictions = [
            "Há itens pendentes ou com restrição.",
            "Revisão humana continua obrigatória.",
        ]
    else:
        decision = "NO_GO_WEEK2_REVIEW"
        next_step = "Não foi possível avançar. Nenhum item está pronto para revisão."
        restrictions = [
            "Nenhum item validado.",
            "Aguardar novas respostas.",
        ]

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(_render_report(device, summary, team_counts, rows_by_team, decision), encoding="utf-8")
    _write_gate(gate_output, device, decision, summary, restrictions, next_step)

    week2_prepared = False
    if decision != "NO_GO_WEEK2_REVIEW":
        week2_prepared = _prepare_week2(device, validation, candidates, responses_dir)

    print(f"✓ Final validation saved: {output}")
    print(f"✓ Activation gate saved: {gate_output}")
    print(f"✓ Week 2 prepared: {'yes' if week2_prepared else 'no'}")
    print(f"✓ Decision: {decision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
