"""
Construção do grafo de dependências entre os objetos de roteamento.

Para cada peer BGP, mapeia a cadeia completa:
  peer → import/export policy → prefix-lists, as-path-filters,
         community-filters → valores de community → local-pref / MED

Também detecta:
  - Referências quebradas (policy referencia prefix-list que não existe)
  - Objetos não utilizados (prefix-list definida mas nunca referenciada)
  - Peers com policy ausente
"""
import re
from typing import Any

# Padrões de cláusulas match
_PL_V4   = re.compile(r"^ip-prefix\s+(\S+)")
_PL_V6   = re.compile(r"^ipv6\s+address\s+prefix-list\s+(\S+)")
_ASPATH  = re.compile(r"^as-path-filter\s+(\S+)")
_CF      = re.compile(r"^community-filter\s+(\S+)")
# Padrões de cláusulas apply
_COMM_VAL   = re.compile(r"\b(\d+:\d+)\b")
_LOCAL_PREF = re.compile(r"^local-preference\s+(\d+)")
_MED        = re.compile(r"^(?:cost|med)\s+(\d+)")
_NEXT_HOP   = re.compile(r"^ip-address\s+next-hop\s+(\S+)")
_ORIGIN     = re.compile(r"^origin\s+(\S+)")


def _analyze_policy(rp, pl_names: set, aspath_names: set, cl_names: set) -> dict:
    """Analisa uma route-policy e extrai todas as referências e ações."""
    result: dict[str, Any] = {
        "nodes":                 len(rp.nodes),
        "uses_prefix_lists":     [],
        "uses_ipv6_prefix_lists": [],
        "uses_aspath_filters":   [],
        "uses_community_filters": [],
        "sets_communities":      [],
        "sets_local_pref":       [],
        "sets_med":              [],
        "sets_next_hop":         [],
        "sets_origin":           [],
        "broken_refs":           [],
    }

    def _add_unique(lst: list, val):
        if val not in lst:
            lst.append(val)

    for node in rp.nodes:
        for clause in node.match:
            m = _PL_V4.match(clause)
            if m:
                ref = m.group(1)
                _add_unique(result["uses_prefix_lists"], ref)
                if ref not in pl_names:
                    result["broken_refs"].append(
                        {"type": "prefix-list", "ref": ref,
                         "node": node.sequence, "clause": clause}
                    )
                continue

            m = _PL_V6.match(clause)
            if m:
                ref = m.group(1)
                _add_unique(result["uses_ipv6_prefix_lists"], ref)
                continue

            m = _ASPATH.match(clause)
            if m:
                ref = m.group(1)
                _add_unique(result["uses_aspath_filters"], ref)
                if ref not in aspath_names:
                    result["broken_refs"].append(
                        {"type": "as-path-filter", "ref": ref,
                         "node": node.sequence, "clause": clause}
                    )
                continue

            m = _CF.match(clause)
            if m:
                ref = m.group(1)
                _add_unique(result["uses_community_filters"], ref)
                if ref not in cl_names:
                    result["broken_refs"].append(
                        {"type": "community-filter", "ref": ref,
                         "node": node.sequence, "clause": clause}
                    )
                continue

        for clause in node.apply:
            for val in _COMM_VAL.findall(clause):
                _add_unique(result["sets_communities"], val)

            m = _LOCAL_PREF.match(clause)
            if m:
                _add_unique(result["sets_local_pref"], int(m.group(1)))
                continue

            m = _MED.match(clause)
            if m:
                _add_unique(result["sets_med"], int(m.group(1)))
                continue

            m = _NEXT_HOP.match(clause)
            if m:
                _add_unique(result["sets_next_hop"], m.group(1))
                continue

            m = _ORIGIN.match(clause)
            if m:
                _add_unique(result["sets_origin"], m.group(1))

    return result


def _peer_chain(session, policy_map: dict, policy_names: set,
                direction: str) -> dict | None:
    """Monta a cadeia de um peer (import ou export)."""
    pol_name = (session.import_policy if direction == "import"
                else session.export_policy)
    if not pol_name:
        return None

    exists = pol_name in policy_names
    chain: dict[str, Any] = {
        "policy":        pol_name,
        "policy_exists": exists,
    }
    if exists:
        chain.update(policy_map[pol_name])
    else:
        chain["broken_refs"] = [
            {"type": "routing-policy", "ref": pol_name, "clause": f"{direction}-policy"}
        ]
    return chain


def build_dependency_graph(inventory) -> dict:
    """
    Constrói o grafo completo de dependências do inventário.

    Retorna dict com:
      peers      — por peer_ip (+ @vrf), cadeia import + export
      policies   — por nome, todas as referências e ações
      validation — referências quebradas, objetos não utilizados
    """
    # Conjuntos de nomes definidos
    pl_names     = {pl.name for pl in inventory.prefix_lists}
    aspath_names = {af.name for af in inventory.as_path_filters}
    cl_names     = {cl.name for cl in inventory.community_lists}
    policy_names = {rp.name for rp in inventory.route_policies}

    # Analisa todas as policies
    policy_map: dict[str, dict] = {}
    for rp in inventory.route_policies:
        policy_map[rp.name] = _analyze_policy(rp, pl_names, aspath_names, cl_names)

    # Monta cadeia por peer
    peers: dict[str, dict] = {}
    for session in inventory.bgp_sessions:
        key = session.peer_ip
        if session.vrf:
            key = f"{session.peer_ip}@{session.vrf}"

        peer_info: dict[str, Any] = {
            "peer_as":        session.peer_as,
            "peer_type":      session.peer_type,
            "state":          session.state,
            "address_family": session.address_family,
            "description":    session.description,
        }
        if session.vrf:
            peer_info["vrf"] = session.vrf

        import_chain = _peer_chain(session, policy_map, policy_names, "import")
        export_chain = _peer_chain(session, policy_map, policy_names, "export")
        if import_chain:
            peer_info["import_chain"] = import_chain
        if export_chain:
            peer_info["export_chain"] = export_chain

        peers[key] = peer_info

    # Objetos utilizados (acumulado de todas as policies)
    used_pl    : set[str] = set()
    used_aspath: set[str] = set()
    used_cl    : set[str] = set()
    used_pol   : set[str] = set()

    for session in inventory.bgp_sessions:
        for pol_name in filter(None, [session.import_policy, session.export_policy]):
            used_pol.add(pol_name)

    for pol in policy_map.values():
        used_pl.update(pol["uses_prefix_lists"])
        used_pl.update(pol["uses_ipv6_prefix_lists"])
        used_aspath.update(pol["uses_aspath_filters"])
        used_cl.update(pol["uses_community_filters"])

    # Consolida todas as referências quebradas
    all_broken: list[dict] = []
    for pol_name, pol in policy_map.items():
        for ref in pol["broken_refs"]:
            all_broken.append({"policy": pol_name, **ref})

    # Peers com policy ausente
    for peer_key, peer in peers.items():
        for direction in ("import_chain", "export_chain"):
            chain = peer.get(direction)
            if chain and not chain.get("policy_exists"):
                for ref in chain.get("broken_refs", []):
                    all_broken.append({"peer": peer_key, **ref})

    return {
        "peers":    peers,
        "policies": policy_map,
        "validation": {
            "total_issues":              len(all_broken),
            "broken_refs":               all_broken,
            "unused_prefix_lists":       sorted(pl_names - used_pl),
            "unused_aspath_filters":     sorted(aspath_names - used_aspath),
            "unused_community_filters":  sorted(cl_names - used_cl),
            "unused_routing_policies":   sorted(policy_names - used_pol),
        },
    }
