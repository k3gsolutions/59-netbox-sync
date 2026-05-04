"""Compliance policy registry loader.

Local only. No NetBox. No writes. PyYAML required.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

try:  # pragma: no cover - required dependency, but imported defensively for explicit failure.
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore


REQUIRED_POLICY_FILES = [
    "discovery-elements.yaml",
    "dependency-map.yaml",
    "naming-conventions.yaml",
    "snmp-policy.yaml",
    "interface-policy.yaml",
    "vrf-policy.yaml",
    "bgp-policy.yaml",
    "route-policy-policy.yaml",
    "ip-prefix-policy.yaml",
    "community-policy.yaml",
    "as-path-policy.yaml",
    "comments-policy.yaml",
    "compliance-severity-policy.yaml",
]

OPTIONAL_POLICY_FILES = [
    "ssh-readonly-collection-policy.yaml",
    "collection-profiles/default-readonly.yaml",
    "collection-profiles/huawei-ne8000-readonly.yaml",
]


def _require_yaml() -> None:
    if yaml is None:
        raise RuntimeError("PyYAML is required to load compliance policy registry")


def load_policy_file(path: str | Path) -> dict[str, Any]:
    """Load a single YAML policy file."""
    _require_yaml()
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(str(path))
    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw) or {}
    if not isinstance(data, dict):
        raise ValueError(f"policy file is not a mapping: {path}")
    return data


def load_compliance_policy_registry(policy_dir: str | Path = "policies/compliance") -> dict[str, Any]:
    """Load all compliance policy files into a local registry."""
    _require_yaml()
    base = Path(policy_dir)
    if not base.exists():
        raise FileNotFoundError(str(base))

    registry: dict[str, Any] = {
        "policy_dir": str(base),
        "files": {},
        "policies": {},
        "warnings": [],
        "blockers": [],
    }

    for path in sorted(base.rglob("*.yaml")):
        rel = str(path.relative_to(base))
        try:
            registry["files"][rel] = load_policy_file(path)
        except Exception as exc:
            registry["blockers"].append(f"{rel}: {exc}")

    registry["validation"] = validate_required_policy_files(registry)
    registry["summary"] = summarize_policy_registry(registry)
    return registry


def validate_required_policy_files(registry: dict[str, Any]) -> dict[str, Any]:
    """Check mandatory and optional policy files."""
    files = registry.get("files") or {}
    missing_required = [name for name in REQUIRED_POLICY_FILES if name not in files]
    missing_optional = [name for name in OPTIONAL_POLICY_FILES if name not in files]
    blockers = list(registry.get("blockers") or [])
    warnings = list(registry.get("warnings") or [])

    for name in missing_required:
        blockers.append(f"missing required policy file: {name}")
    for name in missing_optional:
        warnings.append(f"missing optional policy file: {name}")

    result = {
        "required_files": REQUIRED_POLICY_FILES,
        "optional_files": OPTIONAL_POLICY_FILES,
        "missing_required": missing_required,
        "missing_optional": missing_optional,
        "blockers": blockers,
        "warnings": warnings,
        "valid": len(missing_required) == 0 and len(blockers) == 0,
    }
    registry["blockers"] = blockers
    registry["warnings"] = warnings
    registry["validation"] = result
    return result


def get_policy(registry: dict[str, Any], policy_name: str) -> dict[str, Any]:
    """Return one named policy."""
    files = registry.get("files") or {}
    if policy_name in files:
        return files[policy_name] or {}
    for rel, data in files.items():
        if Path(rel).name == policy_name:
            return data or {}
    return {}


def summarize_policy_registry(registry: dict[str, Any]) -> dict[str, Any]:
    """Summarize loaded policies."""
    files = registry.get("files") or {}
    return {
        "policy_dir": registry.get("policy_dir"),
        "file_count": len(files),
        "required_count": len(REQUIRED_POLICY_FILES),
        "optional_count": len(OPTIONAL_POLICY_FILES),
        "blocker_count": len(registry.get("blockers") or []),
        "warning_count": len(registry.get("warnings") or []),
        "policy_names": sorted(Path(name).name for name in files.keys()),
    }
