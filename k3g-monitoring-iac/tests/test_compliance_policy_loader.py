"""Tests for compliance policy registry loader."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from webui.services.compliance_policy_loader import (
    REQUIRED_POLICY_FILES,
    get_policy,
    load_compliance_policy_registry,
    load_policy_file,
    summarize_policy_registry,
    validate_required_policy_files,
)


def test_loader_loads_required_policies():
    registry = load_compliance_policy_registry("policies/compliance")
    assert registry["validation"]["valid"] is True
    assert set(REQUIRED_POLICY_FILES).issubset(set(registry["validation"]["required_files"]))
    assert registry["summary"]["file_count"] >= len(REQUIRED_POLICY_FILES)
    assert get_policy(registry, "interface-policy.yaml")
    assert summarize_policy_registry(registry)["warning_count"] >= 0


def test_loader_fails_when_required_policy_missing(tmp_path):
    policy_dir = tmp_path / "policies" / "compliance"
    policy_dir.mkdir(parents=True, exist_ok=True)
    (policy_dir / "interface-policy.yaml").write_text("interface: {}\n", encoding="utf-8")
    registry = {"files": {"interface-policy.yaml": load_policy_file(policy_dir / "interface-policy.yaml")}}
    validation = validate_required_policy_files(registry)
    assert validation["valid"] is False
    assert validation["missing_required"]
    assert validation["blockers"]


def test_loader_requires_pyyaml(monkeypatch, tmp_path):
    from webui.services import compliance_policy_loader as loader

    monkeypatch.setattr(loader, "yaml", None, raising=False)
    with pytest.raises(RuntimeError):
        load_policy_file(tmp_path / "missing.yaml")
