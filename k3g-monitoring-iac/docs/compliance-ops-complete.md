# FASES COMPLIANCE-OPS-001–003: Operator Readiness & Execution

**Status:** COMPLETE  
**Purpose:** Pre-execution validation, runbook generation, final checklist  
**Safety:** No writes, no tokens, validation-only  

---

## COMPLIANCE-OPS-001: End-to-End Job Readiness Check

**Service:** `webui/services/compliance_ops_readiness.py`  
**Endpoint:** `GET /compliance/jobs/{job_id}/ops/readiness`  

### What It Does

Validates complete job artifact chain:
- All required artifacts exist (candidates → review → approval → applyplan → dryrun → realwrite)
- Gate decisions are READY or READY_WITH_RESTRICTIONS
- Execution package has execution_allowed=false
- Token required in next phase
- One-shot execution enabled
- Endpoint valid (not null, not root, no /sync)
- Payload contains no secrets (token/password/secret/cipher)
- Method is POST (no PATCH/DELETE)

### Decision Outcomes

- `COMPLIANCE_JOB_READY_FOR_MANUAL_REAL_WRITE` — All gates passed, no blockers
- `COMPLIANCE_JOB_READY_WITH_RESTRICTIONS` — Passed but warnings present
- `COMPLIANCE_JOB_NOT_READY` — Blockers found, cannot execute

### Artifact Output

```
reports/compliance/jobs/<job_id>/ops/
├── readiness-check.json
└── READINESS-CHECK.md
```

### Response

```json
{
  "success": true,
  "decision": "COMPLIANCE_JOB_READY_FOR_MANUAL_REAL_WRITE",
  "blocker_count": 0,
  "warning_count": 0,
  "artifacts": { ... },
  "validations": { ... },
  "gates": { ... },
  "payload_checks": { ... },
  "safety": {
    "netbox_write": false,
    "netbox_read": false,
    "device_connection": false,
    "validation_only": true
  }
}
```

---

## COMPLIANCE-OPS-002: Real-Write Operator Runbook

**Tool:** `tools/local/generate_compliance_realwrite_runbook.py`  
**Usage:** `python3 tools/local/generate_compliance_realwrite_runbook.py <job_id>`

### What It Generates

1. **Pre-Execution Checks**
   - Environment setup (source ~/.env.realwrite.local)
   - Token presence verification (no printing)
   - NetBox connectivity test

2. **Execution Package Review**
   - Execution phrase (copy-exact, case-sensitive)
   - Items summary (method, endpoint, payload)
   - Final safety checklist

3. **Execution Command**
   - Exact Python command with job_id, phrase, confirm flag
   - Token via environment variable (not printed)

4. **Post-Execution Steps**
   - POST /real-write/post-verification
   - POST /real-write/compliance-rerun
   - POST /real-write/closure

5. **Error Handling**
   - Failure response details
   - No automatic retry instruction
   - No automatic rollback
   - Escalation path

6. **Security Warnings**
   - Do not print token
   - Do not log token
   - Do not store in history
   - One-shot execution only

### Artifact Output

```
reports/compliance/jobs/<job_id>/ops/
└── REAL-WRITE-OPERATOR-RUNBOOK.md
```

---

## COMPLIANCE-OPS-003: Final Manual Execution Checklist

**Tool:** `tools/local/generate_compliance_final_checklist.py`  
**Usage:** `python3 tools/local/generate_compliance_final_checklist.py <job_id>`

### What It Contains

**Readiness & Package Section:**
- [ ] Readiness decision is READY
- [ ] Execution package validation VALID
- [ ] Final freeze READY_FOR_REAL_WRITE_PHASE

**Review Section:**
- [ ] Endpoint reviewed
- [ ] Payload reviewed (no secrets visible)
- [ ] Method is POST
- [ ] Item count correct
- [ ] No /sync endpoint

**Authorization Section:**
- [ ] Execution phrase extracted
- [ ] Phrase copied exactly
- [ ] Operator name recorded

**Environment Section:**
- [ ] NETBOX_WRITE_TOKEN loaded
- [ ] NETBOX_URL set and valid
- [ ] Token tested with GET /api/dcim/devices/
- [ ] Token NOT printed/logged

**Execution Understanding:**
- [ ] Operator knows ONE-SHOT only
- [ ] Operator knows NO RETRY
- [ ] Operator knows NO ROLLBACK
- [ ] Operator knows FAIL-FAST
- [ ] Escalation path understood

**Post-Execution Section:**
- [ ] Verification endpoint ready
- [ ] Compliance re-run endpoint ready
- [ ] Closure endpoint ready
- [ ] Knows where to check results

**Item Details:**
- Per-item review checklist

**Authorization Line:**
- Operator name, date/time, signature fields

### Artifact Output

```
reports/compliance/jobs/<job_id>/ops/
└── FINAL-MANUAL-EXECUTION-CHECKLIST.md
```

---

## Web UI Integration

Updated `/compliance/jobs/{job_id}`:

**New Section: "Prontidão Operacional"**
- Readiness decision (READY / READY_WITH_RESTRICTIONS / NOT_READY)
- Blocker count and warning count
- Link to readiness-check.md
- Link to runbook
- Link to checklist
- ⚠ Warning: "Real-write must be executed manually via CLI"
- NO execute button in UI

---

## Execution Flow

1. **Validate readiness:** `GET /compliance/jobs/{job_id}/ops/readiness`
   - All gates must pass
   - No blockers allowed

2. **Generate runbook:** `python3 generate_compliance_realwrite_runbook.py {job_id}`
   - Creates REAL-WRITE-OPERATOR-RUNBOOK.md
   - Operator reviews and follows steps

3. **Print checklist:** `python3 generate_compliance_final_checklist.py {job_id}`
   - Creates FINAL-MANUAL-EXECUTION-CHECKLIST.md
   - Operator completes all checkboxes

4. **Execute CLI tool:** `python3 compliance_execute_realwrite_once.py {job_id} "{phrase}" true`
   - One-shot execution (no retry)
   - Token from env only
   - Fail-fast on error

5. **Post-execution verification:**
   - POST /real-write/post-verification
   - POST /real-write/compliance-rerun
   - POST /real-write/closure

---

## Tests

**test_compliance_ops_readiness.py** (10 tests)
- Requires job
- Blocks missing freeze
- Blocks execution_allowed != false
- Blocks endpoint null
- Blocks endpoint root
- Blocks secret keywords in payload
- Blocks /sync endpoint
- Accepts ready job
- Writes artifacts to file
- No NetBox access

---

## Safety Guarantees

✓ No NetBox writes  
✓ No NetBox reads  
✓ No device connections  
✓ No SSH/SNMP/NETCONF  
✓ No tokens in output  
✓ No tokens in logs  
✓ Validation-only  
✓ Manual execution required  
✓ CLI tool only (not Web UI)  

---

## Summary

Three services create a comprehensive pre-execution safety framework:
1. **Readiness check** validates all artifacts and gates
2. **Runbook generator** provides step-by-step execution guide
3. **Final checklist** ensures operator awareness and authorization

All three are non-destructive, validation-only operations with zero NetBox access or token exposure.

Execution must be performed manually via CLI tool with explicit phrase confirmation and operator acknowledgment.
