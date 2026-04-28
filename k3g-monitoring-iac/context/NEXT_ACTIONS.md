# Next Actions — FASE 1.7+

## FASE 1.6 Complete ✅

**Piloto end-to-end testado:**
- ApprovalRecord generation com validação
- Markdown summary rendering com risk assessment
- Dry-run validation com schema checks
- Zero API calls, zero NetBox writes
- Item: Eth-Trunk0 (base_inventory, safe_create_staged, exact confidence)
- Resultado: Piloto PASSED, workflow confirmado

Arquivo: `reports/pilot-device-compliance/approvals/pending/PILOT-FASE-1-6-RESULT.md`

---

## FASE 1.7 Complete ✅

**Estado Management implementado:**
- Script manage_approval_state.py com 4 comandos
- State machine: proposed → approved/rejected/changes_requested
- File movement automático entre approvals/{pending,approved,rejected,changes_requested}/
- state_history imutável com audit trail (from/to/by/at/reason)
- Backup automático antes de cada save
- Validações rigorosas para approve (action, naming, confidence)
- Testes completos: approve, reject, request-changes, mark-dry-run-passed
- Documentação: docs/26-approval-state-management.md
- Piloto FASE 1.6 atualizado: c9363dfb em approved/ com status=dry_run_passed

---

## FASE 1.8 Complete ✅

**Staged Apply Design documentado:**
- docs/27-staged-apply-design.md (segurança, objetos permitidos, design futuro)
- docs/28-staged-apply-contract.md (contratos, schemas, exemplos)
- ApplyPlan schema definido
- StagedPayload format definido
- Error/blocking codes definidos
- Dry-run requirements claros
- Audit trail design

---

## FASE 1.9 — Staged Apply Dry-Run Engine

### Objective
Implementar engine local para gerar, validar e simular ApplyPlan.

### Scripts

**1. build_staged_apply_plan.py**
- Ler ApprovalRecord status=dry_run_passed
- Validar prerequisites
- Gerar ApplyPlan com readiness_checks
- Output: JSON

**2. validate_staged_apply_plan.py**
- Validar ApplyPlan
- 14 checks definidos
- Exit code: 0 (válido) | 1 (bloqueado)
- Output: validation result JSON

**3. render_staged_apply_plan.py**
- Renderizar ApplyPlan em Markdown
- Output: readable summary com bloqueios

**4. simulate_staged_apply.py**
- Simular resultado de apply
- Zero API calls
- Output: simulation result JSON + Markdown

### Testing

- Use pilot c9363dfb (dry_run_passed)
- Gerar ApplyPlan
- Validar
- Renderizar
- Simular
- Confirmar: zero API, zero writes, real_apply_enabled=false

---

## FASE 1.7.1 — `/compliance/approve` HTTP Endpoint

### Objective (Futuro, depois FASE 1.9)
Expor state management via HTTP endpoint para integração com UIs/workflows.

### Tasks

**1. Create `/compliance/approve` endpoint (netops_netbox_sync)**
- POST /compliance/approve
- Request body:
  ```json
  {
    "approval_id": "c9363dfb-...",
    "decision": "approve|reject|request_changes",
    "reviewed_by": "usuario@empresa.com",
    "comment": "..."
  }
  ```
- Response: ApprovalRecord com status atualizado
- Call manage_approval_state.py via subprocess
- No NetBox writes
- Return status (proposed → approved) e próximo passo

**2. Tests**
- POST /compliance/approve with valid approval_id → 200
- Move file to approved/ on decision=approve
- Return updated ApprovalRecord
- Validation: reject if approval_id not found, decision invalid
- Ensure state_history recorded correctly

**3. Security**
- No write tokens used
- No NetBox API calls
- Audit trail: reviewed_by + timestamp + comment
- Validate: approval_id format, decision enum

---

## FASE 1.7.1 — Batch Generation Script

### Task
Criar script para gerar ApprovalRecords em lote a partir de um ImportPlan.

```bash
python3 tools/local/batch_create_approvals.py \
  --import-plan reports/pilot-device-compliance/import-plan-4WNET-MNS-KTG-RX.json \
  --device 4WNET-MNS-KTG-RX \
  --device-id 1890 \
  --filter "category=base_inventory" \
  --output reports/pilot-device-compliance/approvals/pending/
```

- Parse ImportPlan (JSON ou Markdown)
- Generate ApprovalRecord para cada item matching filter
- Default filter: action=safe_create_staged
- Suportar inclusive opções de filtro por category, confidence, object_type
- Output: batch-<timestamp>.json com lista de approval_ids criados

---

## FASE 1.8 — CI Integration

### Task
Integrar geração de ApprovalRecords em pipeline.

**Trigger:**
- Após cada `/compliance/import-plan/report` bem-sucedido
- Gerar batch de ApprovalRecords (safe_create_staged items)
- Arquivar ImportPlan a reports/pilot-device-compliance/history/

**Artifacts:**
- approval-*.json files em approvals/pending/
- Notificação para revisor (email ou webhook)

---

## FASE 1.9 — Web UI (Basic)

### Task
Interface básica para revisão de approvals.

**Features:**
- GET /ui/approvals → lista approvals/pending/
- GET /ui/approvals/{id} → renderiza approval-summary.md
- POST /ui/approvals/{id}/approve → form submission
- POST /ui/approvals/{id}/reject → form submission

**Implementation:**
- Usar FastAPI + templates (Jinja2)
- No database (tudo em filesystem)
- Renderizar approval-summary.md como HTML
- Form com decision, comment fields

---

## FASE 2.0 Complete ✅

- Primeiro staged apply real executado no NetBox
- Approval ID: `c9363dfb`
- Objeto: `Eth-Trunk0`
- Método: `POST`
- Resultado: `201 Created`
- NetBox object ID: `18228`
- Escopo: 1 objeto
- Nenhum `PATCH`
- Nenhum `DELETE`
- Nenhum `/sync`
- Nenhuma configuração em equipamento
- Token não exposto
- Tags verificadas antes do `POST`
- Compliance pós-apply gerado
- Correção base/service aplicada no netops_netbox_sync
- Total de divergências pós-ajuste: 161
- Eth-Trunk0 não aparece mais como INTERFACE_MISSING_IN_NETBOX
- Eth-Trunk0 não aparece mais como DESCRIPTION_NON_COMPLIANT
- Eth-Trunk0 aparece apenas como INTERFACE_DESCRIPTION_MISMATCH (ação review)

## FASE 2.1 — Next Actions

- Documentar política de batch staged applies controlado para base_inventory
- Consolidar o fluxo completo Device → Compliance → ImportPlan → Approval → Dry-run → Staged Apply → Pós-Compliance
- Registrar lições aprendidas no `reports/pilot-device-compliance/README.md`
- Atualizar `docs/31-...` com estratégia de tag bootstrap e batch apply
- Definir política para múltiplos staged applies em lote controlado, ainda limitado a base_inventory

---

- [x] Workflow completo testado (FASE 1.6 pilot)
- [x] ApprovalRecord schema validado
- [x] Dry-run validation working
- [x] Zero secrets in records
- [x] Zero API calls
- [x] Documentation complete
- [ ] Implementar /compliance/approve
- [ ] Implementar batch_create_approvals.py
- [ ] Tests para /compliance/approve
- [ ] CI integration
- [ ] Web UI
- [ ] Staged import (FASE 2.0)

---

## Referências

- [Approval Workflow Design](../docs/23-approval-workflow-design.md)
- [ApprovalRecord Schema](../docs/24-approval-record-schema.md)
- [Approval Dry-Run](../docs/25-approval-dry-run.md)
- [Pilot Report](../reports/pilot-device-compliance/approvals/pending/PILOT-FASE-1-6-RESULT.md)
