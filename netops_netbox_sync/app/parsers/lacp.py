import re


def parse_lag_members(running_config: str) -> dict:
    """
    Retorna dict: { 'GigabitEthernet0/7/2': 'Eth-Trunk2', ... }
    Parseia blocos de interface do running config buscando 'eth-trunk <id>'.
    """
    members = {}
    current_iface = None

    for line in running_config.splitlines():
        m_iface = re.match(r"^interface (\S+)", line)
        if m_iface:
            current_iface = m_iface.group(1)
            continue

        m_trunk = re.match(r"^\s+eth-trunk (\d+)$", line)
        if m_trunk and current_iface:
            trunk_id = m_trunk.group(1)
            members[current_iface] = f"Eth-Trunk{trunk_id}"

    return members
