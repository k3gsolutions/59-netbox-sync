# Fase 0.9 — Object Diff Read-Only

## Objetivo
Implementar comparação objeto-a-objeto entre inventário aplicado no dispositivo e inventário documentado no NetBox, mantendo a operação read-only.

## Escopo
Comparar apenas os seguintes objetos:
- Interfaces por `name`
- IPs por `address`
- VRFs por `name`
- VLANs por `vid`
- Sessões BGP por `remote_address` / `peer_ip` + `address_family`

## Limitações
- Não compara `route-policies` profundamente.
- Não compara `prefix-lists` linha a linha.
- Não compara `communities` linha a linha.
- Não gera comandos ou corrige nada.
- Não escreve no NetBox.
- Não aplica configuração no dispositivo.

## Códigos de divergência suportados
- `INTERFACE_MISSING_IN_NETBOX`
- `INTERFACE_MISSING_ON_DEVICE`
- `INTERFACE_DESCRIPTION_MISMATCH`
- `DESCRIPTION_NON_COMPLIANT`
- `IP_MISSING_IN_NETBOX`
- `IP_MISSING_ON_DEVICE`
- `VRF_MISSING_IN_NETBOX`
- `VRF_MISSING_ON_DEVICE`
- `VLAN_MISSING_IN_NETBOX`
- `VLAN_MISSING_ON_DEVICE`
- `BGP_PEER_MISSING_IN_NETBOX`
- `BGP_PEER_MISSING_ON_DEVICE`
- `BGP_ASN_MISMATCH`
- `BGP_POLICY_MISMATCH`

## Próxima fase
- Gerar relatório Markdown de divergências.
- Comparação avançada de `route-policies`, `prefix-lists` e `communities`.
- Priorizar correções de NetBox vs dispositivo.
