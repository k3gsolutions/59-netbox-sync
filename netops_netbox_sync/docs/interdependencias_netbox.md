# Fluxograma de Interdependências — NetBox Sync

Mapa completo das dependências entre os objetos sincronizados, do início ao fim.
Para cada elemento: o que precisa existir antes, o que pode falhar e como corrigir.

---

## Índice

1. [Mapa Geral de Dependências](#1-mapa-geral-de-dependências)
2. [Ordem de Criação (do zero ao completo)](#2-ordem-de-criação-do-zero-ao-completo)
3. [Camada DCIM/IPAM — Detalhes por Elemento](#3-camada-dcimipam--detalhes-por-elemento)
4. [Camada BGP Plugin — Detalhes por Elemento](#4-camada-bgp-plugin--detalhes-por-elemento)
5. [Grafo de Dependências BGP (peer → objetos)](#5-grafo-de-dependências-bgp-peer--objetos)
6. [Checklist de Validação por Elemento](#6-checklist-de-validação-por-elemento)
7. [Cenários de Falha e Correção](#7-cenários-de-falha-e-correção)
8. [Fluxo de Verificação Pré-Sync](#8-fluxo-de-verificação-pré-sync)

---

## 1. Mapa Geral de Dependências

```
 Dispositivo no NetBox (dcim.device)
         │
         ├─── Tenant ─────────────────────────────────────────────────┐
         │    (resolvido do device.tenant)                            │
         │                                                            │
         │  ╔══════════ CAMADA DCIM/IPAM ══════════╗                  │
         │  ║                                      ║                  │
         │  ║  [1] VRF                             ║                  │
         │  ║       └── depende de: Tenant         ║                  │
         │  ║                                      ║                  │
         │  ║  [2] VLAN                            ║                  │
         │  ║       └── depende de: Tenant         ║                  │
         │  ║                                      ║                  │
         │  ║  [3] Interface                       ║                  │
         │  ║       └── depende de: Device         ║                  │
         │  ║            └── [3b] LAG member       ║                  │
         │  ║                 └── depende de:      ║                  │
         │  ║                     Interface pai    ║                  │
         │  ║                                      ║                  │
         │  ║  [4] IP Address                      ║                  │
         │  ║       └── depende de: Interface, VRF ║                  │
         │  ║                                      ║                  │
         │  ╚══════════════════════════════════════╝                  │
         │                                                            │
         │  ╔══════════ CAMADA BGP PLUGIN ══════════╗                 │
         │  ║                                       ║                 │
         │  ║  [0a] Tag do Tenant                   ║◄────────────────┘
         │  ║        └── depende de: Tenant         ║
         │  ║                                       ║
         │  ║  [0b] Community (valor X:Y)           ║
         │  ║        └── sem dependências           ║
         │  ║            tenant: Campo nativo       ║
         │  ║                                       ║
         │  ║  [0c] Community-list                  ║
         │  ║        └── sem dependências diretas   ║
         │  ║            tag: slug do tenant        ║
         │  ║                                       ║
         │  ║  [1] Prefix-list                      ║
         │  ║       └── sem dependências            ║
         │  ║           tag: slug do tenant         ║
         │  ║                                       ║
         │  ║  [2] AS-Path List                     ║
         │  ║       └── sem dependências            ║
         │  ║           tag: slug do tenant         ║
         │  ║                                       ║
         │  ║  [3] Routing Policy                   ║
         │  ║       └── sem dependências diretas    ║
         │  ║           tag: slug do tenant         ║
         │  ║                                       ║
         │  ║  [3b] Routing Policy Rule             ║
         │  ║        └── depende de:               ║
         │  ║            • Routing Policy (pai)     ║
         │  ║            • Prefix-list (IDs)        ║
         │  ║            • AS-Path List (IDs)       ║
         │  ║            • Community-list (IDs)     ║
         │  ║                                       ║
         │  ║  [4] ASN (local e remoto)             ║
         │  ║       └── sem dependências            ║
         │  ║                                       ║
         │  ║  [5] IP local / IP remoto             ║
         │  ║       └── depende de: VRF (opcional)  ║
         │  ║                                       ║
         │  ║  [6] BGP Session                      ║
         │  ║       └── depende de:                ║
         │  ║           • IP local (ID)             ║
         │  ║           • IP remoto (ID)            ║
         │  ║           • ASN local (ID)            ║
         │  ║           • ASN remoto (ID)           ║
         │  ║           tenant: Campo nativo        ║
         │  ║                                       ║
         │  ║  [6b] Link Session → Policies         ║
         │  ║        └── depende de:               ║
         │  ║            • BGP Session (ID)         ║
         │  ║            • Routing Policy (ID)      ║
         │  ║            (import + export)          ║
         │  ║                                       ║
         │  ╚═══════════════════════════════════════╝
```

---

## 2. Ordem de Criação (do zero ao completo)

A ordem abaixo é a única que garante que todas as FKs existam no momento do create/update:

```
Pré-requisito manual (fora da tool):
  ├─ Device deve existir no NetBox com nome e tenant corretos
  └─ Plugin netbox-bgp deve estar instalado e com migrations aplicadas

Passo 0  → Tag do tenant (extras/tags)
             ← necessária para marcar objetos sem campo tenant nativo

Passo 1  → VRF (ipam/vrfs)
             ← precisa existir antes dos IPs

Passo 2  → VLAN (ipam/vlans)
             ← independente, mas feita antes das interfaces por organização

Passo 3  → Interfaces — 1ª passagem (dcim/interfaces)
             ← precisa existir antes do LAG e antes dos IPs

Passo 4  → Interfaces — 2ª passagem: vincula LAG members
             ← Eth-Trunk deve existir desde o passo 3

Passo 5  → IP Addresses (ipam/ip-addresses)
             ← interface precisa existir (passo 3)
             ← VRF precisa existir (passo 1)

Passo 6  → Community valores X:Y (plugins/bgp/community)
             ← sem dependências de outros objetos BGP

Passo 7  → Community-lists (plugins/bgp/community-list)
             ← sem dependências de outros objetos BGP

Passo 8  → Prefix-lists + regras (plugins/bgp/prefix-list + prefix-list-rule)
             ← sem dependências de outros objetos BGP

Passo 9  → AS-Path Lists + regras (plugins/bgp/aspath-list + aspath-list-rule)
             ← sem dependências de outros objetos BGP

Passo 10 → Routing Policies + regras (plugins/bgp/routing-policy + routing-policy-rule)
             ← regras referenciam IDs dos objetos criados nos passos 7, 8 e 9
             ← policy pai deve ser criada antes de suas regras

Passo 11 → ASNs (ipam/asns)
             ← necessário antes das sessões BGP

Passo 12 → IPs de peering: local e remoto (ipam/ip-addresses)
             ← necessário antes das sessões BGP

Passo 13 → BGP Sessions (plugins/bgp/session)
             ← depende dos passos 11 e 12

Passo 14 → Link session → import/export policies
             ← depende dos passos 10 e 13
```

---

## 3. Camada DCIM/IPAM — Detalhes por Elemento

### 3.1 VRF (`ipam/vrfs`)

| Campo | Origem | Observação |
|-------|--------|------------|
| `name` | `display ip vpn-instance` — coluna VPN-Instance | Ex: `CDN`, `INFORR` |
| `rd` | `display ip vpn-instance` — coluna RD | Ex: `263934:85` |
| `tenant` | `device.tenant` (resolvido no início) | Aplicado automaticamente |

**Dependências de entrada:**
- Nenhuma (cria-se de forma independente)

**Dependências de saída (outros objetos que dependem de VRF):**
- IPs de peering BGP (VRF onde o IP local existe)
- IPs de interfaces (migrados para a VRF do tenant automaticamente)

**O que verificar antes do sync:**
```
□ Device tem tenant configurado no NetBox?
□ O nome da VPN-Instance no roteador bate com o tenant esperado?
□ O RD está preenchido corretamente no roteador?
```

**Problema comum:**
```
Situação: IPs criados na tabela global (sem VRF)
Causa:    Primeiro sync antes de o tenant estar associado ao device
Solução:  A tool detecta e migra automaticamente — basta rodar o sync
          com o tenant já configurado no device
```

---

### 3.2 VLAN (`ipam/vlans`)

| Campo | Origem | Observação |
|-------|--------|------------|
| `vid` | `display vlan` | ID numérico |
| `name` | `display vlan` | Ou `VLANxxx` se não tiver nome |
| `tenant` | `device.tenant` | Aplicado automaticamente |

**O que verificar:**
```
□ VLANs com mesmo VID em sites diferentes podem colidir no NetBox
  → O sync usa filter(vid=X) sem filtro de site — pode atualizar VLAN errada
□ VLANs sem nome no roteador recebem nome padrão "VLAN{vid}"
```

---

### 3.3 Interface (`dcim/interfaces`)

| Campo | Origem | Observação |
|-------|--------|------------|
| `name` | `display interface brief` | Nome exato do VRP |
| `type` | Inferido do nome | Ver tabela de tipos |
| `enabled` | `display interface brief` — admin status | `*down` → False |
| `description` | `display interface description` | String livre |
| `lag` | `running_config` — `eth-trunk N` | ID da interface pai |

**Tipos mapeados (ordem de prioridade):**

```
Nome contém:          → Tipo NetBox
─────────────────────────────────────────────
"Eth-Trunk" (sem .)   → lag
"100GE", "400GE"      → 100gbase-x-qsfp28
"40GE"                → 40gbase-x-qsfpp
"XGigabitEthernet"    → 10gbase-x-sfpp
"GigabitEthernet"     → 1000base-t
"LoopBack","Tunnel"   → virtual
"Vlanif","NULL"       → virtual
com "." (sub-iface)   → other
demais                → other
```

**O que verificar:**
```
□ Interface existe no NetBox com o nome exato do roteador?
  → Interface renomeada no roteador: o sync cria a nova, não apaga a velha
  → Apagar manualmente no NetBox a interface com nome antigo

□ LAG member aparece no sync mas sem o pai?
  → O pai (Eth-Trunk) precisa aparecer em "display interface brief"
  → Se sumiria do brief (ex: sem sub-interfaces configuradas), verificar
     se aparece no running_config com "interface Eth-TrunkN"

□ Tipo errado (ex: ficou "other" quando devia ser "lag")?
  → Verificar se o nome começa exatamente com "Eth-Trunk" (sem espaço/typo)
```

---

### 3.4 IP Address (`ipam/ip-addresses`)

| Campo | Origem | Observação |
|-------|--------|------------|
| `address` | `display ip interface brief` | Formato CIDR obrigatório |
| `status` | Fixo `"active"` | |
| `vrf` | VRF do tenant (resolvida no passo 1) | |
| `assigned_object_type` | Fixo `"dcim.interface"` | |
| `assigned_object_id` | ID da interface no NetBox | Precisa da 1ª passagem |

**O que verificar:**
```
□ IP já existe em outra VRF ou na tabela global?
  → A tool tenta migrar IPs da tabela global para a VRF do tenant
  → Se o IP estiver em VRF diferente (não global), não migra — verificar manualmente

□ Interface vinculada ao IP existe no NetBox?
  → Se a interface não foi criada (erro no passo 3), o IP é criado sem vínculo
  → Rodar o sync novamente após corrigir a interface

□ IP tem prefixo /32 ou /128 (loopback)?
  → Tratado normalmente — não há lógica especial para loopbacks

□ Mesmo IP em múltiplas interfaces (ex: VRRP/shared)?
  → A busca é por address — o segundo update apenas muda o assigned_object_id
  → Pode causar "vínculo pulando" entre interfaces — verificar manualmente
```

---

## 4. Camada BGP Plugin — Detalhes por Elemento

### 4.1 Community — valor individual (`plugins/bgp/community`)

| Campo | Origem | Observação |
|-------|--------|------------|
| `value` | `apply community X:Y` + `community X:Y` + `ip community-filter` | Formato `ASN:VALOR` |
| `status` | Fixo `"active"` | |
| `tenant` | `device.tenant` | Campo nativo suportado |

**Extraído de (3 fontes no running-config):**
```
apply community 263934:100 additive       → na route-policy
community 263934:200                      → em bgp/neighbor
ip community-filter basic NOME permit 64777:50101  → na definição do filtro
```

**O que verificar:**
```
□ Comunidade no formato correto "X:Y" (ambos numéricos)?
  → Valores como "no-export", "no-advertise" são ignorados (não são X:Y)
  → Regex: \b(\d+:\d+)\b — strings texto não são capturadas

□ Duplicatas entre devices de tenants diferentes?
  → A busca é por value — dois devices com mesma community podem colidir
  → O tenant é aplicado apenas se o objeto existente não tiver tenant

□ Comunidades do tipo "additive" são capturadas?
  → Sim — "additive" é texto após os valores e não interfere no parse
```

---

### 4.2 Community-list (`plugins/bgp/community-list`)

| Campo | Origem | Observação |
|-------|--------|------------|
| `name` | `ip community-filter basic/advanced NAME` | Nome exato do filtro |
| `tags` | slug do tenant | Campo nativo não suporta tenant direto |

**Regra da community-list (community-list-rule):**

| Campo | Origem |
|-------|--------|
| `index` | Número do `index N` no config |
| `action` | `permit` ou `deny` |
| `community` | Valor após permit/deny (pode ser regex se `advanced`) |

**Formatos suportados no running-config:**
```
# Formato 1 — nomeado com índice (formato real NE8000)
ip community-filter basic   NOME index 10 permit 64777:50101

# Formato 2 — numerado com índice
ip community-filter 1 index 10 permit 100:101

# Formato 3 — legado sem índice (backward-compat)
ip community-filter basic NOME permit 64777:50101
```

**O que verificar:**
```
□ Community-filter aparece no running-config com "index N"?
  → Parser suporta os três formatos acima — deve funcionar

□ Community-filter do tipo "advanced" usa regex?
  → A regra é armazenada com o padrão literal (ex: "64777:5210*")
  → O campo community_list no plugin aceita string livre

□ Community-filter referenciada na route-policy mas não definida?
  → Gera "broken ref" no grafo de dependências
  → Verificar se o nome na policy bate exatamente com o nome do filtro
  → Verificar no running-config se o filtro está definido
```

---

### 4.3 Prefix-list (`plugins/bgp/prefix-list`)

| Campo | Origem (display ip ip-prefix) | Observação |
|-------|-------------------------------|------------|
| `name` | `Prefix-list NAME` | |
| `family` | Inferido do prefixo (IPv4/IPv6) | |
| `tags` | slug do tenant | |

**Regra da prefix-list:**

| Campo | Origem |
|-------|--------|
| `index` | `index: N` |
| `action` | `permit` ou `deny` |
| `prefix` | Rede no formato CIDR |
| `ge` / `le` | Opcionais — comprimento mínimo/máximo |

**O que verificar:**
```
□ Prefix-list definida no "display ip ip-prefix" mas ausente no running-config?
  → São fontes diferentes: prefix-list vem do display, não do running-config
  → O parser de prefix-list lê APENAS o output de "display ip ip-prefix"

□ Prefix-list referenciada na route-policy mas sem entrada no display?
  → Gera "broken ref" — a prefix-list foi deletada do device mas a policy ainda a referencia
  → Verificar no roteador: display ip ip-prefix NAME

□ Prefix-list com ge/le não sincronizada corretamente?
  → Verificar formato: "138.219.0.0/16 greater-equal 24 less-equal 32"
  → O parser busca "ge X le Y" no campo options após o prefixo
```

---

### 4.4 AS-Path List (`plugins/bgp/aspath-list`)

| Campo | Origem (display ip as-path-filter) | Observação |
|-------|------------------------------------|------------|
| `name` | `As path filter name: NAME` | |
| `tags` | slug do tenant | |

**Regra:**

| Campo | Origem |
|-------|--------|
| `index` | Número da regra |
| `action` | `permit` ou `deny` |
| `pattern` | Regex do AS-path (ex: `^264409_`) |

**O que verificar:**
```
□ As-path-filter referenciado na policy mas ausente no display?
  → Verificar: display ip as-path-filter NAME
  → Gera "broken ref" no grafo

□ O plugin netbox-bgp suporta as-path-list?
  → Depende da versão — verificar se /api/plugins/bgp/aspath-list/ responde 200
  → A tool verifica automaticamente (self.has_aspath) e coloca no match_custom se não suportado
```

---

### 4.5 Routing Policy (`plugins/bgp/routing-policy`)

| Campo | Origem (running-config) | Observação |
|-------|-------------------------|------------|
| `name` | `route-policy NAME permit node N` | |
| `tags` | slug do tenant | |

**Regra (routing-policy-rule):**

| Campo | Mapeamento |
|-------|------------|
| `index` | Número do `node N` |
| `action` | `permit` ou `deny` |
| `match_ip_address` | IDs das prefix-lists (se `if-match ip-prefix`) |
| `match_ipv6_address` | IDs das prefix-lists IPv6 |
| `match_aspath_list` | IDs dos as-path-lists (se `if-match as-path-filter`) |
| `match_community_list` | IDs das community-lists (se `if-match community-filter`) |
| `match_custom` | Cláusulas sem mapeamento direto para campos do plugin |
| `set_actions` | Dict `{"actions": [...]}` com cláusulas `apply` |

**Prioridade de fonte:**
```
1ª opção: running-config (display current-configuration)
           → captura apply community, local-preference, med com mais fidelidade
           → garante consistência com community-filters e prefix-lists
2ª opção: display route-policy
           → usado como fallback se running-config não trouxer policies
```

**O que verificar:**
```
□ Regra referencia prefix-list que não existe?
  → "broken ref" no grafo — verificar no roteador se a prefix-list existe
  → Ex: "if-match ip-prefix Meu-Bloco-24-1" mas display ip ip-prefix não lista essa PL

□ Regra referencia community-filter que não existe?
  → "broken ref" — filtro definido na policy mas não no config
  → Verificar: grep "ip community-filter NOME" no running-config

□ Policy está em uso (vinculada a alguma sessão)?
  → Verificar no grafo de dependências no Config Context do NetBox
  → Policies sem uso ficam em "unused_routing_policies"
  → Não causa erro, mas é sinal de "policy órfã" no roteador

□ Regras com "apply community" não aparecem no match_community_list?
  → "apply community" é ação (apply), não match — vai para set_actions, não para match_community_list
  → match_community_list vem de "if-match community-filter NOME"
```

---

### 4.6 BGP Session (`plugins/bgp/session`)

| Campo | Origem | Observação |
|-------|--------|------------|
| `name` | Gerado: `{EBGP\|IBGP}-{peer_ip}-{af}[/{vrf}]` | |
| `status` | `active` se Established, senão `offline` | |
| `local_address` | ID do IP local (ipam) | Criado no passo 12 se não existir |
| `remote_address` | ID do IP remoto (ipam) | Criado no passo 12 se não existir |
| `local_as` | ID do ASN local (ipam) | Criado no passo 11 |
| `remote_as` | ID do ASN remoto (ipam) | Criado no passo 11 |
| `device` | ID do device no NetBox | |
| `tenant` | ID do tenant | Campo nativo suportado |
| `description` | Campo description do peer no VRP | |

**Vinculação de policies (passo 14):**
```
session.import_policies = [ID da routing-policy de import]
session.export_policies = [ID da routing-policy de export]
```

**O que verificar:**
```
□ Sessão aparece com status "offline" mesmo estando Established?
  → O parser lê o campo "BGP State" do display verbose
  → Verificar se o display retorna "Established" ou outro valor

□ IP local não encontrado no NetBox?
  → O sync cria o IP automaticamente se não existir
  → Após criar, associa como /32 (host route) sem interface

□ Sessão existe mas sem import/export policy?
  → A policy foi renomeada no roteador e o nome antigo estava no NetBox
  → Rodar o sync novamente — link_session_policies re-vincula pelas políticas do inventário atual

□ Sessão VPNv4 ou VPNv6 não foi criada?
  → Verificar se "display bgp vpnv4 vpn-instance VRF peer verbose" retorna dados
  → O nome da sessão inclui a VRF: "EBGP-192.168.1.1-vpnv4/CDN"

□ Duas sessões com mesmo peer_ip mas AFs diferentes?
  → Cada AF gera uma sessão separada — o nome inclui o AF
  → Ambas devem aparecer no NetBox

□ Sessão com peer_ip em VRF diferente colidindo com global?
  → O nome inclui @vrf — ex: "10.0.0.1@CDN" vs "10.0.0.1" (global)
  → No NetBox as sessões são distinguidas pelo IP (que tem VRF diferente)
```

---

## 5. Grafo de Dependências BGP (peer → objetos)

Este grafo é gerado automaticamente a cada sync e salvo no **Config Context** do device no NetBox (nome: `bgp-routing-{hostname}`).

### Estrutura do Config Context

```json
{
  "summary": {
    "local_as": 263934,
    "total_peers": 57,
    "total_policies": 139,
    "total_pl": 97,
    "total_aspath": 36,
    "total_communities": 224,
    "validation": {
      "total_issues": 1,
      "broken_refs": [
        {
          "policy": "AS26162.IX.RR-Export-IPv4",
          "type": "prefix-list",
          "ref": "Meu-Bloco-24-1",
          "node": 10,
          "clause": "ip-prefix Meu-Bloco-24-1"
        }
      ],
      "unused_prefix_lists": [],
      "unused_aspath_filters": [],
      "unused_community_filters": ["FILTRO-LEGADO-X"],
      "unused_routing_policies": ["OLD-POLICY-CDN"]
    }
  },
  "dependency_graph": {
    "peers": {
      "10.47.113.1": {
        "peer_as": 264409,
        "peer_type": "EBGP",
        "state": "Established",
        "address_family": "ipv4",
        "description": "AS264409-HUGE.264409",
        "import_chain": {
          "policy": "AS264409-HUGE-Import-v4",
          "policy_exists": true,
          "nodes": 3,
          "uses_prefix_lists": ["Meu-Bloco-24-1"],
          "uses_aspath_filters": ["AS264409-HUGE"],
          "uses_community_filters": [],
          "sets_communities": ["263934:100"],
          "sets_local_pref": [200],
          "sets_med": [],
          "broken_refs": []
        },
        "export_chain": {
          "policy": "AS264409-HUGE-Export-v4",
          "policy_exists": true,
          "nodes": 2,
          "uses_prefix_lists": ["Meu-Bloco-24-1", "AS269534-VIANET-V4"],
          "broken_refs": []
        }
      }
    },
    "policies": {
      "AS264409-HUGE-Import-v4": {
        "nodes": 3,
        "uses_prefix_lists": ["Meu-Bloco-24-1"],
        "uses_aspath_filters": ["AS264409-HUGE"],
        "sets_local_pref": [200],
        "broken_refs": []
      }
    }
  }
}
```

### Como ler o grafo

```
peer_ip  →  import_chain.policy  →  uses_prefix_lists  →  prefix-lists no NetBox
                                 →  uses_aspath_filters →  as-path-lists no NetBox
                                 →  uses_community_filters → community-lists no NetBox
                                 →  sets_communities    →  communities criadas
                                 →  broken_refs         →  ATENÇÃO: referências quebradas

         →  export_chain.policy  →  (mesma estrutura)
```

### Como acessar via API

```bash
# Busca o Config Context do device
GET /api/extras/config-contexts/?name=bgp-routing-INFORR-BVA-JCL-RX

# Ou no contexto renderizado do device
GET /api/dcim/devices/2647/?include=config_context
```

---

## 6. Checklist de Validação por Elemento

### Antes do sync (pré-requisitos)

```
DISPOSITIVO NO NETBOX
  □ Device existe com nome correto?
  □ Device tem tenant configurado?
  □ Plugin netbox-bgp está instalado? (GET /api/plugins/bgp/session/ → 200)

CREDENCIAIS
  □ Usuário SSH tem permissão de leitura (display commands)?
  □ Conta não está bloqueada por tentativas anteriores?
  □ Porta SSH correta (ex: 50022)?
```

### Durante o sync — o que monitorar

```
DCIM/IPAM
  □ [VRF]  "VRF do tenant encontrada" ou "criada"?
  □ [VRF]  Migração de IPs globais executada?
  □ [IPs]  Todos os IPs vinculados à interface correta?
  □ [LAG]  Membros do Eth-Trunk estão com lag preenchido?

BGP PLUGIN
  □ [0/6]  Comunidades criadas/atualizadas (contagem)
  □ [0b/6] Community-lists criadas (contagem)
  □ [1/6]  Prefix-lists criadas/atualizadas (contagem)
  □ [2/6]  AS-path lists criadas/atualizadas (contagem)
  □ [3/6]  Routing policies criadas/atualizadas (contagem)
  □ [4/6]  ASNs criados (contagem)
  □ [5/6]  BGP sessions criadas/atualizadas (contagem)

VALIDAÇÃO FINAL
  □ [grafo] total_issues = 0 (referências quebradas)
  □ [grafo] unused_prefix_lists = [] (sem prefix-lists órfãs)
  □ [grafo] unused_aspath_filters = [] (sem as-path-filters órfãs)
  □ [grafo] broken_refs = [] (sem referências quebradas)
```

### Após o sync — verificação no NetBox

```bash
# 1. Verificar sessões BGP
GET /api/plugins/bgp/session/?device_id=2647

# 2. Verificar routing policies com tag do tenant
GET /api/plugins/bgp/routing-policy/?tag=inforr

# 3. Verificar Config Context com o grafo
GET /api/extras/config-contexts/?name=bgp-routing-INFORR-BVA-JCL-RX

# 4. Verificar IPs na VRF correta (não na tabela global)
GET /api/ipam/ip-addresses/?vrf_id=107   # VRF do tenant

# 5. Contar broken refs (deve ser 0 ou apenas refs reais quebradas no roteador)
python3 -c "
import requests, json
r = requests.get('http://netbox:8080/api/extras/config-contexts/',
    headers={'Authorization': 'Token SEU_TOKEN'},
    params={'name': 'bgp-routing-INFORR-BVA-JCL-RX'})
ctx = r.json()['results'][0]['data']
print('Broken refs:', ctx['summary']['validation']['total_issues'])
for ref in ctx['summary']['validation']['broken_refs']:
    print(f\"  {ref['policy']} → {ref['type']}: {ref['ref']}\")
"
```

---

## 7. Cenários de Falha e Correção

### 7.1 Broken ref: policy referencia prefix-list não definida

```
Sintoma no grafo:
  broken_refs: [{"policy": "X-Export", "type": "prefix-list", "ref": "Meu-Bloco-24"}]

Diagnóstico:
  display ip ip-prefix Meu-Bloco-24
  → "Info: No ip ip-prefix was found."  ← a prefix-list não existe mais

Causa: policy desatualizada no roteador — referencia uma prefix-list deletada

Solução:
  1. No roteador: corrigir a route-policy removendo a referência
  2. Ou: recriar a prefix-list no roteador e rodar sync novamente
  3. O broken_ref desaparece automaticamente no próximo sync se corrigido
```

### 7.2 Community-list com 0 regras criadas

```
Sintoma:
  198 CommunityList created | 0 CommunityListRule created

Diagnóstico:
  Verificar o formato no running-config:
  grep "ip community-filter" running-config | head -5

Formatos com suporte:
  ip community-filter basic NOME index 10 permit X:Y   ← suportado
  ip community-filter NUMERO index 10 permit X:Y       ← suportado
  ip community-filter basic NOME permit X:Y            ← suportado (legado)

Formato sem suporte:
  ip community-filter basic NOME permit X:Y additive   ← "additive" após o valor
  → O valor capturado incluirá "additive" — verificar campo community na regra
```

### 7.3 BGP Session sem import/export policy vinculada

```
Sintoma:
  Sessão BGP existe no NetBox mas sem import/export policies

Diagnóstico:
  display bgp peer 10.x.x.x verbose | include Route-policy
  → Peer has no inbound/outbound route-policy

Causa A: peer realmente não tem policy configurada no roteador
Causa B: nome da policy no verbose difere do nome no running-config

Verificar:
  grep "peer 10.x.x.x route-policy" running-config
  → peer 10.x.x.x route-policy NOME-DA-POLICY import
```

### 7.4 IPs na tabela global em vez da VRF do tenant

```
Sintoma:
  GET /api/ipam/ip-addresses/?vrf_id=null&device_id=2647
  → retorna IPs que deveriam estar na VRF do tenant

Causa: sync rodou antes de o device ter tenant configurado no NetBox

Solução:
  1. Configurar o tenant no device no NetBox manualmente
  2. Rodar sync novamente — a tool detecta e migra automaticamente:
     "[VRF] 56 migrado(s)"
```

### 7.5 Interfaces com tipo "other" (incorreto)

```
Sintoma:
  Interface "100GE1/0/1" com type="other" no NetBox

Causa: prefixo da interface não reconhecido pelo parser

Verificar em parsers/interfaces.py: get_interface_type()
  Adicionar o prefixo se o mapeamento estiver faltando

Workaround:
  Corrigir o tipo manualmente no NetBox via PATCH:
  PATCH /api/dcim/interfaces/ID/ {"type": "100gbase-x-qsfp28"}
```

### 7.6 Erro 502 na API do NetBox durante sync

```
Sintoma:
  [3/6] Erro: 502 Bad Gateway

Causa: NetBox com carga alta ou reiniciando

Comportamento da tool:
  Retry automático com backoff exponencial (até 3 tentativas)
  Se persistir após 3 tentativas → lança exceção e aborta

Solução:
  Aguardar o NetBox se recuperar e rodar o sync novamente
  O sync é idempotente — safe para re-executar parcialmente
```

---

## 8. Fluxo de Verificação Pré-Sync

Sequência recomendada antes de rodar o sync pela primeira vez em um device:

```
PASSO 1 — Verificar Device no NetBox
  curl GET /api/dcim/devices/?name=INFORR-BVA-JCL-RX
  □ id existe?
  □ tenant preenchido?
  □ site correto?

PASSO 2 — Testar conectividade SSH
  ssh -p 50022 keslley@138.219.128.1
  display version
  □ Conecta sem erro?
  □ Output retorna versão do VRP?

PASSO 3 — Verificar Plugin no NetBox
  curl GET http://netbox/api/plugins/bgp/session/
  □ Retorna 200 (não 404)?
  □ Versão do plugin ≥ 0.13?

PASSO 4 — Coletar sem sincronizar (action=get)
  python -m app.tool '{"action":"get","device":{...}}'
  □ summary.bgp_sessions > 0?
  □ summary.route_policies > 0?
  □ summary.community_lists > 0?
  □ Nenhum erro de parsing no output?

PASSO 5 — Sincronizar (action=update)
  python -m app.tool '{"action":"update","device":{...},"netbox":{...}}'
  □ bgp_changelog.totals.created > 0 (primeira vez)?
  □ Nenhum erro crítico no stderr?
  □ validation.total_issues = 0 ou justificável?

PASSO 6 — Confirmar no NetBox
  □ Config Context "bgp-routing-HOSTNAME" foi criado?
  □ Sessões BGP aparecem em /api/plugins/bgp/session/?device_id=ID?
  □ IPs estão na VRF do tenant (não na tabela global)?
  □ Routing policies têm a tag do tenant?
```

---

*Atualizado em 2026-04-06 | netops_netbox_sync*
