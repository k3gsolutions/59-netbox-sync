# NetBox Audit Checklist — IDs 18201/18202

**Purpose:** Determine if IDs were created by batch apply or from other source
**Status:** PENDING MANUAL AUDIT
**Required for:** Incident closure + rollback decision

---

## Manual Verification Steps

### Step 1: Check Interface 18201

```bash
# Query interface
curl -H "Authorization: Token $NETBOX_WRITE_TOKEN" \
  "https://docs.k3gsolutions.com.br/api/dcim/interfaces/18201/"
```

Record:
- [ ] ID: 18201
- [ ] Name: LoopBack100 (expected)
- [ ] Device: 2647 / INFORR-BVA-JCL-RX (expected)
- [ ] Type: (record value)
- [ ] Status: (record value)
- [ ] Created: (TIMESTAMP - critical)
- [ ] Last Updated: (TIMESTAMP)
- [ ] Created By: (User/Token - if logged)

### Step 2: Check Interface 18202

```bash
curl -H "Authorization: Token $NETBOX_WRITE_TOKEN" \
  "https://docs.k3gsolutions.com.br/api/dcim/interfaces/18202/"
```

Record:
- [ ] ID: 18202
- [ ] Name: NULL0 (expected)
- [ ] Device: 2647 / INFORR-BVA-JCL-RX (expected)
- [ ] Type: (record value)
- [ ] Status: (record value)
- [ ] Created: (TIMESTAMP - critical)
- [ ] Last Updated: (TIMESTAMP)
- [ ] Created By: (User/Token - if logged)

### Step 3: Check NetBox Audit Log

NetBox UI → Admin → Audit Log (or via API):

```bash
# Search for object creation audit events
curl -H "Authorization: Token $NETBOX_WRITE_TOKEN" \
  "https://docs.k3gsolutions.com.br/api/extras/object-changes/?object_type=dcim.interface&object_id=18201"

curl -H "Authorization: Token $NETBOX_WRITE_TOKEN" \
  "https://docs.k3gsolutions.com.br/api/extras/object-changes/?object_type=dcim.interface&object_id=18202"
```

Record:
- [ ] ID 18201: Created at (TIMESTAMP) by (USER/TOKEN)
- [ ] ID 18202: Created at (TIMESTAMP) by (USER/TOKEN)
- [ ] Creation method: via API (token?) or UI (user?)
- [ ] Request details: if logged

### Step 4: Correlate with Batch Execute Time

From batch apply result:
- Batch execute time: 2026-04-28T19:01:04Z (from earlier logs)
- ID 18201 created: ? (from audit log)
- ID 18202 created: ? (from audit log)

Compare:
- [ ] Created BEFORE batch execute? → Not created by batch
- [ ] Created AT batch execute? → Likely created by batch
- [ ] Created AFTER batch execute? → Not created by batch
- [ ] Created by different user/token? → Different source

### Step 5: Verify No Intended Objects

Confirm that intended objects still DO NOT exist:

```bash
# Eth-Trunk1 on device 1890
curl -H "Authorization: Token $NETBOX_WRITE_TOKEN" \
  "https://docs.k3gsolutions.com.br/api/dcim/interfaces/?device_id=1890&name=Eth-Trunk1"
# Expected: count=0

# GigabitEthernet0/5/0 on device 1890
curl -H "Authorization: Token $NETBOX_WRITE_TOKEN" \
  "https://docs.k3gsolutions.com.br/api/dcim/interfaces/?device_id=1890&name=GigabitEthernet0/5/0"
# Expected: count=0
```

Record:
- [ ] Eth-Trunk1 on device 1890: count=0? YES / NO
- [ ] GigabitEthernet0/5/0 on device 1890: count=0? YES / NO

---

## Decision Matrix

### If IDs 18201/18202 created BEFORE batch execute:

**Conclusion:** NOT created by batch apply
- Created by: Previous operation
- Rollback: NO ROLLBACK NEEDED
- Action: Close incident as "no action required"
- Reason: IDs pre-existed

### If IDs 18201/18202 created AT batch execute (±5 min):

**Conclusion:** LIKELY created by batch apply
- Created by: This batch execution
- Rollback: ROLLBACK REQUIRED (manual approval)
- Action: Manual deletion via NetBox UI or approved script
- Reason: Timestamp matches batch execution

### If IDs 18201/18202 created AFTER batch execute:

**Conclusion:** NOT created by batch apply
- Created by: Subsequent operation
- Rollback: NO ROLLBACK NEEDED
- Action: Close incident as "different source"
- Reason: IDs created after batch ended

### If audit log unavailable:

**Conclusion:** UNKNOWN
- Rollback: INVESTIGATION_PENDING
- Action: Escalate to NetBox admin
- Reason: Cannot determine source without audit trail
- Follow-up: Manual review + approval before any delete

---

## Recording Template

```markdown
## Audit Results — [DATE/TIME]

### Interface 18201
- Created: [ISO8601 TIMESTAMP]
- By: [USER/TOKEN]
- Device: [ID/NAME]
- Matches batch execute time: YES / NO / UNKNOWN

### Interface 18202
- Created: [ISO8601 TIMESTAMP]
- By: [USER/TOKEN]
- Device: [ID/NAME]
- Matches batch execute time: YES / NO / UNKNOWN

### Intended Objects Status
- Eth-Trunk1 on device 1890: EXISTS / NOT EXISTS
- GigabitEthernet0/5/0 on device 1890: EXISTS / NOT EXISTS

## Decision

Rollback decision:
- [ ] ROLLBACK_REQUIRED (IDs created by batch)
- [ ] NO_ROLLBACK_NEEDED (IDs from other source)
- [ ] INVESTIGATION_PENDING (audit log unavailable)

Approver: [NAME/SIGNATURE]
Date: [ISO8601]
```

---

## Incident Closure Criteria

Close incident when:
- ✓ All audit queries executed
- ✓ Timestamps recorded
- ✓ Decision made (rollback yes/no/pending)
- ✓ Approver signature
- ✓ Rollback plan updated with result
- ✓ FASE 2.5 closed

---

## References

- INC-2026-04-28-001: Null payload fields (REMEDIATED)
- INC-2026-04-28-002: Fake IDs f"18{200+i}" (CRITICAL FIX APPLIED)
- Batch execute: 2026-04-28T19:01:04Z
- IDs: 18201 (LoopBack100), 18202 (NULL0)
- Device: 2647 (INFORR-BVA-JCL-RX)
- Expected: 1890 (4WNET-MNS-KTG-RX)
