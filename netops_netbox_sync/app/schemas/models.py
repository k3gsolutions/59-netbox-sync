from pydantic import BaseModel
from typing import List, Optional


class InterfaceModel(BaseModel):
    name: str
    admin_status: Optional[str] = None
    oper_status: Optional[str] = None
    description: Optional[str] = None
    mtu: Optional[int] = None
    vrf: Optional[str] = None
    type: Optional[str] = "other"
    lag_parent: Optional[str] = None


class IPAddressModel(BaseModel):
    address: str
    interface: str
    vrf: Optional[str] = None


class VlanModel(BaseModel):
    vlan_id: int
    name: Optional[str] = None


class VRFModel(BaseModel):
    name: str
    rd: Optional[str] = None


class BGPSessionModel(BaseModel):
    peer_ip: str
    peer_as: Optional[int] = None
    local_as: Optional[int] = None
    router_id: Optional[str] = None        # BGP router-id local (usado como local_address)
    peer_type: Optional[str] = None        # EBGP | IBGP
    state: Optional[str] = None
    description: Optional[str] = None
    vrf: Optional[str] = None             # None = global/default VRF
    address_family: Optional[str] = "ipv4"  # ipv4 | ipv6 | vpnv4 | vpnv6
    import_policy: Optional[str] = None
    export_policy: Optional[str] = None
    import_prefix_list: Optional[str] = None
    export_prefix_list: Optional[str] = None


class RoutePolicyNodeModel(BaseModel):
    action: str
    sequence: int
    match: List[str] = []
    apply: List[str] = []


class RoutePolicyModel(BaseModel):
    name: str
    nodes: List[RoutePolicyNodeModel] = []


class PrefixListEntryModel(BaseModel):
    index: int
    action: str
    prefix: str
    options: Optional[str] = None


class PrefixListModel(BaseModel):
    name: str
    entries: List[PrefixListEntryModel] = []


class ASPathFilterEntryModel(BaseModel):
    index: int
    action: str
    regex: str


class ASPathFilterModel(BaseModel):
    name: str
    entries: List[ASPathFilterEntryModel] = []


class CommunityListEntryModel(BaseModel):
    index: int
    action: str          # permit | deny
    community: str       # valor exato (basic) ou regex (advanced)


class CommunityListModel(BaseModel):
    name: str
    type: str = "basic"  # basic | advanced
    entries: List[CommunityListEntryModel] = []


class DeviceInventory(BaseModel):
    hostname: Optional[str] = None
    interfaces: List[InterfaceModel] = []
    ip_addresses: List[IPAddressModel] = []
    vlans: List[VlanModel] = []
    vrfs: List[VRFModel] = []
    bgp_sessions: List[BGPSessionModel] = []
    route_policies: List[RoutePolicyModel] = []
    prefix_lists: List[PrefixListModel] = []
    as_path_filters: List[ASPathFilterModel] = []
    communities: List[str] = []          # valores X:Y individuais
    community_lists: List[CommunityListModel] = []
