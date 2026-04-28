# Controlled Batch Staged Apply

## 1. Princípio

Batch apply **não é sincronismo automático**.

É execução controlada de múltiplos staged applies já aprovados individualmente.

Cada item precisa ter:
- ApprovalRecord próprio
- status = dry_run_passed
- ApplyPlan validado
- tags existentes (preflight)
- objeto não existente (preflight)
- auditoria individual

## 2. Escopo Permitido

**Object Type:**
- interface

**Category:**
- base_inventory

**Action:**
- safe_create_staged

**Status:**
- dry_run_passed

**Confidence:**
- exact
- normalized

**Método:**
- POST

**Endpoint:**
- /api/dcim/interfaces/

**Limite inicial:**
- máximo 3 objetos por lote

## 3. Escopo Proibido

- service candidates
- subinterfaces de serviço (.1580, etc)
- IP addresses
- VRFs
- VLANs
- BGP peers
- circuits
- L2VPN
- route policies
- prefix/community/as-path
- PATCH
- DELETE
- /sync
- aplicação em equipamento

## 4. Política de Lote

### Preflight: All-or-None

Se **qualquer item** falhar no preflight:
- nenhum POST executado
- gerar relatório batch_blocked
- documentar motivo

### Execução: Item-by-Item

Se todos passarem no preflight:
- aplicar item 1
- se sucesso (201), continuar
- se falha (4xx/5xx), parar lote
- registrar partial_failure
- não tentar rollback automático nesta fase
- não continuar após falha

## 5. Gates por Item

Cada item **antes do POST** deve validar:

**Estrutura:**
- ✅ approval_id presente
- ✅ ApprovalRecord status = dry_run_passed
- ✅ ApplyPlan readiness_status = ready
- ✅ object_type = interface
- ✅ category = base_inventory
- ✅ action = safe_create_staged
- ✅ method = POST
- ✅ target_endpoint = /api/dcim/interfaces/

**Segurança:**
- ✅ payload sem secrets (password, token, secret, api_key, ssh)
- ✅ operator informado
- ✅ approval_id confirmado (--confirm-batch-id)
- ✅ token write via NETBOX_WRITE_TOKEN env var

**Existência:**
- ✅ tags existem no NetBox (GET /api/extras/tags/?name=<tag>)
- ✅ objeto NÃO existe no NetBox (GET /api/dcim/interfaces/?device_id=X&name=Y)

## 6. Gates do Lote

O lote **antes de qualquer preflight** deve validar:

- ✅ tamanho total_items <= max_items (3)
- ✅ todos os approval_ids únicos
- ✅ todos os object_keys únicos
- ✅ todos os items são interface
- ✅ todos os category = base_inventory
- ✅ nenhum service candidate
- ✅ nenhum item blocked/needs_review/ignore
- ✅ nenhum PATCH/DELETE
- ✅ token não aparece em output
- ✅ dry-run batch passou antes de real write

## 7. Estados do Lote

```
batch_planned
  ↓
batch_preflight_passed
  ↓
batch_apply_started
  ├→ batch_applied (sucesso total)
  ├→ batch_partial_failed (falha no POST)
  └→ batch_blocked (gate falhou)
```

## 8. Relatórios

Gerar automaticamente:

- `batch-plan.json` — BatchApplyPlan estruturado
- `batch-preflight.md` — resultado dos gates
- `batch-apply-result.md` — resultado final (sucesso/partial/bloqueado)
- `batch-summary.md` — resumo executivo

## 9. Critério de Sucesso

- ✅ até 3 interfaces base_inventory criadas
- ✅ cada uma com NetBox object ID (201 Created)
- ✅ nenhum PATCH
- ✅ nenhum DELETE
- ✅ nenhum /sync
- ✅ nenhuma configuração em equipamento
- ✅ compliance pós-apply gerado
- ✅ comparação antes/depois gerada
- ✅ tags verificadas antes do POST
- ✅ all-or-none preflight passou

## 10. Critério de Parada (Bloqueia)

Antes de qualquer POST:
- ❌ tag ausente → TAG_MISSING
- ❌ objeto já existe → OBJECT_ALREADY_EXISTS
- ❌ payload inválido → PAYLOAD_INVALID
- ❌ token ausente → TOKEN_MISSING
- ❌ approval inválido → APPROVAL_INVALID
- ❌ method ≠ POST → METHOD_NOT_POST
- ❌ endpoint inesperado → ENDPOINT_MISMATCH
- ❌ item não-base_inventory → NOT_BASE_INVENTORY
- ❌ >3 objetos → BATCH_SIZE_EXCEEDED
- ❌ approval duplicado → APPROVAL_DUPLICATE
- ❌ object_key duplicado → OBJECT_KEY_DUPLICATE
- ❌ categoria ≠ base_inventory → CATEGORY_NOT_BASE_INVENTORY
- ❌ action ≠ safe_create_staged → ACTION_NOT_SAFE_CREATE
- ❌ readiness_status ≠ ready → READINESS_NOT_READY
- ❌ status ≠ dry_run_passed → STATUS_NOT_DRY_RUN_PASSED

Durante POST:
- ❌ NetBox retorna 4xx/5xx → NETBOX_ERROR
- ❌ erro de conexão → CONNECTION_ERROR
- ❌ token inválido (401) → AUTH_ERROR

## 11. Fora de Escopo FASE 2.2

- ❌ rollback automático
- ❌ apply em lote grande (>3)
- ❌ service candidates
- ❌ updates/deletes
- ❌ UI
- ❌ RBAC
- ❌ aplicação em equipamento
- ❌ código de escrita real nesta fase

## 12. Referências

- [Staged Apply Design](./27-staged-apply-design.md)
- [First Staged NetBox Write](./30-first-staged-netbox-write.md)
- [Batch Apply Runbook](./32-batch-apply-runbook.md)
