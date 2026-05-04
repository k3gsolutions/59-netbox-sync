"""Collection profile selection for read-only compliance collection."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

try:  # pragma: no cover - optional dependency
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore

from .compliance_ssh_policy import validate_command_allowed


PROFILES_BASE = Path(__file__).parent.parent.parent / "policies" / "compliance" / "collection-profiles"
DEFAULT_PROFILE_ID = "default-readonly"
HUAWEI_NE8000_PROFILE_ID = "huawei-ne8000-readonly"


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        raw = path.read_text(encoding="utf-8")
        if yaml is None:
            return {}
        data = yaml.safe_load(raw) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def load_collection_profile(profile_id: str) -> dict[str, Any]:
    """Load a collection profile by id."""
    if not profile_id:
        profile_id = DEFAULT_PROFILE_ID

    path = PROFILES_BASE / f"{profile_id}.yaml"
    profile = _load_yaml(path)
    if profile:
        return profile

    if profile_id != DEFAULT_PROFILE_ID:
        return load_collection_profile(DEFAULT_PROFILE_ID)
    return {}


def select_collection_profile(device: dict[str, Any]) -> dict[str, Any]:
    """Select the best profile for a device."""
    manufacturer = str(device.get("manufacturer") or "").lower()
    model = str(device.get("model") or "").lower()
    platform = str(device.get("platform") or "").lower()

    if "huawei" in manufacturer and "ne8000" in model:
        return load_collection_profile(HUAWEI_NE8000_PROFILE_ID)
    if "huawei" in manufacturer and "ne8000" in platform:
        return load_collection_profile(HUAWEI_NE8000_PROFILE_ID)
    return load_collection_profile(DEFAULT_PROFILE_ID)


def validate_profile(profile: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate profile structure and command safety."""
    issues: list[str] = []
    if not isinstance(profile, dict) or not profile:
        return False, ["profile not found"]

    allowed_commands = list(profile.get("allowed_commands") or [])
    forbidden_patterns = [str(item).lower() for item in profile.get("forbidden_patterns") or []]
    if not allowed_commands:
        issues.append("allowed_commands missing")

    for command in allowed_commands:
        allowed, reason = validate_command_allowed(command)
        if not allowed:
            issues.append(f"forbidden command in profile: {command}: {reason}")
        lowered = str(command).lower()
        for pattern in forbidden_patterns:
            if pattern and pattern in lowered:
                issues.append(f"forbidden pattern in profile: {command}")
                break

    return len(issues) == 0, issues


def get_allowed_commands_for_device(device: dict[str, Any], explicit_full_config: bool = False) -> list[str]:
    """Return read-only commands allowed for a device."""
    profile = select_collection_profile(device)
    allowed_commands = list(profile.get("allowed_commands") or [])
    if explicit_full_config:
        return allowed_commands
    return allowed_commands
