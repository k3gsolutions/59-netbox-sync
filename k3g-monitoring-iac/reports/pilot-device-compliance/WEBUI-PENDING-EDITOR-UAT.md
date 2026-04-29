# Web UI Pending Editor UAT - 4WNET-MNS-KTG-RX

## 1. Objetivo
Validar a edição de pendencias via Web UI, com salvamento local de CSV e audit, sem escrita NetBox.

## 2. Escopo
- Service Team: 1 item
- Network Ops: 1 item
- BGP Team: 1 item

## 3. Restricoes
- Nenhum NetBox write
- Nenhum apply
- Nenhum /sync
- Nenhum ApprovalRecord automatico
- Nenhum ApplyPlan automatico

## 4. Dados usados
Todos os dados abaixo sao controlados/UAT e marcados com `updated_by=uat`:
- Service Team: `Eth-Trunk0.10`
- Network Ops: `192.0.2.1/30`
- BGP Team: `203.0.113.1`

## 5. Fluxo executado
1. Abriu-se a pendencia no modal da Web UI.
2. Os tres itens foram preenchidos e salvos via endpoint local.
3. O backend gerou/atualizou os CSVs em `reports/pilot-device-compliance/week1-responses/`.
4. O backend gerou os audits em `reports/pilot-device-compliance/week1-responses/audit/`.
5. O validador Week 1 foi executado com sucesso.

## 6. Resultados
- Service Team salvo localmente: `service-team-response.csv`
- Network Ops salvo localmente: `network-ops-response.csv`
- BGP Team salvo localmente: `bgp-team-response.csv`
- Validacao Week 1: 3 validated, 4 still pending
- Download CSV via `/reports/download` validado com sucesso
- Bloqueio de paths sensiveis validado

## 7. Evidencias
- CSV gerado com cabecalho unificado e coluna opcional `relation_type`
- Audit JSON gerado para os tres times
- Network Ops aceitou `relation_type=infrastructure` sem exigir `service_relation`
- `ip_address` aceitou interface/VRF preenchidos manualmente

## 8. Observacoes
- O audit de BGP foi mantido em modo UAT-only.
- Nenhuma escrita NetBox ocorreu.
- Nenhum token, apply ou sync foi executado.
