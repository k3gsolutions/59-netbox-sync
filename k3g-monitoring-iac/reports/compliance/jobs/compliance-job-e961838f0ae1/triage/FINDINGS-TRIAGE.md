# FINDINGS-TRIAGE

## Job ID
`compliance-job-e961838f0ae1`

## Status
`TRIAGE_COMPLETED`

## Summary
- likely_parser_noise: 25
- likely_policy_too_strict: 21
- needs_human_review: 59
- remediation_candidate: 0
- blocked_from_remediation: 0

## Top 10 para Revisão Humana

### #1 172.28.1.74
- finding_id: CMP-140157A8F6
- severity: warning
- scope: bgp
- rule_id: bgp.peer.state.not_established
- title: Peer BGP fora de Established
- evidence: {"source": "parsed_inventory", "field": "bgp_peers[].state", "value": "272748 0 0 0 4040h10m Idle 0"}
- suggested_human_action: Validar sessão, política e descrição do peer com operador humano.
- why_this_matters: Sessão BGP fora de Established impacta troca de rotas.

### #2 172.28.1.6
- finding_id: CMP-1DB6A3E0E5
- severity: warning
- scope: bgp
- rule_id: bgp.peer.state.not_established
- title: Peer BGP fora de Established
- evidence: {"source": "parsed_inventory", "field": "bgp_peers[].state", "value": "268248 0 0 0 5310h02m Idle 0"}
- suggested_human_action: Validar sessão, política e descrição do peer com operador humano.
- why_this_matters: Sessão BGP fora de Established impacta troca de rotas.

### #3 172.28.1.90
- finding_id: CMP-209762428D
- severity: warning
- scope: bgp
- rule_id: bgp.peer.state.not_established
- title: Peer BGP fora de Established
- evidence: {"source": "parsed_inventory", "field": "bgp_peers[].state", "value": "263450 23794 4152675 0 0341h14m Established 10"}
- suggested_human_action: Validar sessão, política e descrição do peer com operador humano.
- why_this_matters: Sessão BGP fora de Established impacta troca de rotas.

### #4 172.28.1.74
- finding_id: CMP-0B3EDA7B4B
- severity: warning
- scope: bgp
- rule_id: bgp.peer.policy.missing
- title: BGP peer sem política import/export
- evidence: {"source": "parsed_inventory", "field": "bgp_peers[].import_policy/export_policy", "value": {"import_policy": null, "export_policy": null}}
- suggested_human_action: Validar sessão, política e descrição do peer com operador humano.
- why_this_matters: Sem import/export policy, a política de troca fica incompleta.

### #5 172.28.1.6
- finding_id: CMP-0D5569B392
- severity: warning
- scope: bgp
- rule_id: bgp.peer.policy.missing
- title: BGP peer sem política import/export
- evidence: {"source": "parsed_inventory", "field": "bgp_peers[].import_policy/export_policy", "value": {"import_policy": null, "export_policy": null}}
- suggested_human_action: Validar sessão, política e descrição do peer com operador humano.
- why_this_matters: Sem import/export policy, a política de troca fica incompleta.

### #6 10.20.0.14
- finding_id: CMP-0AB8A50C9B
- severity: warning
- scope: bgp
- rule_id: bgp.peer.description.required
- title: BGP peer sem descrição
- evidence: {"source": "parsed_inventory", "field": "bgp_peers[].description", "value": null}
- suggested_human_action: Validar sessão, política e descrição do peer com operador humano.
- why_this_matters: Peer sem descrição atrapalha revisão e governança.

### #7 172.28.1.18
- finding_id: CMP-154F7CEC68
- severity: warning
- scope: bgp
- rule_id: bgp.peer.description.required
- title: BGP peer sem descrição
- evidence: {"source": "parsed_inventory", "field": "bgp_peers[].description", "value": null}
- suggested_human_action: Validar sessão, política e descrição do peer com operador humano.
- why_this_matters: Peer sem descrição atrapalha revisão e governança.

### #8 *
- finding_id: CMP-41E723BA69
- severity: info
- scope: route_policy
- rule_id: route_policy.missing
- title: Nenhuma route-policy parseada
- evidence: {"source": "parsed_inventory", "field": "route_policies", "value": null}
- suggested_human_action: Conferir se ausência é esperada ou se falta cadastro/documentação.
- why_this_matters: Ausência de route-policy pode indicar documentação ou cadastro faltante.

### #9 *
- finding_id: CMP-C55B546A7F
- severity: info
- scope: prefix_list
- rule_id: prefix_list.missing
- title: Nenhum prefix-list parseado
- evidence: {"source": "parsed_inventory", "field": "ip_prefixes/ipv6_prefixes", "value": null}
- suggested_human_action: Conferir se ausência é esperada ou se falta cadastro/documentação.
- why_this_matters: Ausência de prefix-list pode esconder dependências de roteamento.

### #10 200.242.78.57
- finding_id: CMP-349F823871
- severity: warning
- scope: bgp
- rule_id: bgp.peer.state.not_established
- title: Peer BGP fora de Established
- evidence: {"source": "parsed_inventory", "field": "bgp_peers[].state", "value": "4230 12772878 137204 0 0987h42m Established 1037863"}
- suggested_human_action: Validar sessão, política e descrição do peer com operador humano.
- why_this_matters: Sessão BGP fora de Established impacta troca de rotas.

## Parser Noise
- CMP-B0ED197AD0 | Eth-Trunk0 | Mismatch aparece em interface lógica/subinterface e pode vir de parsing incompleto.
- CMP-CB153C93B8 | Eth-Trunk0.812 | Mismatch aparece em interface lógica/subinterface e pode vir de parsing incompleto.
- CMP-A075F93D07 | Eth-Trunk0.828 | Mismatch aparece em interface lógica/subinterface e pode vir de parsing incompleto.
- CMP-CDC6FF2D8F | Eth-Trunk0.1580 | Mismatch aparece em interface lógica/subinterface e pode vir de parsing incompleto.
- CMP-3AE851DD91 | Eth-Trunk0.1606 | Mismatch aparece em interface lógica/subinterface e pode vir de parsing incompleto.
- CMP-586DAEA60B | Eth-Trunk0.2033 | Mismatch aparece em interface lógica/subinterface e pode vir de parsing incompleto.
- CMP-EF0426F092 | Eth-Trunk0.2651 | Mismatch aparece em interface lógica/subinterface e pode vir de parsing incompleto.
- CMP-FDEF9E9F4A | Eth-Trunk0.2749 | Mismatch aparece em interface lógica/subinterface e pode vir de parsing incompleto.
- CMP-FE310B00D1 | Eth-Trunk0.3902 | Mismatch aparece em interface lógica/subinterface e pode vir de parsing incompleto.
- CMP-1DE26A68D2 | Eth-Trunk0.3967 | Mismatch aparece em interface lógica/subinterface e pode vir de parsing incompleto.
- CMP-7CEA3E1891 | Eth-Trunk0.4005 | Mismatch aparece em interface lógica/subinterface e pode vir de parsing incompleto.
- CMP-E2C69F8F0A | Eth-Trunk1 | Mismatch aparece em interface lógica/subinterface e pode vir de parsing incompleto.
- CMP-655FCB1A5C | GigabitEthernet0/5/6(10G) | Mismatch aparece em interface lógica/subinterface e pode vir de parsing incompleto.
- CMP-3644659003 | GigabitEthernet0/5/7(10G) | Mismatch aparece em interface lógica/subinterface e pode vir de parsing incompleto.
- CMP-AD107E2DA6 | GigabitEthernet0/5/8(10G) | Mismatch aparece em interface lógica/subinterface e pode vir de parsing incompleto.
- CMP-2722EF2B20 | GigabitEthernet0/5/9(10G) | Mismatch aparece em interface lógica/subinterface e pode vir de parsing incompleto.
- CMP-4D2419EC81 | LoopBack0 | Mismatch aparece em interface lógica/subinterface e pode vir de parsing incompleto.
- CMP-5F01B5DEC2 | LoopBack1 | Mismatch aparece em interface lógica/subinterface e pode vir de parsing incompleto.
- CMP-37073A0586 | Tunnel0 | Mismatch aparece em interface lógica/subinterface e pode vir de parsing incompleto.
- CMP-3A99848AD5 | Tunnel1 | Mismatch aparece em interface lógica/subinterface e pode vir de parsing incompleto.
- CMP-9D90DFC902 | Virtual-Ethernet0/2/100 | Mismatch aparece em interface lógica/subinterface e pode vir de parsing incompleto.
- CMP-82D96F9E87 | Virtual-Ethernet0/2/101 | Mismatch aparece em interface lógica/subinterface e pode vir de parsing incompleto.
- CMP-76E7D0E61C | Virtual-Ethernet0/2/200 | Mismatch aparece em interface lógica/subinterface e pode vir de parsing incompleto.
- CMP-3A35D2BBEB | Virtual-Ethernet0/2/201 | Mismatch aparece em interface lógica/subinterface e pode vir de parsing incompleto.
- CMP-376CDECFCD | Virtual-Template0 | Mismatch aparece em interface lógica/subinterface e pode vir de parsing incompleto.

## Policy Too Strict
- CMP-FE75504980 | GigabitEthernet0/5/0(10G) | Interface Huawei válida parece bater em policy interna rígida demais.
- CMP-80E3577493 | GigabitEthernet0/5/1(10G) | Interface Huawei válida parece bater em policy interna rígida demais.
- CMP-6C46DA6F73 | GigabitEthernet0/5/2(10G) | Interface Huawei válida parece bater em policy interna rígida demais.
- CMP-79786299EC | GigabitEthernet0/5/3(10G) | Interface Huawei válida parece bater em policy interna rígida demais.
- CMP-1CFEBB7F48 | GigabitEthernet0/5/4(10G) | Interface Huawei válida parece bater em policy interna rígida demais.
- CMP-B4A542CC89 | GigabitEthernet0/5/5(10G) | Interface Huawei válida parece bater em policy interna rígida demais.
- CMP-8588B1D179 | Ethernet0/0/0 | Interface Huawei válida parece bater em policy interna rígida demais.
- CMP-3740F45D14 | GigabitEthernet0/5/6(10G) | Interface Huawei válida parece bater em policy interna rígida demais.
- CMP-42A559F67E | GigabitEthernet0/5/7(10G) | Interface Huawei válida parece bater em policy interna rígida demais.
- CMP-BE0E159900 | GigabitEthernet0/5/8(10G) | Interface Huawei válida parece bater em policy interna rígida demais.
- CMP-1574582148 | GigabitEthernet0/5/9(10G) | Interface Huawei válida parece bater em policy interna rígida demais.
- CMP-8AEE58B988 | Tunnel0 | Interface Huawei válida parece bater em policy interna rígida demais.
- CMP-6E75B0D143 | Tunnel1 | Interface Huawei válida parece bater em policy interna rígida demais.
- CMP-10ED039E62 | Virtual-Ethernet0/2/100 | Interface Huawei válida parece bater em policy interna rígida demais.
- CMP-ECD73947B0 | Virtual-Ethernet0/2/100.100 | Interface Huawei válida parece bater em policy interna rígida demais.
- CMP-A743617324 | Virtual-Ethernet0/2/101 | Interface Huawei válida parece bater em policy interna rígida demais.
- CMP-48B6DA3065 | Virtual-Ethernet0/2/101.100 | Interface Huawei válida parece bater em policy interna rígida demais.
- CMP-4E37AA8162 | Virtual-Ethernet0/2/200 | Interface Huawei válida parece bater em policy interna rígida demais.
- CMP-8412059E0F | Virtual-Ethernet0/2/200.100 | Interface Huawei válida parece bater em policy interna rígida demais.
- CMP-2F328E214C | Virtual-Ethernet0/2/201 | Interface Huawei válida parece bater em policy interna rígida demais.
- CMP-8155A6885F | Virtual-Template0 | Interface Huawei válida parece bater em policy interna rígida demais.

## Safety
- netbox_write=false
- device_connection=false
- sync_called=false
- approval_record_created=false
- apply_plan_created=false
