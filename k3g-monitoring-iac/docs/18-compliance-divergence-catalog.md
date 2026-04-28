# 18 — Compliance Divergence Catalog

Este catálogo descreve os tipos de divergência esperados na comparação entre NetBoxInventory e DeviceInventory.

## Estrutura do catálogo
- `Código`
- `Descrição`
- `Severidade`
- `Evidência esperada`
- `Recomendação`
- `Ação preferencial`
- `Corrige no NetBox ou no equipamento`

## Códigos de divergência

### MISSING_IN_NETBOX
- Descrição: Objeto ou configuração existe no dispositivo, mas não está cadastrado no NetBox.
- Severidade: alta
- Evidência esperada: bloco de configuração do equipamento sem referência NetBox.
- Recomendação: criar ou associar o objeto no NetBox antes de monitorar.
- Ação preferencial: NetBox
- Corrige: NetBox

### MISSING_ON_DEVICE
- Descrição: Objeto existe no NetBox, mas não foi encontrado no equipamento.
- Severidade: média/alta
- Evidência esperada: objeto NetBox ativo sem contraparte no inventário do equipamento.
- Recomendação: validar se o serviço foi retirado ou se há erro de descoberta.
- Ação preferencial: equipamento
- Corrige: equipamento

### DESCRIPTION_NON_COMPLIANT
- Descrição: Descrição de interface ou serviço não segue o naming convention.
- Severidade: média
- Evidência esperada: descrição de interface sem slug válido ou com service_type/tenant divergentes.
- Recomendação: ajustar descrição no dispositivo e/ou NetBox para alinhamento.
- Ação preferencial: equipamento
- Corrige: equipamento

### SERVICE_TYPE_MISMATCH
- Descrição: Service type associado ao objeto difere entre NetBox e equipamento.
- Severidade: alta
- Evidência esperada: `service_type` conflitante em NetBox vs payload do dispositivo.
- Recomendação: corrigir o campo de serviço no NetBox e/ou ajustar descrição no dispositivo.
- Ação preferencial: NetBox
- Corrige: NetBox

### TENANT_MISMATCH
- Descrição: Tenant associado no NetBox não corresponde ao tenant identificado na configuração do equipamento.
- Severidade: alta
- Evidência esperada: tenant NetBox diferente do slug extraído da interface/service description.
- Recomendação: alinhar tenant no NetBox com o serviço real.
- Ação preferencial: NetBox
- Corrige: NetBox

### NETBOX_ID_MISMATCH
- Descrição: Identificador NetBox presente na descrição ou metadata difere do ID real do objeto no NetBox.
- Severidade: alta
- Evidência esperada: `NB-<id>` divergente ou ausente.
- Recomendação: atualizar o identificador para o mesmo valor usado no NetBox.
- Ação preferencial: NetBox
- Corrige: NetBox

### VRF_MISMATCH
- Descrição: VRF/ VPN-instance configurada no dispositivo não corresponde ao VRF informado no NetBox.
- Severidade: alta
- Evidência esperada: VRF name, RD ou route-target diferentes entre as fontes.
- Recomendação: alinhar VRF no NetBox ou revisar a configuração de VRF no equipamento.
- Ação preferencial: NetBox
- Corrige: NetBox / equipamento

### VLAN_MISMATCH
- Descrição: VLAN configurada no equipamento difere da VLAN associada ao objeto NetBox.
- Severidade: média/alta
- Evidência esperada: ID de VLAN, nome ou descrição divergente.
- Recomendação: corrigir a associação de VLAN no NetBox ou ajustar a configuração do equipamento.
- Ação preferencial: NetBox
- Corrige: NetBox / equipamento

### QINQ_MISMATCH
- Descrição: Terminação QinQ no equipamento está divergente do modelo NetBox.
- Severidade: alta
- Evidência esperada: outer/inner VLANs ou encapsulamento diferentes.
- Recomendação: alinhar as VLANs QinQ e a terminologia no NetBox com o dispositivo.
- Ação preferencial: NetBox
- Corrige: NetBox / equipamento

### IP_MISMATCH
- Descrição: Endereço IP ou máscara no equipamento não coincide com o cadastro NetBox.
- Severidade: alta
- Evidência esperada: IP distinto ou máscara diferente para a mesma interface/serviço.
- Recomendação: atualizar NetBox ou corrigir IP no equipamento, conforme origem da verdade.
- Ação preferencial: equipamento
- Corrige: equipamento

### MTU_MISMATCH
- Descrição: MTU configurado no equipamento difere do valor informado no NetBox.
- Severidade: média
- Evidência esperada: MTU discrepante entre as fontes.
- Recomendação: ajustar documentação no NetBox e/ou a configuração do equipamento.
- Ação preferencial: NetBox
- Corrige: equipamento

### BGP_PEER_MISSING
- Descrição: Par BGP esperado no NetBox não foi encontrado no equipamento.
- Severidade: alta
- Evidência esperada: configuração BGP sem peer correspondente ou peer down.
- Recomendação: validar a sessão BGP e ajustar o dispositivo.
- Ação preferencial: equipamento
- Corrige: equipamento

### BGP_PEER_WITHOUT_DESCRIPTION
- Descrição: Peer BGP sem description.
- Severidade: medium
- Evidência esperada: peer_ip, peer_as, address_family, vrf.
- Recomendação: adicionar description no equipamento com aprovação humana.
- Ação preferencial: equipamento
- Corrige: equipamento

### BGP_SESSION_NOT_ESTABLISHED
- Descrição: Peer BGP fora de Established.
- Severidade: depende do service_type/criticality.
- Evidência esperada: peer_ip, state, peer_as, policies.
- Recomendação: investigação operacional antes de correção.
- Ação preferencial: operação
- Corrige: equipamento

### BGP_POLICY_MISSING_ON_PEER
- Descrição: Peer BGP sem import/export policy quando esperado.
- Severidade: high para cliente/operadora/CDN.
- Evidência esperada: peer_ip, import_policy, export_policy.
- Recomendação: adicionar policy no equipamento, com aprovação humana.
- Ação preferencial: equipamento
- Corrige: equipamento

### BGP_ASN_MISMATCH
- Descrição: ASN remoto configurado no equipamento difere do ASN esperado no NetBox.
- Severidade: alta
- Evidência esperada: ASN remota diferente em peer BGP.
- Recomendação: corrigir ASN no equipamento e/ou atualizar o cadastro NetBox.
- Ação preferencial: NetBox
- Corrige: equipamento

### BGP_AF_MISMATCH
- Descrição: Address family BGP no equipamento não corresponde ao esperado no NetBox.
- Severidade: média/alta
- Evidência esperada: IPv4/IPv6/vpnv4/vpnv6 inconsistentes.
- Recomendação: alinhar address-family na configuração BGP.
- Ação preferencial: equipamento
- Corrige: equipamento

### ROUTE_POLICY_MISMATCH
- Descrição: Route-policy referenciada no equipamento diverge da policy registrada no NetBox.
- Severidade: média/alta
- Evidência esperada: nomes de route-policy ou atributos diferentes.
- Recomendação: corrigir política no equipamento e assegurar referência coerente no NetBox.
- Ação preferencial: equipamento
- Corrige: equipamento

### PREFIX_LIST_MISSING
- Descrição: Prefix-list utilizada no equipamento não é encontrada no NetBox.
- Severidade: média
- Evidência esperada: referência a prefix-list em route-policy ou BGP sem objeto NetBox.
- Recomendação: documentar o prefix-list no NetBox ou revisar a dependência.
- Ação preferencial: NetBox
- Corrige: NetBox

### AS_PATH_FILTER_MISSING
- Descrição: AS-path filter utilizada no equipamento não existe no NetBox.
- Severidade: média
- Evidência esperada: referência a filtro AS-path em route-policy sem objeto NetBox.
- Recomendação: criar ou documentar o filtro no NetBox.
- Ação preferencial: NetBox
- Corrige: NetBox

### COMMUNITY_LIST_MISSING
- Descrição: Community list utilizada no equipamento não está cadastrada no NetBox.
- Severidade: média
- Evidência esperada: referência em route-policy ou BGP sem objeto correspondente.
- Recomendação: registrar community list no NetBox ou atualizar a documentação.
- Ação preferencial: NetBox
- Corrige: NetBox

### ORPHAN_DEVICE_CONFIG
- Descrição: Configuração no equipamento não está associada a nenhum objeto NetBox conhecido.
- Severidade: alta
- Evidência esperada: interface ou serviço sem slug ou identificação NetBox.
- Recomendação: identificar se é configuração legada ou serviço não modelado e, em seguida, associar ou limpar.
- Ação preferencial: equipamento
- Corrige: equipamento

### INSUFFICIENT_METADATA
- Descrição: Não há metadata suficiente para mapear corretamente o objeto entre NetBox e equipamento.
- Severidade: alta
- Evidência esperada: falta de `service_type`, `tenant`, `netbox_id` ou descrições machine-parseable.
- Recomendação: completar metadata no NetBox e/ou no equipamento antes de seguir com compliance.
- Ação preferencial: NetBox
- Corrige: NetBox
