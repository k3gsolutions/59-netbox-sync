# 15 — Service Type Dependency Matrix

Este documento relaciona cada `service_type` com seus objetos NetBox esperados, campos obrigatórios, dados de equipamento e tags Zabbix.

## customer-internet
NetBox:
- Tenant
- Circuit
- CircuitTermination
- Interface
- IP Address
- ASN/BGP session, se BGP estiver configurado

Device:
- interface description com slug de serviço e tenant
- ip address no circuito/VRF correto
- vrf, se L3VPN
- bgp peer, se BGP
- route-policy import/export

Zabbix:
- `service_type=customer-internet`
- `tenant=<tenant_slug>`
- `netbox_id=<id>`
- `criticality=<profile>`
- `compliant=true/false`

Divergências típicas:
- DESCRIPTION_NON_COMPLIANT
- MISSING_IN_NETBOX
- BGP_PEER_MISSING
- IP_MISMATCH

## customer-l2vpn
NetBox:
- Tenant
- L2VPN
- Circuit
- Interface
- VC ID

Device:
- interface description com slug de serviço e tenant
- vc_id configurado
- vlan/qinq definido quando aplicável
- terminations consistentes com NetBox

Zabbix:
- `service_type=customer-l2vpn`
- `tenant=<tenant_slug>`
- `netbox_id=<id>`
- `vc_id=<vc_id>`
- `criticality=<profile>`

Divergências típicas:
- VC_ID_MISMATCH
- TERMINATION_MISSING
- CIRCUIT_LINK_MISSING

## customer-l3vpn
NetBox:
- Tenant
- L2VPN
- Circuit
- Interface
- VRF
- BGP session

Device:
- interface description com slug de serviço e tenant
- vrf configurado
- ip address em VRF correta
- bgp peer estabelecido
- route-policy import/export

Zabbix:
- `service_type=customer-l3vpn`
- `tenant=<tenant_slug>`
- `netbox_id=<id>`
- `criticality=<profile>`
- `address_family=<ipv4|ipv6>`

Divergências típicas:
- VRF_MISMATCH
- BGP_PEER_MISSING
- IP_PREFIX_MISMATCH

## customer-transport
NetBox:
- Tenant
- Circuit
- Interface
- IP Address ou interface de camada 2

Device:
- interface description com slug de transporte
- enlace de circuito correto
- vlan/qinq quando aplicável
- path de transporte end-to-end

Zabbix:
- `service_type=customer-transport`
- `tenant=<tenant_slug>`
- `netbox_id=<id>`
- `criticality=<profile>`

Divergências típicas:
- LINK_DOWN
- CIRCUIT_MISMATCH
- BANDWIDTH_INCORRECT

## carrier-transit
NetBox:
- Circuit
- Interface
- ASN/BGP session
- IP Address

Device:
- bgp peer para transit
- route-policy correta
- circuit terminations consistentes

Zabbix:
- `service_type=carrier-transit`
- `netbox_id=<id>`
- `criticality=<profile>`

Divergências típicas:
- BGP_PEER_MISSING
- ASN_MISMATCH
- ROUTE_POLICY_INCONSISTENT

## carrier-peering
NetBox:
- Circuit
- Interface
- ASN/BGP session
- IP Address

Device:
- bgp peering com par de peering
- interface description adequada
- vlan/qinq quando necessário

Zabbix:
- `service_type=carrier-peering`
- `netbox_id=<id>`
- `criticality=<profile>`

Divergências típicas:
- PEERING_MISSING
- BGP_NO_SESSION
- ASN_MISMATCH

## ix-public
NetBox:
- Circuit
- Interface
- VLAN / QinQ
- ASN/BGP session

Device:
- interface description com IX e tenant
- vlan/qinq configurado
- peer BGP com IX público

Zabbix:
- `service_type=ix-public`
- `netbox_id=<id>`
- `criticality=<profile>`

Divergências típicas:
- VLAN_MISMATCH
- BGP_PEER_MISSING
- IX_EXPECTED_BUT_MISSING

## cdn-cache
NetBox:
- Circuit
- Interface
- Tenant
- IP Address

Device:
- interface description com cache e tenant
- ip address consistente
- roteamento para cache

Zabbix:
- `service_type=cdn-cache`
- `netbox_id=<id>`
- `criticality=<profile>`

Divergências típicas:
- CACHE_IP_MISMATCH
- DESCRIPTION_INCONSISTENT

## infra-backbone
NetBox:
- Circuit
- Interface
- ASN/BGP session
- IP Address

Device:
- backbone interface description clara
- bgp peer com backbone
- route-policy alinhado ao design de malha

Zabbix:
- `service_type=infra-backbone`
- `netbox_id=<id>`
- `criticality=<profile>`

Divergências típicas:
- BACKBONE_LOOP
- BGP_PEER_MISSING
- IP_MISMATCH

## infra-management
NetBox:
- Interface
- Device
- Tenant (quando aplicável)

Device:
- management VLAN/interface configurada
- ip address para gestão
- description machine-parseable

Zabbix:
- `service_type=infra-management`
- `netbox_id=<id>`
- `criticality=<profile>`

Divergências típicas:
- MANAGEMENT_PATH_MISSING
- IP_MISMATCH
- DESCRIPTION_NON_COMPLIANT
