# 16 — NetBox Readiness Checklist

## Objetivo
Definir os campos mínimos e critérios que garantem que um objeto NetBox está pronto para ser usado como base de monitoramento e comparação com o equipamento.

## Campos obrigatórios em Device
- `name` ou `hostname`
- `device_role`
- `site`
- `tenant` (quando aplicável)
- `serial`
- `platform`
- `status` (ativo ou em manutenção)
- `custom_fields.service_type`
- `custom_fields.criticality`
- `custom_fields.netbox_id`
- `custom_fields.monitoring_enabled`

## Campos obrigatórios em Interface
- `name`
- `device`
- `type`
- `description`
- `enabled`
- `mtu`
- `mac_address` ou `identifier`
- `untagged_vlan` / `tagged_vlans` quando aplicável
- `l2vpn` / `qinq` metadata se houver serviço L2
- `custom_fields.service_type`
- `custom_fields.tenant`
- `custom_fields.netbox_id`
- `custom_fields.monitoring_enabled`

## Campos obrigatórios em Circuit
- `cid`
- `provider`
- `status`
- `termination_a` / `termination_b`
- `tenant`
- `description`
- `type`
- `install_date` ou `commit_date` quando disponível
- `custom_fields.service_type`
- `custom_fields.criticality`

## Campos obrigatórios em VRF
- `name`
- `rd` (route distinguisher)
- `route_targets`
- `tenant`
- `description`
- `status`
- `custom_fields.service_type` quando VRF estiver associada a serviço de cliente

## Campos obrigatórios em BGP / plugin
- `local_asn`
- `peer_address`
- `remote_asn`
- `description`
- `status`
- `address_family`
- `route_policy_import`
- `route_policy_export`
- `vrf` ou `vpn_instance`
- `custom_fields.service_type`
- `custom_fields.tenant`
- `custom_fields.netbox_id`

## Campos recomendados
- `custom_fields.sla_target`
- `custom_fields.bandwidth_mbps`
- `custom_fields.escalation_profile`
- `custom_fields.circuit_id`
- `custom_fields.vc_id`
- `tags` alinhadas com service_type, tenant e criticality
- `description` com slug válido quando existir serviço associado
- `labels` ou `role` que facilitem filtrar por classe de serviço

## Campos bloqueantes
Campos que impedem a definição do objeto como pronto para monitoramento:
- Ausência de `custom_fields.service_type` em Device/Interface
- Ausência de `tenant` quando há serviço cliente ou transporte
- Ausência de `netbox_id` em objetos que devem ser rastreados pelo naming convention
- VRF sem `route_targets` quando usada em L3VPN/BGP
- BGP peer sem `remote_asn` ou `address_family`
- Interface de serviço sem `description` correta ou sem slug machine-parseable
- Circuit sem terminação ou sem tenant

## Campos opcionais
- `comments`
- `tags` adicionais não obrigatórias de governança
- `custom_fields.backup_window`
- `custom_fields.service_owner`
- `custom_fields.maintenance_window`
- `custom_fields.caixa_` (qualquer metadata local adicional não essencial)

## Critérios de prontidão para monitoramento
1. O objeto está completo?
   - Todos os campos obrigatórios e bloqueantes preenchidos.
   - Campos recomendados presentes sempre que houver serviço definido.
2. O objeto é rastreável?
   - Tem `service_type`, `tenant`, `netbox_id` e descrições coerentes.
3. O objeto é consistente?
   - Relacionamentos NetBox (Device → Interface → VRF → IP → Circuit) estão todos presentes e referenciáveis.
4. O objeto é auditável?
   - Há evidência em campo de que ele pertence a um serviço monitorável.
   - Se houver BGP, route-policy ou filtros, elas existem e são referenciadas.
5. O objeto não é bloqueado por falta de metadata crítica.
   - Qualquer gap bloqueante deve ser tratado como não pronto.

## Resultado esperado
- O readiness check deve fornecer um laudo binário de prontidão (`pronto` / `não pronto`) por objeto.
- Deve identificar os gaps bloqueantes e os campos recomendados ausentes.
- Deve permitir separar o inventário em: pronto para monitoramento, pronto com correções rápidas e não pronto.
