#!/usr/bin/env python3
"""Resumo leve do repositório e atualização de context/MEMORY_INDEX.md.

Percorre o repositório ignorando diretórios ruidosos, identifica arquivos de
contexto, documentação, prompts, skills, ativos GitOps e workflows N8N, gera um
resumo e atualiza `context/MEMORY_INDEX.md` em um formato padronizado.

Uso típico:
    python3 tools/local/summarize_repo.py --root .
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

IGNORE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    "backups",
    "dist",
    "build",
}

MAIN_FILES = {
    "README.md": "Visão geral do projeto",
    "PROJECT_CONTEXT.md": "Contexto rápido para agentes/IA",
    "ROADMAP.md": "Planejamento faseado",
    "PHASE0_BASELINE.md": "Checklist operacional da fase",
    "AGENTS.md": "Regras de atuação para agentes de IA",
}

MEMORY_INDEX_PATH = Path("context/MEMORY_INDEX.md")
MARKER_START = "<!-- AUTO-GENERATED:START -->"
MARKER_END = "<!-- AUTO-GENERATED:END -->"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gerar resumo do repositório")
    parser.add_argument(
        "--root",
        default=".",
        help="Diretório raiz a ser analisado (padrão: diretório atual)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Exibir arquivos analisados",
    )
    return parser.parse_args()


def should_ignore(path: Path) -> bool:
    return any(part in IGNORE_DIRS for part in path.parts if part)


def rel_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def read_first_heading(path: Path) -> str:
    try:
        with path.open(encoding="utf-8") as handle:
            for _ in range(120):
                line = handle.readline()
                if not line:
                    break
                stripped = line.strip()
                if stripped.startswith("#"):
                    return stripped.lstrip("#").strip()
    except OSError:
        return ""
    return ""


def describe_markdown(path: Path) -> str:
    heading = read_first_heading(path)
    if heading:
        return heading
    return path.stem.replace("_", " ").title()


def describe_yaml(path: Path) -> str:
    return f"Configuração declarativa ({path.stem.replace('_', ' ').title()})"


def gather_markdown(root: Path, relative_dir: str) -> List[Tuple[str, str]]:
    base = root / relative_dir
    if not base.exists():
        return []
    entries: List[Tuple[str, str]] = []
    for path in sorted(base.rglob("*.md")):
        rel = rel_posix(path, root)
        if should_ignore(Path(rel)):
            continue
        entries.append((rel, describe_markdown(path)))
    return entries


def gather_yaml(root: Path, relative_dir: str) -> List[Tuple[str, str]]:
    base = root / relative_dir
    if not base.exists():
        return []
    entries: List[Tuple[str, str]] = []
    for path in sorted(base.rglob("*.yaml")):
        rel = rel_posix(path, root)
        if should_ignore(Path(rel)):
            continue
        entries.append((rel, describe_yaml(path)))
    return entries


def gather_context(root: Path) -> List[Tuple[str, str]]:
    entries: List[Tuple[str, str]] = []
    for filename, desc in MAIN_FILES.items():
        path = root / filename
        if path.is_file():
            entries.append((filename, desc))
    context_dir = root / "context"
    if context_dir.is_dir():
        for path in sorted(context_dir.glob("*.md")):
            rel = rel_posix(path, root)
            if should_ignore(Path(rel)) or rel == "context/MEMORY_INDEX.md":
                continue
            entries.append((rel, describe_markdown(path)))
    return entries


def escape_table(text: str) -> str:
    return text.replace("|", "\\|")


def make_table(entries: Sequence[Tuple[str, str]]) -> List[str]:
    if not entries:
        return ["| _Nenhum_ | - |"]
    return [
        f"| {escape_table(path)} | {escape_table(desc)} |"
        for path, desc in entries
    ]


def build_memory_index(
    context_entries: Sequence[Tuple[str, str]],
    docs_entries: Sequence[Tuple[str, str]],
    prompts_entries: Sequence[Tuple[str, str]],
    skills_entries: Sequence[Tuple[str, str]],
    gitops_entries: Sequence[Tuple[str, str]],
    workflows_entries: Sequence[Tuple[str, str]],
) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")
    lines: List[str] = ["# Memory Index", f"Gerado em: {timestamp}"]
    sections = [
        ("## Arquivos de contexto", context_entries),
        ("## Documentação", docs_entries),
        ("## Prompts", prompts_entries),
        ("## Skills", skills_entries),
        ("## Configurações GitOps", gitops_entries),
        ("## Workflows N8N", workflows_entries),
    ]
    for title, entries in sections:
        lines.append(title)
        lines.append("| Arquivo | Finalidade provável |")
        lines.append("| --- | --- |")
        lines.extend(make_table(entries))
        lines.append("")
    lines.append("## Observações")
    lines.append(
        "- Diretórios ignorados: " + (", ".join(sorted(IGNORE_DIRS)) or "nenhum")
    )
    lines.append("- Nenhum conteúdo sensível foi exibido.")
    lines.append("")
    lines.append(MARKER_START)
    lines.append(MARKER_END)
    lines.append("")
    return "\n".join(lines)


def write_memory_index(content: str) -> None:
    MEMORY_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_INDEX_PATH.write_text(content, encoding="utf-8")


def print_summary(
    root: Path,
    context_entries: Sequence[Tuple[str, str]],
    docs_entries: Sequence[Tuple[str, str]],
    prompts_entries: Sequence[Tuple[str, str]],
    skills_entries: Sequence[Tuple[str, str]],
    gitops_entries: Sequence[Tuple[str, str]],
    workflows_entries: Sequence[Tuple[str, str]],
) -> None:
    print(f"Resumo do repositório em {root}")
    print(f"- Arquivos de contexto: {len(context_entries)}")
    print(f"- Documentação: {len(docs_entries)}")
    print(f"- Prompts: {len(prompts_entries)}")
    print(f"- Skills: {len(skills_entries)}")
    print(f"- Configurações GitOps: {len(gitops_entries)}")
    print(f"- Workflows N8N: {len(workflows_entries)}")
    print(f"Arquivo atualizado: {MEMORY_INDEX_PATH.as_posix()}")


def main() -> None:
    args = parse_args()
    root = Path(args.root).resolve()
    if not root.is_dir():
        raise SystemExit(f"Diretório inválido: {root}")

    context_entries = gather_context(root)
    docs_entries = gather_markdown(root, "docs")
    prompts_entries = gather_markdown(root, "prompts")
    skills_entries = gather_markdown(root, "skills")
    gitops_entries: List[Tuple[str, str]] = []
    for directory in ("netbox", "zabbix", "grafana"):
        gitops_entries.extend(gather_yaml(root, directory))
    workflows_entries = gather_markdown(root, "n8n/workflows")

    content = build_memory_index(
        context_entries,
        docs_entries,
        prompts_entries,
        skills_entries,
        gitops_entries,
        workflows_entries,
    )
    write_memory_index(content)
    print_summary(
        root,
        context_entries,
        docs_entries,
        prompts_entries,
        skills_entries,
        gitops_entries,
        workflows_entries,
    )


if __name__ == "__main__":
    main()
