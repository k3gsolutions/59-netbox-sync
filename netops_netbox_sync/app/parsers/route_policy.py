import re


def parse_route_policy(output: str) -> list:
    """
    Parseia a saída de 'display route-policy'.
    Retorna lista de dicts com nome, nós e cláusulas match/apply.
    """
    policies = []
    current_policy = None
    current_node = None

    for line in output.splitlines():
        # Nova policy
        m_policy = re.match(r"^Route-policy:\s+(\S+)", line)
        if m_policy:
            if current_policy:
                if current_node:
                    current_policy["nodes"].append(current_node)
                policies.append(current_policy)
            current_policy = {"name": m_policy.group(1), "nodes": []}
            current_node = None
            continue

        # Novo nó (permit/deny : <seq>)
        m_node = re.match(r"^\s+(permit|deny)\s*:\s*(\d+)", line)
        if m_node and current_policy:
            if current_node:
                current_policy["nodes"].append(current_node)
            current_node = {
                "action": m_node.group(1),
                "sequence": int(m_node.group(2)),
                "match": [],
                "apply": [],
            }
            continue

        # Cláusulas match
        m_match = re.match(r"^\s+if-match\s+(.+)$", line)
        if m_match and current_node is not None:
            current_node["match"].append(m_match.group(1).strip())
            continue

        # Cláusulas apply
        m_apply = re.match(r"^\s+apply\s+(.+)$", line)
        if m_apply and current_node is not None:
            current_node["apply"].append(m_apply.group(1).strip())

    # Flush final
    if current_policy:
        if current_node:
            current_policy["nodes"].append(current_node)
        policies.append(current_policy)

    return policies
