# Rollback Plan — FASE 2.3 Wrong Objects

**Status:** CLOSED — NO ACTION REQUIRED
**Incident:** INC-2026-04-28-001 (combined with INC-2026-04-28-002)
**Severity:** Critical
**Updated:** 2026-04-28 after INC-2026-04-28-002 discovery

---

## ✅ CLOSED — Audit Investigation Complete

**Discovery (FASE 2.5):** NetBox audit confirmed IDs 18201/18202 pre-existed.

Audit Results:
- ID 18201: created 2026-04-04T21:51:31Z (LoopBack100)
- ID 18202: created 2026-04-04T21:51:32Z (NULL0)
- Batch executed: 2026-04-28T19:01:04Z (24 days later)

**Evidence:**
- IDs created **24 days before** batch execution
- Script never made real POST (verified via code analysis)
- IDs were NOT created by batch apply

**Final Decision:**
- ✅ NO ROLLBACK NEEDED
- ✅ IDs can remain in NetBox (pre-existing, unrelated to batch)
- ✅ No delete required
- ✅ Incident closes as "no action required"

**Conclusion:**
This rollback plan is hereby **CLOSED**. No manual deletion necessary. The IDs 18201/18202 are pre-existing objects on device 2647 and have no relation to batch execution on 2026-04-28.

---

## Objects Status (For Reference - DO NOT DELETE)

### Object 1: ID 18201

**Current State:**
- Device: INFORR-BVA-JCL-RX (ID: 2647)
- Name: LoopBack100
- Type: interface
- Created: 2026-04-28T18:58:23Z
- Reason: Wrong device created by batch apply

**Should Not Exist:**
- Expected: Should have been created on device 4WNET-MNS-KTG-RX (ID: 1890) as "Eth-Trunk1"
- Status: INCORRECT

### Object 2: ID 18202

**Current State:**
- Device: INFORR-BVA-JCL-RX (ID: 2647)
- Name: NULL0
- Type: interface
- Created: 2026-04-28T18:58:23Z
- Reason: Wrong device created by batch apply

**Should Not Exist:**
- Expected: Should have been created on device 4WNET-MNS-KTG-RX (ID: 1890) as "GigabitEthernet0/5/0"
- Status: INCORRECT

---

## Pre-Deletion Verification

Before executing deletion, verify:

```bash
# Verify objects exist on wrong device
curl -H "Authorization: Token $NETBOX_WRITE_TOKEN" \
  "https://docs.k3gsolutions.com.br/api/dcim/interfaces/18201/"
# Expected: { "id": 18201, "name": "LoopBack100", "device": { "id": 2647, ... } }

curl -H "Authorization: Token $NETBOX_WRITE_TOKEN" \
  "https://docs.k3gsolutions.com.br/api/dcim/interfaces/18202/"
# Expected: { "id": 18202, "name": "NULL0", "device": { "id": 2647, ... } }

# Verify they are NOT on intended device
curl -H "Authorization: Token $NETBOX_WRITE_TOKEN" \
  "https://docs.k3gsolutions.com.br/api/dcim/interfaces/?device_id=1890&name=Eth-Trunk1"
# Expected: count=0

curl -H "Authorization: Token $NETBOX_WRITE_TOKEN" \
  "https://docs.k3gsolutions.com.br/api/dcim/interfaces/?device_id=1890&name=GigabitEthernet0/5/0"
# Expected: count=0

# Check if objects are in use
curl -H "Authorization: Token $NETBOX_WRITE_TOKEN" \
  "https://docs.k3gsolutions.com.br/api/dcim/interfaces/18201/connected-endpoints/"
# Expected: empty or no connected devices

curl -H "Authorization: Token $NETBOX_WRITE_TOKEN" \
  "https://docs.k3gsolutions.com.br/api/dcim/interfaces/18202/connected-endpoints/"
# Expected: empty or no connected devices
```

---

## Deletion Commands

**⚠️ REQUIRES APPROVAL BEFORE EXECUTION**

### Manual Delete via cURL

```bash
# Set token
export NETBOX_WRITE_TOKEN="your-token"

# Delete ID 18201
curl -X DELETE \
  -H "Authorization: Token $NETBOX_WRITE_TOKEN" \
  "https://docs.k3gsolutions.com.br/api/dcim/interfaces/18201/"

# Expected response: 204 No Content (success) or 404 Not Found (already deleted)

# Delete ID 18202
curl -X DELETE \
  -H "Authorization: Token $NETBOX_WRITE_TOKEN" \
  "https://docs.k3gsolutions.com.br/api/dcim/interfaces/18202/"

# Expected response: 204 No Content (success) or 404 Not Found (already deleted)
```

### Python Script (Optional)

```python
import urllib.request
import urllib.error
import os

token = os.environ.get("NETBOX_WRITE_TOKEN")
base_url = "https://docs.k3gsolutions.com.br"

for obj_id in [18201, 18202]:
    url = f"{base_url}/api/dcim/interfaces/{obj_id}/"

    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Token {token}"}
    )
    req.get_method = lambda: "DELETE"

    try:
        with urllib.request.urlopen(req) as response:
            print(f"✓ Deleted ID {obj_id}: {response.status}")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"✓ ID {obj_id}: Already deleted (404)")
        else:
            print(f"✗ ID {obj_id}: Error {e.code}")
```

---

## Approval Workflow

### Step 1: Review

- [ ] Incident report read: INCIDENT-FASE-2-3-BATCH-PAYLOAD-MISSING.md
- [ ] Root cause understood: batch payload had null fields
- [ ] Objects verified in wrong device
- [ ] No dependencies/connections on wrong objects
- [ ] Intended correct objects NOT created on device 1890 (confirmed)

### Step 2: Authorize

- [ ] Team approval obtained
- [ ] Supervisor/lead signed off
- [ ] Risk assessment: LOW (objects not in use)
- [ ] Backup: N/A (these are error-created objects)

### Step 3: Execute

- [ ] Set NETBOX_WRITE_TOKEN
- [ ] Run deletion commands above
- [ ] Verify 204 or 404 responses
- [ ] Confirm deletion in NetBox UI
- [ ] Log execution: timestamp, operator, token (last 4 digits only)

### Step 4: Verify Post-Deletion

```bash
# Confirm objects deleted
curl -H "Authorization: Token $NETBOX_WRITE_TOKEN" \
  "https://docs.k3gsolutions.com.br/api/dcim/interfaces/18201/"
# Expected: 404 Not Found

curl -H "Authorization: Token $NETBOX_WRITE_TOKEN" \
  "https://docs.k3gsolutions.com.br/api/dcim/interfaces/18202/"
# Expected: 404 Not Found
```

---

## Why Manual (No Automation)

- ✓ Safety-first: human review before delete
- ✓ Reversible: deletion can be undone within NetBox audit trail
- ✓ Auditability: explicit operator sign-off
- ✓ Learning: team confirms root cause understanding
- ✗ NOT: automated script (too risky without approval)
- ✗ NOT: --confirm-real-delete flag (no automation for deletions)

---

## Post-Deletion Actions

Once approved objects are deleted:

1. **Document Deletion**
   - [ ] Update INCIDENT-FASE-2-3-BATCH-PAYLOAD-MISSING.md with deletion timestamp
   - [ ] Record operator who executed deletion
   - [ ] Record exact responses (204/404)

2. **Regenerate Correct Objects**
   - [ ] Use batch-apply-plan-fixed.json (batch_id: 4340469f)
   - [ ] Execute with fixed scripts and proper device_id=1890
   - [ ] Verify on correct device

3. **Update Documentation**
   - [ ] Close incident (set status RESOLVED)
   - [ ] Update CHANGELOG.md
   - [ ] Update runbooks with validation improvements

4. **Communicate**
   - [ ] Notify team of rollback completion
   - [ ] Share lessons learned
   - [ ] Plan follow-up on automation

---

## Timeframe

| Phase | Timeframe | Owner |
|-------|-----------|-------|
| Review | T+0 to T+1h | Team |
| Approval | T+1h to T+2h | Supervisor |
| Execution | T+2h to T+2:30h | Operator |
| Verification | T+2:30h to T+3h | Operator + Team |
| Documentation | T+3h onwards | Team |

---

## Success Criteria

✅ Incident resolved when:
- [ ] Objects 18201/18202 deleted from NetBox
- [ ] Device 2647 (INFORR-BVA-JCL-RX) no longer has these objects
- [ ] Device 1890 (4WNET-MNS-KTG-RX) has correct objects (from fixed batch)
- [ ] Dry-run tests pass with fixed validation scripts
- [ ] No blocked reasons in batch-apply-plan-fixed.json
- [ ] Scripts prevent null payload fields in future batches
- [ ] Incident document marked RESOLVED

---

**Status:** Ready for approval and execution
**Owner:** [To be assigned]
**Approver:** [To be identified]
