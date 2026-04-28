# Relatório de Compliance — <DEVICE>

## 1. Resumo executivo
- Dispositivo piloto: `<DEVICE>`
- Data da análise: `<DATA>`
- Objetivo: comparar NetBoxInventory vs DeviceInventory em modo read-only.
- Status geral: `<PRONTO / NÃO PRONTO / ATENÇÃO>`

## 2. Dados do dispositivo
- Nome: `<HOSTNAME>`
- Site: `<SITE>`
- Tenant: `<TENANT>`
- Service type principal: `<SERVICE_TYPE>`
- Criticality: `<CRITICALITY>`
- Observações: `<OBSERVAÇÕES>`

## 3. Dados coletados do NetBox
- Device: `<NETBOX_DEVICE>`
- Interfaces: `<INTERFACES>`
- VRFs: `<VRFS>`
- VLANs / QinQ: `<VLANs/QINQ>`
- IPs: `<IPS>`
- BGP peers: `<BGP_PEERS>`
- Route-policies: `<ROUTE_POLICIES>`
- Prefix-lists / AS-path / Communities: `<POLICY_LISTS>`

## 4. Dados coletados do equipamento
- Configuração de interfaces: `<INTERFACE_CONFIG>`
- Descrições e slugs: `<DESCRIPTIONS>`
- VRFs / vpn-instances: `<VRFS_DEVICE>`
- VLANs / QinQ: `<VLANs/QINQ_DEVICE>`
- IPs: `<IPS_DEVICE>`
- BGP peers: `<BGP_PEERS_DEVICE>`
- Route-policies: `<ROUTE_POLICIES_DEVICE>`
- Prefix-lists / AS-path / Communities: `<POLICY_LISTS_DEVICE>`

## 5. Comparação geral
- Alinhamento NetBox vs Device: `<RESUMO>`
- Principais gaps identificados: `<GAPS>`
- Nível de risco do piloto: `<BAIXO / MÉDIO / ALTO>`

## 6. Interfaces
- Interfaces auditadas: `<INTERFACES_AUDITADAS>`
- Divergências de descrição: `<DIVERGENCIAS_DESC>`
- Divergências de MTU / VLAN / QinQ: `<DIVERGENCIAS_MTU_VLAN_QINQ>`

## 7. VRFs
- VRFs auditadas: `<VRFS_AUDITADAS>`
- Divergências de nome / RD / route-target: `<DIVERGENCIAS_VRF>`

## 8. VLANs / QinQ
- VLANs auditadas: `<VLANS_AUDITADAS>`
- Divergências de mapeamento: `<DIVERGENCIAS_VLAN_QINQ>`

## 9. IPs
- IPs auditados: `<IPS_AUDITADOS>`
- Divergências de endereçamento ou máscara: `<DIVERGENCIAS_IP>`

## 10. BGP peers
- Peers auditados: `<PEERS_AUDITADOS>`
- Divergências de ASN / AF / estado: `<DIVERGENCIAS_BGP>`

## 11. Route-policies
- Policies auditadas: `<POLICIES_AUDITADAS>`
- Divergências de associação ou conteúdo: `<DIVERGENCIAS_ROUTE_POLICY>`

## 12. Prefix-lists / AS-path / Communities
- Prefix-lists auditadas: `<PREFIX_LISTS_AUDITADAS>`
- AS-path filters auditados: `<AS_PATH_FILTERS_AUDITADOS>`
- Community lists auditadas: `<COMMUNITY_LISTS_AUDITADAS>`
- Divergências identificadas: `<DIVERGENCIAS_LISTAS>`

## 13. Naming convention
- Descrições analisadas: `<DESCRIPTIONS_ANALISADAS>`
- Compliance de slug: `<SLUG_COMPLIANCE>`
- Observações de naming: `<OBS_NAMING>`

## 14. Divergências encontradas
- Código / descrição / severidade / recomendação / corrigir em:
  - `<CÓDIGO_1> — <DESCRIÇÃO> — <SEVERIDADE> — <RECOMENDAÇÃO> — <NETBOX/EQUIPAMENTO>`
  - `<CÓDIGO_2> ...`

## 15. Ações recomendadas no NetBox
- `<AÇÃO_NETBOX_1>`
- `<AÇÃO_NETBOX_2>`

## 16. Ações recomendadas no equipamento
- `<AÇÃO_EQUIPAMENTO_1>`
- `<AÇÃO_EQUIPAMENTO_2>`

## 17. Comandos sugeridos, não executar automaticamente
- `<COMANDO_1>`
- `<COMANDO_2>`
- Observação: esses comandos são apenas para coleta e validação, não para execução de configuração.

## 18. Riscos
- `<RISCO_1>`
- `<RISCO_2>`

## 19. Próximos passos
- `<PASSO_1>`
- `<PASSO_2>`

## 20. Anexos / evidências
- `<ANEXO_1>`
- `<ANEXO_2>`
- Nota: anexar logs de consulta, trechos de configuração e screenshots se disponíveis.
