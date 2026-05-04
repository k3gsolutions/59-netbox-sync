# FASES COMPLIANCE-REALWRITE-001–010: Complete Real-Write Workflow

**Status:** COMPLETE  
**Total phases:** 10  
**Total services:** 2 (compliance_realwrite_execution.py, compliance_realwrite_postwrite.py, compliance_realwrite_closure.py)  
**Total routes:** 9  
**Total tests:** 51 test cases  
**Lines of code:** ~1200  

---

## Overview

Complete governed workflow for NetBox configuration changes:

1. **Pre-execution (REALWRITE-001–007):** Authorization gates, dry-run validation, token-only execution
2. **Post-execution (REALWRITE-008–010):** Verification, compliance check, closure

**Key principle:** Local decisions only until execution moment. Token in environment only. One-shot execution. No automatic rollback.

---

## Architecture

### Phase 1: Authorization (REALWRITE-001–006)

| Phase | What | Where |
|-------|------|-------|
| 001 | Readiness gate | After dry-run PASSED |
| 002 | Authorization package | Generate required phrase |
| 003 | Final preflight | Operator validates phrase |
| 004 | Execution package | execution_allowed=false lock |
| 005 | Package validation | Safety checks |
| 006 | Final freeze | No more gates until token provided |

**Output:** execution-package.json with execution_allowed=false

### Phase 2: Execution (REALWRITE-007)

| Phase | What | Mode |
|-------|------|------|
| 007 | Real-write execution | CLI tool (one-shot) |

**Key:** Token from NETBOX_WRITE_TOKEN env var. Never logged or saved.

**Output:** real-write-execution-result.json (no token stored)

### Phase 3: Post-Write (REALWRITE-008–010)

| Phase | What | Gates |
|-------|------|-------|
| 008 | Verification | Objects created? |
| 009 | Compliance re-run | Local policy compliant? |
| 010 | Closure | Consolidate evidence, close |

**Output:** closure-package.json with final decision

---

## Directory Structure

```
reports/compliance/jobs/<job_id>/real-write/
├── real-write-readiness-gate.json
├── authorization/
│   ├── authorization-request.json
│   ├── REAL-WRITE-AUTHORIZATION-PACKAGE.md
│   ├── final-preflight-gate.json
│   └── FINAL-PREFLIGHT-GATE.md (optional)
├── execution/
│   ├── execution-package.json
│   ├── REAL-WRITE-EXECUTION-PACKAGE.md
│   ├── execution-package-validation.json
│   ├── final-no-write-freeze.json
│   ├── real-write-execution-result.json (from CLI)
│   └── REAL-WRITE-EXECUTION-RESULT.md
├── verification/
│   ├── post-write-verification.json
│   └── POST-WRITE-VERIFICATION.md
├── compliance-rerun/
│   ├── post-write-compliance-rerun.json
│   └── POST-WRITE-COMPLIANCE-RERUN.md
└── closure/
    ├── closure-package.json
    └── CLOSURE-PACKAGE.md
```

---

## HTTP Endpoints

### Authorization Phase

**POST** `/compliance/jobs/{job_id}/real-write/readiness-gate`
- Check dry-run passed
- Return: decision (REAL_WRITE_READINESS_READY)

**POST** `/compliance/jobs/{job_id}/real-write/authorization-package`
- Generate required_phrase (AUTORIZO_PRE_FLIGHT_ESCRITA_REAL_{job_id}_{auth_id})
- Return: authorization_id, required_phrase

**POST** `/compliance/jobs/{job_id}/real-write/final-preflight`
- Validate authorization_phrase (exact case-sensitive match)
- Return: decision (FINAL_PREFLIGHT_READY)

**POST** `/compliance/jobs/{job_id}/real-write/execution-package`
- Build execution package (execution_allowed=false lock)
- Return: execution_phrase (EXECUTAR_ESCRITA_REAL_{job_id}_{exec_id})

**GET** `/compliance/jobs/{job_id}/real-write/execution-package/validation`
- Validate execution_allowed=false, token_required=true, no_retry=true
- Return: decision (EXECUTION_PACKAGE_VALID)

**POST** `/compliance/jobs/{job_id}/real-write/freeze`
- Final gate before execution
- Return: decision (READY_FOR_REAL_WRITE_PHASE)

### Execution Phase

**CLI Tool:** `tools/local/compliance_execute_realwrite_once.py`
- Args: job_id, execution_phrase, confirm (true)
- Env: NETBOX_WRITE_TOKEN, NETBOX_URL
- Output: real-write-execution-result.json

### Post-Execution Phase

**POST** `/compliance/jobs/{job_id}/real-write/post-verification`
- Validate objects created (check response_id)
- Return: decision (POSTWRITE_VERIFICATION_PASSED | POSTWRITE_VERIFICATION_FAILED)

**POST** `/compliance/jobs/{job_id}/real-write/compliance-rerun`
- Local policy compliance check
- Return: decision (COMPLIANCE_RERUN_PASSED | COMPLIANCE_RERUN_PARTIAL_FAILED)

**POST** `/compliance/jobs/{job_id}/real-write/closure`
- Consolidate evidence, generate final decision
- Return: decision (COMPLIANCE_JOB_CLOSED_SUCCESS | CLOSED_WITH_WARNINGS | CLOSED_NOT_APPLICABLE | CLOSED_ACTION_REQUIRED)

---

## Safety Guarantees

### Authorization Phase (001–006)
✓ No NetBox writes  
✓ No NetBox reads  
✓ No SSH/SNMP/NETCONF  
✓ No device connections  
✓ No token used  
✓ No automatic execution  

### Execution Phase (007)
✓ Token in environment only (never logged)  
✓ One-shot execution (no retry)  
✓ Fail-fast (stop on first error)  
✓ No automatic rollback  

### Post-Execution Phase (008–010)
✓ No NetBox writes  
✓ No SSH/SNMP/NETCONF  
✓ No device connections  
✓ Verification and closure only  

---

## Closure Decisions

| Decision | Meaning | Next Step |
|----------|---------|-----------|
| `CLOSED_SUCCESS` | All gates passed | Job complete, remediation verified |
| `CLOSED_WITH_WARNINGS` | Write succeeded but verification/compliance partial | Review warnings, may need manual action |
| `CLOSED_NOT_APPLICABLE` | No items executed | Job complete but no changes made |
| `CLOSED_ACTION_REQUIRED` | Write failed or pre-write gates failed | Manual intervention required |

---

## Key Design Decisions

1. **Phrase-based authorization:** Human-readable, case-sensitive, prevents accidental execution
2. **Execution_allowed safety lock:** Set to false in pre-execution packages, never modified
3. **Token environment-only:** Never written to file, never logged
4. **One-shot execution:** No retry on failure, fail-fast behavior
5. **Local decisions:** No external calls until execution moment
6. **Immutable closure:** Job state is final, no rollback

---

## Testing

**Test files:**
- test_compliance_realwrite_postwrite.py (12 tests)
- test_compliance_realwrite_closure.py (9 tests)

**Total REALWRITE tests:** 51 test cases (including authorization and execution phases)

**Coverage:** All decision paths, all safety gates, all artifacts

---

## Execution Flow Diagram

```
DRYRUN phase complete
        ↓
[001] Readiness gate
        ↓
[002] Authorization package (generate phrase)
        ↓
[003] Final preflight (operator validates phrase)
        ↓
[004] Execution package (execution_allowed=false)
        ↓
[005] Package validation
        ↓
[006] Final freeze
        ↓
[007] CLI tool: Real-write execution (one-shot, token env-only)
        ↓
[008] Post-verification (objects created?)
        ↓
[009] Compliance re-run (local policy check)
        ↓
[010] Closure (consolidate evidence, generate final decision)
        ↓
Job closed (success / warnings / not applicable / action required)
```

---

## Summary

Complete end-to-end workflow from findings review through real-write execution to final closure. All phases are governed, local-first, and safety-locked. Token handling is environment-only with zero exposure. Job state is immutable after closure.

See individual phase documentation for details:
- compliance-realwrite-post-verification.md
- compliance-realwrite-compliance-rerun.md
- compliance-realwrite-closure.md
