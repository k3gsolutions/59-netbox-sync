# netops_netbox_sync

Ferramenta de coleta e sincronização automática de dados de dispositivos Huawei NE8000 com o NetBox.

Conecta via SSH ao dispositivo, coleta todos os dados relevantes (interfaces, IPs, VRFs, sessões BGP, route-policies, prefix-lists, filtros AS-path) e sincroniza com o NetBox via REST API — incluindo o plugin `netbox-bgp` para dados estruturados de BGP.

---

## Visão geral da arquitetura

```
┌──────────────────────────────────────────────────────────────────┐
│                        app/tool.py                               │
│              Entry point JSON-in / JSON-out                      │
│         action: "get"  │  action: "update"                      │
└────────────┬───────────┴──────────────┬─────────────────────────┘
             │                          │
             ▼                          ▼
  ┌──────────────────┐      ┌───────────────────────┐
  │  SSH (Netmiko)   │      │   SSH (Netmiko)       │
  │  Coleta dados    │      │   Coleta + Sincroniza │
  └────────┬─────────┘      └──────────┬────────────┘
           │                           │
           ▼                           ▼
  ┌──────────────────┐      ┌───────────────────────┐
  │  HuaweiNE8000    │      │   sync_to_netbox()    │  ← DCIM/IPAM
  │  Collector       │      │   sync_bgp_plugin()   │  ← BGP Plugin
  └────────┬─────────┘      └──────────┬────────────┘
           │                           │
           ▼                           ▼
  ┌──────────────────┐      ┌───────────────────────┐
  │  Parsers +       │      │   NetBox API          │
  │  build_inventory │      │   172.30.0.112:8080   │
  └──────────────────┘      └───────────────────────┘
```

---

## Requisitos

- Python 3.12+
- Acesso SSH ao dispositivo Huawei NE8000
- NetBox 4.5+ com plugin `netbox-bgp` instalado
- Token de API do NetBox com permissões de leitura e escrita

```bash
# Instalar dependências
pip install -r requirements.txt
```

Dependências principais: `netmiko`, `pynetbox`, `pydantic`, `python-dotenv`, `requests`

---

## Modos de uso

### 1. API HTTP / FastAPI (recomendado para n8n e integrações)

Servidor REST com docs automáticas. Ideal para automação, n8n, múltiplos clientes.

```bash
# Instalar dependências
pip install -r requirements.txt

# Iniciar servidor
uvicorn app.api.main:app --host 0.0.0.0 --port 8888

# Docs interativas
# http://localhost:8888/docs
```

Endpoints principais:

| Endpoint | Ação |
|----------|------|
| `POST /device/collect` | Coleta dados do dispositivo (só leitura) |
| `POST /sync` | Coleta + sincroniza com o NetBox |
| `POST /netbox/sessions` | Consulta sessões BGP no NetBox |
| `POST /netbox/interfaces` | Consulta interfaces no NetBox |
| `GET /health` | Health check |

→ Documentação completa em [`docs/tool_interface.md`](docs/tool_interface.md)

### 2. Tool JSON (scripts e pipes)

Interface JSON-in/JSON-out para uso em linha de comando.

```bash
# Via stdin
echo '{"device":{...},"netbox":{...},"action":"get"}' | python -m app.tool

# Via arquivo
python -m app.tool @params_example.json
```

### 3. CLI interativa

```bash
python -m app.cli
```

Fluxo interativo: conecta ao dispositivo, exibe resumo, pede confirmação e sincroniza.
Usa variáveis de ambiente do arquivo `.env`.

---

## Configuração rápida (CLI interativa)

Copie e preencha o `.env`:

```bash
DEVICE_HOST=172.30.0.1
DEVICE_PORT=51212
DEVICE_USERNAME=admin
DEVICE_PASSWORD=secret

NETBOX_URL=http://172.30.0.112:8080
NETBOX_TOKEN=ojnVy4NsPIDIC0HCyKfejdp7UU1ugmynZ1FrstUO
NETBOX_VERIFY_SSL=false
```

---

## Dados coletados e sincronizados

| Dado | Origem (comando Huawei) | Destino NetBox |
|------|------------------------|----------------|
| Interfaces | `display interface brief` + `description` | `dcim.interfaces` |
| LAG/LACP | `display current-configuration` | `dcim.interfaces` (campo `lag`) |
| IPs | `display ip interface brief` | `ipam.ip_addresses` |
| VRFs | `display ip vpn-instance` | `ipam.vrfs` |
| VLANs | `display vlan` | `ipam.vlans` |
| Sessões BGP (IPv4/IPv6/VPNv4/VPNv6) | `display bgp peer verbose` | Plugin BGP: `session` |
| Route-policies | `display route-policy` | Plugin BGP: `routing-policy` |
| Prefix-lists | `display ip ip-prefix` | Plugin BGP: `prefix-list` |
| Filtros AS-path | `display ip as-path-filter` | Plugin BGP: `aspath-list` |

---

## Documentação complementar

| Documento | Conteúdo |
|-----------|----------|
| [`docs/tool_interface.md`](docs/tool_interface.md) | API JSON completa, exemplos de chamada, integração n8n |
| [`docs/bgp_plugin.md`](docs/bgp_plugin.md) | Instalação do plugin netbox-bgp, modelo de dados BGP |
| [`docs/netbox_data_model.md`](docs/netbox_data_model.md) | Modelo DCIM/IPAM, fluxo de sincronização, parsers |
