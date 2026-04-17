import re
from app.schemas.models import DeviceInventory
from app.parsers.interfaces import parse_interface_brief, parse_interface_description, get_interface_type
from app.parsers.ipaddr import parse_ip_interface_brief
from app.parsers.vlans import parse_vlans
from app.parsers.vrfs import parse_vrfs
from app.parsers.bgp import parse_bgp_peers, parse_bgp_peers_verbose
from app.parsers.lacp import parse_lag_members
from app.parsers.route_policy import parse_route_policy
from app.parsers.route_policy_config import parse_route_policy_from_config
from app.parsers.prefix_filter import parse_ip_prefix, parse_as_path_filter
from app.parsers.community import parse_community_filters, parse_community_values


def _inject_globals(sessions: list, router_id: str, local_as: int,
                    address_family: str, vrf: str = None) -> list:
    """Injeta campos globais que o verbose não traz em cada sessão da lista."""
    for s in sessions:
        if not s.get("router_id"):
            s["router_id"] = router_id
        if not s.get("local_as"):
            s["local_as"] = local_as
        s["address_family"] = address_family
        s["vrf"] = vrf
    return sessions


def build_inventory(raw_data: dict, vrf_bgp: dict = None) -> DeviceInventory:
    """
    raw_data   : saída de HuaweiNE8000Collector.collect_all()
    vrf_bgp    : saída de HuaweiNE8000Collector.collect_bgp_all_vrfs()
                 { "vpnv4:CDN": "<output>", "vpnv6:CDN": "<output>", ... }
    """
    # ── Interfaces ────────────────────────────────────────────────────────────
    interfaces_raw = parse_interface_brief(raw_data["interfaces_brief"])
    descriptions = parse_interface_description(raw_data["interfaces_desc"])
    ip_addresses = parse_ip_interface_brief(raw_data["ip_interfaces"])
    vlans = parse_vlans(raw_data["vlans"])
    vrfs = parse_vrfs(raw_data["vrfs"])
    lag_members = parse_lag_members(raw_data["running_config"])

    # ── Políticas e filtros ───────────────────────────────────────────────────
    running_cfg = raw_data.get("running_config", "")

    # Route-policies: running-config como fonte primária (snapshot atômico,
    # captura apply community / local-pref / med com mais fidelidade).
    # Fallback para 'display route-policy' se o running-config não trouxer nada.
    route_policies = parse_route_policy_from_config(running_cfg)
    if not route_policies:
        route_policies = parse_route_policy(raw_data.get("route_policy", ""))

    prefix_lists    = parse_ip_prefix(raw_data.get("ip_prefix", ""))
    as_path_filters = parse_as_path_filter(raw_data.get("as_path_filter", ""))
    community_lists = parse_community_filters(running_cfg)
    communities     = parse_community_values(running_cfg)

    # ── Parâmetros BGP globais (vêm do summary, não do verbose) ───────────────
    summary_raw = raw_data.get("bgp_summary", "")
    m_rid = re.search(r"BGP local router ID\s*:\s*(\S+)", summary_raw)
    router_id = m_rid.group(1) if m_rid else None
    m_las = re.search(r"Local AS number\s*:\s*(\d+)", summary_raw)
    local_as_global = int(m_las.group(1)) if m_las else None

    # ── BGP peers: IPv4 global ────────────────────────────────────────────────
    if raw_data.get("bgp_peers_verbose", "").strip():
        ipv4_sessions = parse_bgp_peers_verbose(raw_data["bgp_peers_verbose"])
    else:
        ipv4_sessions = parse_bgp_peers(raw_data["bgp_peers"])
    _inject_globals(ipv4_sessions, router_id, local_as_global, "ipv4", vrf=None)

    # ── BGP peers: IPv6 global ────────────────────────────────────────────────
    ipv6_sessions = []
    if raw_data.get("bgp_ipv6_verbose", "").strip():
        ipv6_sessions = parse_bgp_peers_verbose(raw_data["bgp_ipv6_verbose"])
        _inject_globals(ipv6_sessions, router_id, local_as_global, "ipv6", vrf=None)

    # ── BGP peers: por VRF (VPNv4 / VPNv6) ──────────────────────────────────
    vrf_sessions = []
    for key, output in (vrf_bgp or {}).items():
        # key: "vpnv4:CDN" ou "vpnv6:MYVRF"
        af, _, vrf_name = key.partition(":")
        parsed = parse_bgp_peers_verbose(output)
        _inject_globals(parsed, router_id, local_as_global, af, vrf=vrf_name)
        vrf_sessions.extend(parsed)

    all_sessions = ipv4_sessions + ipv6_sessions + vrf_sessions

    # ── Interfaces: adiciona membros LAG omitidos no brief ────────────────────
    interface_names = {i["name"] for i in interfaces_raw}
    for member_name in lag_members:
        if member_name not in interface_names:
            interfaces_raw.append({"name": member_name, "admin_status": "up", "oper_status": "up"})
            interface_names.add(member_name)

    interfaces = []
    for iface in interfaces_raw:
        name = iface["name"]
        iface["description"] = descriptions.get(name)
        iface["type"] = get_interface_type(name)
        iface["lag_parent"] = lag_members.get(name)
        interfaces.append(iface)

    return DeviceInventory(
        interfaces=interfaces,
        ip_addresses=ip_addresses,
        vlans=vlans,
        vrfs=vrfs,
        bgp_sessions=all_sessions,
        route_policies=route_policies,
        prefix_lists=prefix_lists,
        as_path_filters=as_path_filters,
        communities=communities,
        community_lists=community_lists,
    )
