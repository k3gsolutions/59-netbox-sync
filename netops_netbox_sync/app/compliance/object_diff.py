import re
from typing import Dict, Iterable, List, Optional, Set, Tuple

from app.schemas.compliance import ComplianceDivergence
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
    NetBoxInventory,
    NetBoxInterface,
    NetBoxIPAddress,
    NetBoxVRF,
    NetBoxVLAN,
)

SERVICE_SLUG_PATTERN = re.compile(
    r"^(customer-internet|customer-l2vpn|customer-l3vpn|customer-transport|carrier-transit|carrier-peering|"
    r"ix-public|cdn-cache|infra-backbone|infra-management):[a-z0-9-]{2,32}:NB-[0-9]+(:[\w-]+)?$",
    re.IGNORECASE,
)


def is_compliant_service_slug(description: Optional[str]) -> bool:
    if not description:
        return False
    return bool(SERVICE_SLUG_PATTERN.match(description.strip()))


def _normalize_string(value: Optional[str]) -> str:
    return (value or "").strip()


def _normalize_key(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized if normalized else None


def _normalize_ip(address: Optional[str]) -> Optional[str]:
    if not address:
        return None
    return address.strip().lower()


def _build_interface_map(interfaces: Iterable[InterfaceModel]) -> Dict[str, InterfaceModel]:
    return {iface.name.strip(): iface for iface in interfaces if iface.name}


def _build_netbox_interface_map(interfaces: Iterable[NetBoxInterface]) -> Dict[str, NetBoxInterface]:
    return {iface.name.strip(): iface for iface in interfaces if iface.name}


def _build_ip_map(ips: Iterable[IPAddressModel]) -> Dict[str, IPAddressModel]:
    return {ip.address.strip(): ip for ip in ips if ip.address}


def _build_netbox_ip_map(ips: Iterable[NetBoxIPAddress]) -> Dict[str, NetBoxIPAddress]:
    return {ip.address.strip(): ip for ip in ips if ip.address}


def _build_vrf_map(vrfs: Iterable[VRFModel]) -> Dict[str, VRFModel]:
    return {vrf.name.strip(): vrf for vrf in vrfs if vrf.name}


def _build_netbox_vrf_map(vrfs: Iterable[NetBoxVRF]) -> Dict[str, NetBoxVRF]:
    return {vrf.name.strip(): vrf for vrf in vrfs if vrf.name}


def _build_vlan_map(vlans: Iterable[VlanModel]) -> Dict[int, VlanModel]:
    return {vlan.vlan_id: vlan for vlan in vlans if vlan.vlan_id is not None}


def _build_netbox_vlan_map(vlans: Iterable[NetBoxVLAN]) -> Dict[int, NetBoxVLAN]:
    return {vlan.vid: vlan for vlan in vlans if vlan.vid is not None}


def _bgp_peer_key(peer_ip: Optional[str], address_family: Optional[str]) -> Optional[str]:
    if not peer_ip:
        return None
    family = _normalize_string(address_family).lower() or "default"
    return f"{peer_ip.strip()}|{family}"


def _build_bgp_map(sessions: Iterable[BGPSessionModel]) -> Dict[str, BGPSessionModel]:
    result: Dict[str, BGPSessionModel] = {}
    for session in sessions:
        key = _bgp_peer_key(session.peer_ip, session.address_family)
        if key:
            result[key] = session
    return result


def _build_netbox_bgp_map(sessions: Iterable[NetBoxBGPSession]) -> Dict[str, NetBoxBGPSession]:
    result: Dict[str, NetBoxBGPSession] = {}
    for session in sessions:
        key = _bgp_peer_key(session.remote_address, session.address_family)
        if key:
            result[key] = session
    return result


def _monitoring_enabled(interface: NetBoxInterface) -> bool:
    custom_fields = getattr(interface, "custom_fields", {}) or {}
    value = custom_fields.get("monitoring_enabled")
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1", "y"}
    return False


def _policy_set(value) -> Set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        return {item.strip() for item in re.split(r"[\s,;]+", value) if item.strip()}
    if isinstance(value, list):
        return {str(item).strip() for item in value if item}
    return {str(value).strip()}


def _build_divergence(
    code: str,
    severity: str,
    scope: str,
    message: str,
    evidence: Dict[str, object],
    preferred_action: str,
    object_type: str,
    object_key: str,
) -> ComplianceDivergence:
    return ComplianceDivergence(
        code=code,
        severity=severity,
        scope=scope,
        message=message,
        evidence={k: int(v) if isinstance(v, bool) else v for k, v in evidence.items()},
        recommendation="Investigar e corrigir a divergência de compliance.",
        preferred_action=preferred_action,
        object_type=object_type,
        object_key=object_key,
    )


def build_object_diff(
    applied_inventory: DeviceInventory,
    netbox_inventory: NetBoxInventory,
) -> List[ComplianceDivergence]:
    divergences: List[ComplianceDivergence] = []

    applied_interfaces = _build_interface_map(applied_inventory.interfaces)
    netbox_interfaces = _build_netbox_interface_map(netbox_inventory.interfaces)

    interface_keys = set(applied_interfaces) | set(netbox_interfaces)
    for name in sorted(interface_keys):
        applied_iface = applied_interfaces.get(name)
        netbox_iface = netbox_interfaces.get(name)

        if applied_iface and not netbox_iface:
            severity = "high" if is_compliant_service_slug(applied_iface.description) else "medium"
            divergences.append(
                _build_divergence(
                    code="INTERFACE_MISSING_IN_NETBOX",
                    severity=severity,
                    scope="interfaces",
                    message=f"Interface {name} existe no dispositivo, mas não no NetBox.",
                    evidence={"applied": 1, "documented": 0},
                    preferred_action="fix_netbox",
                    object_type="interface",
                    object_key=name,
                )
            )
        elif netbox_iface and not applied_iface:
            severity = "high" if _monitoring_enabled(netbox_iface) else "medium"
            divergences.append(
                _build_divergence(
                    code="INTERFACE_MISSING_ON_DEVICE",
                    severity=severity,
                    scope="interfaces",
                    message=f"Interface {name} existe no NetBox, mas não no dispositivo.",
                    evidence={"applied": 0, "documented": 1},
                    preferred_action="review",
                    object_type="interface",
                    object_key=name,
                )
            )
        elif applied_iface and netbox_iface:
            if _normalize_string(applied_iface.description) != _normalize_string(netbox_iface.description):
                divergences.append(
                    _build_divergence(
                        code="INTERFACE_DESCRIPTION_MISMATCH",
                        severity="medium",
                        scope="interfaces",
                        message=f"Descrição da interface {name} difere entre dispositivo e NetBox.",
                        evidence={
                            "applied": applied_iface.description or "",
                            "documented": netbox_iface.description or "",
                        },
                        preferred_action="review",
                        object_type="interface",
                        object_key=name,
                    )
                )
            if applied_iface.description and not is_compliant_service_slug(applied_iface.description):
                divergences.append(
                    _build_divergence(
                        code="DESCRIPTION_NON_COMPLIANT",
                        severity="medium",
                        scope="interfaces",
                        message=f"Descrição da interface {name} não segue o naming convention esperado.",
                        evidence={
                            "description": applied_iface.description,
                        },
                        preferred_action="fix_device",
                        object_type="interface",
                        object_key=name,
                    )
                )

    applied_ips = _build_ip_map(applied_inventory.ip_addresses)
    netbox_ips = _build_netbox_ip_map(netbox_inventory.ip_addresses)
    ip_keys = set(applied_ips) | set(netbox_ips)
    for address in sorted(ip_keys):
        if address in applied_ips and address not in netbox_ips:
            divergences.append(
                _build_divergence(
                    code="IP_MISSING_IN_NETBOX",
                    severity="high",
                    scope="ip_addresses",
                    message=f"IP {address} existe no dispositivo, mas não no NetBox.",
                    evidence={"applied": 1, "documented": 0},
                    preferred_action="fix_netbox",
                    object_type="ip_address",
                    object_key=address,
                )
            )
        elif address in netbox_ips and address not in applied_ips:
            divergences.append(
                _build_divergence(
                    code="IP_MISSING_ON_DEVICE",
                    severity="high",
                    scope="ip_addresses",
                    message=f"IP {address} existe no NetBox, mas não no dispositivo.",
                    evidence={"applied": 0, "documented": 1},
                    preferred_action="review",
                    object_type="ip_address",
                    object_key=address,
                )
            )

    applied_vrfs = _build_vrf_map(applied_inventory.vrfs)
    netbox_vrfs = _build_netbox_vrf_map(netbox_inventory.vrfs)
    vrf_keys = set(applied_vrfs) | set(netbox_vrfs)
    for name in sorted(vrf_keys):
        if name in applied_vrfs and name not in netbox_vrfs:
            divergences.append(
                _build_divergence(
                    code="VRF_MISSING_IN_NETBOX",
                    severity="medium",
                    scope="vrfs",
                    message=f"VRF {name} existe no dispositivo, mas não no NetBox.",
                    evidence={"applied": 1, "documented": 0},
                    preferred_action="fix_netbox",
                    object_type="vrf",
                    object_key=name,
                )
            )
        elif name in netbox_vrfs and name not in applied_vrfs:
            divergences.append(
                _build_divergence(
                    code="VRF_MISSING_ON_DEVICE",
                    severity="medium",
                    scope="vrfs",
                    message=f"VRF {name} existe no NetBox, mas não no dispositivo.",
                    evidence={"applied": 0, "documented": 1},
                    preferred_action="review",
                    object_type="vrf",
                    object_key=name,
                )
            )

    applied_vlans = _build_vlan_map(applied_inventory.vlans)
    netbox_vlans = _build_netbox_vlan_map(netbox_inventory.vlans)
    vlan_keys = set(applied_vlans) | set(netbox_vlans)
    for vid in sorted(vlan_keys):
        if vid in applied_vlans and vid not in netbox_vlans:
            divergences.append(
                _build_divergence(
                    code="VLAN_MISSING_IN_NETBOX",
                    severity="medium",
                    scope="vlans",
                    message=f"VLAN {vid} existe no dispositivo, mas não no NetBox.",
                    evidence={"applied": 1, "documented": 0},
                    preferred_action="fix_netbox",
                    object_type="vlan",
                    object_key=str(vid),
                )
            )
        elif vid in netbox_vlans and vid not in applied_vlans:
            divergences.append(
                _build_divergence(
                    code="VLAN_MISSING_ON_DEVICE",
                    severity="medium",
                    scope="vlans",
                    message=f"VLAN {vid} existe no NetBox, mas não no dispositivo.",
                    evidence={"applied": 0, "documented": 1},
                    preferred_action="review",
                    object_type="vlan",
                    object_key=str(vid),
                )
            )

    applied_bgp = _build_bgp_map(applied_inventory.bgp_sessions)
    netbox_bgp = _build_netbox_bgp_map(netbox_inventory.bgp_sessions)
    bgp_keys = set(applied_bgp) | set(netbox_bgp)
    for key in sorted(bgp_keys):
        applied_session = applied_bgp.get(key)
        netbox_session = netbox_bgp.get(key)

        if applied_session and not netbox_session:
            divergences.append(
                _build_divergence(
                    code="BGP_PEER_MISSING_IN_NETBOX",
                    severity="high",
                    scope="bgp_peers",
                    message=f"Sessão BGP {key} existe no dispositivo, mas não no NetBox.",
                    evidence={"applied": 1, "documented": 0},
                    preferred_action="fix_netbox",
                    object_type="bgp_session",
                    object_key=key,
                )
            )
            continue
        if netbox_session and not applied_session:
            divergences.append(
                _build_divergence(
                    code="BGP_PEER_MISSING_ON_DEVICE",
                    severity="high",
                    scope="bgp_peers",
                    message=f"Sessão BGP {key} existe no NetBox, mas não no dispositivo.",
                    evidence={"applied": 0, "documented": 1},
                    preferred_action="review",
                    object_type="bgp_session",
                    object_key=key,
                )
            )
            continue

        if applied_session and netbox_session:
            if (
                applied_session.peer_as is not None
                and netbox_session.remote_as is not None
                and applied_session.peer_as != netbox_session.remote_as
            ):
                divergences.append(
                    _build_divergence(
                        code="BGP_ASN_MISMATCH",
                        severity="medium",
                        scope="bgp_peers",
                        message=f"ASN remoto difere para a sessão BGP {key}.",
                        evidence={
                            "applied": applied_session.peer_as,
                            "documented": netbox_session.remote_as,
                        },
                        preferred_action="review",
                        object_type="bgp_session",
                        object_key=key,
                    )
                )

            applied_import = _policy_set(applied_session.import_policy)
            netbox_import = _policy_set(netbox_session.import_policy)
            if applied_import and netbox_import and applied_import != netbox_import:
                divergences.append(
                    _build_divergence(
                        code="BGP_POLICY_MISMATCH",
                        severity="medium",
                        scope="bgp_peers",
                        message=f"Políticas de importação BGP divergem para a sessão {key}.",
                        evidence={
                            "applied": sorted(applied_import),
                            "documented": sorted(netbox_import),
                        },
                        preferred_action="review",
                        object_type="bgp_session",
                        object_key=key,
                    )
                )

            applied_export = _policy_set(applied_session.export_policy)
            netbox_export = _policy_set(netbox_session.export_policy)
            if applied_export and netbox_export and applied_export != netbox_export:
                divergences.append(
                    _build_divergence(
                        code="BGP_POLICY_MISMATCH",
                        severity="medium",
                        scope="bgp_peers",
                        message=f"Políticas de exportação BGP divergem para a sessão {key}.",
                        evidence={
                            "applied": sorted(applied_export),
                            "documented": sorted(netbox_export),
                        },
                        preferred_action="review",
                        object_type="bgp_session",
                        object_key=key,
                    )
                )

    return divergences
