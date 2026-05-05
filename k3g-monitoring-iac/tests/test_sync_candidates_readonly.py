"""Tests for sync candidates discovery (read-only, no writes)."""

import json
from pathlib import Path

import pytest

# Mock device data
MOCK_DEVICE_SYNC_ELIGIBLE = {
    "id": 1890,
    "name": "4WNET-MNS-KTG-RX",
    "status": "active",
    "tenant": {"id": 1, "name": "4W NET"},
    "site": {"id": 100, "name": "4WNET-MNS-KTG"},
    "role": {"id": 50, "name": "12 - Ativos de Borda"},
    "platform": {"id": 5, "name": "Huawei NE8000"},
    "primary_ip4": {"address": "104.234.244.255/32"},
    "device_type": {
        "id": 200,
        "manufacturer": {"id": 10, "name": "Huawei"},
        "model": "NE8000 M8 DC",
    },
}

MOCK_DEVICE_MISSING_PLATFORM = {
    "id": 1891,
    "name": "incomplete-device",
    "status": "active",
    "tenant": {"id": 1, "name": "4W NET"},
    "site": {"id": 100, "name": "4WNET-MNS-KTG"},
    "role": {"id": 50, "name": "Router"},
    "platform": None,  # Missing
    "primary_ip4": {"address": "10.0.0.1/24"},
    "device_type": {"id": 200, "manufacturer": {"id": 10, "name": "Vendor"}, "model": "Model"},
}


def test_sync_candidate_readiness_check():
    """Test sync candidate readiness evaluation."""
    from webui.services.sync_candidates import discover_sync_candidates

    # Mock NetBox client
    class MockNetBox:
        def get_devices(self, status=None):
            return [MOCK_DEVICE_SYNC_ELIGIBLE, MOCK_DEVICE_MISSING_PLATFORM]

    import webui.services.sync_candidates as sync_module

    original_get_netbox = sync_module.get_netbox_client

    try:
        sync_module.get_netbox_client = lambda: MockNetBox()
        result = discover_sync_candidates(operator="test")

        assert result["success"] is True
        assert result["count"] == 1  # Only eligible device
        assert len(result["results"]) == 1

        device = result["results"][0]
        assert device["id"] == 1890
        assert device["name"] == "4WNET-MNS-KTG-RX"
        assert device["sync_eligible"] is True
        assert device["readiness"]["has_platform"] is True
        assert device["readiness"]["has_tenant"] is True

    finally:
        sync_module.get_netbox_client = original_get_netbox


def test_sync_candidates_no_netbox_write():
    """Verify sync candidates uses GET only (no writes)."""
    from webui.services.sync_candidates import discover_sync_candidates

    class MockNetBox:
        def __init__(self):
            self.write_called = False

        def get_devices(self, status=None):
            return [MOCK_DEVICE_SYNC_ELIGIBLE]

        def post(self, *args, **kwargs):
            self.write_called = True
            raise Exception("NetBox write not allowed")

        def patch(self, *args, **kwargs):
            self.write_called = True
            raise Exception("NetBox write not allowed")

    import webui.services.sync_candidates as sync_module

    original_get_netbox = sync_module.get_netbox_client
    mock_client = MockNetBox()

    try:
        sync_module.get_netbox_client = lambda: mock_client
        result = discover_sync_candidates()

        assert result["success"] is True
        assert mock_client.write_called is False
        assert result["safety"]["netbox_write"] is False

    finally:
        sync_module.get_netbox_client = original_get_netbox


def test_sync_candidates_no_device_connection():
    """Verify sync candidates does not connect to devices."""
    from webui.services.sync_candidates import discover_sync_candidates

    class MockNetBox:
        def get_devices(self, status=None):
            return [MOCK_DEVICE_SYNC_ELIGIBLE]

    import webui.services.sync_candidates as sync_module

    original_get_netbox = sync_module.get_netbox_client

    try:
        sync_module.get_netbox_client = lambda: MockNetBox()
        result = discover_sync_candidates()

        assert result["success"] is True
        assert result["safety"]["device_connection"] is False

    finally:
        sync_module.get_netbox_client = original_get_netbox


def test_sync_candidates_save_artifacts(tmp_path):
    """Test saving sync candidates to disk."""
    from webui.services.sync_candidates import save_sync_candidates

    result = {
        "success": True,
        "discovered_at": "2026-05-05T10:00:00+00:00",
        "operator": "test",
        "count": 1,
        "results": [MOCK_DEVICE_SYNC_ELIGIBLE],
        "safety": {"netbox_write": False, "sync_executed": False, "device_connection": False},
    }

    saved = save_sync_candidates(result, tmp_path)

    assert saved["success"] is True
    assert Path(saved["candidates_json"]).exists()
    assert Path(saved["candidates_markdown"]).exists()
    assert saved["count"] == 1

    # Verify JSON content
    json_data = json.loads(Path(saved["candidates_json"]).read_text())
    assert json_data["count"] == 1
    assert json_data["results"][0]["id"] == 1890

    # Verify Markdown content
    md_content = Path(saved["candidates_markdown"]).read_text()
    assert "4WNET-MNS-KTG-RX" in md_content
    assert "Read-only only: true" in md_content


def test_sync_candidate_missing_readiness_fields():
    """Test device missing required readiness fields is excluded."""
    from webui.services.sync_candidates import discover_sync_candidates

    device_missing_role = {
        "id": 1892,
        "name": "no-role",
        "status": "active",
        "tenant": {"name": "4W NET"},
        "site": {"name": "Site"},
        "role": None,  # Missing role
        "platform": {"name": "Huawei"},
        "primary_ip4": {"address": "10.0.0.1/24"},
        "device_type": {"manufacturer": {"name": "Vendor"}, "model": "Model"},
    }

    class MockNetBox:
        def get_devices(self, status=None):
            return [device_missing_role]

    import webui.services.sync_candidates as sync_module

    original_get_netbox = sync_module.get_netbox_client

    try:
        sync_module.get_netbox_client = lambda: MockNetBox()
        result = discover_sync_candidates()

        assert result["success"] is True
        assert result["count"] == 0  # Excluded due to missing role
        assert result["safety"]["netbox_write"] is False

    finally:
        sync_module.get_netbox_client = original_get_netbox
