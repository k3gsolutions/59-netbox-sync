# First Staged NetBox Write — FASE 2.0

Primeira escrita real controlada no NetBox para criar 1 interface staged.

## 1. Objetivo

Executar POST real em `/api/dcim/interfaces/` para criar interface base_inventory aprovada.

Scope:
- Apenas 1 objeto
- Apenas interface
- Apenas POST create
- Nenhum PATCH/DELETE
- Nenhuma configuração em equipamento

## 2. Pré-requisitos

✅ ApprovalRecord com status=dry_run_passed
✅ ApplyPlan gerado e validado
✅ Simulação completada (would_create_staged)
✅ NetBox acessível
✅ Token write disponível (via env var)
✅ Device já existe no NetBox

## 3. Riscos

- Criar objeto indesejado
- Sobrescrever objeto existente
- Expor token em log/output
- Erro de API bloqueia apply futuro

Mitigações:
- Preflight GET antes do POST
- Aborta se objeto existe
- Token via env var (nunca em args)
- Exit code indica sucesso/falha

## 4. Script: apply_staged_netbox_object.py

### Dry-Run (Padrão)

```bash
python3 tools/local/apply_staged_netbox_object.py \
  --plan reports/pilot-device-compliance/approvals/approved/<approval_id>-apply-plan.json \
  --netbox-url https://docs.k3gsolutions.com.br \
  --confirm-approval-id <approval_id> \
  --operator "seu-nome"
```

Resultado:
- Nenhuma escrita
- Validações executadas
- Relatório gerado em approvals/applied/
- Exit code 0

### Real Write (Explícito)

```bash
NETBOX_WRITE_TOKEN="your-token-here" python3 tools/local/apply_staged_netbox_object.py \
  --plan reports/pilot-device-compliance/approvals/approved/<approval_id>-apply-plan.json \
  --netbox-url https://docs.k3gsolutions.com.br \
  --confirm-approval-id <approval_id> \
  --operator "seu-nome" \
  --confirm-real-write
```

Resultado:
- Preflight GET: verificar se objeto existe
- Se existe: aborta (não sobrescreve)
- Se não existe: POST create
- Registra resultado
- Exit code 0 = sucesso, 1 = falha

## 5. Validações Obrigatórias

Antes do POST:
- ✅ approval_id corresponde
- ✅ status = dry_run_passed
- ✅ action = safe_create_staged
- ✅ object_type = interface
- ✅ method = POST
- ✅ readiness_status = ready
- ✅ Nenhum secret em payload
- ✅ Token fornecido (se real write)
- ✅ Dispositivo existe no NetBox
- ✅ Interface NÃO existe no NetBox

Se validação falhar:
- ❌ Aborta imediatamente
- ❌ Nenhuma escrita
- ❌ Erro registrado

## 6. Preflight Check

GET `/api/dcim/interfaces/?device_id={device_id}&name={object_key}`

Respostas:
- 200 + [] = OK, criar
- 200 + [obj] = aborta, objeto existe
- 404 = OK, criar
- 40x/50x = aborta, erro API

## 7. Resultado POST

Sucesso:
```
201 Created
{
  "id": 12345,
  "name": "Eth-Trunk0",
  "device": 1890,
  "status": {"value": "planned", "label": "Planned"},
  "tags": [...],
  "custom_fields": {...}
}
```

Failure:
```
400/422 Bad Request
{
  "errors": [...]
}
```

## 8. Politica de 1 Item por Vez

Por que?
- Menos risco de erro em massa
- Mais fácil validar cada item
- Rollback manual simples
- Auditoria clara

Implementação:
- Script aborta se >1 objeto em ApplyPlan
- Sem suporte a lote em FASE 2.0
- Próximas fases: batch apply (com gatekeeping)

## 9. Rollback Manual (se necessário)

Se interface foi criada e não deveria:

Via NetBox UI:
1. Navegar a Devices > Device > 4WNET-MNS-KTG-RX
2. Navegar a Interfaces
3. Localizar Eth-Trunk0
4. Editar > Delete > Confirm

Via API:
```bash
curl -X DELETE \
  https://docs.k3gsolutions.com.br/api/dcim/interfaces/{id}/ \
  -H "Authorization: Token <token>" \
  -H "Content-Type: application/json"
```

Auditoria:
- Registrar rollback manual em docs
- Não executar compliance automaticamente

## 10. Validação Pós-Apply

Gerar novo compliance report:

```bash
# Opcional: via API se servidor rodando
# curl -s -X POST http://127.0.0.1:8888/compliance/analyze/report

# Ou via payload local se preparado
python3 tools/local/<compliance-script>.py \
  --device 4WNET-MNS-KTG-RX
```

Arquivar relatório:

```bash
python3 tools/local/archive_compliance_report.py \
  --report reports/pilot-device-compliance/<report>.md \
  --device 4WNET-MNS-KTG-RX \
  --device-id 1890
```

Comparar antes/depois:

```bash
python3 tools/local/compare_compliance_reports.py \
  --old reports/pilot-device-compliance/current/<before>.md \
  --new reports/pilot-device-compliance/current/<after>.md \
  --output reports/pilot-device-compliance/comparisons/<comparison>.md
```

Validações esperadas:
- Interface Eth-Trunk0 ainda aparece em divergências (agora em NetBox)
- Nova categoria: INTERFACE_FOUND_IN_NETBOX (em vez de MISSING)
- Divergência resolvida
- Compliance score melhorado

## 11. Politica de Token

✅ Seguro:
- NETBOX_WRITE_TOKEN via ambiente
- Token nunca em args
- Token nunca em log
- Token nunca em arquivo

❌ Inseguro:
- --token flag (expõe em histórico)
- Token em arquivo credentials.txt
- Token em código
- Token em output/print

Verificação:
```bash
# Verificar se token aparece em output
python3 tools/local/apply_staged_netbox_object.py ... 2>&1 | grep -i token
# Output: nenhuma menção ao token
```

## 12. Critérios de Sucesso

✅ Interface criada no NetBox
✅ Status = planned/staged
✅ Tags presentes: discovery:netops_netbox_sync, discovery:staged, approval:...
✅ Custom fields preenchidos: discovery_source, discovery_status, approval_id
✅ ApprovalRecord atualizado para applied_staged
✅ State history atualizado
✅ Relatório pós-apply gerado
✅ Comparação antes/depois gerada
✅ Token não exposto
✅ Nenhum outro objeto tocado

## 13. Critérios de Parada (Aborta)

Antes do POST:
- ❌ Nenhum NETBOX_WRITE_TOKEN
- ❌ approval_id divergente
- ❌ object_type ≠ interface
- ❌ method ≠ POST
- ❌ action ≠ safe_create_staged
- ❌ readiness_status ≠ ready
- ❌ Payload contém secret/token/password
- ❌ Objeto já existe no NetBox
- ❌ >1 objeto no ApplyPlan
- ❌ Validação preflight falha

Se POST falha:
- ❌ NetBox retorna 40x/50x
- ❌ Erro de conexão
- ❌ Token inválido (401)
- ❌ Payload inválido (422)

## 14. Próximas Fases

FASE 2.1 (Futuro):
- Batch apply (múltiplos objetos)
- Approval workflow integrado
- Rollback automático em erro

FASE 2.2 (Futuro):
- Scheduled apply (time-based)
- Dependency graph (ordering)
- Staged → active workflow

FASE 3.0 (Futuro):
- Configuration push (via N8N)
- Monitoring integration
- Compliance feedback loop

## 15. Segurança

✅ **Read-only agora:**
- Nenhuma escrita fora do escopo

✅ **Uma escrita:**
- Apenas 1 POST
- Apenas 1 objeto
- Nenhuma lote
- Nenhuma cascata

✅ **Auditoria:**
- approval_id registrado
- operator registrado
- timestamp registrado
- state_history atualizado
- Payload hash preservado

✅ **Rollback:**
- Hint: DELETE /api/dcim/interfaces/{id}/
- Manual apenas (sem automação)
- Requer confirmação

## Exemplo Completo

```bash
# 1. Gerar ApplyPlan (FASE 1.9)
python3 tools/local/build_staged_apply_plan.py \
  --approval reports/.../approvals/approved/approval-c9363dfb-*.json

# 2. Validar (FASE 1.9)
python3 tools/local/validate_staged_apply_plan.py \
  --plan reports/.../apply-plan-c9363dfb-*.json

# 3. Renderizar (FASE 1.9)
python3 tools/local/render_staged_apply_plan.py \
  --plan reports/.../apply-plan-c9363dfb-*.json

# 4. Simular (FASE 1.9)
python3 tools/local/simulate_staged_apply.py \
  --plan reports/.../apply-plan-c9363dfb-*.json

# 5. Dry-run (FASE 2.0)
python3 tools/local/apply_staged_netbox_object.py \
  --plan reports/.../apply-plan-c9363dfb-*.json \
  --netbox-url https://docs.k3gsolutions.com.br \
  --confirm-approval-id c9363dfb \
  --operator "seu-nome"

# 6. Real write (FASE 2.0, se autorizado)
NETBOX_WRITE_TOKEN="..." python3 tools/local/apply_staged_netbox_object.py \
  --plan reports/.../apply-plan-c9363dfb-*.json \
  --netbox-url https://docs.k3gsolutions.com.br \
  --confirm-approval-id c9363dfb \
  --operator "seu-nome" \
  --confirm-real-write

# 7. Validar pós-apply (read-only)
python3 tools/local/archive_compliance_report.py \
  --report <novo-relatório> \
  --device 4WNET-MNS-KTG-RX \
  --device-id 1890

python3 tools/local/compare_compliance_reports.py \
  --old <antes> \
  --new <depois> \
  --output <comparação>
```

## Referências

- [Staged Apply Design](./27-staged-apply-design.md)
- [Staged Apply Contract](./28-staged-apply-contract.md)
- [Approval State Management](./26-approval-state-management.md)
- [Staged Apply Dry-Run Engine](./29-staged-apply-dry-run-engine.md)
