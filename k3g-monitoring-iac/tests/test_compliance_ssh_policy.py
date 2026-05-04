"""Tests for SSH read-only compliance policy helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from webui.services.compliance_ssh_policy import (
    load_ssh_readonly_policy,
    sanitize_command_filename,
    validate_command_allowed,
    validate_commands_allowed,
    validate_ssh_env,
)


@pytest.fixture(autouse=True)
def clear_ssh_env(monkeypatch):
    for name in [
        "COMPLIANCE_SSH_USERNAME",
        "COMPLIANCE_SSH_PASSWORD",
        "COMPLIANCE_SSH_PORT",
        "COMPLIANCE_SSH_TIMEOUT",
        "COMPLIANCE_SSH_PREFLIGHT_TCP_CHECK",
    ]:
        monkeypatch.delenv(name, raising=False)


def test_policy_loads_minimum_fields():
    policy = load_ssh_readonly_policy()
    assert policy["allowed_protocol"] == "ssh"
    assert "COMPLIANCE_SSH_USERNAME" in policy["required_env_vars"]
    assert "display" in policy["allowed_command_prefixes"]
    assert "show" in policy["allowed_command_prefixes"]


def test_validate_ssh_env_missing_values():
    env = validate_ssh_env()
    assert env["ready"] is False
    assert "COMPLIANCE_SSH_USERNAME" in env["missing_env_vars"]
    assert "COMPLIANCE_SSH_PASSWORD" in env["missing_env_vars"]
    assert env["password_logged"] is False
    assert env["password_saved"] is False


def test_validate_ssh_env_present(monkeypatch):
    monkeypatch.setenv("COMPLIANCE_SSH_USERNAME", "readonly")
    monkeypatch.setenv("COMPLIANCE_SSH_PASSWORD", "very-secret")
    monkeypatch.setenv("COMPLIANCE_SSH_PORT", "2222")
    monkeypatch.setenv("COMPLIANCE_SSH_TIMEOUT", "15")
    monkeypatch.setenv("COMPLIANCE_SSH_PREFLIGHT_TCP_CHECK", "true")

    env = validate_ssh_env()
    assert env["ready"] is True
    assert env["username_present"] is True
    assert env["password_present"] is True
    assert env["port"] == 2222
    assert env["timeout"] == 15
    assert env["tcp_check_enabled"] is True
    assert env["password_logged"] is False
    assert env["password_saved"] is False


@pytest.mark.parametrize("command", ["display version", "show interface brief"])
def test_allowed_commands(command):
    allowed, reason = validate_command_allowed(command)
    assert allowed is True
    assert reason == "allowed"


@pytest.mark.parametrize(
    "command",
    [
        "system-view",
        "configure terminal",
        "commit",
        "save",
        "delete",
        "undo shutdown",
        "shutdown",
        "reboot",
        "reset saved-configuration",
        "patch apply",
    ],
)
def test_forbidden_commands(command):
    allowed, reason = validate_command_allowed(command)
    assert allowed is False
    assert reason


def test_validate_commands_allowed_mixed():
    allowed, issues = validate_commands_allowed(["display version", "system-view"])
    assert allowed is False
    assert any("system-view" in issue for issue in issues)


def test_sanitize_command_filename():
    assert sanitize_command_filename("display interface brief") == "display-interface-brief"
