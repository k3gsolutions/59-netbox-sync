#!/usr/bin/env python3
"""Atualiza a seção auto-gerada em context/MEMORY_INDEX.md com metadados Markdown.

Lê arquivos Markdown relevantes (contexto, docs, prompts, skills, workflows etc.),
extrai o título H1, principais seções H2 e tamanho aproximado em linhas, e escreve
um quadro resumo entre os marcadores `<!-- AUTO-GENERATED:START -->` e
`<!-- AUTO-GENERATED:END -->` no arquivo `context/MEMORY_INDEX.md`.

Uso típico:
    python3 tools/local/update_context_index.py --root .
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

MARKER_START = "<!-- AUTO-GENERATED:START -->"
MARKER_END = "<!-- AUTO-GENERATED:END -->"
MEMORY_INDEX_PATH = Path("context/MEMORY_INDEX.md")
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
ALLOWED_PREFIXES = {
    "",
    "context",
    "docs",
    "prompts",
    "skills",
    "n8n",
    "netbox",
    "zabbix",
    "grafana",
}
MAX_SECTIONS = 5


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Atualizar índice de contexto")
    parser.add_argument(
        "--root",
        default=".",
        help="Diretório raiz (padrão: diretório atual)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Não grava o arquivo, apenas exibe o resultado",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Exibir arquivos analisados",
    )
    return parser.parse_args()


def should_ignore(path: Path) -> bool:
    return any(part in IGNORE_DIRS for part in path.parts if part)


def within_scope(rel_path: Path) -> bool:
    parts = rel_path.parts
    if not parts:
        return False
    prefix = parts[0]
    return prefix in ALLOWED_PREFIXES


def iter_markdown(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root)
        if should_ignore(rel):
            continue
        if rel.as_posix() == "context/MEMORY_INDEX.md":
            continue
        if not within_scope(rel):
            continue
        yield path


def extract_headings(path: Path) -> Tuple[str, List[str], int]:
    title = ""
    sections: List[str] = []
    total_lines = 0
    try:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                total_lines += 1
                stripped = line.strip()
                if stripped.startswith("# ") and not title:
                    title = stripped[2:].strip()
                elif stripped.startswith("## ") and len(sections) < MAX_SECTIONS:
                    sections.append(stripped[3:].strip())
    except OSError:
        return path.stem, [], total_lines
    if not title:
        title = path.stem.replace("_", " ").title()
    return title, sections, total_lines


def escape_cell(value: str) -> str:
    return value.replace("|", "\\|")


def build_table(entries: Sequence[Tuple[str, str, Sequence[str], int]]) -> str:
    lines = [
        "## Índice detalhado (auto)",
        "| Arquivo | Título | Seções (H2) | Linhas |",
        "| --- | --- | --- | --- |",
    ]
    if not entries:
        lines.append("| _Nenhum_ | - | - | - |")
    else:
        for rel, title, sections, line_count in entries:
            sections_text = "; ".join(sections) if sections else "-"
            lines.append(
                "| {path} | {title} | {sections} | {lines_qty} |".format(
                    path=escape_cell(rel),
                    title=escape_cell(title),
                    sections=escape_cell(sections_text),
                    lines_qty=line_count,
                )
            )
    return "\n".join(lines) + "\n"


def replace_block(content: str, replacement: str) -> str:
    start = content.find(MARKER_START)
    end = content.find(MARKER_END)
    if start == -1 or end == -1 or end < start:
        # Anexa bloco ao final caso os marcadores não existam
        addition = "\n".join([MARKER_START, replacement.rstrip(), MARKER_END, ""]) + "\n"
        if content.endswith("\n"):
            return content + addition
        return content + "\n" + addition
    start_end = start + len(MARKER_START)
    return content[:start_end] + "\n" + replacement + content[end:]


def main() -> None:
    args = parse_args()
    root = Path(args.root).resolve()
    if not root.is_dir():
        raise SystemExit(f"Diretório inválido: {root}")

    if not MEMORY_INDEX_PATH.exists():
        raise SystemExit("context/MEMORY_INDEX.md não encontrado. Execute summarize_repo primeiro.")

    entries: List[Tuple[str, str, Sequence[str], int]] = []
    for path in iter_markdown(root):
        rel = path.relative_to(root).as_posix()
        title, sections, total_lines = extract_headings(path)
        entries.append((rel, title, sections, total_lines))
        if args.verbose:
            print(f"Processado: {rel} ({total_lines} linhas)")

    table = build_table(entries)
    current = MEMORY_INDEX_PATH.read_text(encoding="utf-8")
    updated = replace_block(current, table)

    if args.dry_run:
        print(updated)
    else:
        MEMORY_INDEX_PATH.write_text(updated, encoding="utf-8")
        print(f"context/MEMORY_INDEX.md atualizado com {len(entries)} arquivos.")


if __name__ == "__main__":
    main()
