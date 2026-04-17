# Plugin netbox-bgp — Instalação e Modelo de Dados

## Dependências

| Dependência | Versão mínima | Papel |
|-------------|--------------|-------|
| `netbox-bgp` | 0.18.1 | Plugin principal — modelos BGP no NetBox |
| NetBox | 4.5.x | Plataforma base |
| Django | 5.x | Framework web (já incluso no NetBox) |
| Python | 3.12+ | Runtime (já usado pelo NetBox) |
| `requests` | 2.28+ | Usado pelo `bgp_sync.py` para chamar a API do plugin |

---

## Instalação no servidor NetBox (akira — 172.30.0.112)

### Passo 1 — Instalar o pacote no ambiente virtual do NetBox

```bash
# Acesse o servidor
ssh usuario@172.30.0.112

# Ative o venv do NetBox
source /opt/netbox/venv/bin/activate

# Instale o plugin
pip install netbox-bgp==0.18.1
```

> **Se o NetBox rodar em Docker:**
> ```bash
> docker exec -it <container_netbox> /bin/bash
> source /opt/netbox/venv/bin/activate
> pip install netbox-bgp==0.18.1
> ```
> Ou adicione ao `plugin_requirements.txt` e reconstrua a imagem:
> ```
> netbox-bgp==0.18.1
> ```
> ```bash
> docker compose build --no-cache
> docker compose up -d
> ```

---

### Passo 2 — Habilitar o plugin no configuration.py

Edite `/opt/netbox/netbox/netbox/configuration.py` (ou o arquivo de configuração correspondente):

```python
PLUGINS = ['netbox_bgp']

PLUGINS_CONFIG = {
    'netbox_bgp': {
        'device_ext_page': 'right',   # onde exibir na página do device
        # opções: 'right' | 'left' | 'full_width' | 'tab' | '' (desabilitar)
    }
}
```

---

### Passo 3 — Rodar as migrations

```bash
cd /opt/netbox/netbox
python manage.py migrate
python manage.py collectstatic --no-input
```

---

### Passo 4 — Reiniciar os serviços

```bash
# systemd
sudo systemctl restart netbox netbox-rq

# ou Docker
docker compose restart netbox netbox-worker
```

---

### Verificação

```bash
# Confirmar que o plugin está instalado
pip show netbox-bgp

# Confirmar que o endpoint está disponível
curl -s http://172.30.0.112:8080/api/plugins/bgp/ \
  -H "Authorization: Token <SEU_TOKEN>" | python3 -m json.tool
```

---

## Modelo de dados do plugin

### BGPSession
Sessão BGP entre dois roteadores.

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `name` | string | Não | Nome descritivo (ex: `EBGP-179.54.45.21`) |
| `local_address` | FK → IPAddress | Sim | IP local da sessão (router-id ou interface) |
| `remote_address` | FK → IPAddress | Sim | IP do peer |
| `local_as` | FK → ASN | Sim | AS local |
| `remote_as` | FK → ASN | Sim | AS do peer |
| `status` | enum | Sim | `active`, `offline`, `planned` |
| `device` | FK → Device | Não | Dispositivo associado |
| `description` | string | Não | Descrição do peer |
| `import_policies` | M2M → RoutingPolicy | Não | Políticas de importação |
| `export_policies` | M2M → RoutingPolicy | Não | Políticas de exportação |
| `prefix_list_in` | FK → PrefixList | Não | Prefix-list de entrada |
| `prefix_list_out` | FK → PrefixList | Não | Prefix-list de saída |

**Mapeamento de estado (Huawei → NetBox):**
| VRP state | NetBox status |
|-----------|--------------|
| `Established` | `active` |
| `Idle(Admin)` | `planned` |
| `Idle` / outros | `offline` |

---

### RoutingPolicy
Política de roteamento (equivalente a route-policy no Huawei).

| Campo | Tipo | Obrigatório |
|-------|------|-------------|
| `name` | string | Sim |
| `description` | string | Não |

### RoutingPolicyRule
Nó de uma route-policy.

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `routing_policy` | FK | Sim | Policy pai |
| `index` | int | Sim | Sequência do nó |
| `action` | enum | Sim | `permit` ou `deny` |
| `match_custom` | JSON | Não | Cláusulas `if-match` |
| `set_actions` | JSON | Não | Cláusulas `apply` |

---

### PrefixList
Prefix-list de filtragem.

| Campo | Tipo | Obrigatório |
|-------|------|-------------|
| `name` | string | Sim |
| `family` | enum | Sim | `ipv4` ou `ipv6` |

### PrefixListRule
Entrada de uma prefix-list.

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `prefix_list` | FK | Sim | Lista pai |
| `index` | int | Sim | Sequência |
| `action` | enum | Sim | `permit` ou `deny` |
| `prefix_custom` | string | Não | Prefixo CIDR |
| `ge` | int | Não | Greater-or-equal (máscara mínima) |
| `le` | int | Não | Less-or-equal (máscara máxima) |

---

### ASN
Número de sistema autônomo (objeto nativo do NetBox ipam.asns).

| Campo | Tipo | Obrigatório |
|-------|------|-------------|
| `asn` | int | Sim |
| `rir` | FK → RIR | Sim | Usar RIR "Unknown" se não souber |

---

## Endpoints da API (após instalação)

```
GET/POST   /api/plugins/bgp/session/
GET/POST   /api/plugins/bgp/routing-policy/
GET/POST   /api/plugins/bgp/routing-policy-rule/
GET/POST   /api/plugins/bgp/prefix-list/
GET/POST   /api/plugins/bgp/prefix-list-rule/
GET/POST   /api/plugins/bgp/community/
GET/POST   /api/plugins/bgp/community-list/
GET/POST   /api/plugins/bgp/community-list-rule/
GET/POST   /api/ipam/asns/             ← nativo NetBox
GET/POST   /api/ipam/rirs/             ← nativo NetBox
```

---

## Como usar o bgp_sync.py após instalação do plugin

```python
from app.netbox.bgp_sync import sync_bgp_plugin

sync_bgp_plugin(
    base_url="http://172.30.0.112:8080",
    token="<SEU_TOKEN>",
    device_id=1,
    inventory=inv,       # DeviceInventory com bgp_sessions, route_policies, prefix_lists
    verify_ssl=False,
)
```

O `sync_bgp_plugin` faz na ordem:
1. Cria prefix-lists e suas regras
2. Cria route-policies e seus nós
3. Cria ASNs locais e remotos
4. Cria/resolve IPs locais e remotos
5. Cria sessões BGP
6. Vincula import/export policies e prefix-lists a cada sessão
