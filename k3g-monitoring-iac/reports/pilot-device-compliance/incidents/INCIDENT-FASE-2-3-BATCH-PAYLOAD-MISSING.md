# INCIDENT — FASE 2.3 Batch Apply Payload Missing

**Status:** CRITICAL — FREEZE ACTIVE
**Date:** 2026-04-28T18:58:23Z
**Incident ID:** INC-2026-04-28-001
**Severity:** Critical
**Impact:** Objects created in wrong device

---

## Summary

Batch apply reported SUCCESS but created interfaces in wrong device with incomplete payloads.

**Expected Device:** 4WNET-MNS-KTG-RX (ID: 1890)
**Actual Device:** INFORR-BVA-JCL-RX (ID: 2647)

---

## Timeline

| Time | Event |
|------|-------|
| 18:58:23 | Batch apply executed with --confirm-real-write-batch |
| 18:58:23 | Script reported: "🟢 SUCCESS (all items created)" |
| 18:58:23 | Objects created: ID 18201, ID 18202 |
| Post-execution | Verification query revealed wrong device |

---

## What Was Supposed to Happen

**Batch ID:** 33423d0a-6b34-41c9-9549-46a7b359aab4
**Items:** 2

1. **Eth-Trunk1**
   - Device: 4WNET-MNS-KTG-RX (ID: 1890)
   - Type: interface
   - Payload: { device: 1890, name: "Eth-Trunk1", type: "1000base-t", ... }
   - Expected ID: (new, on device 1890)

2. **GigabitEthernet0/5/0**
   - Device: 4WNET-MNS-KTG-RX (ID: 1890)
   - Type: interface
   - Payload: { device: 1890, name: "GigabitEthernet0/5/0", type: "1000base-t", ... }
   - Expected ID: (new, on device 1890)

---

## What Actually Happened

Verification queries showed:

```bash
GET /api/dcim/interfaces/?device_id=1890&name=Eth-Trunk1
→ count=0 (NOT created on intended device)

GET /api/dcim/interfaces/?device_id=1890&name=GigabitEthernet0/5/0
→ count=0 (NOT created on intended device)

GET /api/dcim/interfaces/18201/
→ { id: 18201, name: "LoopBack100", device: 2647 }
   (Created on WRONG device: INFORR-BVA-JCL-RX)

GET /api/dcim/interfaces/18202/
→ { id: 18202, name: "NULL0", device: 2647 }
   (Created on WRONG device: INFORR-BVA-JCL-RX)
```

---

## Root Cause Analysis

### Primary Cause: Incomplete BatchApplyPlan Payload

Inspection of `batch-apply-plan.json`:

```json
{
  "batch_id": "33423d0a-...",
  "device": "4WNET-MNS-KTG-RX",
  "device_id": 1890,
  "total_items": 2,
  "items": [
    {
      "approval_id": "fb0a50b3-...",
      "object_key": "Eth-Trunk1",
      "object_type": "interface",
      "device_id": null,           // ← NULL (CRITICAL)
      "method": null,              // ← NULL (CRITICAL)
      "target_endpoint": null,     // ← NULL (CRITICAL)
      "staged_payload": null       // ← NULL (CRITICAL)
    },
    { ... similar for GigabitEthernet0/5/0 }
  ]
}
```

### Why Validation Failed

Script `validate_batch_staged_apply_plan.py`:
- ✗ Did NOT check for null device_id per item
- ✗ Did NOT check for null method per item
- ✗ Did NOT check for null target_endpoint per item
- ✗ Did NOT check for null staged_payload per item
- ✗ Did NOT validate payload.device matches batch.device_id
- ✗ Did NOT validate payload.name matches item.object_key

Result: Batch marked as "ready" despite incomplete payload.

### Why Apply Failed Silently

Script `apply_batch_staged_netbox_objects.py`:
- ✗ Did NOT validate payload before preflight
- ✗ Made POST request without payload data
- ✗ NetBox accepted POST with incomplete/null payload
- ✗ NetBox created default objects instead of named interfaces
- ✗ Created objects on unexpected device
- ✗ Script reported SUCCESS

---

## Evidence

### Batch Plan Status

File: `reports/pilot-device-compliance/approvals/approved/batch-apply-plan.json`

```
Batch ID: 33423d0a-6b34-41c9-9549-46a7b359aab4
Device: 4WNET-MNS-KTG-RX
Device ID: 1890
Total Items: 2

Item 1: Eth-Trunk1
  approval_id: fb0a50b3-...
  device_id: null ← SHOULD BE 1890
  method: null ← SHOULD BE POST
  target_endpoint: null ← SHOULD BE /api/dcim/interfaces/
  staged_payload: null ← SHOULD BE {...}

Item 2: GigabitEthernet0/5/0
  approval_id: d1dce466-...
  device_id: null ← SHOULD BE 1890
  method: null ← SHOULD BE POST
  target_endpoint: null ← SHOULD BE /api/dcim/interfaces/
  staged_payload: null ← SHOULD BE {...}
```

### Verification Queries

```bash
# Query 1: Search on intended device
curl "https://docs.k3gsolutions.com.br/api/dcim/interfaces/?device_id=1890&name=Eth-Trunk1"
→ count=0 ✗

# Query 2: Check created IDs
curl "https://docs.k3gsolutions.com.br/api/dcim/interfaces/18201/"
→ {
    "id": 18201,
    "name": "LoopBack100",
    "device": {
      "id": 2647,
      "display": "INFORR-BVA-JCL-RX"
    }
  } ✗ WRONG DEVICE
```

---

## Impact Assessment

### Created Objects (Wrong Device)

| ID | Name | Device (Expected) | Device (Actual) | Status |
|----|------|-------------------|-----------------|--------|
| 18201 | LoopBack100 | 4WNET-MNS-KTG-RX (1890) | INFORR-BVA-JCL-RX (2647) | ✗ WRONG |
| 18202 | NULL0 | 4WNET-MNS-KTG-RX (1890) | INFORR-BVA-JCL-RX (2647) | ✗ WRONG |

### Intended Objects (Not Created)

| Name | Device | Status |
|------|--------|--------|
| Eth-Trunk1 | 4WNET-MNS-KTG-RX (1890) | ✗ NOT CREATED |
| GigabitEthernet0/5/0 | 4WNET-MNS-KTG-RX (1890) | ✗ NOT CREATED |

### Systems Affected

- NetBox device 2647 (INFORR-BVA-JCL-RX): 2 unexpected objects created
- NetBox device 1890 (4WNET-MNS-KTG-RX): 0 intended objects created
- Pilot batch workflow: BLOCKED

---

## Immediate Actions (FREEZE)

**Freeze Status:** ACTIVE

- ❌ NO new batch applies until fix validated
- ❌ NO real write commands with --confirm-real-write-batch
- ❌ NO POST/PATCH/DELETE to NetBox
- ❌ NO /sync operations
- ❌ NO equipment configuration changes
- ✓ READ-ONLY queries only
- ✓ Local corrections and script fixes only

---

## Rollback Plan

### Manual Deletion Required

Objects created in wrong device must be deleted manually:

**Object 1: ID 18201 (LoopBack100)**
```bash
curl -X DELETE \
  "https://docs.k3gsolutions.com.br/api/dcim/interfaces/18201/" \
  -H "Authorization: Token $NETBOX_WRITE_TOKEN"
```

**Object 2: ID 18202 (NULL0)**
```bash
curl -X DELETE \
  "https://docs.k3gsolutions.com.br/api/dcim/interfaces/18202/" \
  -H "Authorization: Token $NETBOX_WRITE_TOKEN"
```

**Approval:** Pending manual review before execution
**Automation:** NOT used (safety-first)

---

## Corrective Actions

### 1. Fix `build_batch_staged_apply_plan.py`

**Validation Required:**
- [ ] Each item must embed complete ApplyPlan data
- [ ] Reject ApplyPlan without staged_payload
- [ ] Reject ApplyPlan without target_endpoint
- [ ] Reject ApplyPlan without method
- [ ] Reject ApplyPlan without device_id
- [ ] Validate payload.device == batch.device_id
- [ ] Validate payload.name == item.object_key
- [ ] Validate readiness_status == "ready"
- [ ] Validate write_policy.real_apply_enabled == false

### 2. Fix `validate_batch_staged_apply_plan.py`

**Gates Required:**
- [ ] Reject if item.device_id is null
- [ ] Reject if item.method is null
- [ ] Reject if item.target_endpoint is null
- [ ] Reject if item.staged_payload is null
- [ ] Reject if payload.device is null
- [ ] Reject if payload.name is null
- [ ] Reject if payload.device != batch.device_id
- [ ] Reject if payload.name != item.object_key
- [ ] Reject if method != "POST"
- [ ] Reject if target_endpoint != "/api/dcim/interfaces/"
- [ ] Add --expected-device-id flag
- [ ] Add --expected-device flag
- [ ] Add --allowed-object-keys flag

### 3. Fix `apply_batch_staged_netbox_objects.py`

**Pre-Preflight Validation:**
- [ ] Validate all mandatory fields on each item
- [ ] Abort if any item has null device_id
- [ ] Abort if any item has null method
- [ ] Abort if any item has null staged_payload
- [ ] Abort if payload.device != batch.device_id
- [ ] Abort if payload.name != item.object_key
- [ ] Log item.object_key, payload.name, payload.device, endpoint, method
- [ ] Never use fallback payload
- [ ] Never assume default values

### 4. Fix `render_batch_staged_apply_plan.py`

**Output Required:**
- [ ] Show approval_id per item
- [ ] Show apply_plan_id per item
- [ ] Show object_key per item
- [ ] Show payload.name per item
- [ ] Show device_id per item
- [ ] Show payload.device per item
- [ ] Show method per item
- [ ] Show endpoint per item
- [ ] Show payload_hash per item
- [ ] Show readiness_status per item
- [ ] Render as BLOCKED if payload missing

### 5. Add Tests

**Test Cases Required:**
- [ ] batch with item.device_id=null → validate fails
- [ ] batch with item.method=null → validate fails
- [ ] batch with item.target_endpoint=null → validate fails
- [ ] batch with staged_payload=null → validate fails
- [ ] batch with payload.device=2647, batch.device_id=1890 → validate fails
- [ ] batch with object_key="Eth-Trunk1", payload.name="LoopBack100" → validate fails
- [ ] batch with method="PATCH" → validate fails
- [ ] batch with endpoint="/api/dcim/devices/" → validate fails
- [ ] batch apply with incomplete payload → no POST executed
- [ ] valid batch with correct device/name → all checks pass

### 6. Regenerate Batch Plan

**Steps:**
1. Verify ApplyPlans have complete payloads:
   - apply-plan-fb0a50b3-20260428T173011.json
   - apply-plan-d1dce466-20260428T173011.json

2. Run build_batch_staged_apply_plan.py with fixed validation

3. Validate with validate_batch_staged_apply_plan.py

4. Render with render_batch_staged_apply_plan.py

5. Dry-run (no writes) with apply_batch_staged_netbox_objects.py

6. Deliver real-write command (prepared, not executed)

---

## Prevention

**Going Forward:**

- ✓ Batch plan must embed full ApplyPlan per item
- ✓ No null payloads or endpoints allowed
- ✓ Validation gates BLOCK incomplete batches
- ✓ Apply script validates AGAIN before any POST
- ✓ Logs show item.object_key, payload.name, device before POST
- ✓ Test coverage for payload validation
- ✓ Manual approval required for device_id verification

---

## Next Steps

1. **Immediate:** Implement fixes to all 4 scripts
2. **Immediate:** Add comprehensive test cases
3. **Immediate:** Regenerate batch plan with validation
4. **Review:** Manual inspection of corrected batch plan
5. **Approval:** User confirmation before any new batch apply
6. **Rollback:** Manual deletion of 18201/18202 (pending approval)
7. **Documentation:** Update CHANGELOG, runbooks, validation gates

---

## Status

| Item | Status |
|------|--------|
| Freeze | ✓ ACTIVE |
| New applies | ✓ BLOCKED |
| Rollback | ⏳ PENDING MANUAL APPROVAL |
| Script fixes | ⏳ IN PROGRESS |
| Test coverage | ⏳ IN PROGRESS |
| Batch regeneration | ⏳ PENDING |
| Real write | ⏳ BLOCKED UNTIL FIX APPROVED |

---

**Incident opened:** 2026-04-28T18:58:23Z
**Owner:** Claude Haiku 4.5
**Target Resolution:** 2026-04-28T19:30:00Z (estimated)
