"""Tests for selective candidate search (FASES CANDIDATES-013–018).

Covers: id/name/q search, minimal payload, rejection diagnostics,
no bulk fetch, no config_context, safety blocks.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "webui"))

import pytest
from unittest.mock import MagicMock, patch

from services.compliance_candidates import (
    is_compliance_candidate,
    get_rejection_reason,
    sanitize_device_for_candidate,
    list_compliance_candidates,
)


class TestSelectiveSearch:
    """FASE CANDIDATES-013 — selective search."""

    def test_no_search_param_no_bulk_fetch(self):
        """Without id/name/q, should not call get_devices bulk."""
        mock_client = MagicMock()
        result = list_compliance_candidates(mock_client)

        # Should not have called get_devices
        mock_client.get_devices.assert_not_called()
        assert result["count"] == 0
        assert "message" in result

    def test_no_search_param_returns_message(self):
        """Without search criteria, return helpful message."""
        mock_client = MagicMock()
        result = list_compliance_candidates(mock_client)

        assert result["message"] == "Informe id, name ou q para buscar candidatos."

    def test_id_param_calls_get_device_by_id(self):
        """With id, should call get_device_by_id."""
        mock_client = MagicMock()
        mock_client.get_device_by_id.return_value = {
            "id": 1890,
            "name": "4WNET-MNS-KTG-RX",
            "status": "active",
            "custom_fields": {"Compliance": True},
            "tenant": {"name": "K3G Solutions", "group": {"name": "K3G Solutions"}},
        }

        result = list_compliance_candidates(mock_client, device_id=1890)

        mock_client.get_device_by_id.assert_called_once_with(1890)
        assert result["count"] == 1

    def test_name_param_calls_search_by_name(self):
        """With name, should call search_devices_by_name."""
        mock_client = MagicMock()
        mock_client.search_devices_by_name.return_value = [
            {
                "id": 1890,
                "name": "4WNET-MNS-KTG-RX",
                "status": "active",
                "custom_fields": {"Compliance": True},
                "tenant": {"name": "K3G Solutions", "group": {"name": "K3G Solutions"}},
            }
        ]

        result = list_compliance_candidates(mock_client, name="4WNET-MNS-KTG-RX")

        mock_client.search_devices_by_name.assert_called_once_with("4WNET-MNS-KTG-RX", limit=10)
        assert result["count"] == 1

    def test_q_param_calls_search_devices(self):
        """With q, should call search_devices."""
        mock_client = MagicMock()
        mock_client.search_devices.return_value = [
            {
                "id": 1890,
                "name": "4WNET-MNS-KTG-RX",
                "status": "active",
                "custom_fields": {"Compliance": True},
                "tenant": {"name": "K3G Solutions", "group": {"name": "K3G Solutions"}},
            }
        ]

        result = list_compliance_candidates(mock_client, q="4WNET")

        mock_client.search_devices.assert_called_once_with("4WNET", limit=10, offset=0)
        assert result["count"] == 1


class TestMinimalPayload:
    """FASE CANDIDATES-014 — minimal payload, no config_context."""

    def test_sanitize_removes_config_context(self):
        """Sanitize should never return config_context."""
        device = {
            "id": 1890,
            "name": "test",
            "config_context": {"password": "secret"},
            "custom_fields": {"Compliance": True},
        }

        result = sanitize_device_for_candidate(device)

        assert "config_context" not in result

    def test_sanitize_removes_local_context_data(self):
        """Sanitize should never return local_context_data."""
        device = {
            "id": 1890,
            "name": "test",
            "local_context_data": {"token": "secret"},
            "custom_fields": {"Compliance": True},
        }

        result = sanitize_device_for_candidate(device)

        assert "local_context_data" not in result

    def test_sanitize_removes_raw_custom_fields(self):
        """Sanitize returns only Compliance value, not full custom_fields."""
        device = {
            "id": 1890,
            "name": "test",
            "custom_fields": {
                "Compliance": True,
                "OtherField": "value",
                "SecretField": "password",
            },
        }

        result = sanitize_device_for_candidate(device)

        assert "custom_fields" not in result
        assert result["compliance_field_value"] is True

    def test_normalize_returns_only_allowed_fields(self):
        """Normalized candidate includes only allowed fields."""
        device = {
            "id": 1890,
            "name": "4WNET-MNS-KTG-RX",
            "status": "active",
            "custom_fields": {"Compliance": True},
            "tenant": {"name": "K3G Solutions", "group": {"name": "K3G Solutions"}},
            "site": {"name": "MNS"},
            "device_role": {"name": "Router"},
            "device_type": {"model": "NE8000", "manufacturer": {"name": "Huawei"}},
            "primary_ip4": {"address": "192.0.2.1/32"},
            "config_context": {"secret": "data"},
        }

        from services.compliance_candidates import normalize_compliance_candidate

        result = normalize_compliance_candidate(device)

        # Allowed fields should be present
        assert result["id"] == 1890
        assert result["name"] == "4WNET-MNS-KTG-RX"
        assert result["status"] == "active"

        # Forbidden fields should not be present
        assert "config_context" not in result
        assert "local_context_data" not in result
        assert "custom_fields" not in result


class TestRejectionDiagnostics:
    """FASE CANDIDATES-017 — rejected minimal diagnostics."""

    def test_get_rejection_reason_inactive(self):
        """Inactive device has reason 'inactive'."""
        device = {"status": "offline"}
        reason = get_rejection_reason(device)
        assert reason == "inactive"

    def test_get_rejection_reason_no_compliance(self):
        """Device without Compliance field has reason 'compliance_disabled'."""
        device = {"status": "active", "custom_fields": {}}
        reason = get_rejection_reason(device)
        assert reason == "compliance_disabled"

    def test_get_rejection_reason_no_tenant(self):
        """Device without tenant has reason 'no_tenant'."""
        device = {
            "status": "active",
            "custom_fields": {"Compliance": True},
        }
        reason = get_rejection_reason(device)
        assert reason == "no_tenant"

    def test_get_rejection_reason_wrong_tenant_group(self):
        """Device with wrong tenant group has reason 'wrong_tenant_group'."""
        device = {
            "status": "active",
            "custom_fields": {"Compliance": True},
            "tenant": {"name": "Other", "group": {"name": "Other Group"}},
        }
        reason = get_rejection_reason(device)
        assert reason == "wrong_tenant_group"

    def test_include_rejected_includes_reasons(self):
        """With include_rejected=True, should include rejected list with reasons."""
        mock_client = MagicMock()
        mock_client.search_devices_by_name.return_value = [
            {
                "id": 1,
                "name": "eligible",
                "status": "active",
                "custom_fields": {"Compliance": True},
                "tenant": {"name": "K3G Solutions", "group": {"name": "K3G Solutions"}},
            },
            {
                "id": 2,
                "name": "inactive",
                "status": "offline",
                "custom_fields": {"Compliance": True},
                "tenant": {"name": "K3G Solutions", "group": {"name": "K3G Solutions"}},
            },
        ]

        result = list_compliance_candidates(
            mock_client,
            name="test",
            include_rejected=True
        )

        assert result["count"] == 1
        assert "rejected" in result
        assert len(result["rejected"]) == 1
        assert result["rejected"][0]["id"] == 2
        assert result["rejected"][0]["reason"] == "inactive"

    def test_rejected_no_full_payload(self):
        """Rejected devices only show id, name, reason (minimal)."""
        device = {
            "id": 2,
            "name": "inactive",
            "status": "offline",
            "config_context": {"secret": "data"},
            "custom_fields": {"Compliance": True},
            "tenant": {"name": "K3G Solutions", "group": {"name": "K3G Solutions"}},
        }

        reason = get_rejection_reason(device)
        rejected_item = {
            "id": device.get("id"),
            "name": device.get("name"),
            "reason": reason,
        }

        assert len(rejected_item) == 3
        assert "config_context" not in str(rejected_item)


class TestSafetyBlocks:
    """Verify safety blocks in all responses."""

    def test_safety_block_present_no_search(self):
        """Even with no search, safety block present."""
        mock_client = MagicMock()
        result = list_compliance_candidates(mock_client)

        assert "safety" in result
        assert result["safety"]["read_only"] is True
        assert result["safety"]["netbox_write"] is False
        assert result["safety"]["device_connection"] is False
        assert result["safety"]["auto_compliance_started"] is False

    def test_safety_block_present_with_search(self):
        """With search results, safety block present."""
        mock_client = MagicMock()
        mock_client.get_device_by_id.return_value = {
            "id": 1890,
            "name": "test",
            "status": "active",
            "custom_fields": {"Compliance": True},
            "tenant": {"name": "K3G Solutions", "group": {"name": "K3G Solutions"}},
        }

        result = list_compliance_candidates(mock_client, device_id=1890)

        assert "safety" in result
        assert result["safety"]["read_only"] is True


class TestNetBoxClientMethods:
    """FASE CANDIDATES-015 — NetBox client search methods."""

    @patch("services.netbox_client.NetBoxClient._fetch")
    def test_get_device_by_id_uses_direct_endpoint(self, mock_fetch):
        """get_device_by_id should call /api/dcim/devices/{id}/."""
        from services.netbox_client import NetBoxClient

        client = NetBoxClient("http://test", "token")
        mock_fetch.return_value = [{"id": 1890, "name": "test"}]

        result = client.get_device_by_id(1890)

        mock_fetch.assert_called_once()
        assert result["id"] == 1890

    @patch("services.netbox_client.NetBoxClient._fetch")
    def test_search_devices_by_name_limits_to_10(self, mock_fetch):
        """search_devices_by_name should cap limit at 10."""
        from services.netbox_client import NetBoxClient

        client = NetBoxClient("http://test", "token")
        mock_fetch.return_value = []

        client.search_devices_by_name("test", limit=100)

        # Should have capped at 10
        call_args = mock_fetch.call_args
        assert call_args[0][1]["limit"] == 10

    @patch("services.netbox_client.NetBoxClient._fetch")
    def test_search_devices_limits_to_25(self, mock_fetch):
        """search_devices should cap limit at 25."""
        from services.netbox_client import NetBoxClient

        client = NetBoxClient("http://test", "token")
        mock_fetch.return_value = []

        client.search_devices("test", limit=100)

        # Should have capped at 25
        call_args = mock_fetch.call_args
        assert call_args[0][1]["limit"] == 25
