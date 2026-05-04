"""Tests for collection profiles."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from webui.services.compliance_collection_profiles import (
    DEFAULT_PROFILE_ID,
    HUAWEI_NE8000_PROFILE_ID,
    get_allowed_commands_for_device,
    load_collection_profile,
    select_collection_profile,
    validate_profile,
)
from webui.services.compliance_jobs import create_collection_plan, create_collection_start_gate, create_compliance_job


@pytest.fixture
def jobs_base(tmp_path):
    base = tmp_path / "reports" / "compliance" / "jobs"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _sample_candidates() -> list[dict]:
    return [
        {
            "id": 1890,
            "name": "4WNET-MNS-KTG-RX",
            "status": "active",
            "tenant": "K3G Solutions",
            "site": "MNS",
            "manufacturer": "Huawei",
            "model": "NE8000",
            "primary_ip4": "192.0.2.1/32",
        }
    ]


def test_default_profile_loads():
    profile = load_collection_profile(DEFAULT_PROFILE_ID)
    assert profile["profile_id"] == DEFAULT_PROFILE_ID
    assert profile["vendor"] == "generic"
    assert profile["allowed_commands"]


def test_huawei_profile_selected_by_manufacturer_model():
    profile = select_collection_profile({"manufacturer": "Huawei", "model": "NE8000"})
    assert profile["profile_id"] == HUAWEI_NE8000_PROFILE_ID


def test_profile_with_system_view_is_invalid():
    profile = {
        "profile_id": "bad",
        "allowed_commands": ["display version", "system-view"],
        "forbidden_patterns": ["system-view"],
    }
    valid, issues = validate_profile(profile)
    assert valid is False
    assert any("system-view" in issue.lower() for issue in issues)


def test_huawei_profile_no_full_display_current_configuration():
    profile = load_collection_profile(HUAWEI_NE8000_PROFILE_ID)
    assert not any(command.strip().lower() == "display current-configuration" for command in profile["allowed_commands"])


def test_collection_plan_uses_profile_and_commands(jobs_base):
    job = create_compliance_job([1890], _sample_candidates(), "Keslley", "read_only", jobs_base)
    create_collection_start_gate(job["job_id"], "Keslley", True, jobs_base)
    create_collection_plan(job["job_id"], jobs_base)

    plan = json.loads((jobs_base / job["job_id"] / "collection-plan.json").read_text(encoding="utf-8"))
    device = plan["devices"][0]
    assert device["collection_profile"]["profile_id"] == HUAWEI_NE8000_PROFILE_ID
    assert device["planned_commands"] == get_allowed_commands_for_device(device)
    assert "display version" in device["planned_commands"]
