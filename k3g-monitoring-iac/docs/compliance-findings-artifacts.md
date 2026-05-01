# Compliance Findings Artifacts (FASES COMPARE-003)

## Overview

The `POST /compliance/jobs/{job_id}/compare` endpoint compares parsed inventory to compliance policies and generates local artifact files.

No NetBox writes. No SSH/SNMP/NETCONF. No automatic remediation.

---

## Endpoint

### POST /compliance/jobs/{job_id}/compare

Compare parsed inventory against policy registry. Creates finding artifacts locally.

**Preconditions:**
- `parser-result.json` exists and is not empty
- `parser-safety-validation.json` exists and decision is not PARSER_SAFETY_INVALID
- `parsed-inventory.json` exists for at least one device under `collection-results/devices/<device_id>/parsed/`
- Policy registry loads successfully and validates
- Request contains `confirm_local_compare: true`

**Request:**
```json
{
  "operator": "Keslley",
  "confirm_local_compare": true
}
```

**Success (HTTP 200):**
```json
{
  "job_id": "compliance-job-xxxxxxxxxxxx",
  "status": "COMPLIANCE_COMPARE_COMPLETED",
  "decision": "COMPLIANCE_COMPARE_COMPLETED",
  "summary": {
    "devices": 1,
    "findings_total": 0,
    "blockers": 0,
    "errors": 0,
    "warnings": 0,
    "info": 0
  },
  "safety": {
    "netbox_write": false,
    "device_connection": false,
    "sync_called": false,
    "approval_record_created": false,
    "apply_plan_created": false
  },
  "files": {
    "comparison_result": "<abs path>/comparison/compliance-comparison-result.json",
    "comparison_result_markdown": "<abs path>/comparison/COMPLIANCE-COMPARISON-RESULT.md",
    "comparison_result_report_path": "compliance/jobs/<job_id>/comparison/COMPLIANCE-COMPARISON-RESULT.md"
  },
  "comparison_result": {...full result...}
}
```

**Status values:**
- `COMPLIANCE_COMPARE_COMPLETED` — zero findings
- `COMPLIANCE_COMPARE_COMPLETED_WITH_FINDINGS` — findings present, no blockers
- `COMPLIANCE_COMPARE_BLOCKED` — one or more blocker findings present

**Failure (HTTP 422 or 409):**
```json
{
  "success": false,
  "error": "parser preconditions not satisfied"
}
```

---

## Artifact Directory Structure

```
reports/compliance/jobs/<job_id>/comparison/
├── compliance-comparison-result.json
├── COMPLIANCE-COMPARISON-RESULT.md
└── devices/
    ├── 1890/
    │   ├── compliance-findings.json
    │   └── COMPLIANCE-FINDINGS.md
    ├── 1891/
    │   ├── compliance-findings.json
    │   └── COMPLIANCE-FINDINGS.md
    ...
```

---

## File Schemas

### compliance-comparison-result.json (Job-level)

```json
{
  "job_id": "compliance-job-xxxxxxxxxxxx",
  "status": "COMPLIANCE_COMPARE_COMPLETED|COMPLIANCE_COMPARE_COMPLETED_WITH_FINDINGS|COMPLIANCE_COMPARE_BLOCKED",
  "decision": "COMPLIANCE_COMPARE_COMPLETED|...",
  "parser_result": true,
  "parser_safety_validation": true,
  "summary": {
    "devices": 1,
    "findings_total": 5,
    "blockers": 0,
    "errors": 2,
    "warnings": 3,
    "info": 0
  },
  "safety": {
    "netbox_write": false,
    "device_connection": false,
    "sync_called": false,
    "approval_record_created": false,
    "apply_plan_created": false
  },
  "registry": {
    "policy_dir": "...",
    "file_count": 13,
    "required_count": 13,
    "optional_count": 3,
    "blocker_count": 0,
    "warning_count": 0,
    "policy_names": [...]
  },
  "devices": [...device results...],
  "checked_at": "2026-04-30T15:45:30.123456+00:00",
  "files": {
    "comparison_result": "...",
    "comparison_result_markdown": "...",
    "comparison_result_report_path": "..."
  }
}
```

### compliance-findings.json (Per-device)

```json
{
  "device_id": 1890,
  "name": "4WNET-MNS-KTG-RX",
  "profile": "default-readonly",
  "findings": [
    {
      "finding_id": "CMP-...",
      "device_id": 1890,
      "scope": "interface|bgp|route_policy|prefix_list|snmp|system",
      "object_type": "interface",
      "object_name": "GigabitEthernet0/0/0",
      "rule_id": "interface.description.required",
      "severity": "info|warning|error|blocker",
      "status": "open",
      "title": "Interface sem descrição",
      "description": "Interface parseada sem field description.",
      "evidence": {
        "source": "parsed_inventory",
        "field": "interfaces[].description",
        "value": null
      },
      "recommendation": "Adicionar descrição na interface.",
      "write_required": false,
      "approval_required": false,
      "finding_type": "optional_enrichment|data_missing_for_check"
    }
  ],
  "summary": {
    "findings_total": 5,
    "blockers": 0,
    "errors": 2,
    "warnings": 3,
    "info": 0
  },
  "safety": {
    "netbox_write": false,
    "device_connection": false,
    "sync_called": false,
    "approval_record_created": false,
    "apply_plan_created": false
  },
  "files": {
    "findings_json": "...",
    "findings_markdown": "...",
    "findings_markdown_report_path": "..."
  }
}
```

### COMPLIANCE-FINDINGS.md (Per-device)

Human-readable markdown report per device. Includes:
- Device name
- Summary (total findings, blockers, errors, warnings, info)
- List of findings with severity, scope, object, rule, recommendation

### COMPLIANCE-COMPARISON-RESULT.md (Job-level)

Human-readable markdown report for entire job. Includes:
- Job ID
- Status
- Summary (devices, total findings, blockers, errors, warnings, info)
- Safety confirmations (all false)

---

## Comparators

### Interface Comparator

Checks:
- Interfaces present (missing = info finding)
- Each interface has description (missing = warning)
- Physical/protocol state consistency (mismatch = warning)
- Naming convention compliance (subinterfaces = error if invalid, base = warning if invalid)

### BGP Comparator

Checks:
- Peers present (missing = info finding)
- Each peer has description (missing = warning)
- Peer has import/export policy (missing = warning)
- Peer state is Established (not established = warning)
- Peer/policy/group names follow convention (mismatch = info)

### Route-Policy Comparator

Checks:
- Route-policies present (missing = info finding)
- Policy has nodes (missing = warning)
- Policy name follows convention (invalid = warning)
- Policy node references to prefix-lists exist (broken = error)
- Policy references to community filters are valid (missing validation = warning)

### Prefix-List Comparator

Checks:
- Prefix-lists present (missing = info finding)
- Prefix-list has entries (empty = warning)
- Prefix-list name follows convention (invalid = warning)

### SNMP Comparator

Checks:
- SNMP sys-info present (missing = warning)
- SNMP sys-info complete (missing sys_name = info)

---

## Missing Data Behavior

When parsed inventory is missing data (e.g., no BGP peers found):
- Generates finding with `finding_type: "data_missing_for_check"`
- Severity: info or warning (depends on scope)
- **Does not fail global compare** — continue to next device/scope

---

## Severity Classification

Each finding is classified using `compliance-severity-policy.yaml`:
- Rule ID lookup in `rule_severity_overrides`
- Fallback to `default_mapping` by finding_type
- Default: `"info"`

Allowed severities: `info`, `warning`, `error`, `blocker`

---

## Finding Flags

Every finding has:
- `write_required: false` — never requires NetBox write
- `approval_required: false` — never requires approval record

---

## Safety Guarantees

✓ **No NetBox writes** — only reads local artifacts  
✓ **No device connections** — no SSH, SNMP, NETCONF  
✓ **No automatic remediation** — findings are input, not action  
✓ **No ApprovalRecord creation** — local findings only  
✓ **No ApplyPlan creation** — local findings only  
✓ **Token never logged** — env vars not in response  

---

## References

- **FASE COMPLIANCE-COMPARE-003** — Compliance Findings Artifact
- **Service:** `webui/services/compliance_compare.py`
- **Route:** `POST /compliance/jobs/{job_id}/compare` in `webui/app.py`
