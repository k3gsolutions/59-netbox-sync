# Humanized Compliance Validation UI

## Overview

Frontend redesign for compliance findings review, replacing technical jargon and prompt-based input with
human-readable labels, intuitive dropdowns, batch operations, and local artifact generation.

**No NetBox writes. No device connections. No /sync. Decisions stored locally only.**

---

## Label Mapping (Technical → Human)

| Technical | Human |
|-----------|-------|
| finding | pendência |
| severity: error | Crítico |
| severity: warning | Atenção |
| severity: blocker | Bloqueador |
| decision: needs_remediation | Precisa corrigir |
| decision: needs_more_evidence | Precisa investigar melhor |
| decision: false_positive | É falso positivo |
| decision: accepted | Aceito / Correto |
| decision: blocked | Bloquear avanço |
| decision: ignored_temporarily | Ignorar por enquanto |

---

## UI Components

### 1. Safety Notice (Sticky)

```
⚠️ Segurança: Esta validação não altera o NetBox e não acessa o equipamento.
Ela apenas salva sua avaliação para a próxima etapa.
```

Displayed at top of section, always visible.

### 2. Reviewer Input

Single global text input: "Seu nome" (Your name). Prefilled with "Keslley".
Used for all decisions in the batch.

### 3. Progress Bar

Visual progress bar showing validated findings vs. total.
Updates in real-time as user makes decisions.

Example: "10 de 105 pendências validadas"

### 4. Summary Cards

Seven cards showing:
- Total
- Validadas (reviewed)
- Pendentes (not yet reviewed)
- Precisam corrigir (needs_remediation)
- Precisam investigar (needs_more_evidence)
- Falsos positivos (false_positive)
- Bloqueadas (blocked)

### 5. Info Notices

Two information boxes:
1. Security notice (warning color)
2. "Somente itens marcados como 'Precisa corrigir' seguem para a próxima fase" (info color)

### 6. Presets (Collapsible)

Quick-action buttons that fill decisions for common patterns:

- "Marcar 'BGP fora do ar' como Precisa investigar"
- "Marcar 'Peer sem descrição' como Precisa corrigir"
- "Marcar 'Erro de leitura' como Falso positivo"
- "Marcar 'Regra rígida' como Ignorar por enquanto"

Each preset shows confirmation dialog before applying.

### 7. Filters

Filter buttons to show/hide findings by severity or type:

- Todas (all)
- Mais importantes (blocker, error)
- BGP (scope=bgp)
- Interfaces (scope=interface)
- Pode ser falso positivo (likely_parser_noise, likely_policy_too_strict)

Active filter highlighted.

### 8. Findings Table (Humanized)

**Columns:**
1. **Importância** — Color-coded severity badge (Bloqueador/Crítico/Atenção/Informativo)
2. **Equipamento** — Device name
3. **Objeto afetado** — Finding scope object (e.g., "172.28.1.74")
4. **Tipo** — Scope (bgp, interface, etc.)
5. **Pendência** — Human-readable title (from rule_id mapping)
6. **Explicação** — Recommendation text
7. **Decisão** — Dropdown select with humanized labels
8. **Observação** — Textarea for reason (required)
9. **Técnico** — Collapsible details (finding_id, rule_id, evidence)

**Human Titles** (from rule_id):
- bgp.peer.state.not_established → "Sessão BGP fora do ar"
- bgp.peer.description.required → "Peer BGP sem descrição"
- bgp.route_policy.missing → "Política BGP não encontrada"
- interface.description.invalid → "Interface com padrão fora do esperado"
- interface.state.mismatch → "Estado de interface inesperado"
- interface.naming.invalid → "Nome de interface fora do padrão"

### 9. Batch Actions

Two buttons:
- **Salvar todas as validações** — Submit all decisions via batch endpoint
- **Limpar alterações** — Reset all dropdowns/textareas with confirmation

Status message shows result after save.

---

## New Artifacts

### next-verification-input.json

Generated after batch save. Schema:

```json
{
  "job_id": "...",
  "status": "USER_VALIDATION_APPLIED",
  "validated_by": "Keslley",
  "validated_at": "2026-05-05T...",
  "summary": {
    "total_findings": 105,
    "validated": 10,
    "pending": 95,
    "accepted": 0,
    "false_positive": 0,
    "ignored_temporarily": 0,
    "needs_remediation": 5,
    "needs_more_evidence": 5,
    "blocked": 0
  },
  "next_phase_allowed": true,
  "next_phase": "remediation_draft_eligibility",
  "items_for_next_phase": ["CMP-001", "CMP-002", ...],
  "blocked_items": [],
  "pending_items": ["CMP-003", ...],
  "safety": {
    "netbox_write": false,
    "device_write": false,
    "sync_called": false,
    "approval_record_created": false,
    "apply_plan_created": false
  }
}
```

**Rules for next_phase_allowed:**
- No blocked items
- At least 1 needs_remediation
- All error/blocker findings reviewed
→ true if all pass, false otherwise

### NEXT-VERIFICATION-INPUT.md

Human-readable markdown version of above. Contains:
- Job ID
- Status
- Validation summary (counts)
- Next phase decision
- Safety block

---

## New Routes

### POST /compliance/jobs/{job_id}/findings/decisions/batch

Save multiple finding decisions in one call.

**Request:**
```json
{
  "reviewer": "Keslley",
  "decisions": [
    {
      "finding_id": "CMP-001",
      "decision": "needs_remediation",
      "reason": "Peer confirmado sem descrição. Deve ser padronizado."
    }
  ]
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Validações salvas com sucesso.",
  "saved_count": 5,
  "failed_count": 0,
  "next_phase_allowed": true,
  "next_phase": "remediation_draft_eligibility",
  "summary": {
    "total_findings": 105,
    "validadas": 5,
    "pendentes": 100,
    "aceitos": 0,
    "falsos_positivos": 0,
    "ignoradas": 0,
    "precisa_corrigir": 3,
    "precisa_investigar": 2,
    "bloqueadas": 0
  },
  "safety": { "netbox_write": false, ... }
}
```

**Error (400):**
```json
{
  "error": "reviewer obrigatório"
}
```

---

## JavaScript Logic

### updateValidationCounts()

Recalculates summary cards and progress bar based on current dropdowns.
Called on every decision/reason change and initial load.

### Filter Buttons

Show/hide finding rows based on severity, scope, or triage_bucket.

### Preset Buttons

Fill decision selects and reason textareas matching a pattern.
Shows confirmation before applying.

### Batch Save

1. Validate reviewer name (required)
2. Collect all {finding_id, decision, reason} tuples with non-empty decision + reason
3. POST to batch endpoint
4. On success: show ✓ message, reload page after 1.5s
5. On failure: show error alert

---

## Safety Guarantees

✓ No NetBox writes
✓ No device connections (SSH, SNMP, NETCONF)
✓ No /sync calls
✓ No ApprovalRecord creation
✓ No ApplyPlan creation
✓ All decisions stored locally in review/
✓ Token never logged or returned
✓ Safety block in all responses

---

## Testing

Three test suites:

1. **test_compliance_validation_humanized_ui.py** (12 tests)
   - Template contains humanized labels
   - No NetBox write buttons
   - Safety notice present
   - Filters, presets, batch buttons present

2. **test_compliance_findings_batch_decisions.py** (10 tests)
   - Batch save validates reviewer/reason
   - Creates finding-decisions.json
   - Creates audit files
   - Creates next-verification-input.json
   - Response contains humanized summary

3. **test_compliance_next_verification_input.py** (9 tests)
   - needs_remediation → items_for_next_phase
   - blocked → blocked_items
   - needs_more_evidence → pending_items
   - next_phase_allowed gates work correctly
   - Safety block present

All 31 tests passing.

---

## Implementation Files

| File | Status |
|------|--------|
| webui/services/compliance_findings_review.py | ✓ batch_save_decisions() + generate_next_verification_input() |
| webui/app.py | ✓ POST /findings/decisions/batch |
| webui/templates/compliance_job_detail.html | ✓ New "Validação das Pendências" section |
| tests/test_compliance_validation_humanized_ui.py | ✓ 12 tests |
| tests/test_compliance_findings_batch_decisions.py | ✓ 10 tests |
| tests/test_compliance_next_verification_input.py | ✓ 9 tests |

---

## Example Workflow

1. User sees "Validação das Pendências" tab after comparison
2. Enters name "Keslley" (or custom)
3. Reviews each finding:
   - Reads human-readable title
   - Sees explanation (recommendation)
   - Chooses decision from dropdown
   - Adds observation
4. Uses preset buttons to quickly fill similar findings
5. Uses filters to focus on specific types
6. Clicks "Salvar todas as validações"
7. System validates, saves decisions, generates next-verification-input.json
8. Page reloads, showing next-phase eligibility
9. Operator can now proceed to remediation draft generation

---

**Generated:** 2026-05-05
**Status:** Production ready
