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

## Discriminação: Base Inventory vs Service Interfaces

### Base Inventory Interfaces
Não exigem `DESCRIPTION_NON_COMPLIANT` validation:
- Eth-Trunk0, Eth-Trunk1, etc (LAG)
- GigabitEthernet0/0/0, Ethernet0/0/0, etc (physical)
- 10GE, 25GE, 40GE, 100GE (high-speed)
- Management, mgmt, mgt (management)
- LoopBack0, LoopBack1 (loopback inventory)
- ae0, bundle-ether0 (Juniper/other LAG)

Regra: Se interface é base inventory, não gera `DESCRIPTION_NON_COMPLIANT` mesmo que description não siga padrão.
Pode gerar `INTERFACE_DESCRIPTION_MISMATCH` se houver divergência com NetBox (action: review).

### Service Candidate Interfaces
Exigem `DESCRIPTION_NON_COMPLIANT` validation:
- Subinterfaces com dot: Eth-Trunk0.1580 (válida se base.vlan_id padrão)
- Interfaces com keywords: "customer", "operator", "service", "vpn", etc
- Interfaces com IP/VRF/VLAN aplicado
- Qualquer interface com dot que não siga padrão base.number

Regra: Se interface é service, description deve seguir SERVICE_SLUG_PATTERN:
```
^(customer-internet|customer-l2vpn|customer-l3vpn|customer-transport|carrier-transit|carrier-peering|
  ix-public|cdn-cache|infra-backbone|infra-management):[a-z0-9-]{2,32}:NB-[0-9]+(:[\w-]+)?$
```

Caso contrário, gera `DESCRIPTION_NON_COMPLIANT` com action: fix_device.

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
