from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Set, Tuple

import pynetbox
from pynetbox.core.query import RequestError

from app.api.schemas import NetBoxParams
from app.schemas.analyze import AppliedInventorySummary, AnalyzeWarning
from app.schemas.netbox_inventory import (
    NetBoxASPathFilter,
    NetBoxBGPSession,
    NetBoxCircuit,
    NetBoxCommunity,
    NetBoxCommunityList,
    NetBoxDevice,
    NetBoxInterface,
    NetBoxIPAddress,
    NetBoxInventory,
    NetBoxPrefixList,
    NetBoxRoutingPolicy,
    NetBoxVRF,
    NetBoxVLAN,
)


def _normalize_nb_url(url: str) -> str:
    url = url.rstrip("/")
    if url.endswith("/api"):
        url = url[:-4]
    return url


def _open_netbox(nb: NetBoxParams):
    nb_base = _normalize_nb_url(nb.url)
    client = pynetbox.api(nb_base, token=nb.token)
    client.http_session.verify = nb.verify_ssl
    return client


def _serialize(obj) -> Dict:
    if obj is None:
        return {}
    if hasattr(obj, "serialize"):
        try:
            return obj.serialize()
        except Exception:  # pragma: no cover - fallback
            return {}
    if isinstance(obj, dict):
        return obj
    return {}


# ---------------------------------------------------------------------------
# Safe helpers — handle int/str/dict/None/pynetbox-record uniformly
# ---------------------------------------------------------------------------

def _safe_get(obj, key, default=None):
    """Get key from dict, attr from object, or default if obj is int/None."""
    if obj is None:
        return default
    if isinstance(obj, (int, float, str, bool)):
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _safe_id(obj) -> Optional[int]:
    """Extract id from int/dict/object. Returns int or None."""
    if obj is None:
        return None
    if isinstance(obj, int):
        return obj
    if isinstance(obj, str):
        return None
    if isinstance(obj, dict):
        val = obj.get("id") or obj.get("value")
        return int(val) if val is not None else None
    val = getattr(obj, "id", None) or getattr(obj, "value", None)
    return int(val) if val is not None else None


def _safe_name(obj) -> Optional[str]:
    """Extract name from int/str/dict/object. Returns str or None."""
    if obj is None:
        return None
    if isinstance(obj, (int, float)):
        return str(obj)
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        return (
            obj.get("name")
            or obj.get("display")
            or obj.get("slug")
            or obj.get("value")
            or (str(obj["id"]) if obj.get("id") is not None else None)
        )
    return (
        getattr(obj, "name", None)
        or getattr(obj, "display", None)
        or getattr(obj, "slug", None)
        or getattr(obj, "value", None)
        or (str(getattr(obj, "id")) if getattr(obj, "id", None) is not None else None)
    )


def _safe_custom_fields(obj) -> Dict:
    """Extract custom_fields dict safely from any object type."""
    cf = _safe_get(obj, "custom_fields", {})
    return cf if isinstance(cf, dict) else {}


def _safe_tags(obj) -> List[str]:
    """Extract list of tag names/slugs safely from any object type."""
    tags = _safe_get(obj, "tags", [])
    if not tags:
        return []
    result = []
    for tag in tags:
        name = _safe_name(tag)
        if name:
            result.append(name)
    return result


# ---------------------------------------------------------------------------
# Legacy helpers (kept for compat, now delegate to safe variants)
# ---------------------------------------------------------------------------

def _choice_value(value) -> Optional[str]:
    if isinstance(value, dict):
        return value.get("value") or value.get("slug") or value.get("name")
    if isinstance(value, (int, float)):
        return str(value)
    return value


def _ref_name(value) -> Optional[str]:
    return _safe_name(value)


def _ref_id(value) -> Optional[int]:
    return _safe_id(value)


def _tags_list(data: Dict) -> List[str]:
    tags = data.get("tags", [])
    result = []
    for tag in tags or []:
        if isinstance(tag, dict):
            result.append(tag.get("slug") or tag.get("name") or tag.get("label"))
        elif isinstance(tag, str):
            result.append(tag)
        else:
            result.append(str(tag))
    return [t for t in result if t]


def _custom_fields(data: Dict) -> Dict:
    cf = data.get("custom_fields")
    return cf if isinstance(cf, dict) else {}


def _address(value) -> Optional[str]:
    if isinstance(value, dict):
        return value.get("address") or value.get("display")
    if isinstance(value, str):
        return value
    return None


def _names_list(records: Iterable) -> List[str]:
    items: List[str] = []
    for record in records or []:
        if isinstance(record, dict):
            items.append(record.get("name") or record.get("slug") or record.get("value"))
        else:
            items.append(str(record))
    return [item for item in items if item]


def _map_device(device_obj) -> NetBoxDevice:
    data = _serialize(device_obj)
    device_type_raw = data.get("device_type")
    if isinstance(device_type_raw, dict):
        device_type = device_type_raw
        manufacturer_raw = device_type.get("manufacturer")
        manufacturer = manufacturer_raw if isinstance(manufacturer_raw, dict) else {}
        model = device_type.get("model")
    elif isinstance(device_type_raw, int):
        device_type = {}
        manufacturer = {}
        model = None
    else:
        device_type = {}
        manufacturer = {}
        model = None

    return NetBoxDevice(
        id=data.get("id"),
        name=data.get("name"),
        status=_choice_value(data.get("status")),
        role=_ref_name(data.get("device_role") or data.get("role")),
        site=_ref_name(data.get("site")),
        tenant=_ref_name(data.get("tenant")),
        platform=_ref_name(data.get("platform")),
        manufacturer=_ref_name(manufacturer),
        model=model,
        primary_ip4=_address(data.get("primary_ip4")),
        primary_ip6=_address(data.get("primary_ip6")),
        tags=_tags_list(data),
        custom_fields=_custom_fields(data),
    )


def _map_interface(interface_obj) -> Tuple[NetBoxInterface, Set[int]]:
    data = _serialize(interface_obj)
    tagged_vlan_ids = set()
    tagged_vlans = []

    for vlan in data.get("tagged_vlans") or []:
        if isinstance(vlan, int):
            # raw ID — add to set, no vid to display
            tagged_vlan_ids.add(vlan)
        elif isinstance(vlan, dict):
            vid_key = vlan.get("id")
            if vid_key:
                tagged_vlan_ids.add(vid_key)
            tagged_value = vlan.get("vid") or vlan.get("name")
            if tagged_value is not None:
                tagged_vlans.append(str(tagged_value))
        # else ignore

    untagged_raw = data.get("untagged_vlan")
    if isinstance(untagged_raw, int):
        tagged_vlan_ids.add(untagged_raw)
        untagged_vid = None  # can't resolve vid from raw ID
    elif isinstance(untagged_raw, dict):
        untagged_id = untagged_raw.get("id")
        if untagged_id:
            tagged_vlan_ids.add(untagged_id)
        untagged_vid = untagged_raw.get("vid")
    else:
        untagged_vid = None

    netbox_interface = NetBoxInterface(
        id=data.get("id"),
        name=data.get("name"),
        label=data.get("label"),
        type=_choice_value(data.get("type")),
        enabled=data.get("enabled"),
        description=data.get("description"),
        mtu=data.get("mtu"),
        mac_address=data.get("mac_address"),
        mode=_choice_value(data.get("mode")),
        lag=_ref_name(data.get("lag")),
        parent=_ref_name(data.get("parent")),
        untagged_vlan=untagged_vid,
        tagged_vlans=[v for v in tagged_vlans if v is not None],
        vrf=_ref_name(data.get("vrf")),
        tags=_tags_list(data),
        custom_fields=_custom_fields(data),
    )

    return netbox_interface, tagged_vlan_ids


def _map_ip_address(ip_obj) -> Tuple[NetBoxIPAddress, Optional[int]]:
    data = _serialize(ip_obj)
    assigned_object_raw = data.get("assigned_object")

    if isinstance(assigned_object_raw, dict):
        assigned_obj_id = assigned_object_raw.get("id")
        assigned_obj_name = assigned_object_raw.get("name") or assigned_object_raw.get("display")
    elif isinstance(assigned_object_raw, int):
        assigned_obj_id = assigned_object_raw
        assigned_obj_name = None
    else:
        assigned_obj_id = None
        assigned_obj_name = None

    return (
        NetBoxIPAddress(
            id=data.get("id"),
            address=data.get("address"),
            status=_choice_value(data.get("status")),
            role=_choice_value(data.get("role")),
            dns_name=data.get("dns_name"),
            description=data.get("description"),
            vrf=_ref_name(data.get("vrf")),
            tenant=_ref_name(data.get("tenant")),
            assigned_object_type=data.get("assigned_object_type"),
            assigned_object_id=assigned_obj_id,
            assigned_object_name=assigned_obj_name,
            tags=_tags_list(data),
            custom_fields=_custom_fields(data),
        ),
        _ref_id(data.get("vrf")),
    )


def _collect_vrfs(nb, vrf_ids: Set[int]) -> Tuple[List[NetBoxVRF], List[AnalyzeWarning]]:
    vrfs: List[NetBoxVRF] = []
    warnings: List[AnalyzeWarning] = []
    for vrf_id in sorted(vrf_ids):
        try:
            vrf_obj = nb.ipam.vrfs.get(vrf_id)
        except Exception as exc:  # pragma: no cover - acesso inesperado
            warnings.append(
                AnalyzeWarning(
                    code="NETBOX_VRF_PARTIAL",
                    severity="low",
                    message=f"Não foi possível carregar VRF {vrf_id}: {exc}",
                )
            )
            continue
        data = _serialize(vrf_obj)
        vrfs.append(
            NetBoxVRF(
                id=data.get("id"),
                name=data.get("name"),
                rd=data.get("rd"),
                tenant=_ref_name(data.get("tenant")),
                description=data.get("description"),
                import_targets=_names_list(data.get("import_targets")),
                export_targets=_names_list(data.get("export_targets")),
                tags=_tags_list(data),
                custom_fields=_custom_fields(data),
            )
        )
    return vrfs, warnings


def _collect_vlans(nb, vlan_ids: Set[int]) -> Tuple[List[NetBoxVLAN], List[AnalyzeWarning]]:
    vlans: List[NetBoxVLAN] = []
    warnings: List[AnalyzeWarning] = []
    for vlan_id in sorted(vlan_ids):
        try:
            vlan_obj = nb.ipam.vlans.get(vlan_id)
        except Exception as exc:  # pragma: no cover
            warnings.append(
                AnalyzeWarning(
                    code="NETBOX_VLAN_PARTIAL",
                    severity="low",
                    message=f"Não foi possível carregar VLAN {vlan_id}: {exc}",
                )
            )
            continue
        data = _serialize(vlan_obj)
        vlans.append(
            NetBoxVLAN(
                id=data.get("id"),
                vid=data.get("vid"),
                name=data.get("name"),
                status=_choice_value(data.get("status")),
                role=_choice_value(data.get("role")),
                site=_ref_name(data.get("site")),
                group=_ref_name(data.get("group")),
                tenant=_ref_name(data.get("tenant")),
                description=data.get("description"),
                tags=_tags_list(data),
                custom_fields=_custom_fields(data),
            )
        )
    return vlans, warnings


def _collect_circuits(nb, device_id: int) -> Tuple[List[NetBoxCircuit], List[AnalyzeWarning]]:
    circuits: Dict[int, List[Dict]] = {}
    warnings: List[AnalyzeWarning] = []
    terminations_iter = None
    try:
        terminations_iter = nb.circuits.circuit_terminations.filter(device_id=device_id)
    except (AttributeError, RequestError) as exc:
        warnings.append(
            AnalyzeWarning(
                code="NETBOX_CIRCUIT_PARTIAL",
                severity="info",
                message=f"Circuit terminations não disponíveis: {exc}",
            )
        )
    except Exception as exc:  # pragma: no cover
        warnings.append(
            AnalyzeWarning(
                code="NETBOX_CIRCUIT_PARTIAL",
                severity="info",
                message=f"Circuit terminations não disponíveis: {exc}",
            )
        )

    if terminations_iter:
        for term in terminations_iter:
            data = _serialize(term)
            circuit_raw = data.get("circuit")
            circuit = circuit_raw if isinstance(circuit_raw, dict) else {}
            circuit_id = circuit.get("id")
            if not circuit_id:
                continue
            term_list = circuits.setdefault(circuit_id, [])
            term_list.append(
                {
                    "id": data.get("id"),
                    "term_side": data.get("term_side"),
                    "port_speed": data.get("port_speed"),
                    "pp_info": data.get("pp_info"),
                    "interface": _ref_name(data.get("interface")),
                }
            )

    result: List[NetBoxCircuit] = []
    for circuit_id, term_list in circuits.items():
        try:
            circuit_obj = nb.circuits.circuits.get(circuit_id)
        except Exception as exc:  # pragma: no cover
            warnings.append(
                AnalyzeWarning(
                    code="NETBOX_CIRCUIT_PARTIAL",
                    severity="info",
                    message=f"Circuit {circuit_id} não carregado: {exc}",
                )
            )
            continue
        data = _serialize(circuit_obj)
        result.append(
            NetBoxCircuit(
                id=data.get("id"),
                cid=data.get("cid"),
                provider=_ref_name(data.get("provider")),
                tenant=_ref_name(data.get("tenant")),
                type=_ref_name(data.get("type")),
                status=_choice_value(data.get("status")),
                description=data.get("description"),
                commit_rate=data.get("commit_rate"),
                custom_fields=_custom_fields(data),
                tags=_tags_list(data),
                terminations=term_list,
            )
        )
    return result, warnings


def _load_bgp_plugin_details(nb, device_id: int):
    sessions: List[NetBoxBGPSession] = []
    routing_policies: List[NetBoxRoutingPolicy] = []
    prefix_lists: List[NetBoxPrefixList] = []
    as_path_filters: List[NetBoxASPathFilter] = []
    communities: List[NetBoxCommunity] = []
    community_lists: List[NetBoxCommunityList] = []
    issues: List[str] = []

    plugin_root = getattr(getattr(nb, "plugins", None), "bgp", None)
    if plugin_root is None:
        return (
            {
                "sessions": sessions,
                "routing_policies": routing_policies,
                "prefix_lists": prefix_lists,
                "as_path_filters": as_path_filters,
                "communities": communities,
                "community_lists": community_lists,
            },
            [
                AnalyzeWarning(
                    code="NETBOX_BGP_PLUGIN_PARTIAL",
                    severity="info",
                    message="Plugin NetBox BGP não está disponível.",
                )
            ],
        )

    def collect(label: str, getter) -> List[Dict]:
        try:
            return [
                _serialize(record) for record in getter()
            ]
        except (AttributeError, RequestError) as exc:
            issues.append(f"{label}: {exc}")
            return []
        except Exception as exc:  # pragma: no cover
            issues.append(f"{label}: {exc}")
            return []

    session_records = collect("session", lambda: plugin_root.session.filter(device_id=device_id))
    policy_records = collect("routing_policy", lambda: plugin_root.routing_policy.all())
    prefix_records = collect("prefix_list", lambda: plugin_root.prefix_list.all())
    as_path_records = collect("as_path_filter", lambda: plugin_root.as_path_filter.all())
    community_records = collect("community", lambda: plugin_root.community.all())
    community_list_records = collect("community_list", lambda: plugin_root.community_list.all())

    for data in session_records:
        sessions.append(
            NetBoxBGPSession(
                id=data.get("id"),
                name=data.get("name"),
                status=_choice_value(data.get("status")),
                device=_ref_name(data.get("device")),
                vrf=_ref_name(data.get("vrf")),
                local_as=_safe_id(data.get("local_as")) or data.get("local_as"),
                remote_as=_safe_id(data.get("remote_as")) or data.get("remote_as"),
                local_address=_address(data.get("local_address")),
                remote_address=_address(data.get("remote_address")),
                address_family=_choice_value(data.get("address_family")),
                import_policy=_names_list(data.get("import_policies")),
                export_policy=_names_list(data.get("export_policies")),
                tags=_tags_list(data),
                custom_fields=_custom_fields(data),
            )
        )

    for data in policy_records:
        routing_policies.append(
            NetBoxRoutingPolicy(
                id=data.get("id"),
                name=data.get("name"),
                description=data.get("description"),
                type=_choice_value(data.get("type")),
                address_family=_choice_value(data.get("address_family")),
                tags=_tags_list(data),
                custom_fields=_custom_fields(data),
            )
        )

    for data in prefix_records:
        prefix_lists.append(
            NetBoxPrefixList(
                id=data.get("id"),
                name=data.get("name"),
                address_family=_choice_value(data.get("family")) or _choice_value(data.get("address_family")),
                description=data.get("description"),
                tags=_tags_list(data),
                custom_fields=_custom_fields(data),
            )
        )

    for data in as_path_records:
        as_path_filters.append(
            NetBoxASPathFilter(
                id=data.get("id"),
                name=data.get("name"),
                description=data.get("description"),
                tags=_tags_list(data),
                custom_fields=_custom_fields(data),
            )
        )

    for data in community_records:
        communities.append(
            NetBoxCommunity(
                id=data.get("id"),
                value=data.get("value"),
                status=_choice_value(data.get("status")),
                description=data.get("description"),
                tags=_tags_list(data),
                custom_fields=_custom_fields(data),
            )
        )

    for data in community_list_records:
        community_lists.append(
            NetBoxCommunityList(
                id=data.get("id"),
                name=data.get("name"),
                description=data.get("description"),
                tags=_tags_list(data),
                custom_fields=_custom_fields(data),
            )
        )

    warnings = []
    if issues:
        warnings.append(
            AnalyzeWarning(
                code="NETBOX_BGP_PLUGIN_PARTIAL",
                severity="info",
                message="Plugin NetBox BGP ausente/parcial: " + "; ".join(issues),
            )
        )

    return (
        {
            "sessions": sessions,
            "routing_policies": routing_policies,
            "prefix_lists": prefix_lists,
            "as_path_filters": as_path_filters,
            "communities": communities,
            "community_lists": community_lists,
        },
        warnings,
    )


def resolve_netbox_device_id(
    netbox: NetBoxParams,
    device_id: int | None = None,
    device_name: str | None = None,
    device_host: str | None = None,
) -> tuple[int | None, list[AnalyzeWarning]]:
    """Resolve device_id read-only. No writes to NetBox."""
    if device_id is not None:
        return device_id, []

    warnings: list[AnalyzeWarning] = []
    try:
        nb = _open_netbox(netbox)
    except Exception as exc:
        warnings.append(
            AnalyzeWarning(
                code="NETBOX_DEVICE_ID_RESOLVE_FAILED",
                severity="medium",
                message=f"Erro ao conectar no NetBox para resolução de device_id: {exc}",
            )
        )
        return None, warnings

    if device_name:
        try:
            result = nb.dcim.devices.get(name=device_name)
            if result is not None:
                resolved_id = _safe_id(result)
                if resolved_id:
                    warnings.append(
                        AnalyzeWarning(
                            code="NETBOX_DEVICE_ID_RESOLVED",
                            severity="info",
                            message=f"device_id {resolved_id} resolvido por device_name '{device_name}'.",
                        )
                    )
                    return resolved_id, warnings
            warnings.append(
                AnalyzeWarning(
                    code="NETBOX_DEVICE_ID_NOT_FOUND",
                    severity="medium",
                    message=f"Dispositivo '{device_name}' não encontrado no NetBox.",
                )
            )
            return None, warnings
        except Exception as exc:
            warnings.append(
                AnalyzeWarning(
                    code="NETBOX_DEVICE_ID_RESOLVE_FAILED",
                    severity="medium",
                    message=f"Erro ao resolver device_id por device_name: {exc}",
                )
            )
            return None, warnings

    if device_host:
        try:
            # Try device with primary_ip4 matching host (most direct)
            devices_list = []
            for query in (device_host, f"{device_host}/32"):
                devices_list = list(nb.dcim.devices.filter(primary_ip4=query))
                if devices_list:
                    break

            if len(devices_list) > 1:
                warnings.append(
                    AnalyzeWarning(
                        code="NETBOX_DEVICE_ID_AMBIGUOUS",
                        severity="medium",
                        message=f"Múltiplos devices com primary_ip4 '{device_host}'. Informe device_id diretamente.",
                    )
                )
                return None, warnings

            if len(devices_list) == 1:
                resolved_id = _safe_id(devices_list[0])
                if resolved_id:
                    warnings.append(
                        AnalyzeWarning(
                            code="NETBOX_DEVICE_ID_RESOLVED",
                            severity="info",
                            message=f"device_id {resolved_id} resolvido por device_host '{device_host}' (primary_ip4).",
                        )
                    )
                    return resolved_id, warnings

            # Fallback: search via IP address assigned_object
            ip_results = []
            for query in (device_host, f"{device_host}/32"):
                ip_results = list(nb.ipam.ip_addresses.filter(address=query))
                if ip_results:
                    break

            if not ip_results:
                ip_results = list(nb.ipam.ip_addresses.filter(q=device_host))

            if len(ip_results) > 1:
                warnings.append(
                    AnalyzeWarning(
                        code="NETBOX_DEVICE_ID_AMBIGUOUS",
                        severity="medium",
                        message=f"Múltiplos IPs encontrados para '{device_host}'. Informe device_id diretamente.",
                    )
                )
                return None, warnings

            if ip_results:
                ip_obj = ip_results[0]
                ip_data = _serialize(ip_obj)
                assigned_object_raw = ip_data.get("assigned_object")
                resolved_id = None

                if isinstance(assigned_object_raw, dict):
                    # assigned_object is an interface — try .device inside it
                    device_sub = assigned_object_raw.get("device")
                    if device_sub is not None:
                        resolved_id = _safe_id(device_sub)
                    if resolved_id is None:
                        # some NetBox versions expose device directly on interface obj
                        # try fetching device via interface id
                        iface_id = assigned_object_raw.get("id")
                        if iface_id:
                            try:
                                iface_obj = nb.dcim.interfaces.get(iface_id)
                                if iface_obj:
                                    iface_data = _serialize(iface_obj)
                                    resolved_id = _safe_id(iface_data.get("device"))
                            except Exception:
                                pass

                if resolved_id:
                    warnings.append(
                        AnalyzeWarning(
                            code="NETBOX_DEVICE_ID_RESOLVED",
                            severity="info",
                            message=f"device_id {resolved_id} resolvido por device_host '{device_host}' (IP assignment).",
                        )
                    )
                    return resolved_id, warnings

            warnings.append(
                AnalyzeWarning(
                    code="NETBOX_DEVICE_ID_NOT_FOUND",
                    severity="medium",
                    message=f"Não foi possível resolver device_id pelo IP/nome informado (host='{device_host}').",
                )
            )
            return None, warnings

        except Exception as exc:
            warnings.append(
                AnalyzeWarning(
                    code="NETBOX_DEVICE_ID_RESOLVE_FAILED",
                    severity="medium",
                    message=f"Erro ao resolver device_id por device_host: {exc}",
                )
            )
            return None, warnings

    warnings.append(
        AnalyzeWarning(
            code="NETBOX_DEVICE_ID_NOT_FOUND",
            severity="medium",
            message="Não foi possível resolver device_id: nenhum device_name ou device_host informado.",
        )
    )
    return None, warnings


def load_netbox_inventory(
    netbox: NetBoxParams, device_id: int
) -> tuple[NetBoxInventory, List[AnalyzeWarning]]:
    nb = _open_netbox(netbox)
    warnings: List[AnalyzeWarning] = []

    device_obj = nb.dcim.devices.get(device_id)
    if not device_obj:
        raise ValueError(f"device_id {device_id} não encontrado no NetBox.")

    device = _map_device(device_obj)

    interface_objs = list(nb.dcim.interfaces.filter(device_id=device_id))
    interfaces: List[NetBoxInterface] = []
    vlan_ids: Set[int] = set()
    for interface_obj in interface_objs:
        mapped_interface, vlans_ids_from_interface = _map_interface(interface_obj)
        interfaces.append(mapped_interface)
        vlan_ids.update(vlans_ids_from_interface)

    ip_objs = list(nb.ipam.ip_addresses.filter(device_id=device_id))
    ip_addresses: List[NetBoxIPAddress] = []
    vrf_ids: Set[int] = set()
    for ip_obj in ip_objs:
        mapped_ip, vrf_id = _map_ip_address(ip_obj)
        ip_addresses.append(mapped_ip)
        if vrf_id:
            vrf_ids.add(vrf_id)

    vrfs, vrf_warnings = _collect_vrfs(nb, vrf_ids)
    warnings.extend(vrf_warnings)

    vlans, vlan_warnings = _collect_vlans(nb, vlan_ids)
    warnings.extend(vlan_warnings)

    circuits, circuit_warnings = _collect_circuits(nb, device_id)
    warnings.extend(circuit_warnings)

    bgp_payload, bgp_warnings = _load_bgp_plugin_details(nb, device_id)
    warnings.extend(bgp_warnings)

    summary = AppliedInventorySummary(
        interfaces=len(interfaces),
        ip_addresses=len(ip_addresses),
        vrfs=len(vrfs),
        vlans=len(vlans),
        bgp_sessions=len(bgp_payload["sessions"]),
        route_policies=len(bgp_payload["routing_policies"]),
        prefix_lists=len(bgp_payload["prefix_lists"]),
        as_path_filters=len(bgp_payload["as_path_filters"]),
        communities=len(bgp_payload["communities"]),
        community_lists=len(bgp_payload["community_lists"]),
    )

    inventory = NetBoxInventory(
        device=device,
        interfaces=interfaces,
        ip_addresses=ip_addresses,
        vrfs=vrfs,
        vlans=vlans,
        circuits=circuits,
        bgp_sessions=bgp_payload["sessions"],
        routing_policies=bgp_payload["routing_policies"],
        prefix_lists=bgp_payload["prefix_lists"],
        as_path_filters=bgp_payload["as_path_filters"],
        communities=bgp_payload["communities"],
        community_lists=bgp_payload["community_lists"],
        summary=summary,
    )

    return inventory, warnings
