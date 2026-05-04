"""Tests for SSH output redaction."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from webui.services.compliance_output_redaction import (
    redact_file,
    redact_output,
    redact_sensitive_line,
    scan_sensitive_findings,
)


def test_redact_password():
    assert redact_sensitive_line("password mysecret") == "password ****"


def test_redact_cipher_and_community():
    text = "cipher aes128\nsnmp-agent community read private"
    redacted = redact_output(text)
    assert "cipher ****" in redacted
    assert "snmp-agent community ****" in redacted


def test_scan_sensitive_findings_detects_token():
    findings = scan_sensitive_findings("Authorization: Bearer token-abc")
    assert findings
    assert any(f["pattern"] for f in findings)


def test_redact_file_creates_output(tmp_path):
    input_path = tmp_path / "input.txt"
    output_path = tmp_path / "redacted.txt"
    input_path.write_text("password secret\n", encoding="utf-8")

    result = redact_file(input_path, output_path)
    assert output_path.exists()
    assert "password ****" in output_path.read_text(encoding="utf-8")
    assert result["sensitive_findings_count"] == 1
