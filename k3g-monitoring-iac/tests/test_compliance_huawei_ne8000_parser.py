"""Tests for Huawei NE8000 parser baseline."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from webui.services.compliance_huawei_ne8000_parser import (
    parse_display_bgp_peer,
    parse_display_device,
    parse_display_interface_brief,
    parse_display_ip_interface_brief,
    parse_display_ip_ip_prefix,
    parse_display_ipv6_interface_brief,
    parse_display_ipv6_prefix,
    parse_display_route_policy,
    parse_display_snmp_agent_sys_info,
    parse_display_version,
    parse_redacted_command_file,
)


def test_interface_brief_basic():
    parsed = parse_display_interface_brief(
        """
Interface                       Physical   Protocol  Description
GigabitEthernet0/0/0            up         up        uplink
GigabitEthernet0/0/1            down       down      access
"""
    )
    assert len(parsed["interfaces"]) == 2
    assert parsed["interfaces"][0]["name"] == "GigabitEthernet0/0/0"
    assert parsed["interfaces"][0]["physical"] == "up"


def test_ip_interface_brief_basic():
    parsed = parse_display_ip_interface_brief(
        """
Interface                       IP Address/Mask      Physical  Protocol  Description
GigabitEthernet0/0/0            192.0.2.1/32         up        up        uplink
"""
    )
    assert len(parsed["ipv4_interfaces"]) == 1
    assert parsed["ipv4_interfaces"][0]["ip_address"] == "192.0.2.1/32"


def test_ipv6_interface_brief_basic():
    parsed = parse_display_ipv6_interface_brief(
        """
Interface                       IPv6 Address                     Physical  Protocol
GigabitEthernet0/0/0            2001:db8::1/64                   up        up
"""
    )
    assert len(parsed["ipv6_interfaces"]) == 1
    assert parsed["ipv6_interfaces"][0]["ipv6_address"] == "2001:db8::1/64"


def test_bgp_peer_basic():
    parsed = parse_display_bgp_peer(
        """
Peer IP          ASN     State
192.0.2.10       65001   Established
"""
    )
    assert len(parsed["bgp_peers"]) == 1
    assert parsed["bgp_peers"][0]["peer_ip"] == "192.0.2.10"


def test_route_policy_basic():
    parsed = parse_display_route_policy(
        """
route-policy RP1 permit node 10
 if-match ip-prefix P1
 apply community 100:1
"""
    )
    assert "RP1" in parsed["route_policies"]
    assert parsed["route_policies"]["RP1"]["nodes"][0]["node"] == 10


def test_ip_prefix_basic():
    parsed = parse_display_ip_ip_prefix(
        """
ip ip-prefix P1 index 10 permit 10.0.0.0 24
"""
    )
    assert "P1" in parsed["ip_prefixes"]
    assert parsed["ip_prefixes"]["P1"]["entries"][0]["index"] == 10


def test_ipv6_prefix_basic():
    parsed = parse_display_ipv6_prefix(
        """
ipv6 prefix V6P1 index 10 permit 2001:db8::/64
"""
    )
    assert "V6P1" in parsed["ipv6_prefixes"]


def test_device_and_version_helpers():
    version = parse_display_version(
        """
Huawei Versatile Routing Platform Software
VRP (R) software, Version 8.230 (NE8000 V800R013C00SPC300)
System Name: RX01
"""
    )
    device = parse_display_device(
        """
Device type: NE8000
Slot 0  Main board
"""
    )
    assert "8.230" in (version["version"] or "")
    assert version["system_name"] == "RX01"
    assert device["components"]


def test_snmp_agent_sys_info_basic():
    parsed = parse_display_snmp_agent_sys_info(
        """
sysName: RX01
sysContact: noc@example.com
sysLocation: MNS
snmp-agent sys-info version v3
"""
    )
    assert parsed["sys_name"] == "RX01"
    assert parsed["contact"] == "noc@example.com"


def test_empty_output_warns():
    parsed = parse_redacted_command_file("display version", "")
    assert parsed["warnings"]
    assert not parsed["skipped"]


def test_unknown_command_skipped():
    parsed = parse_redacted_command_file("display something new", "whatever")
    assert parsed["skipped"] is True
    assert parsed["warnings"]
