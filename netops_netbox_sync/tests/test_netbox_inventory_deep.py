from types import SimpleNamespace

from pynetbox.core.query import RequestError

from app.netbox.inventory import load_netbox_inventory, resolve_netbox_device_id
from app.schemas.netbox_inventory import NetBoxInventory
from app.api.schemas import NetBoxParams


class FakeRecord:
    def __init__(self, data):
        self._data = data
        # expose .id as attribute so _safe_id works on pynetbox-like objects
        self.id = data.get("id")

    def serialize(self):
        return self._data


class FakeCollection:
    def __init__(self, records):
        self._records = [FakeRecord(record) for record in records]

    def filter(self, **_kwargs):
        return self._records

    def all(self):  # pragma: no cover - apenas para compat
        return self._records


class FakeLookup:
    def __init__(self, records):
        self._records = {record["id"]: FakeRecord(record) for record in records}

    def get(self, record_id):
        return self._records[record_id]


class FakeCircuitTerminations(FakeCollection):
    pass


class FakeCircuits:
    def __init__(self, records):
        self._records = {record["id"]: FakeRecord(record) for record in records}

    def get(self, record_id):
        return self._records[record_id]


class FakeBGPEndpoint:
    def __init__(self, records, raises: bool = False):
        self._records = [FakeRecord(record) for record in records]
        self._raises = raises

    def filter(self, **_kwargs):
        if self._raises:
            raise RequestError("endpoint indisponível")
        return self._records

    def all(self):
        return self.filter()


class FakeBGPPlugin:
    def __init__(self, raises: bool = False):
        self.session = FakeBGPEndpoint(
            [
                {
                    "id": 501,
                    "name": "BGP-A",
                    "status": {"value": "active"},
                    "device": {"name": "dev1"},
                    "vrf": {"name": "VRF-A"},
                    "local_as": 65001,
                    "remote_as": 65002,
                    "local_address": {"address": "10.0.0.1"},
                    "remote_address": {"address": "10.0.0.2"},
                    "address_family": {"value": "ipv4"},
                    "import_policies": [{"name": "RP-IN"}],
                    "export_policies": [{"name": "RP-OUT"}],
                    "tags": [{"slug": "service"}],
                    "custom_fields": {"monitoring": True},
                }
            ],
            raises=raises,
        )
        self.routing_policy = FakeBGPEndpoint(
            [
                {
                    "id": 601,
                    "name": "RP-IN",
                    "description": "Import",
                    "type": {"value": "import"},
                    "address_family": {"value": "ipv4"},
                }
            ],
            raises=raises,
        )
        self.prefix_list = FakeBGPEndpoint(
            [
                {
                    "id": 701,
                    "name": "PL-IN",
                    "family": {"value": "ipv4"},
                }
            ],
            raises=raises,
        )
        self.as_path_filter = FakeBGPEndpoint(
            [
                {
                    "id": 801,
                    "name": "AS-FILTER",
                }
            ],
            raises=raises,
        )
        self.community = FakeBGPEndpoint(
            [
                {
                    "id": 901,
                    "value": "65001:10",
                    "status": {"value": "active"},
                }
            ],
            raises=raises,
        )
        self.community_list = FakeBGPEndpoint(
            [
                {
                    "id": 1001,
                    "name": "COMM-LIST",
                }
            ],
            raises=raises,
        )


class FakeNetBox:
    def __init__(self, with_bgp: bool = True, bgp_raises: bool = False):
        self.dcim = FakeDCIM()
        self.ipam = FakeIPAM()
        self.circuits = FakeCircuitsModule()
        self.plugins = SimpleNamespace(bgp=FakeBGPPlugin(bgp_raises)) if with_bgp else SimpleNamespace()


class FakeDCIM:
    def __init__(self):
        device = {
            "id": 1,
            "name": "dev1",
            "status": {"value": "active"},
            "device_role": {"name": "router"},
            "site": {"name": "POP-A"},
            "tenant": {"name": "tenant-a"},
            "platform": {"name": "huawei"},
            "device_type": {
                "model": "NE8000",
                "manufacturer": {"name": "Huawei"},
            },
            "primary_ip4": {"address": "10.0.0.10"},
            "primary_ip6": None,
            "tags": [{"slug": "core"}],
            "custom_fields": {"monitoring_enabled": True},
        }
        interfaces = [
            {
                "id": 101,
                "name": "Gig0/0/0",
                "type": {"value": "virtual"},
                "enabled": True,
                "description": "customer-internet:acme:NB-1",
                "mtu": 9216,
                "lag": None,
                "parent": None,
                "untagged_vlan": {"id": 201, "vid": 100},
                "tagged_vlans": [{"id": 202, "vid": 200}],
                "tags": [{"slug": "cust"}],
                "custom_fields": {"service_type": "customer-internet"},
            }
        ]
        self.devices = SimpleNamespace(get=lambda _device_id: FakeRecord(device))
        self.interfaces = SimpleNamespace(filter=lambda **_kwargs: [FakeRecord(i) for i in interfaces])


class FakeIPAM:
    def __init__(self):
        ip_addresses = [
            {
                "id": 301,
                "address": "192.0.2.1/30",
                "status": {"value": "active"},
                "vrf": {"id": 401, "name": "VRF-A"},
                "assigned_object": {"id": 101, "name": "Gig0/0/0"},
            }
        ]
        vrfs = [
            {
                "id": 401,
                "name": "VRF-A",
                "rd": "65001:1",
                "tenant": {"name": "tenant-a"},
                "import_targets": ["65001:100"],
                "export_targets": ["65001:100"],
            }
        ]
        vlans = [
            {
                "id": 201,
                "vid": 100,
                "name": "CUST100",
                "status": {"value": "active"},
                "site": {"name": "POP-A"},
            },
            {
                "id": 202,
                "vid": 200,
                "name": "TRUNK200",
                "status": {"value": "active"},
                "site": {"name": "POP-A"},
            },
        ]
        self.ip_addresses = SimpleNamespace(filter=lambda **_kwargs: [FakeRecord(ip) for ip in ip_addresses])
        self.vrfs = FakeLookup(vrfs)
        self.vlans = FakeLookup(vlans)


class FakeCircuitsModule:
    def __init__(self):
        terminations = [
            {
                "id": 901,
                "term_side": "A",
                "circuit": {"id": 1000},
                "pp_info": None,
                "interface": {"name": "Gig0/0/0"},
            }
        ]
        circuits = [
            {
                "id": 1000,
                "cid": "CCT-1",
                "provider": {"name": "Provider"},
                "status": {"value": "active"},
                "tenant": {"name": "tenant-a"},
                "type": {"name": "Internet"},
                "commit_rate": 1000,
                "tags": [],
                "custom_fields": {},
            }
        ]
        self.circuit_terminations = FakeCircuitTerminations(terminations)
        self.circuits = FakeCircuits(circuits)


# ---------------------------------------------------------------------------
# Core mapping tests
# ---------------------------------------------------------------------------

def test_load_netbox_inventory_core_mapping(monkeypatch):
    fake_nb = FakeNetBox(with_bgp=True)

    monkeypatch.setattr("app.netbox.inventory._open_netbox", lambda _params: fake_nb)

    inventory, warnings = load_netbox_inventory(SimpleNamespace(), device_id=1)

    assert isinstance(inventory, NetBoxInventory)
    assert inventory.device.name == "dev1"
    assert inventory.summary.interfaces == 1
    assert inventory.summary.ip_addresses == 1
    assert inventory.summary.vrfs == 1
    assert inventory.summary.vlans == 2
    assert inventory.summary.bgp_sessions == 1
    assert inventory.circuits[0].cid == "CCT-1"
    assert warnings == []


def test_load_netbox_inventory_without_bgp_plugin(monkeypatch):
    fake_nb = FakeNetBox(with_bgp=False)
    monkeypatch.setattr("app.netbox.inventory._open_netbox", lambda _params: fake_nb)

    _inventory, warnings = load_netbox_inventory(SimpleNamespace(), device_id=1)

    assert any(w.code == "NETBOX_BGP_PLUGIN_PARTIAL" for w in warnings)


def test_load_netbox_inventory_bgp_endpoint_failure(monkeypatch):
    fake_nb = FakeNetBox(with_bgp=True, bgp_raises=True)
    monkeypatch.setattr("app.netbox.inventory._open_netbox", lambda _params: fake_nb)

    _inventory, warnings = load_netbox_inventory(SimpleNamespace(), device_id=1)

    assert any(w.code == "NETBOX_BGP_PLUGIN_PARTIAL" for w in warnings)


# ---------------------------------------------------------------------------
# Int field handling tests — prevent 'int' object has no attribute 'get'
# ---------------------------------------------------------------------------

def _make_fake_nb_with_int_fields():
    """NetBox returning int for vlan/vrf/assigned_object fields."""

    class IntFieldDCIM:
        def __init__(self):
            device = {
                "id": 10,
                "name": "dev-int",
                "status": {"value": "active"},
                "device_type": 5,  # int instead of dict
                "tags": [],
                "custom_fields": {},
            }
            interfaces = [
                {
                    "id": 201,
                    "name": "Eth0/0",
                    "untagged_vlan": 100,         # int instead of dict
                    "tagged_vlans": [200, 300],   # list of ints
                    "tags": ["service", "core"],  # strings instead of dicts
                    "custom_fields": None,         # None instead of dict
                }
            ]
            self.devices = SimpleNamespace(get=lambda _id: FakeRecord(device))
            self.interfaces = SimpleNamespace(filter=lambda **_kw: [FakeRecord(i) for i in interfaces])

    class IntFieldIPAM:
        def __init__(self):
            ip_addresses = [
                {
                    "id": 401,
                    "address": "10.0.0.1/24",
                    "status": {"value": "active"},
                    "vrf": 999,              # int instead of dict
                    "assigned_object": 123,  # int instead of dict
                }
            ]
            self.ip_addresses = SimpleNamespace(filter=lambda **_kw: [FakeRecord(ip) for ip in ip_addresses])
            self.vrfs = SimpleNamespace(get=lambda _id: None)
            self.vlans = SimpleNamespace(get=lambda _id: None)

    class EmptyCircuits:
        circuit_terminations = SimpleNamespace(filter=lambda **_kw: [])
        circuits = SimpleNamespace(get=lambda _id: None)

    nb = SimpleNamespace(
        dcim=IntFieldDCIM(),
        ipam=IntFieldIPAM(),
        circuits=EmptyCircuits(),
        plugins=SimpleNamespace(),
    )
    return nb


def test_load_netbox_inventory_int_untagged_vlan(monkeypatch):
    """untagged_vlan=100 (int) must not raise 'int has no .get'."""
    fake_nb = _make_fake_nb_with_int_fields()
    monkeypatch.setattr("app.netbox.inventory._open_netbox", lambda _params: fake_nb)

    inventory, warnings = load_netbox_inventory(SimpleNamespace(), device_id=10)

    assert isinstance(inventory, NetBoxInventory)
    assert inventory.interfaces[0].name == "Eth0/0"
    # No NETBOX_LOAD_FAILED warning
    assert not any(w.code == "NETBOX_LOAD_FAILED" for w in warnings)


def test_load_netbox_inventory_int_tagged_vlans(monkeypatch):
    """tagged_vlans=[200, 300] (list of ints) must not raise."""
    fake_nb = _make_fake_nb_with_int_fields()
    monkeypatch.setattr("app.netbox.inventory._open_netbox", lambda _params: fake_nb)

    inventory, warnings = load_netbox_inventory(SimpleNamespace(), device_id=10)

    assert not any(w.code == "NETBOX_LOAD_FAILED" for w in warnings)


def test_load_netbox_inventory_int_assigned_object(monkeypatch):
    """assigned_object=123 (int) must not raise 'int has no .get'."""
    fake_nb = _make_fake_nb_with_int_fields()
    monkeypatch.setattr("app.netbox.inventory._open_netbox", lambda _params: fake_nb)

    inventory, warnings = load_netbox_inventory(SimpleNamespace(), device_id=10)

    assert not any(w.code == "NETBOX_LOAD_FAILED" for w in warnings)
    assert inventory.ip_addresses[0].assigned_object_id == 123


def test_load_netbox_inventory_string_tags(monkeypatch):
    """tags as plain strings must not raise."""
    fake_nb = _make_fake_nb_with_int_fields()
    monkeypatch.setattr("app.netbox.inventory._open_netbox", lambda _params: fake_nb)

    inventory, warnings = load_netbox_inventory(SimpleNamespace(), device_id=10)

    assert not any(w.code == "NETBOX_LOAD_FAILED" for w in warnings)
    assert "service" in inventory.interfaces[0].tags


def test_load_netbox_inventory_null_custom_fields(monkeypatch):
    """custom_fields=None must not raise."""
    fake_nb = _make_fake_nb_with_int_fields()
    monkeypatch.setattr("app.netbox.inventory._open_netbox", lambda _params: fake_nb)

    inventory, warnings = load_netbox_inventory(SimpleNamespace(), device_id=10)

    assert not any(w.code == "NETBOX_LOAD_FAILED" for w in warnings)
    assert inventory.interfaces[0].custom_fields == {}


def test_load_netbox_inventory_int_device_type(monkeypatch):
    """device_type=5 (int) must not raise and model stays None."""
    fake_nb = _make_fake_nb_with_int_fields()
    monkeypatch.setattr("app.netbox.inventory._open_netbox", lambda _params: fake_nb)

    inventory, warnings = load_netbox_inventory(SimpleNamespace(), device_id=10)

    assert not any(w.code == "NETBOX_LOAD_FAILED" for w in warnings)
    assert inventory.device.model is None


# ---------------------------------------------------------------------------
# resolve_netbox_device_id tests
# ---------------------------------------------------------------------------

def _make_netbox_params():
    return SimpleNamespace(url="http://nb.local", token="tok", verify_ssl=False)


def test_resolve_device_id_when_provided_directly():
    """device_id given → return as-is, no lookup."""
    result_id, warnings = resolve_netbox_device_id(
        _make_netbox_params(), device_id=42
    )
    assert result_id == 42
    assert warnings == []


def test_resolve_device_id_by_name(monkeypatch):
    """device_name given → nb.dcim.devices.get(name=...) → return id."""
    device_record = FakeRecord({"id": 1890, "name": "MYDEVICE"})
    fake_nb = SimpleNamespace(
        dcim=SimpleNamespace(
            devices=SimpleNamespace(get=lambda **_kw: device_record)
        )
    )
    monkeypatch.setattr("app.netbox.inventory._open_netbox", lambda _p: fake_nb)

    result_id, warnings = resolve_netbox_device_id(
        _make_netbox_params(), device_name="MYDEVICE"
    )

    assert result_id == 1890
    assert any(w.code == "NETBOX_DEVICE_ID_RESOLVED" for w in warnings)
    assert "device_name" in warnings[0].message


def test_resolve_device_id_by_name_not_found(monkeypatch):
    """device_name not in NetBox → None + NOT_FOUND warning."""
    fake_nb = SimpleNamespace(
        dcim=SimpleNamespace(
            devices=SimpleNamespace(get=lambda **_kw: None)
        )
    )
    monkeypatch.setattr("app.netbox.inventory._open_netbox", lambda _p: fake_nb)

    result_id, warnings = resolve_netbox_device_id(
        _make_netbox_params(), device_name="NOTEXIST"
    )

    assert result_id is None
    assert any(w.code == "NETBOX_DEVICE_ID_NOT_FOUND" for w in warnings)


def test_resolve_device_id_by_host_via_primary_ip(monkeypatch):
    """device_host → nb.dcim.devices.filter(primary_ip4=host) → return id."""
    device_record = FakeRecord({"id": 777, "name": "ROUTER-1"})
    fake_nb = SimpleNamespace(
        dcim=SimpleNamespace(
            devices=SimpleNamespace(
                filter=lambda **kw: [device_record] if "primary_ip4" in kw else []
            )
        ),
        ipam=SimpleNamespace(
            ip_addresses=SimpleNamespace(filter=lambda **_kw: [])
        ),
    )
    monkeypatch.setattr("app.netbox.inventory._open_netbox", lambda _p: fake_nb)

    result_id, warnings = resolve_netbox_device_id(
        _make_netbox_params(), device_host="104.1.2.3"
    )

    assert result_id == 777
    assert any(w.code == "NETBOX_DEVICE_ID_RESOLVED" for w in warnings)
    assert "device_host" in warnings[0].message


def test_resolve_device_id_by_host_via_ip_assignment(monkeypatch):
    """IP found via ipam, assigned_object.device.id → return id."""
    ip_record = FakeRecord({
        "id": 500,
        "address": "104.1.2.3/32",
        "assigned_object": {
            "id": 101,
            "name": "Gig0/0",
            "device": {"id": 888, "name": "DEV-A"},
        },
    })
    fake_nb = SimpleNamespace(
        dcim=SimpleNamespace(
            devices=SimpleNamespace(filter=lambda **_kw: []),
            interfaces=SimpleNamespace(get=lambda _id: None),
        ),
        ipam=SimpleNamespace(
            ip_addresses=SimpleNamespace(filter=lambda **_kw: [ip_record])
        ),
    )
    monkeypatch.setattr("app.netbox.inventory._open_netbox", lambda _p: fake_nb)

    result_id, warnings = resolve_netbox_device_id(
        _make_netbox_params(), device_host="104.1.2.3"
    )

    assert result_id == 888
    assert any(w.code == "NETBOX_DEVICE_ID_RESOLVED" for w in warnings)


def test_resolve_device_id_ambiguous_multiple_devices(monkeypatch):
    """Multiple devices with same primary_ip4 → None + AMBIGUOUS warning."""
    dev1 = FakeRecord({"id": 1, "name": "DEV-1"})
    dev2 = FakeRecord({"id": 2, "name": "DEV-2"})
    fake_nb = SimpleNamespace(
        dcim=SimpleNamespace(
            devices=SimpleNamespace(filter=lambda **_kw: [dev1, dev2])
        ),
        ipam=SimpleNamespace(
            ip_addresses=SimpleNamespace(filter=lambda **_kw: [])
        ),
    )
    monkeypatch.setattr("app.netbox.inventory._open_netbox", lambda _p: fake_nb)

    result_id, warnings = resolve_netbox_device_id(
        _make_netbox_params(), device_host="10.0.0.1"
    )

    assert result_id is None
    assert any(w.code == "NETBOX_DEVICE_ID_AMBIGUOUS" for w in warnings)


def test_resolve_device_id_host_not_found(monkeypatch):
    """No device/IP found for host → None + NOT_FOUND warning."""
    fake_nb = SimpleNamespace(
        dcim=SimpleNamespace(
            devices=SimpleNamespace(filter=lambda **_kw: [])
        ),
        ipam=SimpleNamespace(
            ip_addresses=SimpleNamespace(filter=lambda **_kw: [])
        ),
    )
    monkeypatch.setattr("app.netbox.inventory._open_netbox", lambda _p: fake_nb)

    result_id, warnings = resolve_netbox_device_id(
        _make_netbox_params(), device_host="1.2.3.4"
    )

    assert result_id is None
    assert any(w.code == "NETBOX_DEVICE_ID_NOT_FOUND" for w in warnings)


def test_resolve_device_id_api_error(monkeypatch):
    """API error → None + RESOLVE_FAILED warning."""
    def _raise(**_kw):
        raise Exception("connection refused")

    fake_nb = SimpleNamespace(
        dcim=SimpleNamespace(
            devices=SimpleNamespace(filter=_raise)
        ),
        ipam=SimpleNamespace(
            ip_addresses=SimpleNamespace(filter=_raise)
        ),
    )
    monkeypatch.setattr("app.netbox.inventory._open_netbox", lambda _p: fake_nb)

    result_id, warnings = resolve_netbox_device_id(
        _make_netbox_params(), device_host="1.2.3.4"
    )

    assert result_id is None
    assert any(w.code == "NETBOX_DEVICE_ID_RESOLVE_FAILED" for w in warnings)
