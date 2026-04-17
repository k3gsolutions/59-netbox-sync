import re


def parse_vlans(output: str):
    vlans = []
    for line in output.splitlines():
        line = line.strip()
        m = re.match(r"^(\d+)\s+(\S+)", line)
        if m:
            vlans.append({
                "vlan_id": int(m.group(1)),
                "name": m.group(2),
            })
    return vlans