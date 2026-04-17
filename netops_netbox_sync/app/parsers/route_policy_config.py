"""
Parser de route-policy a partir do running-config Huawei NE8000.

Formato no running-config:
  route-policy NAME permit node 10
   if-match ip-prefix PREFIX-LIST
   if-match as-path-filter FILTER
   if-match community-filter CF-NAME
   apply community 263934:100 additive
   apply local-preference 200
   apply med 100

Diferença do 'display route-policy':
  - Fonte única e atômica (mesmo snapshot do running-config já coletado)
  - Captura apply community, local-preference, med sem depender de display separado
  - Permite detectar referências cruzadas entre objetos
"""
import re


_POLICY_HEAD = re.compile(
    r"^route-policy\s+(\S+)\s+(permit|deny)\s+node\s+(\d+)", re.IGNORECASE
)
_IF_MATCH = re.compile(r"^\s+if-match\s+(.+)$")
_APPLY    = re.compile(r"^\s+apply\s+(.+)$")


def parse_route_policy_from_config(running_config: str) -> list:
    """
    Parseia todas as route-policies do running-config.

    Retorna lista no mesmo formato que parse_route_policy():
      [{"name": str, "nodes": [{"action", "sequence", "match": [], "apply": []}]}]

    Usado como fonte primária em build_inventory() — garante consistência
    com os demais parsers que também usam o running-config.
    """
    policies: dict[str, dict] = {}   # name → {name, nodes}
    current_node: dict | None = None

    for line in running_config.splitlines():
        m = _POLICY_HEAD.match(line)
        if m:
            name, action, seq = m.group(1), m.group(2).lower(), int(m.group(3))
            if name not in policies:
                policies[name] = {"name": name, "nodes": []}
            current_node = {
                "action":   action,
                "sequence": seq,
                "match":    [],
                "apply":    [],
            }
            policies[name]["nodes"].append(current_node)
            continue

        if current_node is None:
            continue

        m = _IF_MATCH.match(line)
        if m:
            current_node["match"].append(m.group(1).strip())
            continue

        m = _APPLY.match(line)
        if m:
            current_node["apply"].append(m.group(1).strip())
            continue

        # Linha não-indentada encerra o bloco do nó atual
        if line and not line[0].isspace():
            current_node = None

    return list(policies.values())
