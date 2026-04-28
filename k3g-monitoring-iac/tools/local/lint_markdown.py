#!/usr/bin/env python3
"""Lint básico para arquivos Markdown.

Valida se cada arquivo possui um título H1, acusa títulos H1 duplicados,
avisa sobre linhas acima de 180 caracteres e sobre espaços em branco ao final
de linha. As verificações geram avisos, exceto ausência de H1, que é tratada
como erro. Não altera arquivos.

Uso típico:
    python3 tools/local/lint_markdown.py --root docs
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List, Tuple

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
MAX_LENGTH = 180


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lint básico de Markdown")
    parser.add_argument(
        "paths",
        nargs="*",
        help="Arquivos ou diretórios a analisar (padrão: --root)",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Diretório raiz para busca recursiva (padrão: diretório atual)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Reservado para compatibilidade (nenhuma ação é executada)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Exibir arquivos analisados",
    )
    return parser.parse_args()


def should_ignore(path: Path) -> bool:
    return any(part in IGNORE_DIRS for part in path.parts if part)


def iter_markdown_from_paths(root: Path, paths: List[str]) -> Iterable[Path]:
    if not paths:
        yield from iter_markdown(root)
        return
    for entry in paths:
        candidate = (root / entry).resolve()
        if candidate.is_file() and candidate.suffix.lower() == ".md":
            yield candidate
        elif candidate.is_dir():
            for path in sorted(candidate.rglob("*.md")):
                if should_ignore(path.relative_to(root)):
                    continue
                yield path


def iter_markdown(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root)
        if should_ignore(rel):
            continue
        yield path


def lint_file(path: Path) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        errors.append(f"{path}: erro ao ler arquivo ({exc})")
        return errors, warnings

    has_h1 = False
    for idx, line in enumerate(lines, start=1):
        content = line.rstrip("\n")
        if content.startswith("# "):
            if not has_h1:
                has_h1 = True
            else:
                warnings.append(f"{path}:{idx}: título H1 duplicado")
        if content.rstrip() != content:
            warnings.append(f"{path}:{idx}: espaço em branco ao final da linha")
        if len(content) > MAX_LENGTH:
            warnings.append(f"{path}:{idx}: linha com {len(content)} caracteres (aviso)")

    if not has_h1:
        errors.append(f"{path}: ausência de título H1")
    return errors, warnings


def main() -> None:
    args = parse_args()
    root = Path(args.root).resolve()
    if not root.is_dir():
        raise SystemExit(f"Diretório inválido: {root}")

    all_errors: List[str] = []
    all_warnings: List[str] = []

    for path in iter_markdown_from_paths(root, args.paths):
        if args.verbose:
            print(f"Verificando {path.relative_to(root).as_posix()}")
        errors, warnings = lint_file(path)
        all_errors.extend(errors)
        all_warnings.extend(warnings)

    if all_errors:
        print("Erros encontrados:")
        for msg in all_errors:
            print(f"- {msg}")
    if all_warnings:
        print("Avisos:")
        for msg in all_warnings:
            print(f"- {msg}")

    if not all_errors and not all_warnings:
        print("Nenhum problema identificado.")

    if all_errors:
        raise SystemExit(1)
    raise SystemExit(0)


if __name__ == "__main__":
    main()
