import re


def parse_bgp_peers(output: str) -> list:
    """Parseia 'display bgp peer' (tabular summary)."""
    peers = []
    local_as = None

    m_local = re.search(r"Local AS number\s*:\s*(\d+)", output)
    if m_local:
        local_as = int(m_local.group(1))

    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue

        m = re.match(
            r"^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+\d+\s+(\d+)\s+\S+\s+\S+\s+\S+\s+\S+\s+(\S+)",
            line,
        )
        if m:
            peers.append({
                "peer_ip": m.group(1),
                "peer_as": int(m.group(2)),
                "local_as": local_as,
                "state": m.group(3),
                "vrf": None,
                "description": None,
            })

    return peers


def parse_bgp_peers_verbose(output: str) -> list:
    """
    Parseia 'display bgp peer verbose'.
    Extrai por peer: tipo (EBGP/IBGP), descrição, estado,
    import/export route-policy e import/export prefix-list.
    """
    peers = []
    current = None
    local_as = None
    router_id = None

    m_local = re.search(r"Local AS number\s*:\s*(\d+)", output)
    if m_local:
        local_as = int(m_local.group(1))

    m_rid = re.search(r"BGP local router ID\s*:\s*(\S+)", output)
    if m_rid:
        router_id = m_rid.group(1)

    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        # Novo peer
        m_peer = re.match(r"BGP Peer is (\S+),\s+remote AS (\d+)", stripped)
        if m_peer:
            if current:
                peers.append(current)
            current = {
                "peer_ip": m_peer.group(1),
                "peer_as": int(m_peer.group(2)),
                "local_as": local_as,
                "router_id": router_id,
                "peer_type": None,
                "description": None,
                "state": None,
                "import_policy": None,
                "export_policy": None,
                "import_prefix_list": None,
                "export_prefix_list": None,
            }
            continue

        if current is None:
            continue

        m_type = re.match(r"Type:\s+(EBGP|IBGP) link", stripped)
        if m_type:
            current["peer_type"] = m_type.group(1)
            continue

        m_desc = re.match(r'Peer\'s description:\s+"(.+)"', stripped)
        if m_desc:
            current["description"] = m_desc.group(1)
            continue

        m_state = re.match(r"BGP current state:\s+(\w+)", stripped)
        if m_state:
            current["state"] = m_state.group(1)
            continue

        m_imp_pol = re.match(r"Import route policy is:\s+(\S+)", stripped)
        if m_imp_pol:
            current["import_policy"] = m_imp_pol.group(1)
            continue

        m_exp_pol = re.match(r"Export route policy is:\s+(\S+)", stripped)
        if m_exp_pol:
            current["export_policy"] = m_exp_pol.group(1)
            continue

        m_imp_pl = re.match(r"Import prefix list:\s+(\S+)", stripped)
        if m_imp_pl:
            current["import_prefix_list"] = m_imp_pl.group(1)
            continue

        m_exp_pl = re.match(r"Export prefix list:\s+(\S+)", stripped)
        if m_exp_pl:
            current["export_prefix_list"] = m_exp_pl.group(1)

    if current:
        peers.append(current)

    return peers
