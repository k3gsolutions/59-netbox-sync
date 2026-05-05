# Collection Readiness Recovery — Job fbdda0de527c

**Status:** COLLECTION_RECOVERY_BLOCKED_INCOMPLETE_JOB  
**Evaluated at:** 2026-05-04T18:35:00Z  
**Decision:** Cannot recover this job artifact directly

---

## Readiness Validation

### Required Artifacts for Collection

| Artifact | Status | Location |
|----------|--------|----------|
| job-request.json | ✗ Missing | reports/compliance/jobs/compliance-job-fbdda0de527c/ |
| selected-devices.json | ✗ Missing | reports/compliance/jobs/compliance-job-fbdda0de527c/ |
| eligibility-recheck.json | ✗ Missing | reports/compliance/jobs/compliance-job-fbdda0de527c/ |
| COMPLIANCE-JOB-START-GATE.md | ✗ Missing | reports/compliance/jobs/compliance-job-fbdda0de527c/ |
| collection-plan.json | ✗ Missing | reports/compliance/jobs/compliance-job-fbdda0de527c/ |
| collection-start-gate.json | ✗ Missing | reports/compliance/jobs/compliance-job-fbdda0de527c/ |
| parser-manifest.json | ✓ Present | reports/compliance/jobs/compliance-job-fbdda0de527c/collection-results/ |

### Device Information

Device in parser-manifest:
- ID: 1890
- Name: 4WNET-MNS-KTG-RX
- Profile: default-readonly
- Raw files: 0
- Parsed files: 0
- ready_for_parsing: false

**But:** No device detail available (selected-devices.json missing).

### SSH Credentials Check

| Variable | Status | Required |
|----------|--------|----------|
| COMPLIANCE_SSH_USERNAME | ✗ Missing from env | Yes |
| COMPLIANCE_SSH_PASSWORD | ✗ Missing from env | Yes |
| COMPLIANCE_SSH_PORT | - Optional | No |
| COMPLIANCE_SSH_TIMEOUT | - Optional | No |

---

## Why Job Cannot Be Recovered

Job fbdda0de527c is **severely incomplete**:
1. Missing metadata (job-request, device details, eligibility check)
2. Missing collection planning (collection-plan.json, collection-start-gate.json)
3. Missing SSH preflight (ssh-preflight.json)
4. Missing device selection context

To recover, would need to:
- Reconstruct all missing metadata
- Re-validate device eligibility
- Re-plan collection commands
- Re-execute preflight

**This is equivalent to creating a new job**, not recovering existing one.

---

## Path Forward

### Option A: Create New Clean Compliance Job

If SSH credentials available:
1. Query NetBox for device 4WNET-MNS-KTG-RX (id 1890)
2. Create new compliance job with full metadata
3. Execute fresh collection
4. Parser → Compare → Review workflow
5. Rebuild cycle-004 with new job items

Requires:
- COMPLIANCE_SSH_USERNAME
- COMPLIANCE_SSH_PASSWORD
- Device reachable on network

### Option B: Use Test Data (Tests Only)

Create fixtures for testing recovery workflow without network dependency.
**Cannot be used for operations or cycle-004 real-write.**

### Option C: Wait for Collection Data

If device collection data available elsewhere (manual SSH output, previous backups):
- Import raw output to collection-results/devices/1890/raw/
- Restart from FASE RECOVERY-006 (Parser Staging Refresh)

---

## Recommendation

**Create new compliance job** if SSH credentials available.

Current job fbdda0de527c is too incomplete for recovery. Creating fresh job provides:
- Full audit trail of new collection
- Clean metadata
- Proper device validation
- Reproducible workflow

---

## Safety

- ✓ No write attempted
- ✓ No fake data generation
- ✓ No applyplan creation
- ✓ No cycle-004 execution with incomplete data
