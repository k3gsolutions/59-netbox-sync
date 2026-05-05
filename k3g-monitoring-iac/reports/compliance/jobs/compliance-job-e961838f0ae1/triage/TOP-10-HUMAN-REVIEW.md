# Top 10 para Revisão Humana

Job: `compliance-job-e961838f0ae1`

Fonte:
- `reports/compliance/jobs/compliance-job-e961838f0ae1/triage/findings-triage.json`
- `reports/compliance/jobs/compliance-job-e961838f0ae1/comparison/devices/1890/compliance-findings.json`

Critérios aplicados:
- priorizar BGP peer not established
- priorizar BGP peer missing import/export policy
- priorizar BGP peer missing description
- incluir route_policy.missing e prefix_list.missing
- excluir `Virtual-Ethernet*.100`
- excluir `likely_parser_noise`
- excluir `likely_policy_too_strict` genérico

| Rank | Finding ID | Severity | Scope | Object | Rule ID | Title | Motivo | Ação humana sugerida |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | CMP-140157A8F6 | warning | bgp | 172.28.1.74 | bgp.peer.state.not_established | Peer BGP fora de Established | Sessão BGP fora de Established impacta troca de rotas. | Validar sessão, política e descrição do peer com operador humano. |
| 2 | CMP-1DB6A3E0E5 | warning | bgp | 172.28.1.6 | bgp.peer.state.not_established | Peer BGP fora de Established | Sessão BGP fora de Established impacta troca de rotas. | Validar sessão, política e descrição do peer com operador humano. |
| 3 | CMP-209762428D | warning | bgp | 172.28.1.90 | bgp.peer.state.not_established | Peer BGP fora de Established | Sessão BGP fora de Established impacta troca de rotas. | Validar sessão, política e descrição do peer com operador humano. |
| 4 | CMP-0B3EDA7B4B | warning | bgp | 172.28.1.74 | bgp.peer.policy.missing | BGP peer sem política import/export | Sem import/export policy, a política de troca fica incompleta. | Validar sessão, política e descrição do peer com operador humano. |
| 5 | CMP-0D5569B392 | warning | bgp | 172.28.1.6 | bgp.peer.policy.missing | BGP peer sem política import/export | Sem import/export policy, a política de troca fica incompleta. | Validar sessão, política e descrição do peer com operador humano. |
| 6 | CMP-0AB8A50C9B | warning | bgp | 10.20.0.14 | bgp.peer.description.required | BGP peer sem descrição | Peer sem descrição atrapalha revisão e governança. | Validar sessão, política e descrição do peer com operador humano. |
| 7 | CMP-154F7CEC68 | warning | bgp | 172.28.1.18 | bgp.peer.description.required | BGP peer sem descrição | Peer sem descrição atrapalha revisão e governança. | Validar sessão, política e descrição do peer com operador humano. |
| 8 | CMP-41E723BA69 | info | route_policy | * | route_policy.missing | Nenhuma route-policy parseada | Ausência de route-policy pode indicar documentação ou cadastro faltante. | Conferir se ausência é esperada ou se falta cadastro/documentação. |
| 9 | CMP-C55B546A7F | info | prefix_list | * | prefix_list.missing | Nenhum prefix-list parseado | Ausência de prefix-list pode esconder dependências de roteamento. | Conferir se ausência é esperada ou se falta cadastro/documentação. |
| 10 | CMP-349F823871 | warning | bgp | 200.242.78.57 | bgp.peer.state.not_established | Peer BGP fora de Established | Sessão BGP fora de Established impacta troca de rotas. | Validar sessão, política e descrição do peer com operador humano. |
