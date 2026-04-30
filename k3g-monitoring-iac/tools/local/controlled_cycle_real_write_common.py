#!/usr/bin/env python3
"""Shared helpers for Cycle-002 real-write chain."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


FORBIDDEN_TERMS = ("token", "password", "secret", "api_key", "private key", "bearer", "authorization")


def s(value: Any) -> str:
    return str(value or "").strip()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def write_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def has_forbidden_terms(value: Any) -> bool:
    """Check if value contains actual secret tokens/passwords/keys.
    Only flags actual values, not field names like 'token_logged', 'token_saved'.
    """
    if not isinstance(value, (dict, list)):
        text = str(value or "").lower()
    else:
        text = json.dumps(value, ensure_ascii=False).lower()

    # Exclude common field names that contain these terms
    excluded_fields = {
        "token_logged", "token_saved", "token_not_logged", "token_not_saved",
        "token_required_in_next_phase", "no_token_read", "no_token_save",
        "authorization_id"
    }

    # Remove excluded field names from the text
    for field in excluded_fields:
        text = text.replace(f'"{field}"', '"_excluded_"')
        text = text.replace(f"'{field}'", "'_excluded_'")

    # Now check for forbidden terms
    return any(term in text for term in FORBIDDEN_TERMS)


def https_parts(url: str) -> tuple[str, str]:
    clean = s(url)
    if not clean.startswith("https://"):
        raise ValueError("netbox-url must start with https://")
    rest = clean[len("https://") :]
    host, _, tail = rest.partition("/")
    return host, f"/{tail}" if tail else ""


def cycle_dir(root: Path, cycle_id: str) -> Path:
    return root / "reports" / "controlled-operation" / cycle_id


def load_approved_records(approved_dir: Path) -> list[tuple[Path, dict[str, Any]]]:
    records: list[tuple[Path, dict[str, Any]]] = []
    seen: set[str] = set()
    for candidate_dir in [approved_dir, approved_dir / "approved"]:
        if not candidate_dir.exists():
            continue
        for record_file in sorted(candidate_dir.glob("*.json")):
            marker = str(record_file.resolve())
            if marker in seen:
                continue
            seen.add(marker)
            data = load_json(record_file)
            if s(data.get("status")) == "approved" and s(data.get("state")) == "approved":
                records.append((record_file, data))
    return records


def ensure_allowed_target(endpoint: str) -> bool:
    path = s(endpoint)
    if not path or path == "/":
        return False
    lowered = path.lower()
    if any(term in lowered for term in ["/sync", "equipment", "ssh", "netconf"]):
        return False
    return True


def summarize_issues(issues: Iterable[str]) -> str:
    rows = list(issues)
    return "\n".join(f"- {item}" for item in rows) if rows else "- none"
