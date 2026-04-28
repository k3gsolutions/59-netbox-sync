from app.compliance.object_diff import build_object_diff
from app.schemas.models import (
    BGPSessionModel,
    DeviceInventory,
    InterfaceModel,
    IPAddressModel,
    VRFModel,
    VlanModel,
)
from app.schemas.netbox_inventory import (
    NetBoxBGPSession,
    NetBoxDevice,
    NetBoxInterface,
    NetBoxIPAddress,
    NetBoxInventory,
    NetBoxVRF,
    NetBoxVLAN,
)


def test_interface_missing_in_netbox():
    applied = DeviceInventory(
        interfaces=[InterfaceModel(name="eth0", description="customer-internet:site:NB-1")],
    )
    netbox = NetBoxInventory(device=NetBoxDevice())

    divergences = build_object_diff(applied, netbox)

    assert any(d.code == "INTERFACE_MISSING_IN_NETBOX" for d in divergences)
    assert any(d.object_key == "eth0" for d in divergences)
    assert any(d.preferred_action == "fix_netbox" for d in divergences)


def test_interface_missing_on_device():
    netbox = NetBoxInventory(
        device=NetBoxDevice(),
        interfaces=[NetBoxInterface(name="eth1", custom_fields={"monitoring_enabled": True})],
    )
    applied = DeviceInventory()

    divergences = build_object_diff(applied, netbox)

    assert any(d.code == "INTERFACE_MISSING_ON_DEVICE" for d in divergences)
    assert any(d.severity == "high" for d in divergences)
    assert any(d.preferred_action == "review" for d in divergences)


def test_interface_description_mismatch():
    applied = DeviceInventory(
        interfaces=[InterfaceModel(name="eth0", description="desc-a")],
    )
    netbox = NetBoxInventory(
        device=NetBoxDevice(),
        interfaces=[NetBoxInterface(name="eth0", description="desc-b")],
    )

    divergences = build_object_diff(applied, netbox)

    assert any(d.code == "INTERFACE_DESCRIPTION_MISMATCH" for d in divergences)
    assert any(d.object_key == "eth0" for d in divergences)


def test_description_non_compliant_service_interface():
    """Service interfaces must follow naming convention."""
    applied = DeviceInventory(
        interfaces=[InterfaceModel(name="Eth-Trunk0.1580", description="not-compliant description")],
    )
    netbox = NetBoxInventory(device=NetBoxDevice(), interfaces=[NetBoxInterface(name="Eth-Trunk0.1580", description="not-compliant description")])

    divergences = build_object_diff(applied, netbox)

    assert any(d.code == "DESCRIPTION_NON_COMPLIANT" for d in divergences)
    assert any(d.preferred_action == "fix_device" for d in divergences)


def test_base_interface_no_description_non_compliant():
    """Base inventory interfaces should NOT trigger DESCRIPTION_NON_COMPLIANT."""
    test_cases = [
        ("Eth-Trunk0", "some description"),
        ("GigabitEthernet0/5/0", "not-compliant"),
        ("Ethernet0/0/0", "any text"),
        ("Management", "mgmt interface"),
        ("10GE0/0/1", "ten gig"),
    ]

    for iface_name, description in test_cases:
        applied = DeviceInventory(
            interfaces=[InterfaceModel(name=iface_name, description=description)],
        )
        netbox = NetBoxInventory(
            device=NetBoxDevice(),
            interfaces=[NetBoxInterface(name=iface_name, description=description)]
        )

        divergences = build_object_diff(applied, netbox)

        # Should NOT have DESCRIPTION_NON_COMPLIANT for base interfaces
        assert not any(d.code == "DESCRIPTION_NON_COMPLIANT" for d in divergences), \
            f"Base interface {iface_name} should not trigger DESCRIPTION_NON_COMPLIANT"


def test_base_interface_still_detects_mismatch():
    """Base interfaces should still detect description mismatch (review only)."""
    applied = DeviceInventory(
        interfaces=[InterfaceModel(name="Eth-Trunk0", description="desc-a")],
    )
    netbox = NetBoxInventory(
        device=NetBoxDevice(),
        interfaces=[NetBoxInterface(name="Eth-Trunk0", description="desc-b")]
    )

    divergences = build_object_diff(applied, netbox)

    # Should have MISMATCH but NOT DESCRIPTION_NON_COMPLIANT
    assert any(d.code == "INTERFACE_DESCRIPTION_MISMATCH" for d in divergences)
    assert not any(d.code == "DESCRIPTION_NON_COMPLIANT" for d in divergences)


def test_ip_missing_in_netbox():
    applied = DeviceInventory(ip_addresses=[IPAddressModel(address="192.0.2.1", interface="eth0")])
    netbox = NetBoxInventory(device=NetBoxDevice())

    divergences = build_object_diff(applied, netbox)

    assert any(d.code == "IP_MISSING_IN_NETBOX" for d in divergences)
    assert any(d.object_key == "192.0.2.1" for d in divergences)


def test_vrf_missing_on_device():
    netbox = NetBoxInventory(device=NetBoxDevice(), vrfs=[NetBoxVRF(name="VRF-A")])
    applied = DeviceInventory()

    divergences = build_object_diff(applied, netbox)

    assert any(d.code == "VRF_MISSING_ON_DEVICE" for d in divergences)
    assert any(d.object_key == "VRF-A" for d in divergences)


def test_vlan_missing_in_netbox():
    applied = DeviceInventory(vlans=[VlanModel(vlan_id=100)])
    netbox = NetBoxInventory(device=NetBoxDevice())

    divergences = build_object_diff(applied, netbox)

    assert any(d.code == "VLAN_MISSING_IN_NETBOX" for d in divergences)
    assert any(d.object_key == "100" for d in divergences)


def test_bgp_peer_missing_in_netbox():
    applied = DeviceInventory(
        bgp_sessions=[BGPSessionModel(peer_ip="203.0.113.1", address_family="ipv4")],
    )
    netbox = NetBoxInventory(device=NetBoxDevice())

    divergences = build_object_diff(applied, netbox)

    assert any(d.code == "BGP_PEER_MISSING_IN_NETBOX" for d in divergences)
    assert any("203.0.113.1" in d.object_key for d in divergences)


def test_bgp_asn_mismatch():
    applied = DeviceInventory(
        bgp_sessions=[BGPSessionModel(peer_ip="203.0.113.1", address_family="ipv4", peer_as=65001)],
    )
    netbox = NetBoxInventory(
        device=NetBoxDevice(),
        bgp_sessions=[NetBoxBGPSession(remote_address="203.0.113.1", address_family="ipv4", remote_as=65002)],
    )

    divergences = build_object_diff(applied, netbox)

    assert any(d.code == "BGP_ASN_MISMATCH" for d in divergences)


def test_bgp_policy_mismatch():
    applied = DeviceInventory(
        bgp_sessions=[BGPSessionModel(peer_ip="203.0.113.1", address_family="ipv4", import_policy="IN_POLICY")],
    )
    netbox = NetBoxInventory(
        device=NetBoxDevice(),
        bgp_sessions=[NetBoxBGPSession(remote_address="203.0.113.1", address_family="ipv4", import_policy=["OTHER_POLICY"])],
    )

    divergences = build_object_diff(applied, netbox)

    assert any(d.code == "BGP_POLICY_MISMATCH" for d in divergences)


def test_no_divergences_when_objects_match():
    applied = DeviceInventory(
        interfaces=[InterfaceModel(name="eth0")],
        ip_addresses=[IPAddressModel(address="192.0.2.1", interface="eth0")],
        vrfs=[VRFModel(name="VRF-A")],
        vlans=[VlanModel(vlan_id=100)],
        bgp_sessions=[BGPSessionModel(peer_ip="203.0.113.1", address_family="ipv4")],
    )
    netbox = NetBoxInventory(
        device=NetBoxDevice(),
        interfaces=[NetBoxInterface(name="eth0")],
        ip_addresses=[NetBoxIPAddress(address="192.0.2.1")],
        vrfs=[NetBoxVRF(name="VRF-A")],
        vlans=[NetBoxVLAN(vid=100)],
        bgp_sessions=[NetBoxBGPSession(remote_address="203.0.113.1", address_family="ipv4")],
    )

    divergences = build_object_diff(applied, netbox)

    assert divergences == []


def test_build_object_diff_handles_empty_lists():
    applied = DeviceInventory()
    netbox = NetBoxInventory(device=NetBoxDevice())

    divergences = build_object_diff(applied, netbox)

    assert divergences == []
