import re


def parse_ip_interface_brief(output: str):
    ips = []
    for line in output.splitlines():
        line = line.strip()
        if not line or line.startswith("Interface") or line.startswith("-"):
            continue

        parts = re.split(r"\s{2,}", line)
        if len(parts) >= 2:
            iface = parts[0]
            ip = parts[1]
            if ip.lower() != "unassigned":
                ips.append({
                    "interface": iface,
                    "address": ip,
                })
    return ips