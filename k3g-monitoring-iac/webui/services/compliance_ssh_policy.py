"""SSH read-only collection policy helpers."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

try:  # pragma: no cover - optional dependency
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore


POLICY_PATH = Path(__file__).parent.parent.parent / "policies" / "compliance" / "ssh-readonly-collection-policy.yaml"

DEFAULT_POLICY: dict[str, Any] = {
    "allowed_protocol": "ssh",
    "allowed_auth": ["env_vars"],
    "required_env_vars": ["COMPLIANCE_SSH_USERNAME", "COMPLIANCE_SSH_PASSWORD"],
    "optional_env_vars": ["COMPLIANCE_SSH_PORT", "COMPLIANCE_SSH_TIMEOUT", "COMPLIANCE_SSH_PREFLIGHT_TCP_CHECK"],
    "forbidden": ["NETBOX_WRITE_TOKEN", "device config commands", "enable/configure/system-view"],
    "allowed_command_prefixes": ["display", "show"],
    "forbidden_command_patterns": [
        "system-view",
        "configure",
        "commit",
        "save",
        "delete",
        "undo",
        "shutdown",
        "reboot",
        "reset",
        "patch",
        "sync",
    ],
    "output_storage": ["reports/compliance/jobs/<job_id>/collection-results/devices/<device_id>/raw/"],
}


def load_ssh_readonly_policy() -> dict[str, Any]:
    """Load SSH read-only policy from YAML or fallback default."""
    if POLICY_PATH.exists():
        try:
            raw = POLICY_PATH.read_text(encoding="utf-8")
            if yaml is not None:
                data = yaml.safe_load(raw) or {}
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return dict(DEFAULT_POLICY)


def validate_ssh_env() -> dict[str, Any]:
    """Validate required SSH env vars without exposing secrets."""
    policy = load_ssh_readonly_policy()
    required = list(policy.get("required_env_vars") or [])
    optional = list(policy.get("optional_env_vars") or [])

    missing = [name for name in required if not os.getenv(name)]
    port_raw = os.getenv("COMPLIANCE_SSH_PORT", "22").strip() or "22"
    timeout_raw = os.getenv("COMPLIANCE_SSH_TIMEOUT", "10").strip() or "10"
    tcp_check_raw = os.getenv("COMPLIANCE_SSH_PREFLIGHT_TCP_CHECK", "false").strip().lower()

    try:
        port = int(port_raw)
    except ValueError:
        port = 22

    try:
        timeout = int(timeout_raw)
    except ValueError:
        timeout = 10

    return {
        "ready": len(missing) == 0 and bool(os.getenv("COMPLIANCE_SSH_USERNAME")) and bool(os.getenv("COMPLIANCE_SSH_PASSWORD")),
        "missing_env_vars": missing,
        "required_env_vars": required,
        "optional_env_vars": optional,
        "username_present": bool(os.getenv("COMPLIANCE_SSH_USERNAME")),
        "password_present": bool(os.getenv("COMPLIANCE_SSH_PASSWORD")),
        "port": port,
        "timeout": timeout,
        "tcp_check_enabled": tcp_check_raw in {"1", "true", "yes", "on"},
        "password_logged": False,
        "password_saved": False,
    }


def validate_command_allowed(command: str) -> tuple[bool, str]:
    """Check if a single command is read-only allowed."""
    policy = load_ssh_readonly_policy()
    command_text = (command or "").strip()
    lowered = command_text.lower()
    allowed_prefixes = [str(item).lower() for item in policy.get("allowed_command_prefixes") or []]
    forbidden_patterns = [str(item).lower() for item in policy.get("forbidden_command_patterns") or []]

    if not command_text:
        return False, "empty command"

    for pattern in forbidden_patterns:
        if pattern and pattern in lowered:
            return False, f"forbidden command pattern: {pattern}"

    if not any(lowered.startswith(prefix) for prefix in allowed_prefixes):
        return False, "command prefix not allowed"

    return True, "allowed"


def validate_commands_allowed(commands: list[str]) -> tuple[bool, list[str]]:
    """Validate all planned commands."""
    issues: list[str] = []
    for command in commands or []:
        allowed, reason = validate_command_allowed(command)
        if not allowed:
            issues.append(f"{command}: {reason}")
    return len(issues) == 0, issues


def sanitize_command_filename(command: str) -> str:
    """Generate a safe filename fragment for a command."""
    text = (command or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "command"
