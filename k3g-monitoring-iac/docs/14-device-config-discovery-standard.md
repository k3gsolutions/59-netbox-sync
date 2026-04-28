# 14 — Device Config Discovery Standard

## 1. Objetivo
Definir o padrão de busca, identificação, normalização e validação dos serviços aplicados em equipamentos de rede, começando por Huawei NE8000.

## 2. Escopo inicial
Incluir:
- interfaces físicas;
- Eth-Trunk;
- subinterfaces;
- VLAN dot1q;
- QinQ;
- VRF / vpn-instance;
- IP address;
- BGP peers;
- BGP por VRF;
- route-policies;
- prefix-lists;
- AS-path filters;
- community lists;
- VSI / L2VPN, se aplicável futuramente.

## 3. Fonte da verdade
NetBox é a fonte da verdade. A configuração aplicada que não existe no NetBox é considerada anomalia, e não a fonte primária.

## 4. Relação com netops_netbox_sync
O codebase `/Users/keslleykssantos/projects/ativos/59-netbox_sync/netops_netbox_sync` é responsável por:
- coletar o estado aplicado;
- parsear configuração Huawei NE8000;
- gerar DeviceInventory;
- gerar dependency graph;
- futuramente gerar compliance report;
- não é o orquestrador principal de monitoramento.

## 5. Naming convention oficial
Formato:
<service_type>:<tenant_slug>:NB-<id>[:extra]
Exemplos:
customer-internet:acme-corp:NB-1234
customer-l2vpn:beta-sa:NB-2017:vc-2017
carrier-transit:embratel:NB-9001
cdn-cache:google:NB-5500
infra-backbone:k3g:NB-3001:mao-pop1-mao-pop2

**Regex oficial:**
`^(customer-internet|customer-l2vpn|customer-l3vpn|customer-transport|carrier-transit|carrier-peering|ix-public|cdn-cache|infra-backbone|infra-management):[a-z0-9-]{2,32}:NB-[0-9]+(:[\w-]+)?$`

## 6. Campos extraídos do naming
Mapear:
- service_type
- tenant_slug
- netbox_id
- extra

## 7. Comandos Huawei NE8000 de discovery
Listar comandos:
- display current-configuration
- display interface description
- display interface brief
- display ip interface brief
- display vlan
- display ip vpn-instance
- display bgp all summary
- display bgp peer verbose
- display bgp ipv6 peer verbose
- display bgp vpnv4 vpn-instance <vrf> peer verbose
- display bgp vpnv6 vpn-instance <vrf> peer verbose
- display route-policy
- display ip ip-prefix
- display ip as-path-filter

## 8. Padrões de busca por bloco
### 8.1 Interface
Identificar blocos:
- interface <name>
- description <slug>
- ip binding vpn-instance <vrf>
- ip address <ip> <mask>
- vlan-type dot1q <vlan>
- qinq termination pe-vid <outer> ce-vid <inner>
- mtu <value>
- shutdown / undo shutdown
- statistic enable, se aplicável

### 8.2 VRF
Identificar:
- ip vpn-instance <name>
- route-distinguisher <rd>
- vpn-target <rt> export-extcommunity
- vpn-target <rt> import-extcommunity

### 8.3 VLAN
Identificar:
- vlan <id>
- description <description>

### 8.4 BGP
Identificar:
- bgp <local_asn>
- peer <ip> as-number <asn>
- peer <ip> description <description>
- peer <ip> connect-interface <interface>
- peer <ip> route-policy <policy> import
- peer <ip> route-policy <policy> export
- peer <ip> enable

Dentro de address-family:
- ipv4-family unicast
- ipv6-family unicast
- ipv4-family vpn-instance <vrf>
- ipv6-family vpn-instance <vrf>

### 8.5 Route-policy
Identificar:
- route-policy <name> permit node <id>
- route-policy <name> deny node <id>
- if-match ip-prefix <prefix-list>
- if-match ipv6 prefix-list <prefix-list>
- if-match as-path-filter <as-path>
- if-match community-filter <community-filter>
- apply community <community>
- apply extcommunity rt <rt>
- apply local-preference <value>
- apply med <value>
- apply as-path <value>

### 8.6 Prefix-list
Identificar:
- ip ip-prefix <name> index <idx> permit <prefix>
- ip ipv6-prefix <name> index <idx> permit <prefix>

### 8.7 AS-path filter
Identificar:
- ip as-path-filter <name> index <idx> permit <regex>

### 8.8 Community list/filter
Identificar:
- ip community-filter <id_or_name> permit <community>
- ip community-list <name> permit <community>

## 9. Dependências esperadas
Definir grafo:
- Interface → VRF → VLAN / QinQ → IP → Circuit/Service no NetBox → Tenant → BGP peer, se houver
- BGP Peer → VRF → remote ASN → address-family → import policy → export policy → prefix-list → as-path-filter → community-filter/list
- Route-policy → prefix-list → as-path-filter → community-list → extcommunity → route-target
- L2VPN/VSI → interface → vc-id → peer → tunnel / pw → tenant/service no NetBox

## 10. Tipos de divergência
Listar:
- MISSING_IN_NETBOX
- MISSING_ON_DEVICE
- DESCRIPTION_NON_COMPLIANT
- SERVICE_TYPE_MISMATCH
- TENANT_MISMATCH
- NETBOX_ID_MISMATCH
- VRF_MISMATCH
- VLAN_MISMATCH
- QINQ_MISMATCH
- IP_MISMATCH
- MTU_MISMATCH
- BGP_PEER_MISSING
- BGP_ASN_MISMATCH
- BGP_AF_MISMATCH
- ROUTE_POLICY_MISMATCH
- PREFIX_LIST_MISSING
- AS_PATH_FILTER_MISSING
- COMMUNITY_LIST_MISSING
- ORPHAN_DEVICE_CONFIG
- INSUFFICIENT_METADATA

## 11. Saída normalizada esperada
Definir modelos conceituais:
- AppliedService
- AppliedInterface
- AppliedVRF
- AppliedVLAN
- AppliedBGPPeer
- AppliedRoutePolicy
- AppliedPolicyDependency
- AppliedL2VPN

Registro deve armazenar os dados mínimos requeridos para cada tipo.

## 12. Relação com Zabbix LLD
Explicar:
- Zabbix descobre ifAlias.
- LLD JS preprocessing valida slug.
- Se slug válido, extrai service_type, tenant_slug, netbox_id, extra.
- Item prototype usa tags derivadas.
- Se slug inválido, compliant=false e gera alerta de governança.

## 13. Relação com Brownfield Migration
Explicar:
- redes existentes terão descrições livres;
- linter deve extrair interfaces e sugerir novo slug;
- humano aprova;
- aplicação futura deve ser assistida e com dry-run;
- nesta fase, não aplica configuração.

## 14. Relação com Compliance Engine
Este documento será usado para comparar:
- NetBoxInventory
versus
- DeviceInventory
E gerar divergências, severidade, evidência e recomendação.

## 15. Critérios de aceite do discovery
Exemplos:
- toda interface com service_type deve ter slug válido;
- todo NB-id deve existir no NetBox;
- todo peer BGP de cliente/operadora deve ter descrição ou vínculo rastreável;
- toda route-policy referenciada deve existir;
- todo prefix-list referenciado deve existir;
- todo serviço monitorável deve ter tenant, service_type e criticality no NetBox.
