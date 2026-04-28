no ntetops# FASE 0.8.1 — NetBoxInventory Deep Mapping

## Objetivo
Aprofundar a coleta read-only do NetBox para alimentar o diff e relatórios de compliance sem depender do plugin BGP. O inventário agora retorna campos ricos de dispositivo, interfaces, IPs, VRFs, VLANs, circuitos e objetos opcionais do plugin BGP.

## Componentes coletados
- Device (status, role, site, tenant, platform, fabricante, modelo, IP primário, tags, custom fields)
- Interfaces (descrição, MTU, LAG, VLANs, VRF, tags, custom fields)
- IP addresses (assets atribuídos, VRF, tenant, tags, custom fields)
- VRFs (RD, tenants, targets)
- VLANs (status, role, site, tenant)
- Circuits + terminations (quando existirem)
- BGP sessions, route-policies, prefix-lists, community-lists, communities, as-path filters (best-effort)

## Core obrigatório
- Device + interfaces + IP addresses precisam carregar; falhas acionam `NETBOX_LOAD_FAILED`.
- VRFs e VLANs são buscados a partir das interfaces/IPs referenciadas.

## Plugin BGP
- Continua best-effort: ausência/parcial gera warning `NETBOX_BGP_PLUGIN_PARTIAL`.
- Inventário agrega contagens para futuras comparações, mas não trava análise.

## Limitações atuais
- Circuits são carregados via circuit terminations; ambientes sem esse endpoint recebem aviso leve.
- Inventário detalhado ainda não é devolvido no response de `/compliance/analyze` (mantemos payload leve).
- Diferença objeto-a-objeto ainda não é calculada.

## Próximos passos
- FASE 0.9: gerar diff inicial agregando contagens (já preparado).
- FASE futura: expor detalhes sob demanda e iniciar diff objeto-a-objeto.
