# Pilot Device Summary — Primeiro Piloto de Compliance

## Contexto
Primeiro piloto de compliance com `netops_netbox_sync` em modo read-only, sem escrita no NetBox e sem alterações de configuração. O relatório real foi gerado para o device `4WNET-MNS-KTG-RX`.

## Resultado do primeiro relatório real
- Relatório gerado: `reports/pilot-device-compliance/pilot-device-compliance-report.md`
- Device: `4WNET-MNS-KTG-RX`
- NetBox carregado: Sim
- Compliance habilitado: Sim
- Status: `drift_detected`
- Total de divergências: 161
- Severidade máxima: `high`
- `/sync` usado: não
- Nenhuma configuração aplicada
- O relatório separa diff agregado, divergências agregadas, divergências por objeto, warnings e ações recomendadas

## Dados coletados aplicados
- Interfaces aplicadas: 64
- IP addresses aplicados: 38
- Sessões BGP aplicadas: 45

## Dados documentados no NetBox
- Interfaces documentadas: 1
- IP addresses documentados: 2
- Sessões BGP documentadas: 0

## Observação principal
O NetBox está incompleto para este device: há um grande gap entre o estado aplicado e o estado documentado no NetBox.

## Observações gerais
- O primeiro relatório real confirma que a análise de compliance funciona em modo read-only.
- Não houve nenhuma ação de escrita no equipamento ou no NetBox.
- O resultado aponta claramente a necessidade de enriquecer o NetBox a partir das divergências detectadas.
- Todas as evidências brutas devem permanecer fora do repositório e o JSON raw não deve ser versionado.
- `/compliance/import-plan` e `/compliance/import-plan/report` foram implementados.
- ImportPlan agora diferencia `base_inventory` vs `service`.
- Markdown agora separa:
  - Base Inventory
  - Service Candidates
- Base Inventory representa inventário físico/lógico base.
- Service Candidates representa itens que dependem de regra de serviço/naming.
- Total de itens no ImportPlan: 161.
- Safe create staged: 59.
- Needs review: 92.
- Blocked: 0.
- Ignored: 10.
- Interfaces base podem ser `safe_create_staged` sem naming de serviço.
- Interfaces de serviço/subinterfaces só podem ser `safe_create_staged` com naming válido.
- Subinterfaces inválidas viram `needs_review`.
- BGP peers continuam `needs_review`.
- IPs sem associação/naming continuam `needs_review`.
- Naming inválido nunca vira `safe_create_staged`.
- Nunca gera `delete`.
- Sem `/sync` e sem alteração em equipamento.
- Nenhuma escrita no NetBox.
- Nenhuma configuração aplicada.
- 32 testes passando no `netops_netbox_sync`.
- ImportPlan real gerado para `4WNET-MNS-KTG-RX`.
