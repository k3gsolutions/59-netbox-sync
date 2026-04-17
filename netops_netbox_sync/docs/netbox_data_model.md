# Modelo de Dados NetBox — netops_netbox_sync

## Visão Geral

O NetBox organiza dados em dois grandes grupos:

| Grupo | Módulo | Exemplos de objetos |
|-------|--------|---------------------|
| DCIM | Infraestrutura física | Device, Interface, Cable, Rack |
| IPAM | Gerenciamento de IPs | IP Address, Prefix, VRF, VLAN |
| Extras | Metadados e contextos | Config Context, Custom Fields, Tags |

---

## 1. Interfaces e LACP

### Como o NetBox modela interfaces

Cada interface é um objeto em `dcim.interfaces` com os campos principais:

```
device        → referência ao Device (FK)
name          → nome exato da interface
type          → slug do tipo físico (ver tabela abaixo)
enabled       → True/False (admin status)
description   → string livre
lag           → referência à interface pai (FK para outra interface do tipo "lag")
```

### Mapeamento de tipos Huawei → NetBox

| Prefixo Huawei | Tipo NetBox (slug) |
|----------------|--------------------|
| `Eth-TrunkN` (sem ponto) | `lag` |
| `100GE`, `400GE` | `100gbase-x-qsfp28` |
| `GigabitEthernet*(10G)`, `XGigabitEthernet` | `10gbase-x-sfpp` |
| `GigabitEthernet` (sem 10G) | `1000base-t` |
| `LoopBack`, `Tunnel`, `NULL`, `Virtual*` | `virtual` |
| Sub-interfaces (com `.`) | `other` |

### Como LACP (Eth-Trunk) é sincronizado

O sync faz **duas passagens**:

```
1ª passagem → cria todas as interfaces com seus tipos
              Eth-Trunk2  → type: "lag"
              GE0/7/2     → type: "10gbase-x-sfpp"

2ª passagem → vincula membros ao parent via campo "lag"
              GE0/7/2.lag = ID(Eth-Trunk2)
              GE0/7/3.lag = ID(Eth-Trunk2)
              100GE0/5/1.lag = ID(Eth-Trunk10)
```

A origem da informação de membro vem do parsing do `running_config`:
```
interface GigabitEthernet0/7/2
 eth-trunk 2          ← indica que esta interface é membro do Eth-Trunk2
```

---

## 2. IPs e VRFs

### VRFs (`ipam.vrfs`)

```
name   → nome do VPN-Instance no Huawei
rd     → Route Distinguisher (ex: "263934:85")
```

### IP Addresses (`ipam.ip_addresses`)

```
address                → prefixo CIDR (ex: "10.21.1.5/30")
status                 → "active"
assigned_object_type   → "dcim.interface"
assigned_object_id     → ID da interface no NetBox
```

O vínculo IP → Interface permite ao NetBox exibir os IPs no contexto do dispositivo.

---

## 3. BGP, Route-Policy e Filtros — Plugin netbox-bgp

O NetBox 4.x não tem modelo nativo para sessões BGP sem plugins.
Esta ferramenta usa o plugin **netbox-bgp** (v0.18+) para armazenar dados estruturados de BGP
com objetos dedicados — não Config Contexts.

→ Instalação e modelo de dados: [`bgp_plugin.md`](bgp_plugin.md)

### Objetos criados no plugin

| Endpoint | Objeto | Equivalente Huawei |
|----------|--------|-------------------|
| `/api/plugins/bgp/session/` | BGPSession | peer BGP |
| `/api/plugins/bgp/routing-policy/` | RoutingPolicy | route-policy |
| `/api/plugins/bgp/routing-policy-rule/` | RoutingPolicyRule | nó permit/deny |
| `/api/plugins/bgp/prefix-list/` | PrefixList | ip-prefix |
| `/api/plugins/bgp/prefix-list-rule/` | PrefixListRule | entrada do prefix |
| `/api/plugins/bgp/aspath-list/` | ASPathList | as-path-filter |
| `/api/plugins/bgp/aspath-list-rule/` | ASPathListRule | entrada do filtro |
| `/api/ipam/asns/` | ASN | AS number |

### Address families suportadas

A ferramenta coleta peers de todas as address families e VRFs:

| Address Family | Comando Huawei |
|----------------|---------------|
| IPv4 Unicast (global) | `display bgp peer verbose` |
| IPv6 Unicast (global) | `display bgp ipv6 peer verbose` |
| VPNv4 por VRF | `display bgp vpnv4 vpn-instance <vrf> peer verbose` |
| VPNv6 por VRF | `display bgp vpnv6 vpn-instance <vrf> peer verbose` |

O nome de cada sessão inclui AF e VRF para garantir unicidade:
```
EBGP-10.0.0.1-ipv4
EBGP-2001:db8::1-ipv6
EBGP-172.16.0.1-vpnv4/CDN
```

### Como acessar via API

```bash
# Listar sessões BGP de um device
GET /api/plugins/bgp/session/?device_id=5

# Listar routing policies
GET /api/plugins/bgp/routing-policy/

# Listar prefix-lists
GET /api/plugins/bgp/prefix-list/
```

---

## 4. Fluxo completo de sincronização

```
  JSON de entrada
  { device, netbox, action }
        │
        ▼  app/tool.py
  ┌─────────────────────────────────────────────────────────┐
  │                  COLETA (action=get ou update)          │
  │                                                         │
  │  HuaweiNE8000Collector.collect_all()                    │
  │    display version / current-configuration              │
  │    display interface brief / description                │
  │    display ip interface brief                           │
  │    display ip vpn-instance / vlan                       │
  │    display bgp all summary                              │
  │    display bgp peer verbose        → IPv4 global        │
  │    display bgp ipv6 peer verbose   → IPv6 global        │
  │    display route-policy                                 │
  │    display ip ip-prefix                                 │
  │    display ip as-path-filter                            │
  │                                                         │
  │  collect_bgp_all_vrfs(vrfs_output)                      │
  │    display bgp vpnv4 vpn-instance <vrf> peer verbose    │
  │    display bgp vpnv6 vpn-instance <vrf> peer verbose    │
  │                                                         │
  │  build_inventory(raw, vrf_bgp)                          │
  │    parse_interface_brief()  → interfaces + tipo         │
  │    parse_lag_members()      → membro → LAG parent       │
  │    parse_ip_interface_brief()                           │
  │    parse_vrfs() / parse_vlans()                         │
  │    parse_bgp_peers_verbose() × 3 AFs + N VRFs           │
  │    parse_route_policy()                                 │
  │    parse_ip_prefix() + parse_as_path_filter()           │
  │                                                         │
  │  → DeviceInventory (Pydantic)                           │
  └───────────────────┬─────────────────────────────────────┘
                      │ (somente action=update)
                      ▼
  ┌─────────────────────────────────────────────────────────┐
  │                 SYNC DCIM / IPAM                        │
  │  sync_to_netbox(nb, device_id, inventory)               │
  │    ipam.vrfs.create()                                   │
  │    ipam.vlans.create()                                  │
  │    dcim.interfaces.upsert()       ← 1ª passagem         │
  │    dcim.interfaces.update(lag=…)  ← 2ª passagem (LACP)  │
  │    ipam.ip_addresses.create()     ← vinculado à iface   │
  └───────────────────┬─────────────────────────────────────┘
                      │
                      ▼
  ┌─────────────────────────────────────────────────────────┐
  │                 SYNC BGP PLUGIN                         │
  │  sync_bgp_plugin(base_url, token, device_id, inventory) │
  │    [1/5] Prefix-lists + regras                          │
  │    [2/5] AS-path lists + regras                         │
  │    [3/5] Routing policies + regras                      │
  │    [4/5] ASNs (local + remote)                          │
  │    [5/5] BGP Sessions → vincula políticas               │
  └───────────────────┬─────────────────────────────────────┘
                      │
                      ▼
         JSON de saída { status, inventory_summary, bgp_changelog }
```

---

## 5. Parsers — referência

| Parser | Arquivo | Fonte (comando Huawei) | Retorno |
|--------|---------|------------------------|---------|
| `parse_interface_brief` | `parsers/interfaces.py` | `display interface brief` | lista de interfaces com admin/oper status |
| `parse_interface_description` | `parsers/interfaces.py` | `display interface description` | dict `name → description` |
| `get_interface_type` | `parsers/interfaces.py` | nome da interface | slug do tipo NetBox |
| `parse_ip_interface_brief` | `parsers/ipaddr.py` | `display ip interface brief` | lista de IPs com interface |
| `parse_vrfs` | `parsers/vrfs.py` | `display ip vpn-instance` | lista VRF + RD |
| `parse_vlans` | `parsers/vlans.py` | `display vlan` | lista VLAN ID + nome |
| `parse_bgp_peers` | `parsers/bgp.py` | `display bgp peer` | lista de sessões BGP (tabular, fallback) |
| `parse_bgp_peers_verbose` | `parsers/bgp.py` | `display bgp peer verbose` | sessões com políticas, estado e tipo |
| `parse_lag_members` | `parsers/lacp.py` | `running_config` | dict `interface → Eth-TrunkN` |
| `parse_route_policy` | `parsers/route_policy.py` | `display route-policy` | lista de policies com nós match/apply |
| `parse_ip_prefix` | `parsers/prefix_filter.py` | `display ip ip-prefix` | lista de prefix-lists com entradas |
| `parse_as_path_filter` | `parsers/prefix_filter.py` | `display ip as-path-filter` | lista de filtros AS-path |
