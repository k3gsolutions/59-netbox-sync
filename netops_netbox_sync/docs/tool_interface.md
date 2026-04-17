# Tool Interface — API JSON e Servidor HTTP

A ferramenta tem dois modos de uso:

| Modo | Arquivo | Quando usar |
|------|---------|-------------|
| **CLI JSON** | `app/tool.py` | Scripts, pipes, integração simples |
| **API HTTP (FastAPI)** | `app/api/main.py` | n8n HTTP Request, integrações REST, múltiplos clientes |

---

## API FastAPI (recomendada para n8n)

### Iniciar o servidor

```bash
# Com uvicorn diretamente
uvicorn app.api.main:app --host 0.0.0.0 --port 8888

# Ou via Python
python -m app.api.main

# Com .env carregado
source .env && uvicorn app.api.main:app --host $API_HOST --port $API_PORT
```

Docs interativas disponíveis em:
- **Swagger UI**: `http://localhost:8888/docs`
- **ReDoc**: `http://localhost:8888/redoc`

---

### Endpoints disponíveis

| Método | Path | O que faz |
|--------|------|-----------|
| `GET` | `/health` | Health check |
| `POST` | `/device/collect` | Coleta dados do dispositivo via SSH (sem escrever no NetBox) |
| `POST` | `/sync` | Coleta do dispositivo + sincroniza com o NetBox |
| `POST` | `/netbox/sessions` | Consulta sessões BGP no NetBox |
| `POST` | `/netbox/interfaces` | Consulta interfaces no NetBox |
| `POST` | `/netbox/ip-addresses` | Consulta IPs no NetBox |
| `POST` | `/netbox/routing-policies` | Consulta routing policies no NetBox |
| `POST` | `/netbox/prefix-lists` | Consulta prefix-lists no NetBox |
| `POST` | `/netbox/vrfs` | Consulta VRFs no NetBox |

---

### Autenticação

Configure `API_KEY` no `.env` para habilitar autenticação:

```env
API_KEY=minha-chave-secreta-aqui
```

Todas as requisições precisam do header:
```
X-API-Key: minha-chave-secreta-aqui
```

Se `API_KEY` não estiver definida, a API fica pública (adequado para redes internas).

---

### POST `/device/collect` — Coleta do dispositivo

```bash
curl -X POST http://localhost:8888/device/collect \
  -H "Content-Type: application/json" \
  -d '{
    "device": {
      "host": "172.30.0.1",
      "port": 51212,
      "username": "admin",
      "password": "secret"
    }
  }'
```

**Resposta:**
```json
{
  "summary": {
    "interfaces": 48, "ip_addresses": 31, "vrfs": 3,
    "vlans": 0, "bgp_sessions": 23, "route_policies": 12,
    "prefix_lists": 8, "as_path_filters": 4
  },
  "bgp_sessions": [
    {
      "peer_ip": "10.20.255.2", "peer_as": 263934, "local_as": 263934,
      "router_id": "10.10.1.5", "peer_type": "IBGP", "state": "Established",
      "description": "TO-CORE-01", "address_family": "ipv4", "vrf": null,
      "import_policy": "RP-IMPORT-IBGP", "export_policy": "RP-EXPORT-IBGP"
    }
  ]
}
```

---

### POST `/sync` — Coleta + sincronização

```bash
curl -X POST http://localhost:8888/sync \
  -H "Content-Type: application/json" \
  -d '{
    "device": {
      "host": "172.30.0.1",
      "port": 51212,
      "username": "admin",
      "password": "secret"
    },
    "netbox": {
      "url": "http://172.30.0.112:8080",
      "token": "ojnVy4NsPIDIC0HCyKfejdp7UU1ugmynZ1FrstUO",
      "verify_ssl": false
    },
    "device_id": 5
  }'
```

**Resposta:**
```json
{
  "inventory_summary": {
    "interfaces": 48, "bgp_sessions": 23, "route_policies": 12, ...
  },
  "bgp_changelog": {
    "totals": { "created": 5, "updated": 2, "skipped": 42 },
    "by_type": {
      "BGPSession":    { "created": 5, "updated": 2, "skipped": 16 },
      "PrefixList":    { "created": 3, "updated": 0, "skipped": 5 },
      "RoutingPolicy": { "created": 0, "updated": 1, "skipped": 11 }
    },
    "detail": [...]
  }
}
```

---

### POST `/netbox/sessions` — Consulta NetBox

```bash
curl -X POST http://localhost:8888/netbox/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "netbox": {
      "url": "http://172.30.0.112:8080",
      "token": "ojnVy4NsPIDIC0HCyKfejdp7UU1ugmynZ1FrstUO"
    },
    "device_id": 5
  }'
```

---

### Integração n8n com a API HTTP

#### Nó HTTP Request — Coleta de dados

| Campo | Valor |
|-------|-------|
| Method | `POST` |
| URL | `http://<servidor>:8888/device/collect` |
| Authentication | Header Auth → `X-API-Key: {{$env.NETOPS_API_KEY}}` |
| Body Content Type | `JSON` |
| Body | ver expressão abaixo |

```json
{
  "device": {
    "host":     "={{ $json.device_host }}",
    "port":     "={{ $json.device_port }}",
    "username": "={{ $json.username }}",
    "password": "={{ $json.password }}"
  }
}
```

#### Nó HTTP Request — Sincronização

```json
{
  "device": {
    "host":     "={{ $json.device_host }}",
    "port":     "={{ $json.device_port }}",
    "username": "={{ $json.username }}",
    "password": "={{ $json.password }}"
  },
  "netbox": {
    "url":   "http://172.30.0.112:8080",
    "token": "={{ $env.NETBOX_TOKEN }}"
  },
  "device_id": "={{ $json.netbox_device_id }}"
}
```

#### Fluxo n8n completo — sincronização automática

```
[Cron: 02:00]
      │
      ▼
[HTTP GET → NetBox /api/dcim/devices/?status=active]
      │  retorna lista de devices
      ▼
[Split In Batches]  ← 1 device por vez
      │
      ▼
[HTTP POST → :8888/device/collect]   ← verifica conectividade antes
      │
      ▼
[IF] status == "ok" e bgp_sessions > 0?
      │  sim                          │  não
      ▼                               ▼
[HTTP POST → :8888/sync]      [Slack] "Device offline/sem peers: {{name}}"
      │
      ▼
[Set] Extrai totais do changelog
      │  bgp_changelog.totals.created
      │  bgp_changelog.totals.updated
      ▼
[IF] created > 0 OR updated > 0?
      │  sim                          │  não
      ▼                               ▼
[Slack/Email]                  (silencioso - sem mudanças)
"Sync OK: {{created}} criados,
 {{updated}} atualizados"
```

---

## CLI JSON (app/tool.py)

`app/tool.py` é o ponto de entrada principal da ferramenta.
Recebe parâmetros via JSON e retorna resultado via JSON — sem interação humana.
Ideal para automação, integração com n8n, scripts externos e pipelines CI/CD.

---

## Como invocar

### Via stdin (pipe)
```bash
echo '{"device":{...},"netbox":{...},"action":"get"}' | python -m app.tool
```

### Via argumento posicional
```bash
python -m app.tool '{"device":{...},"netbox":{...},"action":"update"}'
```

### Via arquivo (prefixo `@`)
```bash
python -m app.tool @params_example.json
```

---

## Schema de entrada

```json
{
  "device": {
    "host":     "string (IP ou hostname)",
    "port":     22,
    "username": "string",
    "password": "string"
  },
  "netbox": {
    "url":        "string (ex: http://172.30.0.112:8080)",
    "token":      "string (token de API do NetBox)",
    "device_id":  5,
    "verify_ssl": false
  },
  "action": "get | update"
}
```

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| `device.host` | Sim | IP ou hostname do dispositivo |
| `device.port` | Não (padrão: 22) | Porta SSH |
| `device.username` | Sim | Usuário SSH |
| `device.password` | Sim | Senha SSH |
| `netbox.url` | Sim para `update` | URL base do NetBox |
| `netbox.token` | Sim para `update` | Token de API |
| `netbox.device_id` | Sim para `update` | ID do device no NetBox |
| `netbox.verify_ssl` | Não (padrão: false) | Verificar certificado TLS |
| `action` | Sim | `get` ou `update` |

---

## Ação: `get`

Conecta ao dispositivo via SSH, coleta todos os dados e retorna o inventário estruturado.
**Não faz nenhuma escrita no NetBox.**

### Exemplo de entrada
```json
{
  "device": {
    "host":     "172.30.0.1",
    "port":     51212,
    "username": "admin",
    "password": "secret"
  },
  "action": "get"
}
```

> `netbox` não é necessário para `get`.

### Exemplo de saída (sucesso)
```json
{
  "status": "ok",
  "summary": {
    "interfaces":      48,
    "ip_addresses":    31,
    "vrfs":             3,
    "vlans":            0,
    "bgp_sessions":    23,
    "route_policies":  12,
    "prefix_lists":     8,
    "as_path_filters":  4
  },
  "bgp_sessions": [
    {
      "peer_ip":        "10.20.255.2",
      "peer_as":        263934,
      "local_as":       263934,
      "router_id":      "10.10.1.5",
      "peer_type":      "IBGP",
      "state":          "Established",
      "description":    "TO-CORE-01",
      "address_family": "ipv4",
      "vrf":            null,
      "import_policy":  "RP-IMPORT-IBGP",
      "export_policy":  "RP-EXPORT-IBGP"
    },
    {
      "peer_ip":        "2001:db8::1",
      "peer_as":        65001,
      "local_as":       263934,
      "router_id":      "10.10.1.5",
      "peer_type":      "EBGP",
      "state":          "Established",
      "description":    "PEER-IPV6",
      "address_family": "ipv6",
      "vrf":            null,
      "import_policy":  "RP-IMPORT-IPV6",
      "export_policy":  null
    },
    {
      "peer_ip":        "172.16.0.1",
      "peer_as":        65100,
      "local_as":       263934,
      "router_id":      "10.10.1.5",
      "peer_type":      "EBGP",
      "state":          "Idle",
      "description":    "CDN-PEER",
      "address_family": "vpnv4",
      "vrf":            "CDN",
      "import_policy":  null,
      "export_policy":  null
    }
  ]
}
```

---

## Ação: `update`

Conecta ao dispositivo, coleta todos os dados e sincroniza com o NetBox:
1. Interfaces (com tipos e membros LACP)
2. IPs vinculados às interfaces
3. VRFs e VLANs
4. Sessões BGP com políticas e filtros (via plugin `netbox-bgp`)

Retorna um changelog detalhado de todas as criações e atualizações.

### Exemplo de entrada
```json
{
  "device": {
    "host":     "172.30.0.1",
    "port":     51212,
    "username": "admin",
    "password": "secret"
  },
  "netbox": {
    "url":        "http://172.30.0.112:8080",
    "token":      "ojnVy4NsPIDIC0HCyKfejdp7UU1ugmynZ1FrstUO",
    "device_id":  5,
    "verify_ssl": false
  },
  "action": "update"
}
```

### Exemplo de saída (sucesso)
```json
{
  "status": "ok",
  "inventory_summary": {
    "interfaces":      48,
    "ip_addresses":    31,
    "vrfs":             3,
    "vlans":            0,
    "bgp_sessions":    23,
    "route_policies":  12,
    "prefix_lists":     8,
    "as_path_filters":  4
  },
  "bgp_changelog": {
    "totals": {
      "created": 18,
      "updated":  3,
      "skipped": 42
    },
    "by_type": {
      "ASN":              { "created": 4, "updated": 0, "skipped": 2 },
      "ASPathList":       { "created": 4, "updated": 0, "skipped": 0 },
      "ASPathListRule":   { "created": 8, "updated": 0, "skipped": 0 },
      "BGPSession":       { "created": 5, "updated": 2, "skipped": 16 },
      "IPAddress":        { "created": 2, "updated": 0, "skipped": 44 },
      "PrefixList":       { "created": 3, "updated": 0, "skipped": 5 },
      "PrefixListRule":   { "created": 0, "updated": 0, "skipped": 24 },
      "RoutingPolicy":    { "created": 0, "updated": 1, "skipped": 11 },
      "RoutingPolicyRule":{ "created": 0, "updated": 0, "skipped": 18 }
    },
    "detail": [
      { "type": "ASN",        "name": "263934",        "action": "skipped", "detail": "" },
      { "type": "BGPSession", "name": "EBGP-10.0.0.1-ipv4", "action": "created", "detail": "" },
      { "type": "BGPSession", "name": "EBGP-2001:db8::1-ipv6", "action": "created", "detail": "" }
    ]
  }
}
```

### Saída de erro
```json
{
  "status": "error",
  "message": "netbox.device_id é obrigatório para action=update"
}
```

Erros são escritos em `stderr`. O processo termina com exit code `1`.

---

## Integração com n8n

### Pré-requisitos no servidor do n8n

O Python e este projeto devem ser acessíveis no servidor onde o n8n executa comandos.
Ou o n8n precisa de acesso HTTP a um servidor que exponha a tool como API (ver seção abaixo).

---

### Opção 1 — Execute Command (n8n local com acesso ao Python)

Use o nó **Execute Command** do n8n para chamar a tool diretamente.

**Configuração do nó:**

| Campo | Valor |
|-------|-------|
| Command | `python -m app.tool` |
| Working Directory | `/caminho/para/netops_netbox_sync` |
| Input Data | JSON via stdin |

**Expressão para o campo "Input":**
```json
{
  "device": {
    "host":     "{{ $json.device_host }}",
    "port":     {{ $json.device_port }},
    "username": "{{ $json.device_user }}",
    "password": "{{ $json.device_pass }}"
  },
  "netbox": {
    "url":       "http://172.30.0.112:8080",
    "token":     "{{ $env.NETBOX_TOKEN }}",
    "device_id": {{ $json.device_id }},
    "verify_ssl": false
  },
  "action": "{{ $json.action }}"
}
```

**Nó seguinte — Parse JSON:**
O nó **JSON** ou **Set** pode parsear o stdout do comando anterior:
```javascript
// Em um nó Function
return [{ json: JSON.parse($input.item.json.stdout) }];
```

---

### Opção 2 — HTTP Request (tool exposta como API Flask/FastAPI)

Para chamar de qualquer nó HTTP do n8n, envolva a tool em uma API mínima.

**`app/api_server.py`** (exemplo simples com Flask):

```python
from flask import Flask, request, jsonify
import subprocess, json, sys

app = Flask(__name__)

@app.route("/sync", methods=["POST"])
def sync():
    params = request.get_json()
    result = subprocess.run(
        [sys.executable, "-m", "app.tool", json.dumps(params)],
        capture_output=True, text=True,
        cwd="/caminho/para/netops_netbox_sync"
    )
    if result.returncode != 0:
        err = json.loads(result.stderr) if result.stderr else {"message": "erro desconhecido"}
        return jsonify(err), 500
    return jsonify(json.loads(result.stdout))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8888)
```

**No n8n — nó HTTP Request:**

| Campo | Valor |
|-------|-------|
| Method | POST |
| URL | `http://<servidor>:8888/sync` |
| Body Content Type | JSON |
| Body | expressão com os parâmetros |

**Corpo da requisição:**
```json
{
  "device": {
    "host":     "={{ $json.host }}",
    "port":     "={{ $json.port }}",
    "username": "={{ $json.username }}",
    "password": "={{ $json.password }}"
  },
  "netbox": {
    "url":       "http://172.30.0.112:8080",
    "token":     "={{ $env.NETBOX_TOKEN }}",
    "device_id": "={{ $json.device_id }}"
  },
  "action": "update"
}
```

---

### Fluxo n8n completo — exemplo de sincronização diária

```
[Cron Trigger]          → dispara toda noite às 02:00
       │
       ▼
[NetBox — HTTP Request] → GET /api/dcim/devices/?status=active
       │                  lista devices ativos para sincronizar
       ▼
[Split In Batches]      → itera 1 device por vez
       │
       ▼
[HTTP Request]          → POST http://<servidor>:8888/sync
       │                  body: { device: {...}, netbox: { device_id: {{id}} }, action: "update" }
       ▼
[IF]                    → status == "ok"?
       │  sim                           │ não
       ▼                                ▼
[Slack/Email]           →        [Slack/Email]
"Sync OK: N criados"           "ERRO no device X: {{message}}"
```

---

## Comportamento de saída e exit codes

| Situação | stdout | stderr | Exit code |
|----------|--------|--------|-----------|
| Sucesso | JSON com `"status": "ok"` | vazio | 0 |
| Parâmetro ausente | vazio | JSON com `"status": "error"` | 1 |
| Erro de conexão SSH | vazio | JSON com `"status": "error"` | 1 |
| Erro de API NetBox | vazio | JSON com `"status": "error"` | 1 |

---

## Arquivo de parâmetros de exemplo

O arquivo [`params_example.json`](../params_example.json) na raiz do projeto contém um template completo pronto para editar:

```bash
cp params_example.json meus_params.json
# edite host, senha, device_id...
python -m app.tool @meus_params.json
```
