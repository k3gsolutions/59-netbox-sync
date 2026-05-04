"""Tests for compliance compare engine."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from webui.services.compliance_compare import (
    compare_bgp,
    compare_device_inventory_to_policy,
    compare_interfaces,
    compare_prefix_lists,
    compare_route_policies,
    compare_snmp,
    classify_finding,
)
from webui.services.compliance_policy_loader import load_compliance_policy_registry


@pytest.fixture(scope="module")
def registry():
    return load_compliance_policy_registry("policies/compliance")


def test_compare_tolerates_incomplete_inventory(registry):
    findings = compare_device_inventory_to_policy({}, registry)
    assert findings
    assert any(finding["rule_id"] == "interface.inventory.missing" for finding in findings)


def test_interface_without_description_finding(registry):
    parsed = {"device_id": 1890, "interfaces": [{"name": "GigabitEthernet0/0/0", "physical": "up", "protocol": "up"}]}
    findings = compare_interfaces(parsed, registry)
    assert any(finding["rule_id"] == "interface.description.required" for finding in findings)


def test_bgp_peer_without_description_finding(registry):
    parsed = {"device_id": 1890, "bgp_peers": [{"peer_ip": "192.0.2.10", "asn": "65001", "state": "Established"}]}
    findings = compare_bgp(parsed, registry)
    assert any(finding["rule_id"] == "bgp.peer.description.required" for finding in findings)


def test_bgp_peer_non_established_warning(registry):
    parsed = {
        "device_id": 1890,
        "bgp_peers": [{"peer_ip": "192.0.2.10", "asn": "65001", "state": "Idle", "description": "Peer test"}],
    }
    findings = compare_bgp(parsed, registry)
    assert any(finding["rule_id"] == "bgp.peer.state.not_established" for finding in findings)


def test_route_policy_without_nodes_finding(registry):
    parsed = {"device_id": 1890, "route_policies": {"AS1-SITE-CTX-SVC-IPv4-Import": {"name": "AS1-SITE-CTX-SVC-IPv4-Import", "nodes": []}}}
    findings = compare_route_policies(parsed, registry)
    assert any(finding["rule_id"] == "route_policy.nodes.missing" for finding in findings)


def test_prefix_list_empty_finding(registry):
    parsed = {"device_id": 1890, "ip_prefixes": {"CUSTOMER-FOO-IPv4": {"name": "CUSTOMER-FOO-IPv4", "entries": []}}}
    findings = compare_prefix_lists(parsed, registry)
    assert any(finding["rule_id"] == "prefix_list.entries.missing" for finding in findings)


def test_snmp_absent_generates_warning(registry):
    findings = compare_snmp({"device_id": 1890}, registry)
    assert any(finding["rule_id"] == "snmp.sys_info.missing" for finding in findings)


def test_finding_flags_false(registry):
    parsed = {"device_id": 1890, "interfaces": [{"name": "GigabitEthernet0/0/0"}]}
    findings = compare_interfaces(parsed, registry)
    assert findings
    assert all(finding["write_required"] is False for finding in findings)
    assert all(finding["approval_required"] is False for finding in findings)


def test_classify_finding_uses_severity_policy(registry):
    severity_policy = registry["files"]["compliance-severity-policy.yaml"]
    finding = classify_finding({"rule_id": "PREFIX-001", "finding_type": "optional_enrichment"}, severity_policy)
    assert finding["severity"] in {"info", "warning", "error", "blocker"}
