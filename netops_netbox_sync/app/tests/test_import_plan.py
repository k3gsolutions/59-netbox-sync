"""Tests for ImportPlan building (read-only, no writes)."""

import pytest

from app.compliance.import_plan import build_import_plan
from app.schemas.analyze import AnalyzeResult, AppliedInventorySummary
from app.schemas.compliance import ComplianceDivergence
from app.schemas.import_plan import ImportAction, ConfidenceLevel


@pytest.fixture
def base_result():
    """Base AnalyzeResult for testing."""
    return AnalyzeResult(
        hostname="test-device",
        device_id=123,
        mode="read-only",
        netbox_loaded=True,
        compliance_enabled=True,
        applied_summary=AppliedInventorySummary(
            interfaces=5,
            ip_addresses=3,
        ),
        divergences=[],
    )


def test_interface_missing_with_valid_naming(base_result):
    """Interface missing in NetBox with valid naming → safe_create_staged."""
    base_result.divergences.append(
        ComplianceDivergence(
            code="INTERFACE_MISSING_IN_NETBOX",
            severity="medium",
            scope="interfaces",
            message="Interface ge-0/0/0 não existe no NetBox",
            evidence={"interface": "ge-0/0/0"},
            recommendation="Criar interface no NetBox",
            preferred_action="fix_netbox",
            object_type="interface",
            object_key="ge-0/0/0",
        )
    )

    plan = build_import_plan(base_result)

    assert plan.total_items == 1
    assert plan.safe_create_staged_count == 1
    assert plan.needs_review_count == 0
    assert len(plan.items) == 1

    item = plan.items[0]
    assert item.action == ImportAction.SAFE_CREATE_STAGED
    assert item.object_type == "interface"
    assert item.object_key == "ge-0/0/0"
    assert item.naming_compliant is True
    assert item.confidence == ConfidenceLevel.EXACT


def test_interface_missing_with_invalid_naming(base_result):
    """Interface missing in NetBox with invalid naming → needs_review."""
    base_result.divergences.append(
        ComplianceDivergence(
            code="INTERFACE_MISSING_IN_NETBOX",
            severity="medium",
            scope="interfaces",
            message="Interface 'Invalid@Interface' não existe no NetBox",
            evidence={"interface": "Invalid@Interface"},
            recommendation="Validar naming",
            preferred_action="review",
            object_type="interface",
            object_key="Invalid@Interface",
        )
    )

    plan = build_import_plan(base_result)

    assert plan.total_items == 1
    assert plan.safe_create_staged_count == 0
    assert plan.needs_review_count == 1

    item = plan.items[0]
    assert item.action == ImportAction.NEEDS_REVIEW
    assert item.naming_compliant is False
    assert "naming convention" in item.reason.lower()


def test_ip_address_missing_with_valid_ip(base_result):
    """IP address missing in NetBox with valid format → safe_create_staged."""
    base_result.divergences.append(
        ComplianceDivergence(
            code="IP_ADDRESS_MISSING_IN_NETBOX",
            severity="medium",
            scope="ip_addresses",
            message="IP 10.0.0.1/24 não existe no NetBox",
            evidence={"ip_address": "10.0.0.1/24"},
            recommendation="Criar IP no NetBox",
            preferred_action="fix_netbox",
            object_type="ip_address",
            object_key="10.0.0.1/24",
        )
    )

    plan = build_import_plan(base_result)

    assert plan.safe_create_staged_count == 1
    assert plan.needs_review_count == 0

    item = plan.items[0]
    assert item.action == ImportAction.SAFE_CREATE_STAGED
    assert item.naming_compliant is True


def test_vrf_missing_with_valid_naming(base_result):
    """VRF missing in NetBox with valid naming → safe_create_staged."""
    base_result.divergences.append(
        ComplianceDivergence(
            code="VRF_MISSING_IN_NETBOX",
            severity="medium",
            scope="vrfs",
            message="VRF prod_vrf não existe no NetBox",
            evidence={"vrf": "prod_vrf"},
            recommendation="Criar VRF no NetBox",
            preferred_action="fix_netbox",
            object_type="vrf",
            object_key="prod_vrf",
        )
    )

    plan = build_import_plan(base_result)

    assert plan.safe_create_staged_count == 1
    item = plan.items[0]
    assert item.action == ImportAction.SAFE_CREATE_STAGED


def test_vlan_missing_with_valid_id(base_result):
    """VLAN missing in NetBox with valid ID → safe_create_staged."""
    base_result.divergences.append(
        ComplianceDivergence(
            code="VLAN_MISSING_IN_NETBOX",
            severity="medium",
            scope="vlans",
            message="VLAN 100 não existe no NetBox",
            evidence={"vlan_id": "100"},
            recommendation="Criar VLAN no NetBox",
            preferred_action="fix_netbox",
            object_type="vlan",
            object_key="100",
        )
    )

    plan = build_import_plan(base_result)

    assert plan.safe_create_staged_count == 1
    item = plan.items[0]
    assert item.naming_compliant is True


def test_bgp_peer_missing_always_needs_review(base_result):
    """BGP peer missing → always needs_review (complex relationships)."""
    base_result.divergences.append(
        ComplianceDivergence(
            code="BGP_PEER_MISSING_IN_NETBOX",
            severity="high",
            scope="bgp_sessions",
            message="BGP peer 10.0.0.2 não existe no NetBox",
            evidence={"peer_ip": "10.0.0.2"},
            recommendation="Criar BGP peer no NetBox",
            preferred_action="review",
            object_type="bgp_peer",
            object_key="10.0.0.2",
        )
    )

    plan = build_import_plan(base_result)

    assert plan.needs_review_count == 1
    assert plan.safe_create_staged_count == 0

    item = plan.items[0]
    assert item.action == ImportAction.NEEDS_REVIEW
    assert "BGP" in item.reason or "complex" in item.reason


def test_missing_on_device_needs_review(base_result):
    """Object missing on device (present in NetBox) → needs_review."""
    base_result.divergences.append(
        ComplianceDivergence(
            code="INTERFACE_MISSING_ON_DEVICE",
            severity="medium",
            scope="interfaces",
            message="Interface ge-0/0/1 existe no NetBox mas não no device",
            evidence={"interface": "ge-0/0/1"},
            recommendation="Sincronizar device",
            preferred_action="review",
            object_type="interface",
            object_key="ge-0/0/1",
        )
    )

    plan = build_import_plan(base_result)

    assert plan.needs_review_count == 1
    item = plan.items[0]
    assert item.action == ImportAction.NEEDS_REVIEW
    assert "device" in item.reason.lower()


def test_description_non_compliant_needs_review(base_result):
    """Description non-compliant → needs_review."""
    base_result.divergences.append(
        ComplianceDivergence(
            code="DESCRIPTION_NON_COMPLIANT",
            severity="low",
            scope="interfaces",
            message="Interface ge-0/0/0 description não está conforme",
            evidence={"description": "bad description"},
            recommendation="Corrigir descrição",
            preferred_action="fix_device",
            object_type="interface",
            object_key="ge-0/0/0",
        )
    )

    plan = build_import_plan(base_result)

    assert plan.needs_review_count == 1
    item = plan.items[0]
    assert item.action == ImportAction.NEEDS_REVIEW


def test_aggregated_divergence_ignored(base_result):
    """Divergence without object context → ignore."""
    base_result.divergences.append(
        ComplianceDivergence(
            code="SUMMARY_METRIC_MISMATCH",
            severity="info",
            scope="summary",
            message="Interface count mismatch: 5 applied vs 4 documented",
            evidence={"applied": 5, "documented": 4},
            recommendation="Review interface list",
            preferred_action="review",
            object_type=None,
            object_key=None,
        )
    )

    plan = build_import_plan(base_result)

    assert plan.ignore_count == 1
    item = plan.items[0]
    assert item.action == ImportAction.IGNORE


def test_blocked_ambiguous_metadata(base_result):
    """Ambiguous scope/insufficient metadata with object context → blocked."""
    base_result.divergences.append(
        ComplianceDivergence(
            code="UNKNOWN_OBJECT_TYPE",
            severity="info",
            scope="ambiguous",
            message="Unknown object type",
            evidence={},
            recommendation="Investigate",
            preferred_action="review",
            object_type="unknown",
            object_key="some_object",
        )
    )

    plan = build_import_plan(base_result)

    assert plan.blocked_count == 1
    item = plan.items[0]
    assert item.action == ImportAction.BLOCKED


def test_mixed_divergences(base_result):
    """Test with mixture of all action types."""
    base_result.divergences = [
        # safe_create_staged
        ComplianceDivergence(
            code="INTERFACE_MISSING_IN_NETBOX",
            severity="medium",
            scope="interfaces",
            message="Interface ge-0/0/0 missing",
            evidence={"interface": "ge-0/0/0"},
            recommendation="Create",
            preferred_action="fix_netbox",
            object_type="interface",
            object_key="ge-0/0/0",
        ),
        # needs_review (invalid naming)
        ComplianceDivergence(
            code="INTERFACE_MISSING_IN_NETBOX",
            severity="medium",
            scope="interfaces",
            message="Bad interface missing",
            evidence={"interface": "Bad@Interface"},
            recommendation="Validate",
            preferred_action="review",
            object_type="interface",
            object_key="Bad@Interface",
        ),
        # needs_review (BGP)
        ComplianceDivergence(
            code="BGP_PEER_MISSING_IN_NETBOX",
            severity="high",
            scope="bgp_sessions",
            message="BGP peer missing",
            evidence={"peer_ip": "10.0.0.2"},
            recommendation="Review",
            preferred_action="review",
            object_type="bgp_peer",
            object_key="10.0.0.2",
        ),
        # ignore
        ComplianceDivergence(
            code="SUMMARY_MISMATCH",
            severity="info",
            scope="summary",
            message="Summary mismatch",
            evidence={},
            recommendation="Review",
            preferred_action="review",
            object_type=None,
            object_key=None,
        ),
    ]

    plan = build_import_plan(base_result)

    assert plan.total_items == 4
    assert plan.safe_create_staged_count == 1
    assert plan.needs_review_count == 2
    assert plan.ignore_count == 1
    assert plan.blocked_count == 0


def test_no_deletes_ever_generated(base_result):
    """Verify that no delete actions are ever generated."""
    # Add various divergences
    base_result.divergences = [
        ComplianceDivergence(
            code="INTERFACE_MISSING_IN_NETBOX",
            severity="medium",
            scope="interfaces",
            message="Missing",
            evidence={},
            recommendation="Create",
            preferred_action="fix_netbox",
            object_type="interface",
            object_key="ge-0/0/0",
        ),
        ComplianceDivergence(
            code="INTERFACE_MISSING_ON_DEVICE",
            severity="medium",
            scope="interfaces",
            message="Missing on device",
            evidence={},
            recommendation="Remove",
            preferred_action="fix_netbox",
            object_type="interface",
            object_key="ge-0/0/1",
        ),
    ]

    plan = build_import_plan(base_result)

    # Check that NO action is "delete"
    for item in plan.items:
        assert item.action != "delete"
        assert item.action in [
            ImportAction.SAFE_CREATE_STAGED,
            ImportAction.NEEDS_REVIEW,
            ImportAction.BLOCKED,
            ImportAction.IGNORE,
        ]


def test_plan_metadata_populated(base_result):
    """Verify plan metadata is correctly populated."""
    base_result.divergences = [
        ComplianceDivergence(
            code="INTERFACE_MISSING_IN_NETBOX",
            severity="medium",
            scope="interfaces",
            message="Missing",
            evidence={},
            recommendation="Create",
            preferred_action="fix_netbox",
            object_type="interface",
            object_key="ge-0/0/0",
        ),
    ]

    plan = build_import_plan(base_result)

    assert plan.device == "test-device"
    assert plan.device_id == 123
    assert plan.source == "compliance"
    assert plan.generated_at is not None
    assert "Z" in plan.generated_at  # ISO8601 with Z suffix
    assert plan.total_items == 1


def test_base_interface_eth_trunk(base_result):
    """Eth-Trunk0 (base interface) → safe_create_staged."""
    base_result.divergences.append(
        ComplianceDivergence(
            code="INTERFACE_MISSING_IN_NETBOX",
            severity="medium",
            scope="interfaces",
            message="Eth-Trunk0 missing",
            evidence={"interface": "Eth-Trunk0"},
            recommendation="Create",
            preferred_action="fix_netbox",
            object_type="interface",
            object_key="Eth-Trunk0",
        )
    )

    plan = build_import_plan(base_result)

    assert plan.safe_create_staged_count == 1
    item = plan.items[0]
    assert item.action == ImportAction.SAFE_CREATE_STAGED
    assert "base interface" in item.reason.lower()
    assert item.category == "base_inventory"


def test_base_interface_gigabit_ethernet(base_result):
    """GigabitEthernet0/5/0 (base interface) → safe_create_staged."""
    base_result.divergences.append(
        ComplianceDivergence(
            code="INTERFACE_MISSING_IN_NETBOX",
            severity="medium",
            scope="interfaces",
            message="GigabitEthernet0/5/0 missing",
            evidence={"interface": "GigabitEthernet0/5/0"},
            recommendation="Create",
            preferred_action="fix_netbox",
            object_type="interface",
            object_key="GigabitEthernet0/5/0",
        )
    )

    plan = build_import_plan(base_result)

    assert plan.safe_create_staged_count == 1
    item = plan.items[0]
    assert item.action == ImportAction.SAFE_CREATE_STAGED
    assert item.category == "base_inventory"


def test_subinterface_valid_naming(base_result):
    """Eth-Trunk0.1580 (subinterface with valid naming) → safe_create_staged."""
    base_result.divergences.append(
        ComplianceDivergence(
            code="INTERFACE_MISSING_IN_NETBOX",
            severity="medium",
            scope="interfaces",
            message="Eth-Trunk0.1580 missing",
            evidence={"interface": "Eth-Trunk0.1580"},
            recommendation="Create",
            preferred_action="fix_netbox",
            object_type="interface",
            object_key="Eth-Trunk0.1580",
        )
    )

    plan = build_import_plan(base_result)

    assert plan.safe_create_staged_count == 1
    item = plan.items[0]
    assert item.action == ImportAction.SAFE_CREATE_STAGED
    assert item.category == "service"
    assert "service interface" in item.reason.lower()


def test_subinterface_invalid_naming(base_result):
    """Eth-Trunk0.Bad!Name (subinterface with invalid naming) → needs_review."""
    base_result.divergences.append(
        ComplianceDivergence(
            code="INTERFACE_MISSING_IN_NETBOX",
            severity="medium",
            scope="interfaces",
            message="Bad subinterface naming",
            evidence={"interface": "Eth-Trunk0.Bad!Name"},
            recommendation="Fix naming",
            preferred_action="review",
            object_type="interface",
            object_key="Eth-Trunk0.Bad!Name",
        )
    )

    plan = build_import_plan(base_result)

    assert plan.needs_review_count == 1
    assert plan.safe_create_staged_count == 0
    item = plan.items[0]
    assert item.action == ImportAction.NEEDS_REVIEW
    assert "pattern" in item.reason.lower() or "naming" in item.reason.lower()


def test_base_interfaces_no_naming_required(base_result):
    """Base interfaces don't need service naming convention."""
    base_result.divergences = [
        # These are base interfaces, naming is OK even without service pattern
        ComplianceDivergence(
            code="INTERFACE_MISSING_IN_NETBOX",
            severity="medium",
            scope="interfaces",
            message="Ethernet0/0/0 missing",
            evidence={},
            recommendation="Create",
            preferred_action="fix_netbox",
            object_type="interface",
            object_key="Ethernet0/0/0",
        ),
        ComplianceDivergence(
            code="INTERFACE_MISSING_IN_NETBOX",
            severity="medium",
            scope="interfaces",
            message="10GE0/0/1 missing",
            evidence={},
            recommendation="Create",
            preferred_action="fix_netbox",
            object_type="interface",
            object_key="10GE0/0/1",
        ),
    ]

    plan = build_import_plan(base_result)

    assert plan.safe_create_staged_count == 2
    for item in plan.items:
        assert item.action == ImportAction.SAFE_CREATE_STAGED
        assert item.category == "base_inventory"
