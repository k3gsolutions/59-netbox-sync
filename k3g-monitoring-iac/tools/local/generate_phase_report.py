#!/usr/bin/env python3
"""Gera um relatório resumido da fase atual.

Agrega informações do ROADMAP, PHASE0_BASELINE, context/NEXT_ACTIONS e
context/CURRENT_STATE para produzir um relatório Markdown em `reports/`.
Não executa automações externas e opera apenas com a biblioteca padrão.

Uso típico:
    python3 tools/local/generate_phase_report.py --phase 0
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

DEFAULT_OUTPUT_DIR = Path("reports")
ROADMAP_PATH = Path("ROADMAP.md")
BASELINE_PATH = Path("PHASE0_BASELINE.md")
NEXT_ACTIONS_PATH = Path("context/NEXT_ACTIONS.md")
CURRENT_STATE_PATH = Path("context/CURRENT_STATE.md")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gerar relatório de fase")
    parser.add_argument(
        "--phase",
        type=int,
        default=0,
        help="Número da fase (padrão: 0)",
    )
    parser.add_argument(
        "--output",
        help="Arquivo de saída opcional. Se omitido, cria em reports/phase<fase>-report.md",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Exibir informações adicionais",
    )
    return parser.parse_args()


def read_lines(path: Path) -> List[str]:
    if not path.exists():
        return []
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []


def parse_roadmap_status(phase: int, lines: List[str]) -> Tuple[str, str]:
    token = f"Fase {phase}"
    for line in lines:
        if token in line:
            cells = [cell.strip() for cell in line.strip().split("|") if cell.strip()]
            if len(cells) >= 7:
                status = cells[4]
                risks = cells[6]
                return status, risks
    return ("Status não encontrado", "Riscos não encontrados")


def parse_checkboxes(lines: List[str]) -> Tuple[List[str], List[str]]:
    done: List[str] = []
    pending: List[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- [x]") or stripped.startswith("- [X]"):
            done.append(stripped[5:].strip())
        elif stripped.startswith("- [ ]"):
            pending.append(stripped[5:].strip())
    return done, pending


def parse_numbered_list(lines: List[str]) -> List[str]:
    items: List[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and stripped[0].isdigit():
            parts = stripped.split(".", 1)
            if len(parts) == 2:
                items.append(parts[1].strip())
    return items


def parse_section(lines: List[str], header: str) -> List[str]:
    collected: List[str] = []
    capture = False
    for line in lines:
        if line.startswith("## "):
            capture = line.strip() == header
            continue
        if capture:
            if line.startswith("## "):
                break
            stripped = line.strip()
            if stripped.startswith("-"):
                collected.append(stripped[1:].strip())
    return collected


def build_report(
    phase: int,
    roadmap_status: str,
    roadmap_risks: str,
    highlights: List[str],
    missing: List[str],
    done: List[str],
    pending: List[str],
    next_actions: List[str],
) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")
    lines: List[str] = [
        f"# Relatório de Fase — FASE {phase}",
        f"Gerado em: {timestamp}",
        "## Status geral",
        f"- Status no roadmap: {roadmap_status}",
    ]
    if highlights:
        lines.append("- Principais pontos:")
        for item in highlights:
            lines.append(f"  - {item}")
    lines.append("## Checkboxes concluídos")
    if done:
        for item in done:
            lines.append(f"- {item}")
    else:
        lines.append("- Nenhum item concluído.")

    lines.append("## Checkboxes pendentes")
    if pending:
        for item in pending:
            lines.append(f"- {item}")
    else:
        lines.append("- Nenhum item pendente.")

    lines.append("## Próximas ações")
    if next_actions:
        for idx, item in enumerate(next_actions, start=1):
            lines.append(f"{idx}. {item}")
    else:
        lines.append("- Nenhuma ação registrada.")

    lines.append("## Riscos / observações")
    if roadmap_risks:
        lines.append(f"- {roadmap_risks}")
    for item in missing:
        lines.append(f"- Pendência: {item}")

    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()

    roadmap_lines = read_lines(ROADMAP_PATH)
    baseline_lines = read_lines(BASELINE_PATH)
    next_actions_lines = read_lines(NEXT_ACTIONS_PATH)
    current_state_lines = read_lines(CURRENT_STATE_PATH)

    status, risks = parse_roadmap_status(args.phase, roadmap_lines)
    done, pending = parse_checkboxes(baseline_lines)
    next_actions = parse_numbered_list(next_actions_lines)
    highlights = parse_section(current_state_lines, "## Onde estamos")
    missing = parse_section(current_state_lines, "## O que ainda falta")

    report_text = build_report(
        args.phase,
        status,
        risks,
        highlights[:5],
        missing[:5],
        done,
        pending,
        next_actions,
    )

    if args.output:
        output_path = Path(args.output)
    else:
        DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = DEFAULT_OUTPUT_DIR / f"phase{args.phase}-report.md"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_text, encoding="utf-8")

    if args.verbose:
        print(report_text)
    print(f"Relatório gerado em {output_path.as_posix()}")


if __name__ == "__main__":
    main()
