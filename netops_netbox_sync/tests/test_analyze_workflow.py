from unittest.mock import patch, MagicMock

from app.workflow.analyze_device import run_analyze_device
from app.schemas.models import (
    BGPSessionModel,
    DeviceInventory,
    InterfaceModel,
    IPAddressModel,
    VRFModel,
    VlanModel,
)
from app.schemas.analyze import AppliedInventorySummary, AnalyzeWarning
from app.schemas.netbox_inventory import NetBoxDevice, NetBoxInventory


def _empty_inventory(hostname="test-device"):
    return DeviceInventory(
        hostname=hostname,
        interfaces=[],
        ip_addresses=[],
        vlans=[],
        vrfs=[],
        bgp_sessions=[],
        route_policies=[],
        prefix_lists=[],
        as_path_filters=[],
        communities=[],
        community_lists=[],
    )


def test_run_analyze_device_returns_read_only_summary():
    driver = MagicMock()
    driver.host = "test-device"
    inventory = _empty_inventory()

    with patch("app.collectors.huawei_ne8000.HuaweiNE8000Collector.collect_all", return_value={"vrfs": ""}), \
         patch("app.collectors.huawei_ne8000.HuaweiNE8000Collector.collect_bgp_all_vrfs", return_value={}), \
         patch("app.workflow.analyze_device.build_inventory", return_value=inventory), \
         patch("app.workflow.sync_device.sync_to_netbox") as mock_sync_to_netbox, \
         patch("app.workflow.sync_device.sync_bgp_plugin") as mock_sync_bgp_plugin:
        result = run_analyze_device(driver)

    assert result.mode == "read-only"
    assert result.netbox_loaded is False
    assert result.compliance_enabled is False
    assert result.applied_summary.communities == 0
    assert result.applied_summary.community_lists == 0
    assert any(w.code == "NO_NETBOX_PARAMS" for w in result.warnings)
    assert any(w.code == "NO_NETBOX_DEVICE_ID" for w in result.warnings)
    assert mock_sync_to_netbox.call_count == 0
    assert mock_sync_bgp_plugin.call_count == 0


def test_run_analyze_device_loads_netbox_inventory_when_provided():
    driver = MagicMock()
    driver.host = "test-device"
    inventory = _empty_inventory()
    netbox_params = MagicMock()
    netbox_params.url = "http://netbox.local"
    netbox_params.token = "token"
    netbox_params.verify_ssl = False

    documented_summary = AppliedInventorySummary(
        interfaces=1,
        ip_addresses=2,
        vrfs=1,
        vlans=1,
    )
    netbox_inventory = NetBoxInventory(
        device=NetBoxDevice(id=42, name="test-device"),
        summary=documented_summary,
    )

    with patch("app.collectors.huawei_ne8000.HuaweiNE8000Collector.collect_all", return_value={"vrfs": ""}), \
         patch("app.collectors.huawei_ne8000.HuaweiNE8000Collector.collect_bgp_all_vrfs", return_value={}), \
         patch("app.workflow.analyze_device.build_inventory", return_value=inventory), \
         patch("app.workflow.analyze_device.load_netbox_inventory", return_value=(netbox_inventory, [])):
        result = run_analyze_device(driver, device_id=42, netbox=netbox_params)

    assert result.netbox_loaded is True
    assert result.compliance_enabled is True
    assert result.documented_summary == documented_summary
    assert all(w.code not in {"NETBOX_NOT_LOADED", "NO_NETBOX_DEVICE_ID", "NO_NETBOX_PARAMS"} for w in result.warnings)
    assert result.applied_summary.interfaces == 0
    assert result.summary_diff
    assert result.compliance_summary.status in {"drift_detected", "ok"}


def test_run_analyze_device_builds_object_divergences():
    driver = MagicMock()
    driver.host = "test-device"
    inventory = DeviceInventory(
        hostname="test-device",
        interfaces=[InterfaceModel(name="eth0")],
        ip_addresses=[IPAddressModel(address="192.0.2.1", interface="eth0")],
        vlans=[VlanModel(vlan_id=100)],
        vrfs=[VRFModel(name="VRF-A")],
        bgp_sessions=[BGPSessionModel(peer_ip="203.0.113.1", address_family="ipv4")],
        route_policies=[],
        prefix_lists=[],
        as_path_filters=[],
        communities=[],
        community_lists=[],
    )
    netbox_params = MagicMock()
    netbox_params.url = "http://netbox.local"
    netbox_params.token = "token"
    netbox_params.verify_ssl = False

    netbox_inventory = NetBoxInventory(
        device=NetBoxDevice(id=42, name="test-device"),
        interfaces=[],
        ip_addresses=[],
        vrfs=[],
        vlans=[],
        bgp_sessions=[],
        summary=AppliedInventorySummary(),
    )

    with patch("app.collectors.huawei_ne8000.HuaweiNE8000Collector.collect_all", return_value={"vrfs": ""}), \
         patch("app.collectors.huawei_ne8000.HuaweiNE8000Collector.collect_bgp_all_vrfs", return_value={}), \
         patch("app.workflow.analyze_device.build_inventory", return_value=inventory), \
         patch("app.workflow.analyze_device.load_netbox_inventory", return_value=(netbox_inventory, [])):
        result = run_analyze_device(driver, device_id=42, netbox=netbox_params)

    assert result.netbox_loaded is True
    assert result.compliance_enabled is True
    assert result.divergences
    assert any(d.code == "INTERFACE_MISSING_IN_NETBOX" for d in result.divergences)
    assert any(d.code == "IP_MISSING_IN_NETBOX" for d in result.divergences)
    assert any(d.code == "VRF_MISSING_IN_NETBOX" for d in result.divergences)
    assert any(d.code == "VLAN_MISSING_IN_NETBOX" for d in result.divergences)
    assert any(d.code == "BGP_PEER_MISSING_IN_NETBOX" for d in result.divergences)


def test_run_analyze_device_adds_warning_when_netbox_plugin_partial():
    driver = MagicMock()
    driver.host = "test-device"
    inventory = _empty_inventory()
    netbox_params = MagicMock()

    plugin_warning = AnalyzeWarning(
        code="NETBOX_BGP_PLUGIN_PARTIAL",
        severity="info",
        message="Plugin NetBox BGP ausente/parcial: session",
    )
    netbox_inventory = NetBoxInventory(
        device=NetBoxDevice(id=99, name="test-device"),
        summary=AppliedInventorySummary(),
    )

    with patch("app.collectors.huawei_ne8000.HuaweiNE8000Collector.collect_all", return_value={"vrfs": ""}), \
         patch("app.collectors.huawei_ne8000.HuaweiNE8000Collector.collect_bgp_all_vrfs", return_value={}), \
         patch("app.workflow.analyze_device.build_inventory", return_value=inventory), \
         patch("app.workflow.analyze_device.load_netbox_inventory", return_value=(netbox_inventory, [plugin_warning])):
        result = run_analyze_device(driver, device_id=99, netbox=netbox_params)

    assert result.netbox_loaded is True
    assert any(w.code == "NETBOX_BGP_PLUGIN_PARTIAL" for w in result.warnings)
    assert bool(result.summary_diff) is True


def test_run_analyze_device_resolves_device_id_by_host(monkeypatch):
    """No device_id, but netbox + device.host → resolves device_id → loads NetBox."""
    driver = MagicMock()
    driver.host = "104.1.2.3"
    inventory = _empty_inventory("ROUTER-A")
    netbox_params = MagicMock()

    documented_summary = AppliedInventorySummary(interfaces=2)
    netbox_inventory = NetBoxInventory(
        device=NetBoxDevice(id=1890, name="ROUTER-A"),
        summary=documented_summary,
    )
    resolve_warning = AnalyzeWarning(
        code="NETBOX_DEVICE_ID_RESOLVED",
        severity="info",
        message="device_id 1890 resolvido por device_host '104.1.2.3'.",
    )

    with patch("app.collectors.huawei_ne8000.HuaweiNE8000Collector.collect_all", return_value={"vrfs": ""}), \
         patch("app.collectors.huawei_ne8000.HuaweiNE8000Collector.collect_bgp_all_vrfs", return_value={}), \
         patch("app.workflow.analyze_device.build_inventory", return_value=inventory), \
         patch("app.workflow.analyze_device.resolve_netbox_device_id", return_value=(1890, [resolve_warning])) as mock_resolve, \
         patch("app.workflow.analyze_device.load_netbox_inventory", return_value=(netbox_inventory, [])):
        result = run_analyze_device(driver, device_id=None, netbox=netbox_params)

    mock_resolve.assert_called_once()
    assert result.device_id == 1890
    assert result.netbox_loaded is True
    assert result.compliance_enabled is True
    assert any(w.code == "NETBOX_DEVICE_ID_RESOLVED" for w in result.warnings)


def test_run_analyze_device_resolves_device_id_by_name(monkeypatch):
    """device_name provided → resolves via name → loads NetBox."""
    driver = MagicMock()
    driver.host = "10.0.0.1"
    inventory = _empty_inventory("DEV-NAMED")
    netbox_params = MagicMock()

    documented_summary = AppliedInventorySummary()
    netbox_inventory = NetBoxInventory(
        device=NetBoxDevice(id=500, name="DEV-NAMED"),
        summary=documented_summary,
    )
    resolve_warning = AnalyzeWarning(
        code="NETBOX_DEVICE_ID_RESOLVED",
        severity="info",
        message="device_id 500 resolvido por device_name 'DEV-NAMED'.",
    )

    with patch("app.collectors.huawei_ne8000.HuaweiNE8000Collector.collect_all", return_value={"vrfs": ""}), \
         patch("app.collectors.huawei_ne8000.HuaweiNE8000Collector.collect_bgp_all_vrfs", return_value={}), \
         patch("app.workflow.analyze_device.build_inventory", return_value=inventory), \
         patch("app.workflow.analyze_device.resolve_netbox_device_id", return_value=(500, [resolve_warning])) as mock_resolve, \
         patch("app.workflow.analyze_device.load_netbox_inventory", return_value=(netbox_inventory, [])):
        result = run_analyze_device(driver, device_name="DEV-NAMED", netbox=netbox_params)

    mock_resolve.assert_called_once()
    assert result.device_id == 500
    assert result.netbox_loaded is True


def test_hostname_falls_back_to_driver_host_when_inventory_empty():
    """inventory.hostname empty → use driver.host."""
    driver = MagicMock()
    driver.host = "192.0.2.5"
    inventory = _empty_inventory(hostname="")  # empty hostname

    with patch("app.collectors.huawei_ne8000.HuaweiNE8000Collector.collect_all", return_value={"vrfs": ""}), \
         patch("app.collectors.huawei_ne8000.HuaweiNE8000Collector.collect_bgp_all_vrfs", return_value={}), \
         patch("app.workflow.analyze_device.build_inventory", return_value=inventory):
        result = run_analyze_device(driver)

    assert result.hostname == "192.0.2.5"


def test_hostname_prefers_inventory_over_driver_host():
    """inventory.hostname set → use it even when driver.host differs."""
    driver = MagicMock()
    driver.host = "192.0.2.5"
    inventory = _empty_inventory(hostname="REAL-HOSTNAME")

    with patch("app.collectors.huawei_ne8000.HuaweiNE8000Collector.collect_all", return_value={"vrfs": ""}), \
         patch("app.collectors.huawei_ne8000.HuaweiNE8000Collector.collect_bgp_all_vrfs", return_value={}), \
         patch("app.workflow.analyze_device.build_inventory", return_value=inventory):
        result = run_analyze_device(driver)

    assert result.hostname == "REAL-HOSTNAME"


def test_hostname_fallback_to_netbox_device_name_when_unknown():
    """If hostname unknown and NetBox loaded, use device.name."""
    driver = MagicMock()
    driver.host = None  # Force hostname to "unknown"
    inventory = _empty_inventory(hostname=None)  # None → no hostname
    netbox_params = MagicMock()

    netbox_inventory = NetBoxInventory(
        device=NetBoxDevice(id=1890, name="PRODUCTION-ROUTER-A"),
        summary=AppliedInventorySummary(),
    )

    with patch("app.collectors.huawei_ne8000.HuaweiNE8000Collector.collect_all", return_value={"vrfs": ""}), \
         patch("app.collectors.huawei_ne8000.HuaweiNE8000Collector.collect_bgp_all_vrfs", return_value={}), \
         patch("app.workflow.analyze_device.build_inventory", return_value=inventory), \
         patch("app.workflow.analyze_device.load_netbox_inventory", return_value=(netbox_inventory, [])):
        result = run_analyze_device(driver, device_id=1890, netbox=netbox_params)

    # Hostname should be updated to NetBox device name
    assert result.hostname == "PRODUCTION-ROUTER-A"


def test_hostname_keeps_driver_host_when_netbox_device_name_empty():
    """If hostname unknown and NetBox device.name empty, keep driver.host."""
    driver = MagicMock()
    driver.host = "10.0.0.1"
    inventory = _empty_inventory(hostname=None)  # → "unknown"
    netbox_params = MagicMock()

    netbox_inventory = NetBoxInventory(
        device=NetBoxDevice(id=1890, name=""),  # empty name
        summary=AppliedInventorySummary(),
    )

    with patch("app.collectors.huawei_ne8000.HuaweiNE8000Collector.collect_all", return_value={"vrfs": ""}), \
         patch("app.collectors.huawei_ne8000.HuaweiNE8000Collector.collect_bgp_all_vrfs", return_value={}), \
         patch("app.workflow.analyze_device.build_inventory", return_value=inventory), \
         patch("app.workflow.analyze_device.load_netbox_inventory", return_value=(netbox_inventory, [])):
        result = run_analyze_device(driver, device_id=1890, netbox=netbox_params)

    # Should keep driver.host since device.name is empty (fallback condition not met)
    assert result.hostname == "10.0.0.1"


def test_compliance_enabled_true_when_netbox_and_diff_available():
    """applied + documented summaries + netbox loaded → compliance_enabled=True."""
    driver = MagicMock()
    driver.host = "10.0.0.1"
    inventory = _empty_inventory()
    netbox_params = MagicMock()

    netbox_inventory = NetBoxInventory(
        device=NetBoxDevice(id=1, name="dev"),
        summary=AppliedInventorySummary(),
    )

    with patch("app.collectors.huawei_ne8000.HuaweiNE8000Collector.collect_all", return_value={"vrfs": ""}), \
         patch("app.collectors.huawei_ne8000.HuaweiNE8000Collector.collect_bgp_all_vrfs", return_value={}), \
         patch("app.workflow.analyze_device.build_inventory", return_value=inventory), \
         patch("app.workflow.analyze_device.load_netbox_inventory", return_value=(netbox_inventory, [])):
        result = run_analyze_device(driver, device_id=1, netbox=netbox_params)

    assert result.netbox_loaded is True
    assert result.compliance_enabled is True


def test_password_not_in_result():
    """Password/token never appear in AnalyzeResult fields."""
    driver = MagicMock()
    driver.host = "10.0.0.1"
    inventory = _empty_inventory()

    with patch("app.collectors.huawei_ne8000.HuaweiNE8000Collector.collect_all", return_value={"vrfs": ""}), \
         patch("app.collectors.huawei_ne8000.HuaweiNE8000Collector.collect_bgp_all_vrfs", return_value={}), \
         patch("app.workflow.analyze_device.build_inventory", return_value=inventory):
        result = run_analyze_device(driver)

    result_dict = result.model_dump()
    import json
    serialized = json.dumps(result_dict)
    assert "password" not in serialized
    assert "secret" not in serialized.lower()


def test_sync_not_called():
    """sync_to_netbox and sync_bgp_plugin never called from analyze workflow."""
    driver = MagicMock()
    driver.host = "10.0.0.1"
    inventory = _empty_inventory()

    with patch("app.collectors.huawei_ne8000.HuaweiNE8000Collector.collect_all", return_value={"vrfs": ""}), \
         patch("app.collectors.huawei_ne8000.HuaweiNE8000Collector.collect_bgp_all_vrfs", return_value={}), \
         patch("app.workflow.analyze_device.build_inventory", return_value=inventory), \
         patch("app.workflow.sync_device.sync_to_netbox") as mock_sync, \
         patch("app.workflow.sync_device.sync_bgp_plugin") as mock_bgp_sync:
        run_analyze_device(driver)

    assert mock_sync.call_count == 0
    assert mock_bgp_sync.call_count == 0
