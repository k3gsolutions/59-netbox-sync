import re


def parse_vrfs(output: str):
    seen = {}

    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        # ignora linhas de cabeçalho e totalizadores
        if line.startswith("Total") or line.startswith("VPN-Instance Name"):
            continue

        # formato tabular: "CDN   263934:85   IPv4"
        parts = re.split(r"\s{2,}", line)
        if len(parts) >= 1:
            name = parts[0].strip()
            if not name:
                continue
            rd = parts[1].strip() if len(parts) >= 2 else None
            if rd and not re.match(r"^\d+:\d+$", rd):
                rd = None
            if name not in seen:
                seen[name] = {"name": name, "rd": rd or None}

    return list(seen.values())