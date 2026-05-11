"""API tests for /compliance/candidates and related routes.

Uses FastAPI TestClient with mocked NetBox client. Tests that:
- Routes exist and return correct status codes
- Responses include safety blocks
- No forbidden operations occur
"""

import json
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

# Import app from webui package
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from webui.app import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_netbox_client():
    """Create a mock NetBox client that returns sample devices."""
    client = MagicMock()

    # Sample eligible device
    eligible_device = {
        "id": 1890,
        "name": "4WNET-MNS-KTG-RX",
        "status": "active",
            "role": {"slug": "12-ativos-de-borda", "name": "12 - ativos de borda"},
        "custom_fields": {"Compliance": True},
        "tenant": {"name": "K3G Solutions", "group": {"name": "K3G Solutions"}},
        "site": {"name": "MNS"},
        "device_role": {"name": "Router"},
        "primary_ip4": {"address": "192.0.2.1/32"},
        "device_type": {
            "model": "NE8000",
            "manufacturer": {"name": "Huawei"}
        }
    }

    # Sample ineligible device (Compliance=False)
    ineligible_device = {
        "id": 1891,
        "name": "DEVICE-NONCOMPLIANT",
        "status": "active",
            "role": {"slug": "12-ativos-de-borda", "name": "12 - ativos de borda"},
        "custom_fields": {"Compliance": False},
        "tenant": {"name": "K3G Solutions", "group": {"name": "K3G Solutions"}},
    }

    client.get_devices.return_value = [eligible_device, ineligible_device]
    return client


class TestGetComplianceCandidatesRoute:
    """Test GET /compliance/candidates endpoint."""

    def test_route_exists_and_returns_200(self, client, mock_netbox_client):
        """Route should return 200 OK."""
        with patch("webui.services.compliance_candidates.NetBoxClient", return_value=mock_netbox_client):
            with patch("webui.app.get_netbox_client", return_value=mock_netbox_client):
                response = client.get("/compliance/candidates")
                assert response.status_code == 200

    def test_response_has_safety_block(self, client, mock_netbox_client):
        """Response must include safety block."""
        with patch("webui.app.get_netbox_client", return_value=mock_netbox_client):
            response = client.get("/compliance/candidates")
            data = response.json()
            assert "safety" in data
            assert data["safety"]["read_only"] is True
            assert data["safety"]["netbox_write"] is False
            assert data["safety"]["device_connection"] is False
            assert data["safety"]["auto_compliance_started"] is False

    def test_returns_only_eligible_devices(self, client, mock_netbox_client):
        """Response should filter to only eligible devices."""
        with patch("webui.app.get_netbox_client", return_value=mock_netbox_client):
            response = client.get("/compliance/candidates")
            data = response.json()
            # Should have 1 eligible, not 2
            assert data["count"] == 1
            assert len(data["results"]) == 1
            assert data["results"][0]["name"] == "4WNET-MNS-KTG-RX"

    def test_response_includes_candidate_reason(self, client, mock_netbox_client):
        """Each candidate should list why it qualifies."""
        with patch("webui.app.get_netbox_client", return_value=mock_netbox_client):
            response = client.get("/compliance/candidates")
            data = response.json()
            candidate = data["results"][0]
            assert "candidate_reason" in candidate
            assert "device_active" in candidate["candidate_reason"]
            assert "compliance_enabled" in candidate["candidate_reason"]
            assert "tenant_present" in candidate["candidate_reason"]
            assert "tenant_group_match" in candidate["candidate_reason"]

    def test_no_ssh_calls_made(self, client, mock_netbox_client):
        """Should not attempt SSH connections."""
        with patch("webui.app.get_netbox_client", return_value=mock_netbox_client):
            # Mock any SSH library
            with patch("paramiko.SSHClient") as mock_ssh:
                response = client.get("/compliance/candidates")
                assert response.status_code == 200
                # Verify SSH was never called
                mock_ssh.connect.assert_not_called()

    def test_no_snmp_calls_made(self, client, mock_netbox_client):
        """Should not attempt SNMP queries."""
        with patch("webui.app.get_netbox_client", return_value=mock_netbox_client):
            # Mock any SNMP library
            with patch("pysnmp.hlapi.getCmd") as mock_snmp:
                response = client.get("/compliance/candidates")
                assert response.status_code == 200
                # Verify SNMP was never called
                mock_snmp.assert_not_called()

    def test_no_netbox_write_methods_called(self, client, mock_netbox_client):
        """Should only call GET, no POST/PATCH/DELETE on NetBox."""
        with patch("webui.app.get_netbox_client", return_value=mock_netbox_client):
            response = client.get("/compliance/candidates")
            assert response.status_code == 200
            # Verify only get_devices was called, no write methods
            mock_netbox_client.get_devices.assert_called()
            # There should be no POST, PATCH, DELETE methods on the client
            assert not hasattr(mock_netbox_client, "create_device")
            assert not hasattr(mock_netbox_client, "update_device")
            assert not hasattr(mock_netbox_client, "delete_device")

    def test_handles_netbox_not_configured(self, client):
        """Should return 503 if NetBox not configured."""
        from webui.services.netbox_client import NetBoxNotConfiguredError
        with patch("webui.app.get_netbox_client", side_effect=NetBoxNotConfiguredError()):
            response = client.get("/compliance/candidates")
            assert response.status_code == 503
            data = response.json()
            assert "error" in data

    def test_handles_netbox_auth_error(self, client):
        """Should return 401 if NetBox auth fails."""
        from webui.services.netbox_client import NetBoxAuthError
        with patch("webui.app.get_netbox_client", side_effect=NetBoxAuthError()):
            response = client.get("/compliance/candidates")
            assert response.status_code == 401


class TestPostComplianceAnalyzeRoute:
    """Test POST /compliance/analyze endpoint."""

    def test_analyze_route_exists(self, client, mock_netbox_client):
        """Route should exist and accept valid payload."""
        payload = {
            "device_ids": [1890],
            "mode": "read_only",
            "triggered_by": "operator"
        }
        with patch("webui.app.get_netbox_client", return_value=mock_netbox_client):
            response = client.post("/compliance/analyze", json=payload)
            assert response.status_code in (200, 422)  # Success or validation error

    def test_analyze_revalidates_eligibility(self, client, mock_netbox_client):
        """Should re-check eligibility before confirming."""
        payload = {
            "device_ids": [1890],
            "mode": "read_only",
            "triggered_by": "operator"
        }
        with patch("webui.app.get_netbox_client", return_value=mock_netbox_client):
            response = client.post("/compliance/analyze", json=payload)
            # Should verify device is still eligible
            mock_netbox_client.get_devices.assert_called()

    def test_analyze_blocks_ineligible(self, client, mock_netbox_client):
        """Should reject if device lost eligibility."""
        # Mock device that is no longer active
        mock_netbox_client.get_devices.return_value = [{
            "id": 1890,
            "name": "4WNET-MNS-KTG-RX",
            "status": "offline",  # Now inactive
            "custom_fields": {"Compliance": True},
            "tenant": {"name": "K3G Solutions", "group": {"name": "K3G Solutions"}},
        }]

        payload = {
            "device_ids": [1890],
            "mode": "read_only",
            "triggered_by": "operator"
        }
        with patch("webui.app.get_netbox_client", return_value=mock_netbox_client):
            response = client.post("/compliance/analyze", json=payload)
            # Should return error
            assert response.status_code in (400, 422)
