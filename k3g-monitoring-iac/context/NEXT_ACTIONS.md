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

## FASE 1.7.1 — `/compliance/approve` HTTP Endpoint

### Objective
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

## FASE 2.0 — Staged Import Execution

### Task
Implementar staged import real com token write separado.

**Scope (FUTURE):**
- POST /compliance/apply
- Accept list of approval_ids
- Call NetBox API with write token
- Track status em ApprovalRecord.future_staging.applied_at
- Move ApprovalRecord a approvals/applied/ após sucesso
- Rollback mechanism se import falhar

**Security:**
- Token write separado, nunca em code
- Cada import auditado com timestamp
- Nunca delete, apenas create/update
- Dry-run obrigatório antes (FASE 1.5 already done)

---

## Checklist: Ready for FASE 1.7

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
