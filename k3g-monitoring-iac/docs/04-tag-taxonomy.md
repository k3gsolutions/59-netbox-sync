# 04 — Tag Taxonomy

## Objetivo
Definir tags consistentes entre NetBox, Zabbix e Grafana.

## Estrutura base
- `environment`: `prod`, `staging`, `lab`
- `tenant`: slug derivado do NetBox
- `service_type`: baseado em custom field
- `criticality`: `platinum`, `gold`, `silver`, `bronze`
- `device_role`, `vendor`, `pop`, `alert_class`, `owner`
- Identificadores de suporte: `netbox_id`, `circuit_id`, `vc_id`, `asn_remote`
- `address_family`: `ipv4`, `ipv6`
- `compliant`: `true`, `false`

## Service types oficiais
- customer-internet
- customer-l2vpn
- customer-l3vpn
- customer-transport
- carrier-transit
- carrier-peering
- ix-public
- cdn-cache
- infra-backbone
- infra-management

## Matriz de service_type
| service_type | Descrição | Objeto NetBox | Requer BGP | Requer VRF | Requer VLAN/QinQ | Entra no LLD | Dashboard |
| --- | --- | --- | --- | --- | --- | --- | --- |
| customer-internet | Acesso IP de cliente final | circuit / interface | opcional | opcional | não | sim | customer |
| customer-l2vpn | Serviço L2VPN de cliente | l2vpn / circuit / interface | não | não | sim | sim | customer |
| customer-l3vpn | Serviço L3VPN de cliente | l2vpn / circuit / interface | sim | sim | opcional | sim | customer |
| customer-transport | Transporte de cliente entre PoPs | circuit / interface | opcional | opcional | opcional | sim | transport |
| carrier-transit | Trânsito para redes carrier | circuit / interface | sim | opcional | opcional | sim | infra |
| carrier-peering | Peering com outros carriers | circuit / interface | sim | não | opcional | sim | infra |
| ix-public | Interconexão pública com IX | circuit / interface | sim | não | sim | sim | infra |
| cdn-cache | Serviço CDN de cache | circuit / interface | não | opcional | opcional | sim | customer |
| infra-backbone | Backbone de rede interna | circuit / interface | sim | opcional | opcional | sim | infra |
| infra-management | Rede de gestão/infraestrutura | interface / device | não | não | opcional | sim | infra |

## Observações
- `service_type` deve ser preenchido sempre que `monitoring_enabled=true`.
- A taxonomia Zabbix deve refletir os campos do NetBox, mas não deve criar uma segunda fonte da verdade.
- Campos críticos de objetos monitoráveis devem ser mapeados no NetBox e expostos nas tags Zabbix.

## Ações próximas
- Validar lista com stakeholders.
- Garantir consistência entre YAMLs em `netbox/` e `zabbix/`.