# netops_netbox_sync — Guia de Uso e Roadmap

## Índice

1. [Visão Geral](#1-visão-geral)
2. [Roadmap de Fluxo](#2-roadmap-de-fluxo)
3. [Interfaces de Acesso](#3-interfaces-de-acesso)
4. [Exemplos — CLI (python -m app.tool)](#4-exemplos--cli-python--m-apptool)
5. [Exemplos — API HTTP (FastAPI)](#5-exemplos--api-http-fastapi)
6. [Modelos de Resposta por Elemento](#6-modelos-de-resposta-por-elemento)
7. [Integração com n8n / Automações Externas](#7-integração-com-n8n--automações-externas)

**Outros documentos:**
- [`interdependencias_netbox.md`](interdependencias_netbox.md) — Fluxograma completo de dependências entre elementos, checklist de validação e cenários de falha
- [`netbox_data_model.md`](netbox_data_model.md) — Modelo de dados do NetBox (DCIM/IPAM/BGP)
- [`bgp_plugin.md`](bgp_plugin.md) — Detalhes do plugin netbox-bgp

---

## 1. Visão Geral

A tool conecta via SSH a roteadores **Huawei NE8000 (VRP)**, coleta a configuração completa e sincroniza com o **NetBox** (IPAM/DCIM + plugin `netbox-bgp`).

```
┌─────────────┐   SSH / Netmiko   ┌─────────────────────┐
│  Operador   │ ───────────────── │ Huawei NE8000 (VRP)  │
│  n8n / API  │                   └────────────┬────────┘
└──────┬──────┘                                │ display *
       │                              ┌─────────▼────────┐
       │  HTTP / CLI                  │   Collectors +    │
       ▼                              │   Parsers +       │
┌─────────────┐                      │   Normalizers      │
│  app.tool   │ ◄────────────────── │  (inventário)      │
│  FastAPI    │                      └─────────┬──────────┘
└──────┬──────┘                               │
       │  REST API (pynetbox / requests)       │
       ▼                                       │
┌─────────────┐  ◄────────────────────────────┘
│   NetBox    │
│  DCIM/IPAM  │
│  + netbox-  │
│    bgp      │
└─────────────┘
```

### O que é sincronizado

| Origem (VRP) | Destino (NetBox) | Elemento |
|---|---|---|
| `display interface brief` | `dcim/interfaces` | Interfaces + tipo + LAG |
| `display ip interface brief` | `ipam/ip-addresses` | IPs vinculados à interface |
| `display ip vpn-instance` | `ipam/vrfs` | VRFs com RD |
| `display vlan` | `ipam/vlans` | VLANs |
| `display bgp peer verbose` | `plugins/bgp/session` | Sessões BGP (IPv4/v6/VPNv4/v6) |
| `display route-policy` | `plugins/bgp/routing-policy` | Route-Policies + nodes |
| `display ip ip-prefix` | `plugins/bgp/prefix-list` | Prefix-lists + regras |
| `display ip as-path-filter` | `plugins/bgp/aspath-list` | AS-Path Filters + regras |
| `display current-configuration` | `plugins/bgp/community` | Valores de community (X:Y) |
| `display current-configuration` | `plugins/bgp/community-list` | Community-filter lists |

**Referência ao tenant:** todos os objetos criados/atualizados recebem:
- Campo `tenant` (objetos que suportam): Community, BGP Session, VRF, VLAN, IP
- Tag com slug do tenant (objetos sem campo tenant): RoutingPolicy, PrefixList, ASPathList, CommunityList

---

## 2. Roadmap de Fluxo

### Ação `get` — Consulta ao dispositivo

```
CLI / API
   │
   ├─ Abre conexão SSH (Netmiko)
   │
   ├─ HuaweiNE8000Collector.collect_all()
   │   ├─ display version
   │   ├─ display current-configuration
   │   ├─ display interface brief
   │   ├─ display interface description
   │   ├─ display ip interface brief
   │   ├─ display vlan
   │   ├─ display ip vpn-instance
   │   ├─ display bgp all summary
   │   ├─ display bgp peer verbose
   │   ├─ display bgp ipv6 peer verbose
   │   ├─ display route-policy
   │   ├─ display ip ip-prefix
   │   └─ display ip as-path-filter
   │
   ├─ collect_bgp_all_vrfs()          ← peers por VRF (VPNv4/v6)
   │
   ├─ build_inventory()               ← parseia + normaliza tudo
   │   ├─ parse_interface_brief()
   │   ├─ parse_ip_interface_brief()
   │   ├─ parse_vlans()
   │   ├─ parse_vrfs()
   │   ├─ parse_bgp_peers_verbose()
   │   ├─ parse_route_policy()
   │   ├─ parse_ip_prefix()
   │   ├─ parse_as_path_filter()
   │   ├─ parse_community_values()    ← extrai X:Y do running-config
   │   └─ parse_community_filters()   ← extrai ip community-filter
   │
   └─ Retorna DeviceInventory (JSON)
```

### Ação `update` — Sincronização com NetBox

```
CLI / API
   │
   ├─ [coleta SSH — igual ao get acima]
   │
   ├─ Resolve tenant do device no NetBox
   │   └─ dcim/devices/{id}  →  device.tenant (ex: INFORR)
   │
   ├─ sync_to_netbox() — DCIM/IPAM padrão
   │   ├─ VRFs   → ipam/vrfs           (cria se não existir, com tenant)
   │   ├─ VLANs  → ipam/vlans          (cria se não existir, com tenant)
   │   ├─ Interfaces → dcim/interfaces  (upsert: cria ou atualiza)
   │   ├─ LAG members → dcim/interfaces (2ª passagem: vincula parent)
   │   ├─ Resolve VRF do tenant         (cria se necessário)
   │   ├─ Migra IPs da tabela global → VRF do tenant
   │   └─ IPs    → ipam/ip-addresses    (cria/atualiza, na VRF do tenant)
   │
   ├─ sync_bgp_plugin() — plugin netbox-bgp
   │   ├─ [0]  Tag do tenant            (extras/tags — get or create)
   │   ├─ [0a] Communities X:Y          (plugins/bgp/community)
   │   ├─ [0b] Community-lists          (plugins/bgp/community-list)
   │   ├─ [1]  Prefix-lists + regras    (plugins/bgp/prefix-list[-rule])
   │   ├─ [2]  AS-Path Lists + regras   (plugins/bgp/aspath-list[-rule])
   │   ├─ [3]  Routing-policies + nodes (plugins/bgp/routing-policy[-rule])
   │   ├─ [4]  ASNs + IPs de peers      (ipam/asns, ipam/ip-addresses)
   │   └─ [5]  BGP Sessions             (plugins/bgp/session)
   │               └─ link_session_policies() — import/export policy + prefix-list
   │
   └─ Retorna ChangeLog (created / updated / skipped por tipo)
```

---

## 3. Interfaces de Acesso

A tool expõe **três interfaces**:

| Interface | Quando usar |
|---|---|
| **CLI** `python -m app.tool '...'` | Testes, scripts, cron, n8n Execute Command |
| **FastAPI HTTP** `POST /device/collect` etc. | Integrações, n8n HTTP Request, Postman |
| **Python direto** `from app.workflow...` | Embeds em outros projetos Python |

**URL base da API** (quando o servidor está rodando):
```
http://localhost:8888
```

**Iniciar o servidor:**
```bash
python -m uvicorn app.api.main:app --host 0.0.0.0 --port 8888 --reload
# ou
python -m app.api.main
```

**Documentação interativa:** http://localhost:8888/docs

---

## 4. Exemplos — CLI (`python -m app.tool`)

A tool recebe um JSON como argumento (string, `@arquivo.json` ou stdin).

### 4.1 Consultar dados do dispositivo (`get`)

```bash
python -m app.tool '{
  "action": "get",
  "device": {
    "host": "138.219.128.1",
    "port": 50022,
    "username": "keslley",
    "password": "#100784KyK_"
  },
  "netbox": {
    "url": "https://docs.k3gsolutions.com.br/api",
    "token": "c6b004ac425b1571ec2a06724f658da3a8bd6e58",
    "device_id": 2647
  }
}'
```

**Resposta:**
```json
{
  "status": "ok",
  "inventory_summary": {
    "interfaces": 98,
    "ip_addresses": 56,
    "vrfs": 2,
    "vlans": 23,
    "bgp_sessions": 57,
    "route_policies": 139,
    "prefix_lists": 97,
    "as_path_filters": 36,
    "communities": 84,
    "community_lists": 0
  },
  "bgp_sessions": [
    {
      "peer_ip": "10.20.0.6",
      "peer_as": 263934,
      "local_as": 263934,
      "router_id": "138.219.129.1",
      "peer_type": "IBGP",
      "state": "Established",
      "description": "Peer_INFORR_CDN-BVB-Direto",
      "address_family": "ipv4",
      "vrf": null,
      "import_policy": "AS263934-INFORR-CDN-Import-V4",
      "export_policy": "AS263934-INFORR-CDN-Export-V4"
    }
  ]
}
```

### 4.2 Sincronizar dispositivo com NetBox (`update`)

```bash
python -m app.tool '{
  "action": "update",
  "device": {
    "host": "138.219.128.1",
    "port": 50022,
    "username": "keslley",
    "password": "#100784KyK_"
  },
  "netbox": {
    "url": "https://docs.k3gsolutions.com.br/api",
    "token": "c6b004ac425b1571ec2a06724f658da3a8bd6e58",
    "device_id": 2647
  }
}'
```

**Resposta:**
```json
{
  "status": "ok",
  "inventory_summary": {
    "interfaces": 98,
    "ip_addresses": 56,
    "vrfs": 2,
    "vlans": 23,
    "bgp_sessions": 57,
    "route_policies": 139,
    "prefix_lists": 97,
    "as_path_filters": 36,
    "communities": 84,
    "community_lists": 0
  },
  "bgp_changelog": {
    "totals": {
      "created": 0,
      "updated": 54,
      "skipped": 1736
    },
    "by_type": {
      "Community":        {"created": 0, "updated": 84, "skipped": 0},
      "BGPSession":       {"created": 0, "updated": 54, "skipped": 3},
      "RoutingPolicy":    {"created": 0, "updated": 139, "skipped": 0},
      "PrefixList":       {"created": 0, "updated": 97, "skipped": 0},
      "ASPathList":       {"created": 0, "updated": 36, "skipped": 0},
      "PrefixListRule":   {"created": 0, "updated": 0, "skipped": 222},
      "RoutingPolicyRule":{"created": 0, "updated": 0, "skipped": 911}
    }
  }
}
```

### 4.3 Usando arquivo JSON (`@arquivo.json`)

```bash
# Cria o arquivo de parâmetros
cat > /tmp/sync_inforr.json << 'EOF'
{
  "action": "update",
  "device": {
    "host": "138.219.128.1",
    "port": 50022,
    "username": "keslley",
    "password": "#100784KyK_"
  },
  "netbox": {
    "url": "https://docs.k3gsolutions.com.br/api",
    "token": "c6b004ac425b1571ec2a06724f658da3a8bd6e58",
    "device_id": 2647
  }
}
EOF

# Executa passando o arquivo
python -m app.tool @/tmp/sync_inforr.json
```

### 4.4 Busca por nome ou device_id no NetBox

A tool aceita `device_id` ou `device_name` no bloco `netbox`:

```bash
# Por device_id
python -m app.tool '{
  "action": "update",
  "device": { "host": "138.219.128.1", "port": 50022,
              "username": "keslley", "password": "#100784KyK_" },
  "netbox": {
    "url": "https://docs.k3gsolutions.com.br/api",
    "token": "c6b004ac425b1571ec2a06724f658da3a8bd6e58",
    "device_id": 2647
  }
}'

# Por nome do device
python -m app.tool '{
  "action": "update",
  "device": { "host": "138.219.128.1", "port": 50022,
              "username": "keslley", "password": "#100784KyK_" },
  "netbox": {
    "url": "https://docs.k3gsolutions.com.br/api",
    "token": "c6b004ac425b1571ec2a06724f658da3a8bd6e58",
    "device_name": "INFORR-BVA-JCL-RX"
  }
}'
```

---

## 5. Exemplos — API HTTP (FastAPI)

### 5.1 `POST /device/collect` — Consultar dispositivo

Coleta dados via SSH. **Não escreve nada no NetBox.**

```bash
curl -X POST http://localhost:8888/device/collect \
  -H "Content-Type: application/json" \
  -d '{
    "device": {
      "host": "138.219.128.1",
      "port": 50022,
      "username": "keslley",
      "password": "#100784KyK_"
    }
  }'
```

**Python (requests):**
```python
import requests

resp = requests.post("http://localhost:8888/device/collect", json={
    "device": {
        "host": "138.219.128.1",
        "port": 50022,
        "username": "keslley",
        "password": "#100784KyK_"
    }
})
data = resp.json()
print(f"Interfaces: {data['summary']['interfaces']}")
print(f"BGP Sessions: {data['summary']['bgp_sessions']}")
for s in data['bgp_sessions'][:3]:
    print(f"  {s['peer_ip']} AS{s['peer_as']} [{s['state']}]")
```

**Resposta:**
```json
{
  "summary": {
    "interfaces": 98,
    "ip_addresses": 56,
    "vrfs": 2,
    "vlans": 23,
    "bgp_sessions": 57,
    "route_policies": 139,
    "prefix_lists": 97,
    "as_path_filters": 36
  },
  "bgp_sessions": [
    {
      "peer_ip": "10.20.0.6",
      "peer_as": 263934,
      "peer_type": "IBGP",
      "state": "Established",
      "description": "Peer_INFORR_CDN-BVB-Direto",
      "address_family": "ipv4",
      "import_policy": "AS263934-INFORR-CDN-Import-V4",
      "export_policy": "AS263934-INFORR-CDN-Export-V4"
    }
  ]
}
```

---

### 5.2 `POST /sync` — Sincronizar com NetBox

Coleta do dispositivo + escreve no NetBox.

```bash
curl -X POST http://localhost:8888/sync \
  -H "Content-Type: application/json" \
  -d '{
    "device": {
      "host": "138.219.128.1",
      "port": 50022,
      "username": "keslley",
      "password": "#100784KyK_"
    },
    "netbox": {
      "url": "https://docs.k3gsolutions.com.br",
      "token": "c6b004ac425b1571ec2a06724f658da3a8bd6e58",
      "verify_ssl": false
    },
    "device_id": 2647
  }'
```

**Python (requests):**
```python
import requests

resp = requests.post("http://localhost:8888/sync", json={
    "device": {
        "host": "138.219.128.1",
        "port": 50022,
        "username": "keslley",
        "password": "#100784KyK_"
    },
    "netbox": {
        "url": "https://docs.k3gsolutions.com.br",
        "token": "c6b004ac425b1571ec2a06724f658da3a8bd6e58",
        "verify_ssl": False
    },
    "device_id": 2647
}, timeout=300)

data = resp.json()
totals = data["bgp_changelog"]["totals"]
print(f"Criados: {totals['created']} | Atualizados: {totals['updated']} | Já existia: {totals['skipped']}")
```

---

### 5.3 `POST /netbox/sessions` — Consultar sessões BGP no NetBox

```bash
curl -X POST http://localhost:8888/netbox/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "netbox": {
      "url": "https://docs.k3gsolutions.com.br",
      "token": "c6b004ac425b1571ec2a06724f658da3a8bd6e58",
      "verify_ssl": false
    },
    "device_id": 2647
  }'
```

**Resposta (exemplo de sessão BGP):**
```json
{
  "total": 57,
  "sessions": [
    {
      "id": 4,
      "name": "EBGP-10.47.113.1-ipv4",
      "status": "active",
      "local_address": "138.219.129.1/32",
      "remote_address": "10.47.113.1/32",
      "local_as": 263934,
      "remote_as": 264409,
      "description": "AS264409-HUGE.264409",
      "import_policies": ["AS264409-HUGE-Import-v4"],
      "export_policies": ["AS264409-HUGE-Export-v4"]
    }
  ]
}
```

---

### 5.4 `POST /netbox/interfaces` — Consultar interfaces no NetBox

```bash
curl -X POST http://localhost:8888/netbox/interfaces \
  -H "Content-Type: application/json" \
  -d '{
    "netbox": {
      "url": "https://docs.k3gsolutions.com.br",
      "token": "c6b004ac425b1571ec2a06724f658da3a8bd6e58",
      "verify_ssl": false
    },
    "device_id": 2647
  }'
```

**Resposta (exemplo de interface):**
```json
{
  "total": 98,
  "interfaces": [
    {
      "id": 12341,
      "name": "GigabitEthernet0/0/0",
      "type": "1000base-t",
      "enabled": true,
      "description": "UPLINK-CORE",
      "lag": null
    },
    {
      "id": 12342,
      "name": "Eth-Trunk1",
      "type": "lag",
      "enabled": true,
      "description": "LACP-BUNDLE",
      "lag": null
    }
  ]
}
```

---

### 5.5 `POST /netbox/ip-addresses` — Consultar IPs no NetBox

```bash
curl -X POST http://localhost:8888/netbox/ip-addresses \
  -H "Content-Type: application/json" \
  -d '{
    "netbox": {
      "url": "https://docs.k3gsolutions.com.br",
      "token": "c6b004ac425b1571ec2a06724f658da3a8bd6e58",
      "verify_ssl": false
    },
    "device_id": 2647
  }'
```

**Resposta (exemplo de IP):**
```json
{
  "total": 56,
  "ip_addresses": [
    {
      "id": 9801,
      "address": "138.219.129.1/30",
      "status": "active",
      "interface": "GigabitEthernet0/0/0"
    },
    {
      "id": 9802,
      "address": "10.20.0.1/30",
      "status": "active",
      "interface": "GigabitEthernet0/0/1"
    }
  ]
}
```

---

### 5.6 `POST /netbox/vrfs` — Consultar VRFs no NetBox

```bash
curl -X POST http://localhost:8888/netbox/vrfs \
  -H "Content-Type: application/json" \
  -d '{
    "netbox": {
      "url": "https://docs.k3gsolutions.com.br",
      "token": "c6b004ac425b1571ec2a06724f658da3a8bd6e58",
      "verify_ssl": false
    }
  }'
```

**Resposta (exemplo de VRF):**
```json
{
  "total": 2,
  "vrfs": [
    {
      "id": 107,
      "name": "INFORR",
      "rd": "263934:100"
    },
    {
      "id": 108,
      "name": "CDN",
      "rd": "263934:200"
    }
  ]
}
```

---

### 5.7 `POST /netbox/routing-policies` — Consultar Route-Policies no NetBox

```bash
curl -X POST http://localhost:8888/netbox/routing-policies \
  -H "Content-Type: application/json" \
  -d '{
    "netbox": {
      "url": "https://docs.k3gsolutions.com.br",
      "token": "c6b004ac425b1571ec2a06724f658da3a8bd6e58",
      "verify_ssl": false
    }
  }'
```

**Resposta:**
```json
{
  "total": 139,
  "routing_policies": [
    {"id": 73, "name": "AS264409-HUGE-Export-v4", "description": ""},
    {"id": 74, "name": "AS264409-HUGE-Import-v4", "description": ""}
  ]
}
```

---

### 5.8 `POST /netbox/prefix-lists` — Consultar Prefix-Lists no NetBox

```bash
curl -X POST http://localhost:8888/netbox/prefix-lists \
  -H "Content-Type: application/json" \
  -d '{
    "netbox": {
      "url": "https://docs.k3gsolutions.com.br",
      "token": "c6b004ac425b1571ec2a06724f658da3a8bd6e58",
      "verify_ssl": false
    }
  }'
```

**Resposta:**
```json
{
  "total": 97,
  "prefix_lists": [
    {"id": 12, "name": "Meu-Bloco-24-1", "family": "ipv4"},
    {"id": 13, "name": "AS264409-4WNET",  "family": "ipv4"}
  ]
}
```

---

## 6. Modelos de Resposta por Elemento

### IP Address

```json
{
  "id": 9801,
  "address": "138.219.129.1/30",
  "status": "active",
  "vrf": {
    "id": 107,
    "name": "INFORR"
  },
  "tenant": {
    "id": 18,
    "name": "INFORR"
  },
  "interface": "GigabitEthernet0/0/0"
}
```

**Como é sincronizado:**
- Coletado via `display ip interface brief`
- Inserido em `ipam/ip-addresses` com `assigned_object_type: dcim.interface`
- Associado à VRF com nome igual ao tenant do device
- IPs em tabela global são migrados automaticamente para a VRF correta

---

### Interface

```json
{
  "id": 12341,
  "name": "GigabitEthernet0/0/0",
  "type": "1000base-t",
  "enabled": true,
  "description": "UPLINK-CORE",
  "lag": null,
  "device": {"id": 2647, "name": "INFORR-BVA-JCL-RX"}
}
```

**Tipos mapeados automaticamente:**
| Prefixo VRP | Tipo NetBox |
|---|---|
| `GigabitEthernet` | `1000base-t` |
| `XGigabitEthernet` | `10gbase-x-sfpp` |
| `40GE`, `40G` | `40gbase-x-qsfpp` |
| `100GE`, `100G` | `100gbase-x-qsfp28` |
| `Eth-Trunk` | `lag` |
| `LoopBack` | `virtual` |
| `Vlanif` | `virtual` |

---

### VLAN

```json
{
  "id": 551,
  "vid": 100,
  "name": "VLAN100",
  "tenant": {
    "id": 18,
    "name": "INFORR"
  }
}
```

---

### VRF

```json
{
  "id": 107,
  "name": "INFORR",
  "rd": "263934:100",
  "tenant": {
    "id": 18,
    "name": "INFORR"
  }
}
```

---

### BGP Session

```json
{
  "id": 4,
  "name": "EBGP-10.47.113.1-ipv4",
  "status": "active",
  "tenant": {"id": 18, "name": "INFORR"},
  "device": {"id": 2647, "name": "INFORR-BVA-JCL-RX"},
  "local_address": {"address": "138.219.129.1/32"},
  "remote_address": {"address": "10.47.113.1/32"},
  "local_as": {"asn": 263934},
  "remote_as": {"asn": 264409},
  "description": "AS264409-HUGE.264409",
  "import_policies": [
    {"id": 74, "name": "AS264409-HUGE-Import-v4"}
  ],
  "export_policies": [
    {"id": 73, "name": "AS264409-HUGE-Export-v4"}
  ]
}
```

**Naming convention:** `{EBGP|IBGP}-{peer_ip}-{af}[/{vrf}]`
- IPv4 global: `EBGP-10.47.113.1-ipv4`
- IPv6 global: `IBGP-2804:28e4::1-ipv6`
- VPNv4/VRF: `EBGP-192.168.1.1-vpnv4/CDN`

---

### BGP Community (valor individual)

```json
{
  "id": 201,
  "value": "263934:100",
  "status": "active",
  "tenant": {"id": 18, "name": "INFORR"}
}
```

**Origem:** extraído automaticamente de linhas `apply community X:Y` no running-config.

---

### Route-Policy

```json
{
  "id": 74,
  "name": "AS264409-HUGE-Import-v4",
  "description": "",
  "tags": [{"slug": "inforr", "name": "INFORR"}]
}
```

**Regras da policy (routing-policy-rule):**
```json
{
  "id": 445,
  "routing_policy": {"id": 74, "name": "AS264409-HUGE-Import-v4"},
  "index": 10,
  "action": "permit",
  "match_ip_address": [{"id": 12, "name": "Meu-Bloco-24-1"}],
  "match_aspath_list": [{"id": 8, "name": "AS264409-HUGE"}],
  "match_community_list": [],
  "set_actions": {"actions": ["local-preference 200"]}
}
```

---

### Prefix-List

```json
{
  "id": 12,
  "name": "Meu-Bloco-24-1",
  "family": "ipv4",
  "tags": [{"slug": "inforr", "name": "INFORR"}]
}
```

**Regras:**
```json
{
  "id": 88,
  "prefix_list": {"id": 12, "name": "Meu-Bloco-24-1"},
  "index": 5,
  "action": "permit",
  "prefix_custom": "138.219.128.0/24",
  "ge": 24,
  "le": 32
}
```

---

### AS-Path Filter

```json
{
  "id": 8,
  "name": "AS264409-HUGE",
  "tags": [{"slug": "inforr", "name": "INFORR"}]
}
```

**Regras:**
```json
{
  "id": 55,
  "aspath_list": {"id": 8, "name": "AS264409-HUGE"},
  "index": 10,
  "action": "permit",
  "pattern": "^264409_"
}
```

---

## 7. Integração com n8n / Automações Externas

### n8n — Execute Command (CLI)

Adicione um nó **Execute Command** com:

```
python3 -m app.tool '{"action":"update","device":{"host":"{{$json.host}}","port":50022,"username":"keslley","password":"#100784KyK_"},"netbox":{"url":"https://docs.k3gsolutions.com.br/api","token":"c6b004ac425b1571ec2a06724f658da3a8bd6e58","device_id":{{$json.device_id}}}}'
```

O stdout é JSON puro — parse com o nó **JSON** do n8n.

---

### n8n — HTTP Request (API)

**Nó HTTP Request:**
- Method: `POST`
- URL: `http://localhost:8888/sync`
- Body: `JSON`

```json
{
  "device": {
    "host": "{{ $json.device_ip }}",
    "port": 50022,
    "username": "keslley",
    "password": "#100784KyK_"
  },
  "netbox": {
    "url": "https://docs.k3gsolutions.com.br",
    "token": "c6b004ac425b1571ec2a06724f658da3a8bd6e58",
    "verify_ssl": false
  },
  "device_id": "{{ $json.netbox_id }}"
}
```

**Timeout recomendado:** 300 segundos (a coleta SSH pode levar 2-5 min).

---

### Chamada direta via Python (embed)

```python
from app.drivers.huawei_netmiko import HuaweiNetmikoDriver
from app.workflow.sync_device import run_update

driver = HuaweiNetmikoDriver(
    host="138.219.128.1",
    port=50022,
    username="keslley",
    password="#100784KyK_"
)
driver.open()
try:
    result = run_update(
        driver=driver,
        nb_url="https://docs.k3gsolutions.com.br",
        nb_token="c6b004ac425b1571ec2a06724f658da3a8bd6e58",
        device_id=2647,
        verify_ssl=False,
    )
finally:
    driver.close()

print(result["inventory_summary"])
print(result["bgp_changelog"]["totals"])
```

---

### Autenticação na API (opcional)

Se `API_KEY` estiver configurado no `.env`, todas as requisições precisam do header:

```
X-API-Key: <valor-definido-no-env>
```

**curl:**
```bash
curl -X POST http://localhost:8888/sync \
  -H "X-API-Key: minha-chave-segura" \
  -H "Content-Type: application/json" \
  -d '{...}'
```

---

*Gerado em 2026-04-06 | netops_netbox_sync*
