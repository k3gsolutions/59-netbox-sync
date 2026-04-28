#!/usr/bin/env python3
"""Valida links internos entre arquivos Markdown.

Varre arquivos `.md`, identifica links relativos e verifica se o arquivo alvo
existe. Anchors (`arquivo.md#secao`) são aceitas, mas o script valida apenas a
existência do arquivo. Links externos (http/https/mailto/tel) e âncoras locais
(`#secao`) são ignorados. Emite relatório no stdout e retorna código 1 caso
links quebrados sejam encontrados.

Uso típico:
    python3 tools/local/check_docs_links.py --root . --context docs
"""
from __future__ import annotations

import argparse
import re
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
LINK_RE = re.compile(r"(?<!\\)!?\[([^\]]+)\]\(([^)]+)\)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verificar links Markdown internos")
    parser.add_argument(
        "--root",
        default=".",
        help="Diretório raiz a analisar (padrão: diretório atual)",
    )
    parser.add_argument(
        "--context",
        action="append",
        default=[],
        help="Diretórios adicionais para resolução de caminhos",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Exibir arquivos analisados",
    )
    return parser.parse_args()


def should_ignore(path: Path) -> bool:
    return any(part in IGNORE_DIRS for part in path.parts if part)


def iter_markdown(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root)
        if should_ignore(rel):
            continue
        yield path


def is_external(target: str) -> bool:
    lowered = target.lower()
    return (
        lowered.startswith("http://")
        or lowered.startswith("https://")
        or lowered.startswith("mailto:")
        or lowered.startswith("tel:")
    )


def resolve_candidate(base: Path, target: str, search_roots: Sequence[Path]) -> bool:
    if target.startswith("#"):
        return True  # âncora local
    path_part = target.split("#", 1)[0]
    if not path_part:
        return True
    candidate = (base / path_part).resolve()
    if candidate.is_file():
        return True
    for root in search_roots:
        candidate = (root / path_part).resolve()
        if candidate.is_file():
            return True
    return False


def main() -> None:
    args = parse_args()
    root = Path(args.root).resolve()
    extra_roots = [Path(p).resolve() for p in args.context]

    if not root.is_dir():
        raise SystemExit(f"Diretório inválido: {root}")

    broken: List[Tuple[str, int, str]] = []
    checked_files = 0

    for path in iter_markdown(root):
        checked_files += 1
        if args.verbose:
            print(f"Analisando {path.relative_to(root).as_posix()}")
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        base = path.parent
        rel_source = path.relative_to(root).as_posix()
        for idx, line in enumerate(lines, start=1):
            for match in LINK_RE.finditer(line):
                target = match.group(2).strip()
                if not target or is_external(target):
                    continue
                if target.startswith("mailto:") or target.startswith("tel:"):
                    continue
                # Ignora links que começam com "!" (imagens) capturados por regex
                if match.group(0).startswith("!"):
                    continue
                if not resolve_candidate(base, target, extra_roots):
                    broken.append((rel_source, idx, target))

    if not broken:
        print(f"Nenhum link quebrado encontrado ({checked_files} arquivos validados).")
        raise SystemExit(0)

    print("Links quebrados detectados:")
    for rel_source, line_no, target in broken:
        print(f"- {rel_source}:{line_no} -> {target}")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
