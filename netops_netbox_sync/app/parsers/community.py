"""
Parser de community do running_config Huawei NE8000.

Formatos suportados no running-config:

  1. Nomeados com índice explícito (formato real do device):
       ip community-filter basic   NAME index N permit|deny VALUE
       ip community-filter advanced NAME index N permit|deny REGEX

  2. Numerados (sem keyword basic/advanced):
       ip community-filter NUMBER index N permit|deny VALUE
       → tratado como type="basic", name=str(NUMBER)

  3. Legado sem índice (backward-compat):
       ip community-filter basic   NAME permit|deny VALUE
       ip community-filter advanced NAME permit|deny REGEX

  4. apply community X:Y [additive]   → valores individuais em route-policy
  5. community X:Y dentro de bgp/neighbor → valores individuais

Saída de parse_community_values():
  ["263934:100", "263934:200", ...]

Saída de parse_community_filters():
  [
    {
      "name": "C01-EXPORT-P1",
      "type": "basic",
      "entries": [
        {"index": 10, "action": "permit", "community": "64777:50101"},
      ]
    },
    {
      "name": "EXPORTA_CDNS",
      "type": "advanced",
      "entries": [
        {"index": 10, "action": "permit", "community": "64777:5210*"},
        {"index": 20, "action": "permit", "community": "64777:5220*"},
      ]
    }
  ]
"""
import re

# ── Padrões para parse_community_values ──────────────────────────────────────
_COMM_VALUE_RE = re.compile(r'\b(\d+:\d+)\b')

_APPLY_COMM_RE = re.compile(r'^\s+apply\s+community\s+(.+)$', re.IGNORECASE)
_CF_ANY_RE     = re.compile(
    r'^\s*ip\s+community-filter\s+(?:basic|advanced|\d+)\s+\S+\s+'
    r'(?:index\s+\d+\s+)?'
    r'(?:permit|deny)\s+(.+)$',
    re.IGNORECASE,
)
_BGP_COMM_RE   = re.compile(r'^\s+community\s+(.+)$', re.IGNORECASE)

# ── Padrões para parse_community_filters ─────────────────────────────────────

# Formato 1/2: com índice explícito
#   ip community-filter basic|advanced NAME index N permit|deny VALUE
_CF_NAMED_IDX = re.compile(
    r"^\s*ip\s+community-filter\s+"
    r"(basic|advanced)\s+"          # tipo
    r"(\S+)\s+"                      # nome
    r"index\s+(\d+)\s+"             # índice
    r"(permit|deny)\s+"             # ação
    r"(.+)$",                        # valor/regex
    re.IGNORECASE,
)

# Formato numerado com índice: ip community-filter NUMBER index N permit|deny VALUE
_CF_NUM_IDX = re.compile(
    r"^\s*ip\s+community-filter\s+"
    r"(\d+)\s+"                      # número (= nome)
    r"index\s+(\d+)\s+"             # índice
    r"(permit|deny)\s+"             # ação
    r"(.+)$",                        # valor
    re.IGNORECASE,
)

# Formato legado sem índice: ip community-filter basic|advanced NAME permit|deny VALUE
_CF_NAMED_LEGACY = re.compile(
    r"^\s*ip\s+community-filter\s+"
    r"(basic|advanced)\s+"
    r"(\S+)\s+"
    r"(permit|deny)\s+"
    r"(.+)$",
    re.IGNORECASE,
)


def parse_community_values(running_config: str) -> list:
    """
    Extrai todos os valores únicos de community (X:Y) do running-config.

    Fontes varridas:
      - apply community X:Y [additive]  (route-policy)
      - ip community-filter ... permit X:Y  (qualquer formato)
      - community X:Y  (bgp neighbor/peer-group)

    Retorna lista ordenada de strings únicas no formato "X:Y".
    """
    values: set[str] = set()
    for line in running_config.splitlines():
        m = _APPLY_COMM_RE.match(line) \
            or _CF_ANY_RE.match(line) \
            or _BGP_COMM_RE.match(line)
        if m:
            for val in _COMM_VALUE_RE.findall(m.group(1)):
                values.add(val)
    return sorted(values)


def parse_community_filters(running_config: str) -> list:
    """
    Extrai todas as definições de community-filter do running-config.

    Suporta:
      - ip community-filter basic|advanced NAME index N permit|deny VALUE
      - ip community-filter NUMBER index N permit|deny VALUE
      - ip community-filter basic|advanced NAME permit|deny VALUE  (legado)

    Agrupa entradas pelo nome, preserva o índice real do config.
    """
    lists: dict[str, dict] = {}

    def _add(name: str, cf_type: str, index: int, action: str, value: str):
        if name not in lists:
            lists[name] = {"name": name, "type": cf_type, "entries": []}
        # Evita duplicata de índice (mesmo filtro pode aparecer em múltiplas linhas)
        existing_idx = {e["index"] for e in lists[name]["entries"]}
        if index not in existing_idx:
            lists[name]["entries"].append({
                "index":     index,
                "action":    action.lower(),
                "community": value.strip(),
            })

    for line in running_config.splitlines():
        # Formato 1: nomeado com índice
        m = _CF_NAMED_IDX.match(line)
        if m:
            _add(m.group(2), m.group(1).lower(),
                 int(m.group(3)), m.group(4), m.group(5))
            continue

        # Formato 2: numerado com índice
        m = _CF_NUM_IDX.match(line)
        if m:
            _add(m.group(1), "basic",
                 int(m.group(2)), m.group(3), m.group(4))
            continue

        # Formato 3: legado sem índice (contador sequencial)
        m = _CF_NAMED_LEGACY.match(line)
        if m:
            name = m.group(2)
            if name not in lists:
                lists[name] = {"name": name, "type": m.group(1).lower(), "entries": []}
            idx = (max((e["index"] for e in lists[name]["entries"]), default=0) + 10)
            lists[name]["entries"].append({
                "index":     idx,
                "action":    m.group(3).lower(),
                "community": m.group(4).strip(),
            })

    return list(lists.values())
