"""Unit tests for compliance candidate discovery.

Pure Python tests — no HTTP, no app imports. Tests the eligibility functions
with mock device dicts.
"""

import pytest

# Import directly from webui.services without going through app
import sys
from pathlib import Path

# Add webui to path so we can import services
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "webui"))

from services.compliance_candidates import (
    get_status_value,
    get_custom_field_bool,
    get_tenant_group_name,
    is_compliance_candidate,
    normalize_compliance_candidate,
)


class TestGetStatusValue:
    """Test status value extraction."""

    def test_status_string(self):
        device = {"status": "active"}
        assert get_status_value(device) == "active"

    def test_status_dict(self):
        device = {"status": {"value": "active", "label": "Active"}}
        assert get_status_value(device) == "active"

    def test_status_missing(self):
        device = {}
        assert get_status_value(device) == ""


class TestGetCustomFieldBool:
    """Test custom field boolean lookup."""

    def test_compliance_true(self):
        device = {"custom_fields": {"Compliance": True}}
        assert get_custom_field_bool(device, "Compliance", "compliance") is True

    def test_compliance_lowercase(self):
        device = {"custom_fields": {"compliance": True}}
        assert get_custom_field_bool(device, "Compliance", "compliance") is True

    def test_compliance_false(self):
        device = {"custom_fields": {"Compliance": False}}
        assert get_custom_field_bool(device, "Compliance", "compliance") is False

    def test_compliance_missing(self):
        device = {"custom_fields": {}}
        assert get_custom_field_bool(device, "Compliance", "compliance") is False

    def test_custom_fields_missing(self):
        device = {}
        assert get_custom_field_bool(device, "Compliance", "compliance") is False


class TestGetTenantGroupName:
    """Test tenant group name extraction."""

    def test_tenant_group_name(self):
        device = {
            "tenant": {
                "group": {"name": "K3G Solutions"}
            }
        }
        assert get_tenant_group_name(device) == "K3G Solutions"

    def test_tenant_group_slug(self):
        device = {
            "tenant": {
                "group": {"slug": "k3g-solutions"}
            }
        }
        assert get_tenant_group_name(device) == "k3g-solutions"

    def test_tenant_missing(self):
        device = {}
        assert get_tenant_group_name(device) is None

    def test_tenant_group_missing(self):
        device = {"tenant": {}}
        assert get_tenant_group_name(device) is None


class TestIsComplianceCandidate:
    """Test full 4-gate eligibility check."""

    def test_all_gates_pass(self):
        """Active + Compliance true + tenant + tenant group K3G."""
        device = {
            "status": "active",
            "custom_fields": {"Compliance": True},
            "tenant": {
                "group": {"name": "K3G Solutions"}
            }
        }
        assert is_compliance_candidate(device) is True

    def test_inactive_fails(self):
        """Gate 1 fails."""
        device = {
            "status": "offline",
            "custom_fields": {"Compliance": True},
            "tenant": {
                "group": {"name": "K3G Solutions"}
            }
        }
        assert is_compliance_candidate(device) is False

    def test_compliance_false_fails(self):
        """Gate 2 fails."""
        device = {
            "status": "active",
            "custom_fields": {"Compliance": False},
            "tenant": {
                "group": {"name": "K3G Solutions"}
            }
        }
        assert is_compliance_candidate(device) is False

    def test_compliance_missing_fails(self):
        """Gate 2 fails (missing field)."""
        device = {
            "status": "active",
            "custom_fields": {},
            "tenant": {
                "group": {"name": "K3G Solutions"}
            }
        }
        assert is_compliance_candidate(device) is False

    def test_tenant_missing_fails(self):
        """Gate 3 fails."""
        device = {
            "status": "active",
            "custom_fields": {"Compliance": True},
        }
        assert is_compliance_candidate(device) is False

    def test_tenant_group_wrong_fails(self):
        """Gate 4 fails."""
        device = {
            "status": "active",
            "custom_fields": {"Compliance": True},
            "tenant": {
                "group": {"name": "Other Group"}
            }
        }
        assert is_compliance_candidate(device) is False

    def test_tenant_group_slug_passes(self):
        """Gate 4 passes with slug."""
        device = {
            "status": "active",
            "custom_fields": {"Compliance": True},
            "tenant": {
                "group": {"slug": "k3g-solutions"}
            }
        }
        assert is_compliance_candidate(device) is True

    def test_compliance_lowercase_passes(self):
        """Case-insensitive custom field lookup."""
        device = {
            "status": "active",
            "custom_fields": {"compliance": True},
            "tenant": {
                "group": {"name": "K3G Solutions"}
            }
        }
        assert is_compliance_candidate(device) is True

    def test_status_dict_passes(self):
        """Status as dict."""
        device = {
            "status": {"value": "active", "label": "Active"},
            "custom_fields": {"Compliance": True},
            "tenant": {
                "group": {"name": "K3G Solutions"}
            }
        }
        assert is_compliance_candidate(device) is True


class TestNormalizeCandidateCandidate:
    """Test response normalization."""

    def test_normalize_fields(self):
        """Check all expected fields present."""
        device = {
            "id": 1890,
            "name": "4WNET-MNS-KTG-RX",
            "status": "active",
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

        result = normalize_compliance_candidate(device)

        assert result["id"] == 1890
        assert result["name"] == "4WNET-MNS-KTG-RX"
        assert result["status"] == "active"
        assert result["compliance_enabled"] is True
        assert result["tenant"] == "K3G Solutions"
        assert result["tenant_group"] == "K3G Solutions"
        assert result["site"] == "MNS"
        assert result["role"] == "Router"
        assert result["manufacturer"] == "Huawei"
        assert result["model"] == "NE8000"
        assert result["primary_ip4"] == "192.0.2.1/32"
        assert result["primary_ip6"] is None
        assert "device_active" in result["candidate_reason"]
        assert "compliance_enabled" in result["candidate_reason"]
        assert "tenant_present" in result["candidate_reason"]
        assert "tenant_group_match" in result["candidate_reason"]
