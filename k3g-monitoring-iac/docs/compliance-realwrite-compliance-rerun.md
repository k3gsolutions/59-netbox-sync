# FASES COMPLIANCE-REALWRITE-009: Post-Write Compliance Re-Run

**Status:** COMPLETED  
**Lines of code:** ~150 (compliance_realwrite_postwrite.py)  
**Tests:** 6 test cases

---

## Purpose

Post-execution compliance re-run: local policy comparison without external calls.

**Regra máxima:** Somente local policy comparison. Sem NetBox read/write. Sem SSH/SNMP/NETCONF.

---

## What It Does

1. Loads real-write execution result
2. Checks that execution succeeded and created items
3. For each item, validates against local policy artifacts
4. Records compliance status (compliant_with_policy / pending)
5. Does NOT call NetBox, SSH, or device

---

## Decision Outcomes

| Decision | When | Action |
|----------|------|--------|
| `COMPLIANCE_RERUN_PASSED` | All items compliant | Next: Closure (success) |
| `COMPLIANCE_RERUN_PARTIAL_FAILED` | Some items non-compliant | Next: Closure (warnings) |
| `COMPLIANCE_RERUN_NOT_APPLICABLE_WRITE_FAILED` | Execution status not SUCCESS | Next: Closure (action required) |
| `COMPLIANCE_RERUN_NOT_APPLICABLE_NO_OBJECT_CREATED` | No items in execution | Next: Closure (not applicable) |
| `COMPLIANCE_RERUN_NOT_APPLICABLE_NO_EXECUTION` | Execution result not found | Next: Closure (action required) |

---

## Safety Guarantees

✓ No NetBox reads/writes  
✓ No SSH/SNMP/NETCONF  
✓ No device connections  
✓ Local policy comparison only  

---

## Artifact Output

```
reports/compliance/jobs/<job_id>/real-write/compliance-rerun/
├── post-write-compliance-rerun.json
└── POST-WRITE-COMPLIANCE-RERUN.md
```

### JSON Structure

```json
{
  "job_id": "job-123",
  "status": "compliance_rerun_completed",
  "decision": "COMPLIANCE_RERUN_PASSED",
  "rerun_at": "2026-05-04T12:00:00Z",
  "rerun_by": "operator",
  "checks": [
    {
      "item_id": "APC-001",
      "response_id": 1234,
      "endpoint": "/api/dcim/interfaces/",
      "local_policy_status": "compliant_with_policy",
      "checked_at": "2026-05-04T12:00:00Z"
    }
  ],
  "check_count": 1,
  "passed": 1,
  "failed": 0,
  "safety": {
    "netbox_read": false,
    "netbox_write": false,
    "device_connection": false,
    "ssh_connection": false,
    "compliance_rerun_only": true
  }
}
```

---

## HTTP Endpoint

**POST** `/compliance/jobs/{job_id}/real-write/compliance-rerun`

### Request

```json
{
  "operator": "username",
  "confirm_compliance_rerun": true
}
```

### Response (200 Success)

```json
{
  "success": true,
  "job_id": "job-123",
  "decision": "COMPLIANCE_RERUN_PASSED",
  "check_count": 1,
  "passed": 1,
  ...
}
```

### Response (409 Conflict)

```json
{
  "success": false,
  "error": "Real-write execution result not found"
}
```

---

## Next Phase

→ **REALWRITE-010: Closure Package**
