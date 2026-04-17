import re


def parse_ip_prefix(output: str) -> list:
    """
    Parseia 'display ip ip-prefix'.
    Retorna lista de prefix-lists com suas entradas.
    """
    prefix_lists = []
    current = None

    for line in output.splitlines():
        # Nova prefix-list
        m_name = re.match(r"^Prefix-list\s+(\S+)", line)
        if m_name:
            if current:
                prefix_lists.append(current)
            current = {"name": m_name.group(1), "entries": []}
            continue

        # Entrada de prefixo
        m_entry = re.match(
            r"^\s+index:\s*(\d+)\s+(permit|deny)\s+(\S+)(.*)?$", line
        )
        if m_entry and current:
            entry = {
                "index": int(m_entry.group(1)),
                "action": m_entry.group(2),
                "prefix": m_entry.group(3),
                "options": m_entry.group(4).strip() if m_entry.group(4) else "",
            }
            current["entries"].append(entry)

    if current:
        prefix_lists.append(current)

    return prefix_lists


def parse_as_path_filter(output: str) -> list:
    """
    Parseia 'display ip as-path-filter'.
    Retorna lista de filtros AS-path com suas entradas.
    """
    filters = []
    current = None

    for line in output.splitlines():
        m_name = re.match(r"^As path filter name:\s+(\S+)", line)
        if m_name:
            if current:
                filters.append(current)
            current = {"name": m_name.group(1), "entries": []}
            continue

        m_entry = re.match(r"^\s+index:\s*(\d+)\s+(permit|deny)\s+(.+)$", line)
        if m_entry and current:
            current["entries"].append({
                "index": int(m_entry.group(1)),
                "action": m_entry.group(2),
                "regex": m_entry.group(3).strip(),
            })

    if current:
        filters.append(current)

    return filters
