from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field
from app.schemas.analyze import AppliedInventorySummary


class NetBoxDevice(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    status: Optional[str] = None
    role: Optional[str] = None
    site: Optional[str] = None
    tenant: Optional[str] = None
    platform: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    primary_ip4: Optional[str] = None
    primary_ip6: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    custom_fields: Dict[str, object] = Field(default_factory=dict)


class NetBoxInterface(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    label: Optional[str] = None
    type: Optional[str] = None
    enabled: Optional[bool] = None
    description: Optional[str] = None
    mtu: Optional[int] = None
    mac_address: Optional[str] = None
    mode: Optional[str] = None
    lag: Optional[str] = None
    parent: Optional[str] = None
    untagged_vlan: Optional[int] = None
    tagged_vlans: List[str] = Field(default_factory=list)
    vrf: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    custom_fields: Dict[str, object] = Field(default_factory=dict)


class NetBoxIPAddress(BaseModel):
    id: Optional[int] = None
    address: Optional[str] = None
    status: Optional[str] = None
    role: Optional[str] = None
    dns_name: Optional[str] = None
    description: Optional[str] = None
    vrf: Optional[str] = None
    tenant: Optional[str] = None
    assigned_object_type: Optional[str] = None
    assigned_object_id: Optional[int] = None
    assigned_object_name: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    custom_fields: Dict[str, object] = Field(default_factory=dict)


class NetBoxVRF(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    rd: Optional[str] = None
    tenant: Optional[str] = None
    description: Optional[str] = None
    import_targets: List[str] = Field(default_factory=list)
    export_targets: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    custom_fields: Dict[str, object] = Field(default_factory=dict)


class NetBoxVLAN(BaseModel):
    id: Optional[int] = None
    vid: Optional[int] = None
    name: Optional[str] = None
    status: Optional[str] = None
    role: Optional[str] = None
    site: Optional[str] = None
    group: Optional[str] = None
    tenant: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    custom_fields: Dict[str, object] = Field(default_factory=dict)


class NetBoxCircuit(BaseModel):
    id: Optional[int] = None
    cid: Optional[str] = None
    provider: Optional[str] = None
    tenant: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    commit_rate: Optional[int] = None
    custom_fields: Dict[str, object] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    terminations: List[Dict[str, object]] = Field(default_factory=list)


class NetBoxBGPSession(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    status: Optional[str] = None
    device: Optional[str] = None
    vrf: Optional[str] = None
    local_as: Optional[int] = None
    remote_as: Optional[int] = None
    local_address: Optional[str] = None
    remote_address: Optional[str] = None
    address_family: Optional[str] = None
    import_policy: List[str] = Field(default_factory=list)
    export_policy: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    custom_fields: Dict[str, object] = Field(default_factory=dict)


class NetBoxRoutingPolicy(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    address_family: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    custom_fields: Dict[str, object] = Field(default_factory=dict)


class NetBoxPrefixList(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    address_family: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    custom_fields: Dict[str, object] = Field(default_factory=dict)


class NetBoxASPathFilter(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    custom_fields: Dict[str, object] = Field(default_factory=dict)


class NetBoxCommunity(BaseModel):
    id: Optional[int] = None
    value: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    custom_fields: Dict[str, object] = Field(default_factory=dict)


class NetBoxCommunityList(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    custom_fields: Dict[str, object] = Field(default_factory=dict)


class NetBoxInventory(BaseModel):
    device: NetBoxDevice
    interfaces: List[NetBoxInterface] = Field(default_factory=list)
    ip_addresses: List[NetBoxIPAddress] = Field(default_factory=list)
    vrfs: List[NetBoxVRF] = Field(default_factory=list)
    vlans: List[NetBoxVLAN] = Field(default_factory=list)
    circuits: List[NetBoxCircuit] = Field(default_factory=list)
    bgp_sessions: List[NetBoxBGPSession] = Field(default_factory=list)
    routing_policies: List[NetBoxRoutingPolicy] = Field(default_factory=list)
    prefix_lists: List[NetBoxPrefixList] = Field(default_factory=list)
    as_path_filters: List[NetBoxASPathFilter] = Field(default_factory=list)
    communities: List[NetBoxCommunity] = Field(default_factory=list)
    community_lists: List[NetBoxCommunityList] = Field(default_factory=list)
    summary: Optional['AppliedInventorySummary'] = None


try:  # pragma: no cover - compatibilidade Pydantic v1/v2
    NetBoxInventory.model_rebuild()
except AttributeError:  # pragma: no cover
    NetBoxInventory.update_forward_refs()
