# Staged Apply Dry-Run Engine — FASE 1.9

Local generation, validation, and simulation of ApplyPlan. Zero API calls, zero NetBox writes.

## 1. Objetivo

Implementar engine local para preparar futura aplicação staged no NetBox.

- Ler ApprovalRecord em status dry_run_passed
- Gerar ApplyPlan com readiness checks
- Validar ApplyPlan contra 13 critérios
- Renderizar Markdown legível
- Simular resultado sem API

Tudo local. Zero API. Zero NetBox writes.

## 2. Scripts

### build_staged_apply_plan.py

Gera ApplyPlan a partir de ApprovalRecord.

```bash
python3 tools/local/build_staged_apply_plan.py \
  --approval reports/pilot-device-compliance/approvals/approved/<approval>.json \
  --output reports/pilot-device-compliance/approvals/approved/
```

**Entrada:**
- ApprovalRecord JSON com status=dry_run_passed

**Saída:**
- ApplyPlan JSON em approvals/approved/

**Validações:**
- status = dry_run_passed (obrigatório)
- action = safe_create_staged (obrigatório)
- object_type suportado (interface apenas em FASE 1.9)

**Readiness Checks (13 total):**
1. approval_id_present ✓
2. status_dry_run_passed ✓
3. action_safe_create_staged ✓
4. object_type_supported ✓
5. no_secrets_in_payload ✓
6. tags_staged_present ✓
7. tags_approval_present ✓
8. custom_fields_valid ✓
9. confidence_valid ✓
10. naming_follows_pattern ✓
11. object_not_exists (NOT_CHECKED — requer API)
12. write_policy_enforced ✓
13. write_token_not_provided ✓

**ApplyPlan JSON:**
```json
{
  "apply_plan_id": "uuid",
  "approval_id": "c9363dfb-...",
  "import_plan_id": "uuid",
  "device": "4WNET-MNS-KTG-RX",
  "device_id": 1890,
  "object_type": "interface",
  "object_key": "Eth-Trunk0",
  "action": "safe_create_staged",
  "category": "base_inventory",
  "confidence": "exact",
  "target_endpoint": "/api/dcim/interfaces/",
  "method": "POST",
  "staged_payload": {...},
  "payload_hash": "sha256:...",
  "readiness_status": "ready|blocked|simulated",
  "readiness_checks": [...],
  "blocked_reasons": [],
  "generated_at": "ISO8601",
  "write_policy": {
    "real_apply_enabled": false,
    "write_token_provided": false
  }
}
```

### validate_staged_apply_plan.py

Valida ApplyPlan contra requisitos.

```bash
python3 tools/local/validate_staged_apply_plan.py \
  --plan reports/pilot-device-compliance/approvals/approved/<approval_id>-apply-plan.json
```

**Validações:**
- Campos obrigatórios presentes
- real_apply_enabled = false
- write_token_provided = false
- action = safe_create_staged
- method = POST (nunca PATCH/DELETE)
- object_type suportado
- readiness_status válido
- Nenhum secret em payload
- 14+ checks presentes

**Exit Code:**
- 0: Válido
- 1: Inválido

### render_staged_apply_plan.py

Renderiza ApplyPlan em Markdown legível.

```bash
python3 tools/local/render_staged_apply_plan.py \
  --plan reports/pilot-device-compliance/approvals/approved/<approval_id>-apply-plan.json \
  --output reports/pilot-device-compliance/approvals/approved/<approval_id>-apply-plan.md
```

**Markdown Sections:**
1. Resumo (device, object, endpoint, method)
2. Readiness Status (🟢 READY / 🔴 BLOCKED)
3. Readiness Checks (passed, failed, warnings, not_checked)
4. Bloqueios (se houver)
5. Payload Sugerido (JSON)
6. Política de Escrita
7. Observações de Segurança

### simulate_staged_apply.py

Simula resultado de staged apply sem API.

```bash
python3 tools/local/simulate_staged_apply.py \
  --plan reports/pilot-device-compliance/approvals/approved/<approval_id>-apply-plan.json \
  --output reports/pilot-device-compliance/approvals/approved/<approval_id>-apply-simulation.md
```

**Simulação:**
- real_apply_executed = false
- Nenhuma API chamada
- Nenhum objeto criado

**Resultado Possível:**
- `would_create_staged`: pronto para criar (status 201)
- `would_fail_blocked`: bloqueado (status 400)

**Output Markdown:**
- Resultado simulado (🟢 WOULD CREATE STAGED)
- Resposta prevista (status 201, message)
- Estado futuro (approval_status → applied_staged)
- Rollback hint (DELETE /api/dcim/interfaces/{id}/)
- Observações de segurança

## 3. Fluxo Completo

```
1. ApprovalRecord com status=dry_run_passed
   ↓
2. build_staged_apply_plan.py
   └→ ApplyPlan JSON gerado (readiness_status=ready|blocked)
   ↓
3. validate_staged_apply_plan.py
   └→ Validação: exit code 0 (válido) / 1 (inválido)
   ↓
4. render_staged_apply_plan.py
   └→ Markdown com readiness checks
   ↓
5. simulate_staged_apply.py
   └→ Markdown com simulação (would_create_staged)
   ↓
6. FASE 2.0: Apply Real (futuro)
   └→ POST /api/dcim/interfaces/ com token write
   └→ Criar objeto com status=staged
   └→ Atualizar ApprovalRecord → applied_staged
```

## 4. Garantias (FASE 1.9)

✅ **Zero API:**
- Nenhuma chamada HTTP
- Nenhuma conexão com NetBox
- Apenas geração e validação local

✅ **Zero Writes:**
- Nenhuma escrita no NetBox
- Nenhuma alteração de equipamento
- Nenhuma configuração aplicada

✅ **Segurança:**
- Nenhuma credencial em payload
- Nenhum secret detectado
- Validação de forbidden patterns
- real_apply_enabled=false
- write_token_provided=false

✅ **Auditável:**
- ApplyPlan com apply_plan_id único
- state_history previsão inclusa
- Rollback hint documentado
- Evidence_hash preservado

## 5. Limitações (FASE 1.9)

❌ Nenhum POST real ao NetBox
❌ Nenhum endpoint HTTP /compliance/apply
❌ Nenhuma escrita no NetBox
❌ Nenhum token write
❌ Nenhuma alteração no equipamento
❌ Nenhuma UI
❌ Nenhuma autenticação
❌ object_not_exists check: NOT_CHECKED (requer API)

Tudo implementado em FASE 2.0.

## 6. Teste Manual: Piloto c9363dfb

Approval em status dry_run_passed.

### Passo 1: Gerar ApplyPlan

```bash
python3 tools/local/build_staged_apply_plan.py \
  --approval reports/pilot-device-compliance/approvals/approved/approval-4WNET-MNS-KTG-RX-c9363dfb-*.json
```

Resultado:
```
✓ ApplyPlan generated
  apply_plan_id: 8017f140-07a4-4401-bbed-42f7e705a6af
  readiness_status: ready
  ✓ All checks passed
```

### Passo 2: Validar ApplyPlan

```bash
python3 tools/local/validate_staged_apply_plan.py \
  --plan reports/pilot-device-compliance/approvals/approved/apply-plan-c9363dfb-*.json
```

Resultado:
```
✓ ApplyPlan is valid
  readiness_status: ready
  checks: 13 total
  passed: 12
```

### Passo 3: Renderizar Markdown

```bash
python3 tools/local/render_staged_apply_plan.py \
  --plan reports/pilot-device-compliance/approvals/approved/apply-plan-c9363dfb-*.json
```

Resultado: apply-plan-c9363dfb-*.md com seções:
- Resumo
- Readiness Status: 🟢 READY
- Readiness Checks: 12/13 PASSED
- Payload Sugerido
- Política de Escrita
- Observações de Segurança

### Passo 4: Simular Apply

```bash
python3 tools/local/simulate_staged_apply.py \
  --plan reports/pilot-device-compliance/approvals/approved/apply-plan-c9363dfb-*.json
```

Resultado: apply-simulation-c9363dfb-*.md
- 🟢 WOULD CREATE STAGED
- Status Code: 201
- Objeto seria criado com status=staged
- Rollback hint: DELETE /api/dcim/interfaces/{id}/

## 7. Confirmações Obrigatórias (FASE 1.9)

✅ Nenhuma API real chamada
✅ Nenhuma escrita NetBox
✅ Nenhum /sync
✅ Nenhum token write
✅ Nenhuma configuração aplicada
✅ netops_netbox_sync não alterado
✅ real_apply_enabled=false
✅ simulate only

## 8. Próximos Passos (FASE 2.0)

FASE 2.0 implementará:

**POST /compliance/apply endpoint**
- Aceita approve_plan_id
- Valida token write
- Chama POST /api/dcim/interfaces/
- Cria objeto com status=staged
- Atualiza ApprovalRecord → applied_staged
- Registra auditoria completa

**Guarantees:**
- Escrita é staged (nunca active)
- Nunca DELETE
- Nunca UPDATE de active
- Token write separado
- Auditoria completa
- Rollback hint disponível

## Referências

- [Staged Apply Design](./27-staged-apply-design.md)
- [Staged Apply Contract](./28-staged-apply-contract.md)
- [Approval State Management](./26-approval-state-management.md)
- [ApprovalRecord Schema](./24-approval-record-schema.md)
