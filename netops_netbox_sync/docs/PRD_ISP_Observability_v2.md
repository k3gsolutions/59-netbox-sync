# ISP Observability Automation Framework — Análise Crítica e PRD v2.0

**Autor da revisão:** Arquitetura K3G
**Status:** Proposta — substitui o PRD v1.0
**Stack alvo:** NetBox · Zabbix · Grafana · N8N · PostgreSQL · Redis · Git

---

## 0. Resumo executivo das mudanças

| # | Tema | PRD v1 (atual) | PRD v2 (proposto) | Por quê |
|---|------|----------------|-------------------|---------|
| 1 | Source of Truth | "NetBox **ou** Nautobot **ou** IXC **ou** YAML/Git" | **NetBox é a única SoT.** Nada mais. | Múltiplas SoTs = nenhuma SoT. K3G já usa NetBox. |
| 2 | Modelo de evento | Polling a cada 5/10/30 min | **Webhook-first**, com reconciliação por cron como rede de segurança | Provisionamento real-time; reduz janela de cegueira. |
| 3 | Discovery | Regex em descrição de interface | **Naming machine-parseable + LLD JS preprocessing + custom fields NetBox** | Regex em string humana é frágil; uma vírgula quebra tudo. |
| 4 | Naming convention | Brackets `[SVC:X] [CID:Y] ...` | Slug delimitado: `customer-l2vpn:acme:NB-1234:vc-2001` | Mais curto, mais fácil de parsear, sem brackets para escapar. |
| 5 | YAML como inventário | Schema com `monitoring.zabbix_template`, `grafana_dashboard` | **YAML acopla SoT a ferramenta** — separar concerns | Tooling muda; SoT não deve mudar com ele. |
| 6 | Templates Zabbix | Misto por fabricante e por serviço | **Atômicos e composíveis** (vendor-base + role + service) | Reuso real, evita "mega templates". |
| 7 | Grafana | Dashboards por persona, mas variáveis manuais | **Dashboards-template provisionadas via Git**, variáveis derivadas de tags | Zero clique para novo cliente. |
| 8 | Drift / reconciliação | Não tratado | **Job dedicado** + relatório auditável | NetBox e Zabbix divergem na vida real. |
| 9 | CI/CD | Não mencionado | **GitOps obrigatório**: templates, dashboards e schemas em Git com pipeline | Junior team precisa de guarda-corpo. |
| 10 | Idempotência | Citada en passant | **Princípio explícito + dry-run obrigatório em todo worker** | Re-rodar sync 100x precisa dar o mesmo resultado. |
| 11 | Brownfield | Ausente | Fase de **backfill assistido** com linter de descrição | Você tem rede em produção, não greenfield. |
| 12 | SLA/Criticality | Tag existe, sem efeito real | **Criticality drive-thru**: severidade, intervalo, SLA, escalation | Tag sem efeito é decoração. |
| 13 | Observabilidade da plataforma | Ausente | Sync worker, N8N, NetBox webhooks **monitoram a si mesmos** | Quem vigia o vigia. |
| 14 | DR / SPOF | Ausente | NetBox HA, backup diário, runbook de restore | NetBox vira o ponto crítico. |
| 15 | Multi-tenancy | Ausente | RBAC por tenant em NetBox/Zabbix/Grafana via host groups e folders | K3G é MSP — gerencia clientes-de-clientes. |

---

## 1. Diagnóstico do PRD v1

### 1.1 O que está correto e deve ser preservado

- **A premissa central** ("monitoramento como produto de engenharia, não tarefa do NOC") está certa.
- A separação em **discovery → tagging → triggers → dashboards** é o pipeline correto.
- O catálogo de **tipos de serviço** (cliente, operadora, L2VPN, BGP, CDN, IX, transporte) cobre o que um ISP típico precisa.
- A ideia de **dashboards genéricas com variáveis** está correta — é a única forma de escalar Grafana.
- O **fluxo de novo cliente** (entrada → SoT → config → discovery → dashboard) é o desenho certo.

### 1.2 Problemas estruturais

#### 1.2.1 Confusão de Source of Truth
O documento ora diz "NetBox", ora "Nautobot", ora "YAML/Git", ora "IXC/ERP". Isso é um anti-pattern. Toda SoT alternativa **vira inconsistente em semanas**. Decisão: **NetBox é único**. Outros sistemas (IXC/ERP) são *fontes comerciais* que **alimentam** NetBox via integração — não SoTs paralelas.

#### 1.2.2 Discovery por regex em descrição é frágil
```
description [SVC:CLIENTE] [CID:CID-10492] [CUSTOMER:EMPRESA-ABC] ...
```
Problemas reais que vão ocorrer:
- Operador digita `EMPRESA ABC` (com espaço) → regex quebra.
- Operador esquece o `[CID:...]` → discovery perde o serviço.
- Operador inverte ordem dos brackets → regex que assume ordem quebra.
- Caractere acentuado entra → regex Posix quebra.
- Limite de tamanho da descrição em alguns vendors (ifAlias = 64 bytes em IF-MIB padrão; alguns Huawei aceitam mais, mas não confiável).

Fix: **descrição = slug machine-parseable curto**, e os metadados ricos vivem no NetBox/Custom Fields. Discovery puxa o slug, faz lookup em NetBox via API, e enriquece o item.

#### 1.2.3 YAML acopla SoT à ferramenta
No schema v1:
```yaml
monitoring:
  zabbix:
    templates:
      - TEMPLATE_SERVICE_CLIENTE_INTERNET
  grafana:
    dashboard_profile: cliente-internet
```
Isso amarra o **inventário** ao **fornecedor de monitoramento**. Se trocar Zabbix por VictoriaMetrics+Grafana puro, reescreve tudo. **Concern errado**: a SoT diz *o que* o serviço é (criticidade, banda, BGP sim/não); a camada de monitoramento decide *como* monitorá-lo (mapeamento `role → templates`).

A regra é:
> **NetBox descreve o serviço. O `role_template_map` (Git) decide quais templates aplicar. Mude a ferramenta, mude o mapa — não o inventário.**

#### 1.2.4 Polling em vez de event-driven
"Sync a cada 5 min" significa **5 min de cegueira** entre cadastro e monitoramento. Para um circuito que sobe e tem incidente em 2 min, você descobre por reclamação. NetBox tem webhooks nativos (`device`, `interface`, `circuit`, `tenant`); use-os. Polling fica só como **rede de segurança** (reconciliação 30 min) e auditoria.

#### 1.2.5 Falta idempotência e dry-run como princípios
O algoritmo do PRD v1 cria/aplica/atualiza, mas não diz:
- O que acontece se rodar 2x? (precisa dar o mesmo estado)
- Como simular antes de aplicar? (`--dry-run` deveria ser default em staging)
- Como rollback? (Git revert + re-sync)

#### 1.2.6 Nenhuma menção a drift
Cenário real: alguém cria host direto no Zabbix (porque o NetBox estava lento, ou porque é fim-de-semana). NetBox não sabe. Sync não detecta. Esse host vira **fantasma** — recebe alertas, gera ruído, mas ninguém o "possui". Precisa de **reconciliação bidirecional**.

#### 1.2.7 Tag `criticality: gold` é decorativa
A tag existe, mas o PRD não diz **o que muda** entre `gold` e `bronze`. Sem efeito prático, vira lixo. Critério: criticidade precisa **dirigir** severidade da trigger, intervalo de coleta, perfil de alerta (WhatsApp imediato vs. e-mail batch), SLA, on-call.

#### 1.2.8 Brownfield ignorado
K3G e clientes têm rede em produção com descrições inconsistentes. O PRD v1 trata como greenfield. Precisa de **fase de migração** com linter, sugestão automática de descrição padronizada, e validação humana antes de aplicar.

#### 1.2.9 NetBox vira SPOF sem backup
Se NetBox cai, todo o pipeline para. Não basta dizer "use NetBox"; precisa de **HA, backup diário, runbook de restore** — e o pipeline precisa **degradar graciosamente** (cache local, fila de webhooks).

#### 1.2.10 Quem vigia o vigia?
Sync worker pode falhar. N8N pode estar fora. Webhook pode ter retry esgotado. Sem **observabilidade da plataforma de observabilidade**, descobre-se por sintoma. Precisa de:
- Heartbeat do sync worker no Zabbix.
- Métrica `webhook_processed_total{status="ok|fail"}`.
- Alerta se reconciliação reportar drift > N por mais de 1h.

---

## 2. Princípios não-negociáveis (PRD v2)

São **regras**, não sugestões. Toda decisão deve passar por elas.

1. **NetBox é a única SoT.** Tudo o mais é projeção dele.
2. **Se não está no NetBox, não existe.** Discovery sem match em NetBox vira *anomalia* auditável, não monitoramento "best effort".
3. **Event-driven primeiro, polling como rede de segurança.**
4. **Idempotência total.** Rodar o sync 1x ou 100x dá o mesmo estado.
5. **Dry-run em staging é mandatório antes de prod.**
6. **GitOps em tudo:** templates Zabbix, dashboards Grafana, schemas, role_template_map.
7. **Naming convention machine-parseable, com slug curto.** Brackets humanos vão para *comments* internos, não para descrição de interface.
8. **Tagging com taxonomia fechada.** Lista de chaves permitidas em Git; CI rejeita PR com tag não catalogada.
9. **Separação de concerns:** SoT descreve o serviço; `role_template_map` decide como monitorá-lo.
10. **Observabilidade da observabilidade:** o pipeline monitora a si mesmo.
11. **Multi-tenant por design.** K3G opera para múltiplos ISPs; permissions matter.
12. **Open source preferido, on-premise por default.** (Restrição da K3G.)

---

## 3. Arquitetura v2

```
   ┌─────────────────────────────────────────────────────────────┐
   │  IXC / ERP / Comercial  →  importa para  →  NetBox          │
   │  (fontes comerciais)                       (única SoT)      │
   └─────────────────────────────────────────────────────────────┘
                                │
                          webhooks (HTTP POST)
                                ▼
   ┌─────────────────────────────────────────────────────────────┐
   │                  N8N — Orchestrator                         │
   │  wf-netbox-router → wf-onboard-device                       │
   │                  → wf-onboard-circuit                       │
   │                  → wf-update-tenant                         │
   │                  → wf-decommission                          │
   │  wf-reconcile (cron 30min) — drift detection                │
   │  wf-error-handler (DLQ + Evolution API alert)               │
   └─────────────────────────────────────────────────────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
   ┌────────────────┐  ┌────────────────┐  ┌────────────────┐
   │ Zabbix API     │  │ Grafana API    │  │ Equipamentos   │
   │  hosts/groups  │  │  folders/perms │  │  (read-only    │
   │  templates     │  │  (dashboards   │  │   nesta fase;  │
   │  macros/tags   │  │   provisioning │  │   backup       │
   │  triggers      │  │   é Git→FS)    │  │   audita drift)│
   └────────────────┘  └────────────────┘  └────────────────┘
              │                 │
              ▼                 ▼
   ┌─────────────────────────────────────────────────────────────┐
   │  Postgres — audit log + DLQ + drift report                  │
   │  Redis — webhook retry queue + cache NetBox                 │
   └─────────────────────────────────────────────────────────────┘
              │
              ▼
   ┌─────────────────────────────────────────────────────────────┐
   │  Git monorepo: k3g-monitoring-iac                           │
   │  ├── netbox/custom-fields.yaml                              │
   │  ├── zabbix/templates/*.yaml                                │
   │  ├── grafana/dashboards/*.json                              │
   │  ├── role_template_map.yaml                                 │
   │  ├── tag_taxonomy.yaml                                      │
   │  └── n8n/workflows/*.json                                   │
   │  CI: lint + import staging + smoke tests                    │
   └─────────────────────────────────────────────────────────────┘
```

**Decisões-chave:**
- N8N como orquestrador (já é a stack K3G; junior team consegue manter).
- Postgres para audit + DLQ; Redis para retry queue (já presentes na stack K3G).
- Git monorepo agrega tudo que afeta monitoramento — atomic changes.
- Equipamentos em **read-only nesta fase**: o sistema lê descrição, valida no NetBox, audita. Aplicar configuração é Fase 2 (separada, com aprovação).

---

## 4. Modelo de dados — NetBox como SoT

### 4.1 Mapeamento de objetos NetBox → conceito de negócio

| Conceito | Objeto NetBox nativo | Custom fields necessários |
|----------|---------------------|---------------------------|
| Cliente / Operadora | `Tenant` (com `tenant_group`) | `crm_id`, `sla_target`, `escalation_profile` |
| Equipamento | `Device` | `criticality`, `monitoring_enabled` |
| Role do equipamento | `DeviceRole` | (usar slug: `pe`, `p`, `rr`, `olt`, `sw-access`, `sw-core`, `cgnat`, `bng`) |
| POP | `Site` | (já tem código nativo) |
| Interface de cliente | `Interface` | `service_type`, `circuit_id` (FK textual), `bandwidth_mbps` |
| Circuito (qualquer) | `Circuit` + `CircuitTermination` | `service_type`, `criticality`, `vc_id`, `sla_target`, `bandwidth_mbps` |
| Peering BGP | `Provider` + `ASN` + custom model `BGPSession` (plugin `netbox-bgp`) | `peer_type`, `address_family` |
| VRF | `VRF` | `tenant` (FK nativo) |
| L2VPN | `L2VPN` + `L2VPNTermination` (nativos a partir do NetBox 3.7+) | `service_type`, `vc_id` |

**Princípio:** usar primitivos nativos do NetBox sempre que existirem. Custom fields **complementam**, não substituem.

### 4.2 Choice fields obrigatórios

```yaml
# netbox/custom-fields/service_type.yaml
type: choice
required: true
applies_to: [circuit, interface, l2vpn]
choices:
  - customer-internet         # Cliente Internet dedicado
  - customer-l2vpn            # L2VPN cliente (VPWS/VPLS/EVPN)
  - customer-l3vpn            # L3VPN cliente (VRF MPLS)
  - customer-transport        # Transporte ponto-a-ponto
  - carrier-transit           # Trânsito de operadora
  - carrier-peering           # Peering privado
  - ix-public                 # Peering em IX (PTT.br, etc.)
  - cdn-cache                 # GGC, Netflix OCA, FNA, etc.
  - infra-backbone            # Link interno entre POPs
  - infra-management          # OOB, gerência
```

```yaml
# netbox/custom-fields/criticality.yaml
type: choice
required: true
applies_to: [device, circuit, l2vpn]
choices:
  - platinum   # Core, RR, sai imediato — escalation imediata
  - gold       # Cliente corporativo, operadora — alerta < 1 min
  - silver     # PME — alerta < 5 min
  - bronze     # Best-effort — alerta < 15 min
```

A criticidade **dirige**:
- **Severidade da trigger:** platinum=Disaster, gold=High, silver=Average, bronze=Warning.
- **Intervalo de coleta:** platinum=30s, gold=60s, silver=120s, bronze=300s.
- **Perfil de alerta:** platinum=ligação automática + WhatsApp NOC sênior; gold=WhatsApp NOC; silver=WhatsApp grupo; bronze=e-mail batch.
- **SLA target:** platinum=99.99%, gold=99.95%, silver=99.5%, bronze=99%.

Esse mapa fica em `criticality_profile.yaml` no Git.

---

## 5. Naming convention machine-parseable

### 5.1 Princípio
- O nome carrega o **mínimo** para o sync funcionar offline (sem consultar API).
- Metadados ricos ficam no NetBox.
- Slug, lowercase, sem acento, sem espaço.

### 5.2 Formato canônico

```
<service_type>:<tenant_slug>:<netbox_id>[:<extra>]
```

Onde:
- `service_type` — um dos enums acima (`customer-l2vpn`, etc.).
- `tenant_slug` — slug NetBox do tenant (ex.: `acme-corp`).
- `netbox_id` — ID NetBox do objeto (Circuit, Interface, etc.) prefixado: `NB-1234`.
- `extra` — opcional (ex.: `vc-2001`, `pe1-pe2`).

### 5.3 Exemplos

| Tipo | Descrição da interface | Significado |
|------|------------------------|-------------|
| Cliente Internet (BGP) | `customer-internet:acme-corp:NB-1234` | Acme, Circuit 1234 NetBox |
| L2VPN VPWS | `customer-l2vpn:beta-sa:NB-2017:vc-2017` | Beta, Circuit 2017, VC ID 2017 |
| Trânsito Embratel | `carrier-transit:embratel:NB-9001` | Embratel uplink |
| Peering Google | `cdn-cache:google:NB-5500` | GGC Google |
| Backbone | `infra-backbone:k3g:NB-3001:mao-pop1-mao-pop2` | Link entre POPs |

### 5.4 Validação automática
```regex
^(customer-internet|customer-l2vpn|customer-l3vpn|customer-transport|carrier-transit|carrier-peering|ix-public|cdn-cache|infra-backbone|infra-management):[a-z0-9-]{2,32}:NB-[0-9]+(:[\w-]+)?$
```

CI rejeita PR de descrição que não case. Sync N8N rejeita webhook com descrição não-conforme (joga em DLQ + abre alerta).

### 5.5 Onde o nome humano fica
- Nome do cliente legível: campo `name` do `Tenant` em NetBox.
- Descrição comercial: `description` do `Circuit`.
- Comentários técnicos: `comments` do `Interface`.

A descrição da interface no equipamento **não** é documentação humana — é chave de lookup. Documentação humana fica no NetBox (que renderiza bonito no dashboard de cliente).

---

## 6. Discovery: do regex frágil ao LLD JS preprocessing

### 6.1 Pipeline em 3 estágios

```
1. SNMP descobre interface (ifIndex, ifAlias)
2. Zabbix LLD JavaScript preprocessing parseia ifAlias
3. Item prototype puxa metadados do NetBox via HTTP agent (cache 1h)
```

### 6.2 Preprocessing JavaScript no LLD (Zabbix 6.0+)

```javascript
// LLD preprocessing applied to {#IFALIAS}
// Returns enriched LLD macros for item prototypes
var alias = (value || "").trim().toLowerCase();

// Matches naming convention
var rx = /^([a-z-]+):([a-z0-9-]+):nb-(\d+)(?::(.+))?$/;
var m = alias.match(rx);

if (!m) {
    // Não-conforme: marca para auditoria, mas continua descoberta para sinalizar
    return JSON.stringify({
        "{#SERVICE_TYPE}": "unknown",
        "{#TENANT}":       "unknown",
        "{#NETBOX_ID}":    "0",
        "{#EXTRA}":        "",
        "{#COMPLIANT}":    "false"
    });
}

return JSON.stringify({
    "{#SERVICE_TYPE}": m[1],
    "{#TENANT}":       m[2],
    "{#NETBOX_ID}":    m[3],
    "{#EXTRA}":        m[4] || "",
    "{#COMPLIANT}":    "true"
});
```

### 6.3 Item prototypes que enriquecem via NetBox

```yaml
# Pseudo-template
- name: 'Interface {#IFNAME}: tenant name (from NetBox)'
  type: HTTP_AGENT
  url: '{$NETBOX_URL}/api/circuits/circuits/{#NETBOX_ID}/?brief=true'
  headers:
    Authorization: Token {$NETBOX_TOKEN}
  delay: 1h                       # NetBox não muda toda hora
  preprocessing:
    - type: JSONPATH
      params: '$.tenant.name'
  tags:
    - tag: service_type
      value: '{#SERVICE_TYPE}'
    - tag: tenant
      value: '{#TENANT}'
    - tag: netbox_id
      value: '{#NETBOX_ID}'
    - tag: compliant
      value: '{#COMPLIANT}'
```

### 6.4 Trigger para descrição não-conforme

```
Trigger: "Interface descoberta com descrição não-conforme"
Expression: count(/Template/compliance.check[{#IFNAME}],#1,"eq","false")=1
Severity: Warning
Tags:
  - alert_class: governance
  - owner: noc-engineering
```

Resultado: **descoberta acontece sempre**, mas descrição quebrada gera alerta de governança em vez de monitoramento silencioso e errado.

---

## 7. Templates Zabbix — atômicos, composíveis, versionados

### 7.1 Hierarquia

```
┌─────────────────────────────────┐
│ TEMPLATES VENDOR-BASE           │  Snmp, env, fan, psu, cpu, mem
│  T_HUAWEI_NE8000_BASE           │  Reusável em qualquer host Huawei NE8000
│  T_HUAWEI_S6730_BASE            │
│  T_JUNIPER_MX_BASE              │
│  T_MIKROTIK_ROS_BASE            │
│  T_DATACOM_DMOS_BASE            │
└─────────────────────────────────┘
                +
┌─────────────────────────────────┐
│ TEMPLATES POR ROLE              │  O que muda entre PE, P, RR, OLT...
│  T_ROLE_PE                      │  Tem clientes, tem BGP CE, tem VRFs
│  T_ROLE_P                       │  Sem clientes, só MPLS/IGP
│  T_ROLE_RR                      │  Foco BGP sessions
│  T_ROLE_OLT                     │
│  T_ROLE_SW_CORE                 │
└─────────────────────────────────┘
                +
┌─────────────────────────────────┐
│ TEMPLATES POR SERVIÇO           │  Aplicado seletivamente
│  T_SVC_BGP_PEERING              │  Discovery de peers BGP
│  T_SVC_L2VPN_VPWS               │  Discovery de pseudowires
│  T_SVC_L3VPN_VRF                │  Discovery de VRFs
│  T_SVC_INTERFACE_CUSTOMER       │  Filtra LLD para customer-*
│  T_SVC_INTERFACE_CARRIER        │  Filtra LLD para carrier-*
│  T_SVC_INTERFACE_INFRA          │
└─────────────────────────────────┘
                +
┌─────────────────────────────────┐
│ TEMPLATE GOVERNANÇA             │
│  T_GOV_NAMING_COMPLIANCE        │  Audita descrições não-conformes
│  T_GOV_HEARTBEAT_AGENT          │  Heartbeat do sync worker
└─────────────────────────────────┘
```

### 7.2 `role_template_map.yaml` (em Git)

```yaml
# Decide quais templates aplicar em cada device baseado no role NetBox
roles:
  pe:
    base_by_vendor:
      huawei: T_HUAWEI_NE8000_BASE
      juniper: T_JUNIPER_MX_BASE
    role: T_ROLE_PE
    services:
      - T_SVC_BGP_PEERING
      - T_SVC_L2VPN_VPWS
      - T_SVC_L3VPN_VRF
      - T_SVC_INTERFACE_CUSTOMER
      - T_SVC_INTERFACE_CARRIER
    governance:
      - T_GOV_NAMING_COMPLIANCE

  p:
    base_by_vendor:
      huawei: T_HUAWEI_NE8000_BASE
    role: T_ROLE_P
    services: []
    governance:
      - T_GOV_NAMING_COMPLIANCE

  rr:
    base_by_vendor:
      huawei: T_HUAWEI_NE8000_BASE
    role: T_ROLE_RR
    services:
      - T_SVC_BGP_PEERING

  sw-access:
    base_by_vendor:
      huawei: T_HUAWEI_S6730_BASE
      mikrotik: T_MIKROTIK_ROS_BASE
    role: T_ROLE_SW_ACCESS
    services:
      - T_SVC_INTERFACE_CUSTOMER

  olt:
    base_by_vendor:
      huawei: T_HUAWEI_OLT_BASE
      datacom: T_DATACOM_OLT_BASE
    role: T_ROLE_OLT
    services: []
```

Sync worker resolve no momento de criar/atualizar host:
```
host = NetBox device
templates = base_by_vendor[device.platform.vendor] +
            role +
            services +
            governance
```

### 7.3 Macros padronizadas (overridable em host)

```yaml
{$SNMP_COMMUNITY}              # default: read-only
{$SNMP_VERSION}                # default: 3
{$IFOPER.UTIL.WARN}            # 70%
{$IFOPER.UTIL.HIGH}            # 85%
{$IFOPER.UTIL.CRIT}            # 95%
{$BGP.SESSION.RECOVER.TIME}    # 60s
{$L2VPN.OAM.TIMEOUT}           # 5s
{$NETBOX_URL}                  # global, secret
{$NETBOX_TOKEN}                # global, secret (Vault no futuro)
{$CRITICALITY}                 # platinum|gold|silver|bronze (vem do NetBox)
{$ALERT.PROFILE}               # vem do criticality_profile.yaml
```

---

## 8. Grafana — dashboards data-driven via Git

### 8.1 Anti-pattern a abolir
"Dashboard por cliente" é a fonte primária de débito técnico em monitoramento de ISP. Quando o cliente sai, a dashboard fica órfã. Quando o painel-padrão evolui, é preciso editar 200 dashboards. **Nunca mais.**

### 8.2 Dashboards-template (em Git, provisionadas via Grafana provisioning)

```
grafana/
├── provisioning/
│   ├── dashboards.yaml                # aponta pro filesystem
│   └── datasources.yaml
└── dashboards/
    ├── customer/
    │   ├── customer-overview.json     # 1 dashboard p/ TODOS os clientes
    │   └── customer-circuit-detail.json
    ├── carrier/
    │   ├── carrier-uplink-health.json
    │   └── carrier-bgp-status.json
    ├── infra/
    │   ├── pop-health.json
    │   ├── backbone-utilization.json
    │   └── core-bgp-fabric.json
    ├── noc/
    │   ├── noc-overview.json
    │   └── noc-active-incidents.json
    └── platform/
        └── observability-self.json    # observa o pipeline
```

### 8.3 Variáveis derivadas de tags Zabbix

```
$tenant         → query: tag.tenant in items
$service_type   → query: tag.service_type in items
$pop            → query: tag.pop in items
$device         → query: host.name where tag.role=...
$criticality    → query: tag.criticality in items
```

Para `customer-overview.json`, basta abrir:
```
https://grafana.k3g/d/customer-overview/?var-tenant=acme-corp
```
e a dashboard mostra **só** o que é Acme, com base nas tags Zabbix. Zero painel manual, zero dashboard órfã.

### 8.4 Folders e RBAC (multi-tenant)

```
Grafana folders:
  /Customers/Acme Corp        → permissão: viewer Acme + admin K3G NOC
  /Customers/Beta SA          → permissão: viewer Beta + admin K3G NOC
  /Internal/Backbone          → admin K3G NOC + engenharia
  /Internal/Carriers          → admin K3G NOC + engenharia
  /Internal/Platform          → admin K3G NOC + engenharia
```

Provisionado via API (Grafana folder permissions), versionado em `grafana/folders/*.yaml`.

---

## 9. N8N — workflows obrigatórios

### 9.1 Lista mínima

| Workflow | Trigger | Função |
|----------|---------|--------|
| `wf-netbox-router` | Webhook | Recebe payload NetBox, valida HMAC, roteia por `event` + `model` |
| `wf-onboard-device` | Sub-workflow | Cria host Zabbix, aplica grupos+templates+tags+macros |
| `wf-onboard-interface` | Sub-workflow | Valida descrição compliant; ativa LLD se necessário |
| `wf-onboard-circuit` | Sub-workflow | Cria itens de circuito (L2VPN/L3VPN), tags |
| `wf-onboard-tenant` | Sub-workflow | Cria host group `/Customers/<tenant>` no Zabbix; folder Grafana |
| `wf-update` | Sub-workflow | Atualiza tags/macros quando custom field muda no NetBox |
| `wf-decommission` | Sub-workflow | Desabilita host (não deleta) — preserva histórico SLA |
| `wf-reconcile` | Cron 30 min | Lê NetBox completo, compara com Zabbix, gera diff e corrige (com dry-run em staging) |
| `wf-audit-write` | Chamado por todos | Grava em Postgres tabela `monitoring_audit_log` |
| `wf-error-handler` | Erro de qualquer wf | Grava em DLQ, alerta via Evolution API |
| `wf-heartbeat` | Cron 1 min | Pinga endpoint `/health` que Zabbix monitora — se cair, NOC sabe |
| `wf-compliance-report` | Cron diário | Lista interfaces não-conformes, hosts órfãos, dashboards mortas → e-mail |

### 9.2 Boas práticas N8N (já está na prática K3G, reforço aqui)

- **1 webhook = 1 workflow.** Roteia em sub-workflows.
- **Credenciais sempre em N8N credentials store**, nunca hardcoded.
- **HMAC obrigatório** em webhooks NetBox (compartilhar secret).
- **Retry com backoff** em chamadas Zabbix/Grafana.
- **Idempotência:** todo update faz `host.get → diff → update if changed`. Sem `host.delete + host.create`.
- **DLQ obrigatório** em todo node que faz IO externo.

### 9.3 Sketch de `wf-onboard-device`

```
[Webhook NetBox] 
    ↓ (event=created, model=device)
[Validate Custom Fields] ─── falta criticality? → DLQ + alerta
    ↓
[Resolve Templates from Map] (lê role_template_map.yaml de Git via API)
    ↓
[Zabbix host.get] (existe?)
    ↓                   ↓
   sim                 não
    ↓                   ↓
[host.update]      [host.create]
  - tags             - SNMP iface
  - macros           - groups (POP+Role+Tenant)
  - templates        - templates resolvidos
                     - macros padrão
                     - tags
    ↓
[Audit write]
    ↓
[Notify NOC] (Evolution API, só se criação ou erro)
```

---

## 10. Itens novos detalhados

### 10.1 Idempotência e dry-run

**Regra:** todo worker N8N que escreve em sistema externo (Zabbix, Grafana, equipamento) tem de respeitar:

1. **Read before write.** Sempre `get` antes de `create/update`. Compare estado atual vs. desejado.
2. **Estado desejado é declarativo.** Vem do NetBox + Git. Não derivar de "estado atual".
3. **Dry-run mode.** Variável de ambiente `DRY_RUN=true` faz worker logar o que faria, sem aplicar.
4. **Re-run safety.** Rodar `wf-reconcile` 5x seguidas dá o mesmo resultado.

Implementação prática em N8N:
- Cada sub-workflow recebe `{ dry_run: bool }` no input.
- Antes de `host.create`, checar `host.get`.
- Antes de `host.update`, computar diff: se vazio, skip.
- Logar `action_taken` no audit (`created|updated|noop|skipped|error`).

### 10.2 Reconciliação e drift detection

**`wf-reconcile`** (cron 30 min):
```
1. Lê todos devices NetBox com monitoring_enabled=true.
2. Lê todos hosts Zabbix.
3. Computa 4 conjuntos:
   - in_netbox AND in_zabbix         → verifica drift (templates, tags, groups)
   - in_netbox NOT in_zabbix         → falta provisionar (auto-corrige)
   - NOT in_netbox AND in_zabbix     → host órfão (alerta governança, NÃO deleta)
   - in_zabbix com tag.compliant=false → audita
4. Grava relatório em Postgres tabela `drift_report`.
5. Aplica correções automáticas para casos seguros (provisionar faltantes).
6. Hosts órfãos viram ticket no Movidesk para revisão humana.
```

**Política:** o sync **nunca deleta** automaticamente. Só desabilita ou alerta. Deleção é decisão humana.

### 10.3 CI/CD de templates e dashboards

`k3g-monitoring-iac` é monorepo Git com pipeline GitHub Actions (ou Gitlab CI):

```yaml
# .github/workflows/ci.yml (simplificado)
on: [pull_request, push]
jobs:
  lint:
    - validate YAML schemas (templates, role_template_map, tag_taxonomy)
    - validate JSON Grafana dashboards (jsonschema)
    - validate naming convention regex em arquivos de exemplo
    - lint Python sync workers (ruff + mypy)

  staging:
    needs: lint
    if: pull_request
    - import templates Zabbix em ambiente staging via API
    - import dashboards Grafana em folder /staging
    - rodar smoke tests (criar host fake, ver se templates linkam)
    - rodar wf-reconcile em --dry-run
    - postar resultado no PR

  prod:
    needs: staging
    if: push to main
    - aplicar em produção (com aprovação manual no GitHub)
    - tag git release vYYYY.MM.DD-N
    - notificar NOC via Evolution API
```

Rollback = `git revert` + re-run pipeline. Sem cliques manuais em produção.

### 10.4 Auditoria e governança

Tabela Postgres `monitoring_audit_log`:
```sql
CREATE TABLE monitoring_audit_log (
  id BIGSERIAL PRIMARY KEY,
  ts TIMESTAMPTZ DEFAULT NOW(),
  workflow VARCHAR(64) NOT NULL,
  action VARCHAR(32) NOT NULL,        -- created|updated|noop|skipped|error
  object_type VARCHAR(32) NOT NULL,   -- device|circuit|interface|tenant|host
  netbox_id INT,
  zabbix_hostid BIGINT,
  diff JSONB,
  error_msg TEXT,
  dry_run BOOLEAN DEFAULT FALSE,
  trigger_source VARCHAR(32)          -- webhook|cron|manual
);
CREATE INDEX ON monitoring_audit_log (ts DESC);
CREATE INDEX ON monitoring_audit_log (object_type, netbox_id);
```

Relatórios diários (e-mail / Grafana):
- `compliance_report.daily`: % interfaces compliant, hosts órfãos, dashboards mortas.
- `drift_report.daily`: divergências NetBox ↔ Zabbix.
- `coverage_report.daily`: % devices NetBox com `monitoring_enabled=true` que estão em Zabbix.

KPI: **MTBF (mean time between drifts)** > 30 dias. Se cair, processo está furando.

### 10.5 Brownfield migration

Cenário: K3G ou cliente já tem 200 interfaces de cliente com descrição livre (`Cliente XYZ - 100M`, `Empresa ABC G1/0/1`, etc.).

**Fase de backfill assistido:**

1. **Linter Python** (`scripts/lint_descriptions.py`):
   - Conecta via SSH (ou usa backups Rancid/Oxidized) em todos devices.
   - Extrai todas descrições de interface.
   - Aplica heurística de fuzzy match (descrição ↔ tenant name em NetBox via `rapidfuzz`).
   - Gera CSV `proposed_descriptions.csv` com colunas: `device, interface, current_desc, proposed_desc, confidence, action_needed`.

2. **Revisão humana** (operador NOC):
   - Abre CSV em planilha.
   - Marca `approved=true` ou ajusta.

3. **Apply assistido** (`scripts/apply_descriptions.py --dry-run` primeiro):
   - Aplica via SSH (Netmiko/NAPALM) só as `approved=true`.
   - Logs em audit.

4. **Validation**: `wf-reconcile` confirma que LLD descobriu corretamente.

Sem isso, o sistema "novo" começa com `compliant=false` em 80% dos itens — vira ruído.

### 10.6 SLA / Criticality enforcement (criticality_profile.yaml)

```yaml
criticality_profiles:
  platinum:
    poll_interval: 30s
    trigger_severity: disaster
    sla_target_pct: 99.99
    alert_channels:
      - whatsapp_noc_senior
      - phone_call
      - email_engineering
    escalation_minutes: [0, 5, 15]
    maintenance_blackout: false   # alertas mesmo em janela
  gold:
    poll_interval: 60s
    trigger_severity: high
    sla_target_pct: 99.95
    alert_channels:
      - whatsapp_noc
      - email_noc
    escalation_minutes: [0, 15, 60]
  silver:
    poll_interval: 120s
    trigger_severity: average
    sla_target_pct: 99.5
    alert_channels:
      - whatsapp_noc_group
    escalation_minutes: [0, 60]
  bronze:
    poll_interval: 300s
    trigger_severity: warning
    sla_target_pct: 99.0
    alert_channels:
      - email_noc_batch
    escalation_minutes: []
```

Worker traduz isso em macros Zabbix por host (`{$ALERT.PROFILE}`, `{$POLL.INTERVAL}`) e em ações Zabbix (escalation steps por severidade).

### 10.7 Observabilidade da observabilidade

A plataforma **monitora a si mesma**. Dashboard `platform/observability-self.json`:

| Painel | Métrica | Alerta |
|--------|---------|--------|
| Webhook health | `webhooks_received_total{status}` por minuto | sem evento em 1h → alerta |
| N8N workflow success rate | `wf-onboard-device success ratio` (5min) | < 95% → alerta |
| Reconcile drift | `drift_count` última execução | > 10 → ticket auto |
| Sync worker heartbeat | item `sync.heartbeat` no Zabbix | sem ping em 2 min → disaster |
| NetBox API latency p95 | medido no sync worker | > 2s → warning |
| Compliance % | `interfaces_compliant / total` | < 90% → ticket |
| Hosts órfãos | count(in_zabbix not in_netbox) | > 0 → governança |
| DLQ depth | `dlq_messages_total` | > 0 por > 30 min → high |

Heartbeat: cron N8N a cada 60s POST em endpoint dummy → Zabbix HTTP agent → trigger se ausência > 2 min.

### 10.8 DR e backup

- **NetBox HA**: 2 nós ativos atrás de HAProxy/Nginx, Postgres com replicação streaming.
- **Backup diário**: `pg_dump` NetBox + Zabbix + Grafana, com retenção 30 dias local + 90 dias offsite (B2/S3 compatible).
- **Runbook de restore**: documentado e testado **trimestralmente**.
- **Cache local Redis**: sync worker cacheia respostas NetBox por 1h. Se NetBox cai, opera por mais 1h em modo somente-leitura.
- **Filas Redis**: webhooks NetBox enfileiram em Redis antes de processar. Se N8N cai, eventos não são perdidos.

### 10.9 Multi-tenancy / RBAC

K3G opera para múltiplos ISPs (modelo MSP). Estrutura:

- **NetBox**: usar `tenant_group` para separar ISP-cliente (cada ISP é um grupo). Permissões por grupo.
- **Zabbix**: host groups hierárquicos `/MSP/<isp>/Customers/<tenant>`. Usuários do ISP-cliente só veem seu prefixo.
- **Grafana**: organizations por ISP, ou folders por ISP com permissões.
- **Sync**: contextualizado por `tenant_group` para evitar vazar dados entre ISPs gerenciados.

---

## 11. Plano de ação revisado (6 fases, ~10 semanas)

### Fase 0 — Discovery e Baseline (1 sem)
- Inventário Zabbix atual (export CSV); marcar tagging existente.
- Inventário Grafana (dashboards vivas vs. mortas).
- Mapear roles atuais de equipamentos.
- Validar versões: NetBox ≥ 4.x, Zabbix ≥ 6.4 LTS, Grafana ≥ 10.x.
- **Aprovar com engenharia + comercial:** taxonomia de tags, naming convention, lista de service_types e criticality.
- **Entrega:** `01-baseline.md`, `02-gaps.md`, decisões aprovadas em ata.

### Fase 1 — NetBox como SoT (2 sem)
- Criar custom fields via Terraform/API.
- Importar tenants (clientes + operadoras) — script Python lendo CRM/IXC.
- Backfill de devices: role, vendor, model, criticality.
- Backfill de circuitos: service_type, criticality.
- **Linter de descrição** (Fase brownfield) — gerar CSV de propostas.
- Configurar webhooks NetBox apontando para endpoint N8N de teste.
- **Entrega:** NetBox 100% preenchido, webhook entregando payloads válidos.

### Fase 2 — Templates Zabbix (3 sem)
- Criar repo Git `k3g-monitoring-iac` (sub-pasta `zabbix/`).
- Refatorar templates existentes Huawei/Juniper/Datacom em modelo atômico (vendor + role + service).
- Implementar LLD JS preprocessing.
- Criar `T_GOV_NAMING_COMPLIANCE`, `T_GOV_HEARTBEAT_AGENT`.
- CI: lint, import staging, smoke test.
- **Entrega:** biblioteca de templates + `role_template_map.yaml`.

### Fase 3 — N8N Orchestrator (2 sem)
- Workflows da seção 9.1.
- Idempotência implementada.
- Audit log Postgres.
- DLQ + retry queue Redis.
- HMAC nas webhooks.
- **Entrega:** workflows em produção, taxa de sucesso ≥ 95%.

### Fase 4 — Grafana data-driven (2 sem)
- Configurar provisioning filesystem (Git-backed).
- Criar dashboards-template (customer-overview, circuit-detail, carrier-uplink-health, pop-health, noc-overview, observability-self).
- Definir variáveis derivadas de tags Zabbix.
- Migrar permissões: folder por tenant, dashboard compartilhada.
- **Marcar dashboards antigas como `[LEGACY]`**, retirar em 30 dias.
- **Entrega:** clientes acessam URL padronizada `/d/customer-overview?var-tenant=<slug>`.

### Fase 5 — CI/CD, governança e auditoria (1 sem)
- Pipeline GitHub Actions com staging+prod.
- `wf-reconcile` em produção com auto-correção segura.
- `wf-compliance-report` rodando diariamente.
- Dashboard `observability-self`.
- Runbook DR documentado e testado.
- **Entrega:** plataforma autossustentável, junior team consegue operar.

### Fase 6 (opcional, futura) — Equipment config push
- A partir do NetBox, gerar config via Jinja2 e aplicar via NAPALM/Netmiko.
- Sai do escopo desta plataforma de observabilidade — projeto separado.

---

## 12. Critérios de aceite (mensuráveis)

A plataforma só é considerada "produção" quando:

| # | Critério | Métrica | Meta |
|---|----------|---------|------|
| 1 | Cadastro novo cliente é one-click | Tempo SoT-cadastro → Zabbix-monitorando | ≤ 60s |
| 2 | LLD funciona em todos os service_types | Coverage por service_type | ≥ 99% |
| 3 | Tags aplicadas corretamente | `compliant=true` ratio | ≥ 95% |
| 4 | Dashboards Grafana = zero manuais | Dashboards no folder `/Customers/*` criadas manualmente | 0 |
| 5 | Drift NetBox ↔ Zabbix | Drift por dia | ≤ 5, todos justificados |
| 6 | Hosts órfãos | Count | 0 (sem aprovação) |
| 7 | Pipeline self-monitored | Cobertura `observability-self` | 100% dos componentes |
| 8 | DR | Tempo de restore NetBox | ≤ 30 min, testado trimestralmente |
| 9 | Dry-run | Workers em prod sem flag | 0 |
| 10 | Operação por junior | Tickets de "como faço?" sobre cadastro | ≤ 1/semana após 30d |

---

## 13. Riscos e mitigações

| Risco | Sev. | Mitigação |
|-------|------|-----------|
| NetBox vira SPOF | Alta | HA + backup + cache Redis 1h + DLQ Redis |
| Equipe junior cadastra fora do padrão | Alta | Custom fields obrigatórios + webhook valida + linter CI + treinamento |
| Drift por mudança manual em Zabbix | Média | `wf-reconcile` 30 min + alerta governança |
| Templates Zabbix evoluem e quebram hosts | Alta | Versionamento Git + staging + deploy por host group |
| Tag explosion (cardinalidade) | Baixa | Taxonomia fechada + CI valida |
| Webhook perdido | Média | Redis queue + reconcile como backup |
| Vendor SNMP MIB inconsistente | Média | LLD por vendor; itens base validados em lab |
| ifAlias > 64 bytes em vendor antigo | Baixa | Slug curto cabe; alertar se overflow |

---

## 14. Anexos

### A. Estrutura completa do monorepo `k3g-monitoring-iac`

```
k3g-monitoring-iac/
├── README.md
├── docs/
│   ├── 00-overview.md
│   ├── 01-baseline.md
│   ├── 02-naming-convention.md
│   ├── 03-tag-taxonomy.md
│   ├── 04-criticality-profiles.md
│   ├── 05-onboarding-runbook.md
│   ├── 06-decommission-runbook.md
│   ├── 07-dr-runbook.md
│   ├── 08-troubleshooting.md
│   └── adr/
│       ├── 0001-netbox-as-single-sot.md
│       ├── 0002-naming-machine-parseable.md
│       └── 0003-event-driven-with-reconcile.md
├── netbox/
│   ├── custom-fields/
│   │   ├── service_type.yaml
│   │   ├── criticality.yaml
│   │   ├── sla_target.yaml
│   │   └── monitoring_enabled.yaml
│   ├── tenant-groups.yaml
│   ├── webhooks.yaml
│   └── terraform/
│       ├── main.tf
│       └── variables.tf
├── zabbix/
│   ├── templates/
│   │   ├── vendor/
│   │   │   ├── T_HUAWEI_NE8000_BASE.yaml
│   │   │   ├── T_HUAWEI_S6730_BASE.yaml
│   │   │   ├── T_JUNIPER_MX_BASE.yaml
│   │   │   ├── T_MIKROTIK_ROS_BASE.yaml
│   │   │   └── T_DATACOM_DMOS_BASE.yaml
│   │   ├── role/
│   │   │   ├── T_ROLE_PE.yaml
│   │   │   ├── T_ROLE_P.yaml
│   │   │   ├── T_ROLE_RR.yaml
│   │   │   ├── T_ROLE_OLT.yaml
│   │   │   └── T_ROLE_SW_ACCESS.yaml
│   │   ├── service/
│   │   │   ├── T_SVC_BGP_PEERING.yaml
│   │   │   ├── T_SVC_L2VPN_VPWS.yaml
│   │   │   ├── T_SVC_L3VPN_VRF.yaml
│   │   │   ├── T_SVC_INTERFACE_CUSTOMER.yaml
│   │   │   └── T_SVC_INTERFACE_CARRIER.yaml
│   │   └── governance/
│   │       ├── T_GOV_NAMING_COMPLIANCE.yaml
│   │       └── T_GOV_HEARTBEAT_AGENT.yaml
│   ├── role_template_map.yaml
│   ├── tag_taxonomy.yaml
│   ├── criticality_profiles.yaml
│   └── macros_defaults.yaml
├── grafana/
│   ├── dashboards/
│   │   ├── customer/
│   │   ├── carrier/
│   │   ├── infra/
│   │   ├── noc/
│   │   └── platform/
│   ├── folders/
│   │   └── permissions.yaml
│   └── provisioning/
│       ├── dashboards.yaml
│       └── datasources.yaml
├── n8n/
│   └── workflows/
│       ├── wf-netbox-router.json
│       ├── wf-onboard-device.json
│       ├── wf-onboard-circuit.json
│       ├── wf-onboard-interface.json
│       ├── wf-onboard-tenant.json
│       ├── wf-update.json
│       ├── wf-decommission.json
│       ├── wf-reconcile.json
│       ├── wf-audit-write.json
│       ├── wf-error-handler.json
│       ├── wf-heartbeat.json
│       └── wf-compliance-report.json
├── scripts/
│   ├── lint_descriptions.py
│   ├── apply_descriptions.py
│   ├── backfill_netbox.py
│   ├── reconcile_dryrun.py
│   └── compliance_report.py
├── ci/
│   ├── lint_yaml.sh
│   ├── lint_grafana.py
│   ├── smoke_test_zabbix.py
│   └── smoke_test_n8n.py
├── tests/
│   ├── unit/
│   └── integration/
├── docker-compose.staging.yml
└── .github/workflows/
    ├── ci.yml
    └── deploy.yml
```

### B. `tag_taxonomy.yaml` (taxonomia fechada — fonte de verdade das tags)

```yaml
# Apenas estas chaves são permitidas em items/triggers Zabbix.
# CI rejeita templates que usem tag fora desta lista.
allowed_tags:
  environment:        [prod, staging, lab]
  tenant:             { type: slug, source: netbox.tenant.slug }
  service_type:       *service_type_choices
  criticality:        [platinum, gold, silver, bronze]
  pop:                { type: slug, source: netbox.site.slug }
  device_role:        [pe, p, rr, olt, sw-access, sw-core, cgnat, bng, mgmt]
  vendor:             [huawei, juniper, mikrotik, cisco, datacom, raisecom, zte]
  netbox_id:          { type: integer }
  circuit_id:         { type: string, max_length: 32 }
  alert_class:        [service, infra, governance, security]
  owner:              [noc, engineering, backbone, corporativo]
  compliant:          [true, false]
  vc_id:              { type: integer }
  asn_remote:         { type: integer }
  address_family:     [ipv4, ipv6]
```

### C. ADR-0001: NetBox como única SoT (anchor decision)

```markdown
# ADR-0001: NetBox como única Source of Truth para inventário de rede

## Status
Aceito — 2026-01-15

## Contexto
A K3G tem múltiplos sistemas com dados de inventário: NetBox (técnico), 
IXC/ERP (comercial), planilhas, descrições livres em equipamentos. 
Cada um é "fonte da verdade" para alguém. Resultado: divergência crônica.

## Decisão
NetBox é a única SoT para inventário de rede. IXC/ERP permanecem como 
fontes comerciais e alimentam NetBox via integração. Configurações 
de equipamento e Zabbix/Grafana são projeções de NetBox.

## Consequências
- Positivas: ponto único de verdade, auditável, com API.
- Negativas: NetBox vira SPOF (mitigado por HA + backup); equipe precisa 
  ser disciplinada para sempre cadastrar primeiro lá.
- Custo: tempo de backfill brownfield (~2 semanas).

## Alternativas consideradas
- Nautobot: similar, sem ganho relevante; troca de stack custosa.
- YAML/Git: mais simples, mas perde UI para operadores não-dev.
- Multi-SoT: anti-pattern conhecido.
```

---

## 15. O que **não** fazer (anti-padrões a evitar)

1. **Criar dashboard nova por cliente.** Já dito — vira lixo.
2. **Confiar em descrição livre como discovery.** Use slug + NetBox.
3. **Permitir cadastro direto em Zabbix sem passar por NetBox.** Exceto staging.
4. **Misturar concerns:** SoT decidindo template Zabbix.
5. **Sync sem dry-run.** Em staging, sempre dry-run primeiro.
6. **Polling sem webhook.** Webhook é primário.
7. **Tag livre.** Taxonomia fechada.
8. **Templates "mega".** Quebrar em vendor + role + service.
9. **Editar templates direto no Zabbix UI.** Mexer no Git, deixar CI aplicar.
10. **Apagar host quando sai cliente.** Desabilitar e mover para `/Decommissioned`.

---

## 16. Pergunta para você (decisão de escopo)

O documento original tinha um prompt para "criar a automação com Codex/Claude" gerando um `observability-sync` em FastAPI. **Isso compete com N8N** que você já roda. Recomendo:

- **Mantê-lo em N8N** (consistente com a stack K3G, junior team).
- **Scripts Python (`scripts/`)** apenas para tarefas que não são webhook-driven: backfill, linter, reconcile complexo, relatórios.
- **Não construir um serviço FastAPI separado** — duplica responsabilidade.

Confirma essa direção, ou prefere evoluir para um daemon FastAPI dedicado em vez de workflows N8N? A escolha muda o esforço da Fase 3 e o perfil de manutenção.
