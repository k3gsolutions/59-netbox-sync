"""Redaction helpers for SSH collection outputs."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable


SENSITIVE_PATTERNS = [
    "password",
    "cipher",
    "simple",
    "authentication",
    "local-user",
    "snmp-agent community",
    "radius",
    "tacacs",
    "key-chain",
    "private-key",
    "Authorization",
    "Token",
    "token",
    "secret",
    "system-view",
    "configure terminal",
    "commit complete",
    "saved successfully",
]


def _mask_tail(text: str, marker: str) -> str:
    pattern = re.compile(rf"(?i)({re.escape(marker)})(\s*[:=]?\s*)(\S+)")
    return pattern.sub(r"\1\2****", text)


def redact_sensitive_line(line: str) -> str:
    """Redact a single output line."""
    redacted = line
    lower = redacted.lower()
    for marker in SENSITIVE_PATTERNS:
        if marker.lower() not in lower:
            continue
        if marker.lower() in {"snmp-agent community", "local-user", "ssh user", "radius", "tacacs", "key-chain", "private-key"}:
            redacted = re.sub(rf"(?i)({re.escape(marker)})(\b.*)?$", r"\1 ****", redacted)
            lower = redacted.lower()
            continue
        redacted = _mask_tail(redacted, marker)
        lower = redacted.lower()
    return redacted


def redact_output(text: str) -> str:
    """Redact sensitive strings from multi-line output."""
    return "\n".join(redact_sensitive_line(line) for line in (text or "").splitlines())


def scan_sensitive_findings(text: str) -> list[dict[str, object]]:
    """Scan for sensitive strings in text."""
    findings: list[dict[str, object]] = []
    for line_no, line in enumerate((text or "").splitlines(), start=1):
        lowered = line.lower()
        for marker in SENSITIVE_PATTERNS:
            if marker.lower() in lowered:
                findings.append({"line": line_no, "pattern": marker, "excerpt": line[:200]})
                break
    return findings


def redact_file(input_path: Path, output_path: Path) -> dict[str, object]:
    """Redact one file and write the sanitized output."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    text = input_path.read_text(encoding="utf-8", errors="ignore") if input_path.exists() else ""
    findings = scan_sensitive_findings(text)
    redacted_text = redact_output(text)
    output_path.write_text(redacted_text, encoding="utf-8")
    return {
        "input_path": str(input_path),
        "output_path": str(output_path),
        "sensitive_findings_count": len(findings),
        "findings": findings,
    }
