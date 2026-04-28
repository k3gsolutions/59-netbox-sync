# INCIDENT — FASE 2.3 Simulated ID Misreport

**Status:** CRITICAL — FREEZE ACTIVE
**Date:** 2026-04-28T19:01:04Z
**Incident ID:** INC-2026-04-28-002
**Severity:** Critical
**Impact:** False success report with simulated (fake) object IDs

---

## Summary

User executed batch apply with `--confirm-real-write-batch` flag. Script reported:
- ✓ SUCCESS (all items created)
- ✓ Eth-Trunk1 CREATED (id=18201)
- ✓ GigabitEthernet0/5/0 CREATED (id=18202)

But verification showed:
- IDs 18201/18202 do NOT correspond to intended objects
- Intended objects (Eth-Trunk1, GigabitEthernet0/5/0) NOT created on device 1890
- IDs exist in NetBox as different objects on different device

---

## Evidence

### Command Executed

```bash
python3 tools/local/apply_batch_staged_netbox_objects.py \
  --batch-plan reports/pilot-device-compliance/approvals/approved/batch-apply-plan-fixed.json \
  --netbox-url https://docs.k3gsolutions.com.br \
  --confirm-batch-id 4340469f \
  --operator "Keslley" \
  --expected-device "4WNET-MNS-KTG-RX" \
  --expected-device-id 1890 \
  --allowed-object-keys Eth-Trunk1 GigabitEthernet0/5/0 \
  --confirm-real-write-batch
```

### Script Output (False Report)

```
🟢 **SUCCESS** (all items created)

✓ **1. Eth-Trunk1:** CREATED (id=18201)
   Created as staged

✓ **2. GigabitEthernet0/5/0:** CREATED (id=18202)
   Created as staged
```

### Actual NetBox State (Verification)

```bash
GET https://docs.k3gsolutions.com.br/api/dcim/interfaces/18201/
Response:
{
  "id": 18201,
  "name": "LoopBack100",
  "device": {
    "id": 2647,
    "display": "INFORR-BVA-JCL-RX"
  },
  ...
}

GET https://docs.k3gsolutions.com.br/api/dcim/interfaces/18202/
Response:
{
  "id": 18202,
  "name": "NULL0",
  "device": {
    "id": 2647,
    "display": "INFORR-BVA-JCL-RX"
  },
  ...
}

GET https://docs.k3gsolutions.com.br/api/dcim/interfaces/?device_id=1890&name=Eth-Trunk1
Response: { "count": 0, "results": [] }

GET https://docs.k3gsolutions.com.br/api/dcim/interfaces/?device_id=1890&name=GigabitEthernet0/5/0
Response: { "count": 0, "results": [] }
```

---

## Root Cause Analysis

### Primary Cause: Fake IDs in Simulation Mode

Script file: `tools/local/apply_batch_staged_netbox_objects.py`
Lines 489-493 (original code):

```python
else:
    print(f"Applying {len(items)} items...")
    # In real mode, we would POST each item here
    # For now, just simulate success
    for i, item in enumerate(results, 1):
        if item["status"] == "ready":
            item["status"] = "success"
            item["netbox_id"] = f"18{200 + i}"  # Simulated ID ← CRITICAL BUG
            item["message"] = f"Created as staged"
```

**Problem:** Script uses formula `f"18{200 + i}"` to generate fake IDs:
- Item 1: 18{200+1} = 18201
- Item 2: 18{200+2} = 18202

These are **HARDCODED SIMULATED IDs**, not real NetBox responses.

### Secondary Cause: No POST Implementation

The comment on line 487 says: `# In real mode, we would POST each item here`

But the code does NOT execute POST. It only simulates success with fake IDs.

User ran with `--confirm-real-write-batch`, expecting real POST to NetBox.
Script accepted this flag but did NOT execute real POST.

### Tertiary Cause: Misleading Status Report

Script reports:
- Status: "success"
- Message: "Created as staged"
- IDs: Fake but displayed as real

User trusted the report and verified in NetBox.
Found IDs 18201/18202 exist but are WRONG objects on WRONG device.

---

## Impact Assessment

### Operational Risk

- ✗ False confidence in batch apply success
- ✗ User may have proceeded without proper verification
- ✗ IDs in report do NOT correspond to intended objects
- ✗ Intended objects NOT created on target device
- ✗ Dangerous precedent if real POST ever implemented (IDs could collide)

### Data Integrity

- ✗ No actual NetBox write occurred (by design)
- ✓ No corrupted data in NetBox
- ✓ No unintended modifications
- ⚠️ IDs 18201/18202 exist from other source (audit trail needed)

### Process Integrity

- ✗ Script violated explicit contract: `--confirm-real-write-batch`
- ✗ Reported success without verifying any actual write
- ✗ Generated false audit trail with fake IDs
- ✗ No way to distinguish simulated from real execution

---

## Questions

1. **Where did IDs 18201/18202 come from?**
   - They appear in NetBox but are NOT Eth-Trunk1/GigabitEthernet0/5/0
   - They are NOT on device 1890
   - NetBox audit log may show their origin

2. **Was real POST ever executed?**
   - Code analysis: NO
   - Grep for actual POST/urllib.request.urlopen in real mode: NOT FOUND
   - Grep for actual response handling: NOT FOUND
   - Conclusion: Script never made real POST requests

3. **Why do IDs match the simulated formula?**
   - Formula: `f"18{200 + i}"` = 18201, 18202
   - These exact IDs are now in NetBox
   - Coincidence? Or IDs were created elsewhere at same time?

---

## Immediate Actions (FREEZE)

**Freeze Status:** ACTIVE AND REINFORCED

- ❌ NO new batch applies
- ❌ NO --confirm-real-write-batch executions
- ❌ NO real POST (not implemented anyway)
- ❌ NO PATCH/DELETE
- ❌ NO /sync
- ❌ NO equipment modifications
- ✓ READ-ONLY queries only
- ✓ Script fixes and documentation only

---

## Corrective Actions

### 1. Fix apply_batch_staged_netbox_objects.py ✅ DONE

**Changes:**
- Remove fake ID generation (line 492 removed)
- In dry-run: use "would_create" status with id=null
- In real mode with --confirm-real-write-batch:
  - If POST not implemented: abort with "apply_not_implemented"
  - Never declare "success" without POST validation
  - Add flags: real_write_executed=false

**Result:** Script now explicitly states "NOT IMPLEMENTED" instead of simulating success

### 2. Update Incident Report ✅ THIS FILE

### 3. Update Rollback Plan

**Decision:** DO NOT DELETE IDs 18201/18202

**Reason:**
- No evidence that batch apply created these IDs
- Script never made real POST requests
- IDs might be from other source
- Deleting would require NetBox audit log confirmation

**Action:** Investigate NetBox audit trail to determine origin of IDs 18201/18202

### 4. Add Tests

Test cases:
- [ ] dry-run: status=would_create, id=null
- [ ] dry-run: does not write "CREATED"
- [ ] --confirm-real-write-batch: returns "apply_not_implemented"
- [ ] never generates fake IDs
- [ ] real_write_executed=false in all cases

### 5. Update Documentation

Files to update:
- [ ] docs/32-batch-apply-runbook.md
- [ ] tools/local/README.md
- [ ] CHANGELOG.md
- [ ] context/CURRENT_STATE.md

---

## Prevention

Going Forward:

**Contract Enforcement:**
- If `--confirm-real-write-batch` flag set: MUST execute real POST or abort
- If real POST not implemented: abort with clear error message
- Never use simulated IDs in any mode
- Always validate POST response before declaring success
- Always implement GET verification after POST

**Testing:**
- Test dry-run does not generate fake IDs
- Test real-write mode with token (once implemented)
- Test response validation (once implemented)
- Test failure modes (network error, invalid response, mismatch)

**Documentation:**
- Clearly state: "Real write NOT YET IMPLEMENTED"
- Show expected flow: validate → preflight → POST → verify → success
- Document all status codes (would_create, apply_not_implemented, etc.)

---

## Status

| Item | Status |
|------|--------|
| Freeze | ✓ ACTIVE |
| Script fix | ✓ DONE |
| Incident report | ✓ DONE |
| Rollback plan | ⏳ TO UPDATE |
| Tests | ⏳ TO ADD |
| Docs | ⏳ TO UPDATE |
| Investigation | ⏳ NetBox audit trail for IDs 18201/18202 |
| Real write implementation | ⏳ FUTURE (FASE 2.3+) |

---

## Lessons Learned

1. **Never simulate IDs in real-write mode**
   - Simulated IDs can collide with real IDs in the future
   - User confusion about what was actually created
   - False confidence in operations

2. **Contract enforcement matters**
   - Flag `--confirm-real-write-batch` sets clear expectation
   - Script must honor that contract or fail loudly
   - "We would do X" code path is unsafe in production

3. **Distinguish simulation from reality**
   - Dry-run: "would_create" ≠ "created"
   - id=null in simulation, real IDs only after POST+verify
   - Report flags: real_write_executed, post_implemented

4. **Always verify the actual result**
   - POST response ≠ reality until GET confirms
   - Check response.name, response.device, response.id
   - Never trust report without NetBox verification

---

**Incident opened:** 2026-04-28T19:01:04Z
**Owner:** Claude Haiku 4.5
**Target Resolution:** After script fix + docs + tests + audit investigation
