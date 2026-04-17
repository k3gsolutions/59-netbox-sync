import re


def get_interface_type(name: str) -> str:
    """Mapeia nome de interface Huawei para o type slug do NetBox."""
    if re.match(r"^Eth-Trunk\d+$", name):
        return "lag"
    if name.startswith("100GE") or name.startswith("400GE"):
        return "100gbase-x-qsfp28"
    if "(10G)" in name or name.startswith("10GE") or name.startswith("XGigabitEthernet"):
        return "10gbase-x-sfpp"
    if name.startswith("GigabitEthernet") and "(10G)" not in name:
        return "1000base-t"
    if name.startswith("LoopBack") or name.startswith("Loopback"):
        return "virtual"
    if name.startswith("Tunnel") or name.startswith("NULL") or name.startswith("Null"):
        return "virtual"
    if name.startswith("Virtual") or name.startswith("Virtual-Template"):
        return "virtual"
    # sub-interfaces mantêm o tipo do pai; usamos "other" como fallback
    if "." in name:
        return "other"
    return "other"


IFACE_PREFIXES = (
    "100GE", "10GE", "40GE", "400GE", "25GE",
    "Eth-Trunk", "GigabitEthernet", "XGigabitEthernet",
    "LoopBack", "Loopback", "NULL", "Null",
    "Tunnel", "Virtual-Ethernet", "Virtual-Template",
    "Ethernet", "Vlanif", "Pos", "Serial",
)


def parse_interface_brief(output: str):
    interfaces = []
    for line in output.splitlines():
        # membros de Eth-Trunk ficam indentados — ignorar
        if line != line.lstrip():
            continue
        line = line.strip()
        if not line or line.startswith("Interface") or line.startswith("-"):
            continue
        # ignora linhas de legenda (primeiro token termina com ':')
        first = line.split()[0]
        if first.endswith(":") or not first.startswith(IFACE_PREFIXES):
            continue

        m = re.match(r"^(\S+)\s+(\S+)\s+(\S+)", line)
        if m:
            interfaces.append({
                "name": m.group(1),
                "admin_status": m.group(2),
                "oper_status": m.group(3).strip("()"),
            })
    return interfaces


def parse_interface_description(output: str):
    descriptions = {}
    for line in output.splitlines():
        line = line.strip()
        if not line or line.startswith("Interface") or line.startswith("-"):
            continue

        parts = re.split(r"\s{2,}", line)
        if len(parts) >= 2:
            iface = parts[0].strip()
            desc = parts[-1].strip()
            descriptions[iface] = desc
    return descriptions