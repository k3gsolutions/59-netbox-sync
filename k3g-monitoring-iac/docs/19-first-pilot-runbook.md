# Runbook — Primeiro Piloto de Compliance

## 1. Objetivo
Executar análise read-only de um dispositivo Huawei NE8000 comparando NetBox vs configuração aplicada.

## 2. Escopo inicial
Incluir:
- Device
- Interfaces
- Descriptions
- VRFs
- IPs
- BGP peers
- Route-policy como evidência
- Prefix-lists/community-lists apenas como contagem/evidência

Excluir por enquanto:
- aplicação de configuração
- escrita no NetBox
- criação de hosts Zabbix
- dashboards Grafana
- execução em lote

## 3. Pré-requisitos
- `device_id` no NetBox
- nome do device no NetBox
- IP/porta SSH
- usuário SSH read-only
- token NetBox read-only
- endpoint local do netops_netbox_sync
- confirmação de janela/teste
- confirmação de que credenciais não serão commitadas

## 4. Dados a preencher antes da execução

| Campo | Valor | Observação |
| --- | --- | --- |
| device_name | PREENCHER | Nome no NetBox |
| device_id | PREENCHER | ID NetBox |
| device_host | PREENCHER | IP ou hostname |
| device_port | PREENCHER | Porta SSH |
| netbox_url | PREENCHER | URL |
| ssh_user | PREENCHER | read-only |
| escopo | interfaces/vrf/ip/bgp | primeiro ciclo |

## 5. Checklist de segurança
- [ ] Credencial SSH é read-only.
- [ ] Token NetBox é read-only.
- [ ] Nenhum comando de configuração será executado.
- [ ] Nenhum endpoint `/sync` será chamado.
- [ ] Apenas `/compliance/analyze` ou equivalente será usado.
- [ ] Relatório será salvo em `reports/pilot-device-compliance/`.
- [ ] Segredos não serão gravados em arquivo.

## 6. Comandos proibidos
- `/sync`
- qualquer endpoint que escreva no NetBox
- qualquer comando system-view
- `commit`
- `save`
- `interface ... configuration`
- `route-policy ... configuration`
- qualquer alteração de configuração

## 7. Comandos permitidos
- `curl /health`
- `curl /compliance/analyze`
- comandos `display` no equipamento, via collector read-only
- ferramentas locais de documentação

## 8. Payload template

```json
{
  "device": {
    "host": "<DEVICE_HOST>",
    "port": <DEVICE_PORT>,
    "username": "<SSH_READONLY_USER>",
    "password": "<SSH_READONLY_PASSWORD>"
  },
  "device_id": <NETBOX_DEVICE_ID>,
  "netbox": {
    "url": "<NETBOX_URL>",
    "token": "<NETBOX_READONLY_TOKEN>",
    "verify_ssl": false
  }
}
```

## 9. Execução prevista
Passo 1:
- Validar health do netops_netbox_sync.

Passo 2:
- Executar analyze read-only.

Passo 3:
- Salvar JSON bruto em:
  `reports/pilot-device-compliance/<device_name>-raw-analyze.json`

Passo 4:
- Gerar relatório Markdown:
  `reports/pilot-device-compliance/<device_name>-compliance-report.md`

Passo 5:
- Revisar manualmente.

## 10. Critérios de sucesso
- Coleta executada sem erro SSH.
- NetBoxInventory carregado, se já implementado.
- DeviceInventory gerado.
- Nenhuma escrita realizada.
- Relatório Markdown criado.
- Divergências classificadas.
- Ações separadas entre:
  - corrigir NetBox
  - corrigir equipamento
  - revisar manualmente

## 11. Critérios de parada
Parar se:
- credencial não for read-only;
- endpoint tentar chamar `/sync`;
- erro de autenticação NetBox;
- erro SSH repetido;
- payload contiver segredo em arquivo versionado;
- comando proibido aparecer no plano.

## 12. Pós-execução
- Atualizar relatório.
- Atualizar `CURRENT_STATE`.
- Atualizar `NEXT_ACTIONS`.
- Registrar lições aprendidas.
- Não aplicar correções automaticamente.

## Resultado do primeiro teste read-only
- Endpoint: `/device/collect`
- Status: sucesso
- Modo: read-only
- Escrita no NetBox: não
- Configuração aplicada: não
- `/sync` usado: não
- `/compliance/analyze`: implementado e disponível no runtime atual

Summary:
| Métrica | Valor |
| --- | ---: |
| interfaces | 64 |
| ip_addresses | 38 |
| vrfs | 2 |
| vlans | 1 |
| bgp_sessions | 45 |
| route_policies | 163 |
| prefix_lists | 102 |
| as_path_filters | 34 |
| communities | 190 |
| community_lists | 187 |

### Atualização — FASE 0.8 (CAVEMAN)
- NetBoxInventory read-only ficou resiliente: core DCIM/IPAM é obrigatório, plugin BGP é best-effort.
- Falha em endpoint do plugin gera aviso `NETBOX_BGP_PLUGIN_PARTIAL` (severity info) e não derruba a análise.
- `netbox_loaded=true` quando o núcleo DCIM/IPAM é carregado com sucesso; `compliance_enabled=false` permanece nesta fase para o fluxo inicial.
- Testes do `netops_netbox_sync` (`PYTHONPATH=. .venv/bin/pytest -q`) passaram: **9 passed**.

### Primeiro relatório real de compliance
- Relatório gerado: `reports/pilot-device-compliance/pilot-device-compliance-report.md`
- Device: `4WNET-MNS-KTG-RX`
- NetBox carregado: Sim
- Compliance habilitado: Sim
- Status: `drift_detected`
- Total de divergências: 161
- Severidade máxima: `high`
- `/sync` não foi usado
- Nenhuma configuração aplicada
- Relatório já separa diff agregado, divergências agregadas, divergências por objeto, warnings e ações recomendadas
- Descoberta principal: NetBox está incompleto para este device (64 interfaces aplicadas vs 1 documentada, 38 IPs aplicados vs 2 documentados, 45 sessões BGP aplicadas vs 0 documentadas)

### ImportPlan read-only implementado
- Endpoints: `/compliance/import-plan` e `/compliance/import-plan/report`
- ImportPlan classifica `safe_create_staged`, `needs_review`, `blocked` e `ignore`
- Naming inválido nunca vira `safe_create_staged`
- Nunca gera `delete`
- Sem escrita no NetBox
- Sem `/sync`
- Sem alteração em equipamento
- ImportPlan real gerado para `4WNET-MNS-KTG-RX`
- Testes no `netops_netbox_sync`: 32 passing

### ImportPlan base/service interface
- ImportPlan diferencia `base_inventory` de `service`.
- Markdown agora separa `Base Inventory` e `Service Candidates`.
- Base Inventory representa inventário físico/lógico base.
- Service Candidates representa itens que dependem de regra de serviço/naming.
- Total de itens no ImportPlan: 161.
- Safe create staged: 59.
- Needs review: 92.
- Blocked: 0.
- Ignored: 10.
- Interfaces base podem ser `safe_create_staged` mesmo sem naming de serviço.
- Interfaces de serviço e subinterfaces só podem ser `safe_create_staged` com naming válido.
- Subinterfaces inválidas são classificadas como `needs_review`.
- BGP peers continuam `needs_review`.
- IPs sem associação ou naming continuam `needs_review`.

Nota curta:
O relatório mostra que o NetBox atual não representa o estado aplicado do device, tornando urgente o próximo passo de NetBox Staged Import com aprovação humana.
