# ADR 0001 — NetBox como single source of truth técnico

## Status
Aceito — Fase 0

## Contexto
O projeto precisa de uma fonte única e confiável para todos os dados técnicos dos ativos do ISP.

## Decisão
Adoção do NetBox como SoT técnico para dispositivos, circuitos, interfaces, tenants e metadados relevantes.

## Consequências
- Todas as automações leem dados do NetBox.
- Custom fields, naming e tags devem estar alinhados.
- Alterações sem passar pelo NetBox são consideradas exceção e geram drift.

## Referências
- `docs/06-netbox-sot.md`
- `netops_netbox_sync` para auditoria.