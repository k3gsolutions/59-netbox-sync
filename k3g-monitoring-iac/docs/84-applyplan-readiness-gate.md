# FASE 2.39 — ApplyPlan Readiness Gate

## Overview

**FASE 2.39** validates that proposed ApprovalRecords are ready for ApplyPlan creation. This gate:

- ✅ Reads proposed ApprovalRecords from directory
- ✅ Validates readiness criteria (status, evidence, safety flags)
- ✅ Checks for secrets and structural integrity
- ✅ Generates decision: READY_FOR_APPROVAL_REVIEW or NOT_READY_FOR_APPLYPLAN
- ✅ **Does NOT create ApplyPlan** (validation only)
- ✅ Maintains zero NetBox writes, no tokens, no automatic actions

**No ApplyPlan creation.** Gate validates readiness; actual ApplyPlan creation is separate authorized step.

---

## Key Purpose

Gate answers: **"Can these proposed ApprovalRecords safely advance to ApplyPlan creation?"**

Decision criteria:
- ✅ All records have valid status (proposed/pending)
- ✅ All records have reviewer metadata
- ✅ All records have evidence hash
- ✅ All records have source evidence (draft or payload)
- ✅ No records have ApplyPlan already
- ✅ No secrets detected in payloads
- ✅ All records have required safety flags
- ✅ No structural corruption

---

## Gate Tool

**Script:** `tools/local/applyplan_readiness_gate.py`

**Usage:**
```bash
python3 tools/local/applyplan_readiness_gate.py \
  --device <device_name> \
  --device-id <int> \
  --approvals-dir path/to/proposed/approvals \
  --output path/to/APPLYPLAN-READINESS-GATE.md
```

**Required Arguments:**
- `--device` — Device name
- `--device-id` — NetBox device ID
- `--approvals-dir` — Directory containing proposed ApprovalRecords
- `--output` — Path to write readiness gate report

**Optional:**
- `--policy-baseline` — Reference policy file (informational)

---

## Validation Checks

For each ApprovalRecord in `--approvals-dir/approval-*.json`:

### 1. Status Validation
```
✓ status must be "proposed" or "pending"
✗ cannot be "approved" or "applied"
✗ cannot be empty
```
**Reason:** Gate validates ONLY records in pre-ApplyPlan state.

### 2. Reviewer Requirement
```
✓ reviewer field must not be empty
✗ null, empty string, or whitespace = INVALID
```
**Reason:** Every decision must be traceable to who approved it.

### 3. Evidence Hash
```
✓ evidence_hash field must be present
✗ empty or missing = INVALID
```
**Reason:** Ensures source draft/payload is integrity-verified.

### 4. Source Evidence
```
✓ Must have source_draft OR proposed_payload
✗ both missing = INVALID
```
**Reason:** Gate validates that ApprovalRecord references actual object data.

### 5. No Existing ApplyPlan
```
✓ apply_plan field must not be present (or empty)
✗ ApplyPlan already exists = INVALID
```
**Reason:** Records should not already have ApplyPlan (would indicate duplicate processing).

### 6. Secret Scanning
```
Blocked keywords: token, password, secret, netbox_write
✓ None found in proposed_payload
✗ Any found = INVALID
```
**Reason:** Extra safeguard prevents credentials in records.

### 7. Safety Flags
```
✓ safety.no_netbox_write = true
✓ safety.no_apply_plan_created = true
✗ Either missing = INVALID
```
**Reason:** Confirms record was created with safety policies enforced.

---

## Decision Logic

### Eligible ApprovalRecords
Pass ALL validation checks → Added to "eligible" list

### Not Eligible
Fail ANY validation check → Reason documented in report

### Final Decision

**READY_FOR_APPROVAL_REVIEW**
- At least ONE record is eligible
- Gate passes: `approved >= 1`

**NOT_READY_FOR_APPLYPLAN**
- Zero eligible records
- All records failed validation
- Gate fails: must fix violations before proceeding

---

## Output: Readiness Gate Report

File: `{output}` (typically `APPLYPLAN-READINESS-GATE.md`)

### Report Sections

1. **Decision** — READY_FOR_APPROVAL_REVIEW or NOT_READY_FOR_APPLYPLAN
2. **Summary** — Count of total, eligible, not eligible
3. **Eligible ApprovalRecords** — Table of records passing all checks
4. **Not Eligible** — Table of failed records with reasons
5. **Security Confirmations** — No NetBox writes, no ApplyPlan creation, no auto-approvals
6. **Next Phase** — Guidance based on decision

### Example Report (READY Decision)

```markdown
# Gate de Prontidão para ApplyPlan

**Device:** 4WNET-MNS-KTG-RX (ID: 1890)
**Data:** 2026-04-29T17:43:29.042157

## 1. Decisão

### READY_FOR_APPROVAL_REVIEW
2 ApprovalRecords ready for review

## 2. Resumo

- Total ApprovalRecords: 2
- Elegíveis para ApplyPlan: 2
- Não elegíveis: 0

## 3. ApprovalRecords Elegíveis

| Approval ID | Object Type | Object Key | Status |
|---|---|---|---|
| 877e6eb4-44fe-49d4-9cdc-ac6eee18d8bc | Interface | Eth-Trunk0 | proposed |
| 959189bf-5955-488d-a4f3-953f02945a0d | Interface | Eth-Trunk2 | proposed |

## 5. Segurança

✓ Nenhuma escrita NetBox
✓ Nenhum ApplyPlan criado
✓ Nenhum ApprovalRecord aprovado automaticamente

## 6. Próxima Fase

Se READY_FOR_APPROVAL_REVIEW:
- Review proposed ApprovalRecords
- Approval/rejection workflow (separate step)
- No automatic progression
```

---

## Workflow Integration

### Before Gate

1. FASE 2.38 promotion complete
2. Proposed ApprovalRecords in directory
3. All records have `status=proposed`

### Gate Validation

```bash
python3 tools/local/applyplan_readiness_gate.py \
  --device "4WNET-MNS-KTG-RX" \
  --device-id 1890 \
  --approvals-dir "reports/pilot-device-compliance/week2-review/promoted" \
  --output "reports/pilot-device-compliance/week2-review/APPLYPLAN-READINESS-GATE.md"
```

### Interpret Decision

**READY_FOR_APPROVAL_REVIEW:**
- Gate passes ✅
- Proposed ApprovalRecords are structurally valid
- Can proceed to approval/rejection workflow
- ApplyPlan creation can be authorized

**NOT_READY_FOR_APPLYPLAN:**
- Gate fails ❌
- Fix violations in ApprovalRecords
- Re-run gate validation
- Do not attempt ApplyPlan creation

---

## Security Guarantees

### ✅ What Gate Validates

- Structure integrity (all required fields present)
- No secrets in payloads
- Safety policies enforced (no_netbox_write, no_apply_plan_created)
- Audit metadata present (reviewer, timestamps)
- Evidence integrity (evidence_hash)

### ✅ What Gate Does NOT Do

- Create or modify ApprovalRecords
- Make NetBox API calls
- Generate ApplyPlan
- Auto-approve records
- Transition record status

### ⚠️ Important

Gate is **read-only validation**. Does not alter state. Safe to run multiple times.

---

## Troubleshooting

### "Invalid status: draft_review (must be proposed/pending)"
- ApprovalRecord still in draft status
- Run FASE 2.38 promotion first
- Or manually transition to `proposed` if needed

### "No reviewer"
- Reviewer field empty or missing
- Check ApprovalRecord JSON has reviewer name
- Re-create record if metadata incomplete

### "No evidence_hash"
- Evidence integrity field missing
- Record may be corrupted
- Check source draft file exists

### "Secrets detected in payload"
- Keywords (token, password, secret, netbox_write) found in payload
- Review payload for accidentally included credentials
- Remove secrets and re-create record

### "Missing safety flags"
- `safety.no_netbox_write` or `safety.no_apply_plan_created` missing
- Check ApprovalRecord safety section
- Verify FASE 2.38 tool created record correctly

### "No eligible ApprovalRecords found"
- All records failed validation
- Check gate report for specific reasons
- Fix violations one at a time
- Re-run gate to validate fixes

---

## Decision Flowchart

```
        ┌─────────────────────────────────┐
        │ ApplyPlan Readiness Gate        │
        └─────────────────────────────────┘
                        │
                        ↓
        ┌─────────────────────────────────┐
        │ Validate all ApprovalRecords:   │
        │ - status = proposed/pending     │
        │ - has reviewer                  │
        │ - has evidence_hash             │
        │ - has source evidence           │
        │ - no apply_plan                 │
        │ - no secrets                    │
        │ - has safety_flags              │
        └─────────────────────────────────┘
                        │
                ┌───────┴───────┐
                ↓               ↓
        ✅ >= 1 eligible    ❌ 0 eligible
                │               │
        ┌───────┘       ┌───────┘
        ↓               ↓
    READY_FOR_      NOT_READY_FOR_
    APPROVAL_       APPLYPLAN
    REVIEW
        │               │
        ↓               ↓
    Proceed to      Fix violations
    approval/       and rerun gate
    rejection
    workflow
```

---

## Example: Full Gate Run

```bash
# Setup
export DEVICE="4WNET-MNS-KTG-RX"
export DEVICE_ID="1890"
export REVIEW_DIR="reports/pilot-device-compliance/week2-review"
export PROMOTED_DIR="$REVIEW_DIR/promoted"

# Run gate
python3 tools/local/applyplan_readiness_gate.py \
  --device "$DEVICE" \
  --device-id "$DEVICE_ID" \
  --approvals-dir "$PROMOTED_DIR" \
  --output "$REVIEW_DIR/APPLYPLAN-READINESS-GATE.md"

# Check decision
grep "^### " "$REVIEW_DIR/APPLYPLAN-READINESS-GATE.md" | head -1

# If READY, check eligible records
grep "| approval-" "$REVIEW_DIR/APPLYPLAN-READINESS-GATE.md"

# If NOT_READY, check failures
grep "| " "$REVIEW_DIR/APPLYPLAN-READINESS-GATE.md" | grep -v "^| Arquivo" | tail -10
```

---

## Comparison: Gate Validation vs ApplyPlan Creation

| Aspect | Gate (FASE 2.39) | ApplyPlan (Next) |
|--------|------------------|-----------------|
| **What** | Validates readiness | Creates execution plan |
| **Writes** | None (read-only) | None (plan only) |
| **Modifies Records** | No | No |
| **Can be re-run** | Yes, safe | No (plan once) |
| **Requires authorization** | No | Yes |
| **Decision** | READY / NOT_READY | Plan created / failed |
| **Next step** | Approval workflow | Execution |

---

## Next Steps After Gate

### If READY_FOR_APPROVAL_REVIEW

1. Gate passes ✅
2. Proposed ApprovalRecords confirmed structurally valid
3. Proceed to manual approval/rejection workflow:
   - Review each proposed record
   - Approve (status → approved) or Reject (status → rejected)
   - Update audit trail with approval decision
4. Once approved, authorized user can request ApplyPlan creation

### If NOT_READY_FOR_APPLYPLAN

1. Gate fails ❌
2. Review gate report for specific violations
3. Fix ApprovalRecord issues:
   - Missing reviewer → Add reviewer name
   - Invalid status → Check promotion step
   - Secrets detected → Remove and re-create
   - Missing flags → Verify FASE 2.38 tool
4. Re-run gate validation (step 2 of workflow)
5. Repeat until READY

---

## Safety Philosophy

**Zero automation for approval decisions.** Gate validates structural readiness, but:

- ❌ Does NOT auto-approve records
- ❌ Does NOT auto-create ApplyPlan
- ❌ Does NOT transition statuses
- ❌ Does NOT make NetBox changes

Every progression requires explicit human action with full audit trail.
