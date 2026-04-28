# 06 — NetBox como SoT

## Diretrizes
- NetBox contém dados técnicos verdadeiros.
- Custom fields obrigatórios e validados.
- Naming e descrições machine-parseable.
- Webhooks para N8N utilizam dados oficiais.

## Ações Fase 0
- Mapear estado atual do NetBox.
- Registrar custom fields necessários (`netbox/custom-fields/`).
- Definir service types, criticality e monitoring flag.

## Relação com netops_netbox_sync
Ferramenta dedicada para auditoria NetBox ⇄ dispositivo, garantindo aderência do SoT.

## Regras mínimas para monitoramento

### Device monitorável precisa ter
- `monitoring_enabled=true`
- `criticality`
- `role`
- `site`
- `platform/vendor`
- `primary_ip`

### Interface monitorável precisa ter
- `monitoring_enabled=true` ou herdado do circuito/device
- `service_type`
- `description` no padrão machine-parseable
- `tenant` ou vínculo via circuit
- `bandwidth_mbps` recomendado

### Circuit monitorável precisa ter
- `monitoring_enabled=true`
- `tenant`
- `service_type`
- `criticality`
- `bandwidth_mbps`
- terminations, quando aplicável

### L2VPN monitorável precisa ter
- `service_type`
- `vc_id`
- `tenant`
- `criticality`
- terminations
