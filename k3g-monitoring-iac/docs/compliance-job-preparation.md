# Compliance Job Preparation (FASES CANDIDATES-025–027)

## Overview

After candidates are discovered and selected, the **Compliance Job** is a local artifact that captures:
- Device eligibility validation
- Job metadata (status, safety flags, next steps)
- Human-readable summary for manual review

No SSH, SNMP, NETCONF, or NetBox writes are triggered. This is a **preparation phase only**.

---

## Flow

```
Dashboard (candidate search)
    ↓
[Select candidates] → [Criar job de Compliance button]
    ↓
Modal: "Criar Job de Compliance"
    ├─ Show: Devices selecionados: N
    ├─ Warning: "Esta etapa ainda não conecta no equipamento..."
    └─ Button: "Criar job de Compliance"
    ↓
POST /compliance/analyze
    ├─ Per-ID validation (get_device_by_id)
    ├─ Tenant group enrichment
    ├─ Eligibility re-check
    ├─ Create job artifacts
    └─ Return: status="COMPLIANCE_JOB_PREPARED", job_id=...
    ↓
Success: Job created locally at reports/compliance/jobs/<job_id>/
```

---

## Job Directory Structure

```
reports/compliance/jobs/<job_id>/
├── job-request.json                    # Job metadata, safety flags, status
├── selected-devices.json               # Device list with normalized fields
├── eligibility-recheck.json            # Recheck results, all_eligible flag
└── COMPLIANCE-JOB-START-GATE.md         # Human-readable summary
```

### FASES COMPLIANCE-JOB-001-003

Depois da preparação inicial, o fluxo segue somente por revisão local:

- `GET /compliance/jobs` lista jobs preparados.
- `GET /compliance/jobs/{job_id}` abre o detalhe do job.
- `POST /compliance/jobs/{job_id}/collection/start-gate` valida o gate explícito.
- `POST /compliance/jobs/{job_id}/collection/plan` gera o plano read-only.

Novos artefatos locais:

- `collection-start-gate.json`
- `COLLECTION-START-GATE.md`
- `collection-plan.json`
- `COLLECTION-PLAN.md`

Nenhuma coleta, SSH, SNMP, NETCONF, NetBox write, ApprovalRecord, ApplyPlan ou `/sync` é executada nesta fase.

---

## Job ID Format

```
compliance-job-<12-hex-characters>
```

Example: `compliance-job-a1b2c3d4e5f6`

Generated via `uuid.uuid4().hex[:12]` at job creation time.

---

## File Schemas

### job-request.json

```json
{
  "job_id": "compliance-job-a1b2c3d4e5f6",
  "status": "prepared",
  "mode": "read_only",
  "triggered_by": "operator",
  "created_at": "2026-04-30T15:45:30.123456+00:00",
  "device_ids": [1890, 1891],
  "safety": {
    "netbox_write": false,
    "device_connection_started": false,
    "collection_started": false,
    "approval_record_created": false,
    "apply_plan_created": false
  },
  "next_required_action": "manual_review_before_collection"
}
```

---

### selected-devices.json

```json
{
  "job_id": "compliance-job-a1b2c3d4e5f6",
  "selected_count": 2,
  "devices": [
    {
      "id": 1890,
      "name": "4WNET-MNS-KTG-RX",
      "status": "active",
      "tenant": "4W NET",
      "tenant_group": "K3G Solutions",
      "tenant_group_source": "tenant_detail",
      "compliance_enabled": true,
      "primary_ip4": "104.234.244.255/32",
      "primary_ip6": null,
      "site": "MNS",
      "role": "Router",
      "manufacturer": "Huawei",
      "model": "NE8000 M8 DC",
      "candidate_reason": [
        "device_active",
        "compliance_enabled",
        "tenant_present",
        "tenant_group_match"
      ]
    }
  ]
}
```

---

### eligibility-recheck.json

```json
{
  "job_id": "compliance-job-a1b2c3d4e5f6",
  "rechecked_at": "2026-04-30T15:45:30.123456+00:00",
  "device_ids_submitted": [1890, 1891],
  "confirmed_eligible": [1890, 1891],
  "ineligible": [],
  "all_eligible": true,
  "recheck_method": "per_id_get_with_enrichment"
}
```

---

### COMPLIANCE-JOB-START-GATE.md

Human-readable summary:
- Job ID and status
- Creation timestamp
- Who triggered (operator)
- Device list (name, tenant)
- Eligibility criteria verified (status, Compliance field, tenant, group)
- Safety confirmations (no coleta, no SSH/SNMP, no NetBox writes)
- Next step: `manual_review_before_collection`

---

## API Endpoint

### POST /compliance/analyze

Request:
```json
{
  "device_ids": [1890],
  "mode": "read_only",
  "triggered_by": "operator"
}
```

**Success (HTTP 200):**
```json
{
  "success": true,
  "status": "COMPLIANCE_JOB_PREPARED",
  "job_id": "compliance-job-a1b2c3d4e5f6",
  "confirmed_eligible": [1890],
  "ineligible": [],
  "message": "Job local de Compliance criado para revisão. Nenhuma coleta foi iniciada.",
  "safety": {
    "read_only": true,
    "netbox_write": false,
    "device_connection": false,
    "auto_compliance_started": false,
    "job_only": true
  }
}
```

**Failure (HTTP 422)** — device lost eligibility:
```json
{
  "success": false,
  "error": "Dispositivos perderam elegibilidade: [1891]",
  "ineligible": [1891],
  "confirmed_eligible": [1890]
}
```

---

## Validation Steps

When POST /compliance/analyze is called:

1. **Per-ID Fetch** — Call `get_device_by_id(id)` for each device (not bulk fetch)
2. **Enrich Tenant Group** — If device.tenant lacks group, fetch from `/api/tenancy/tenants/{id}/`
3. **Eligibility Re-check** — Apply all 4 gates:
   - status == "active"
   - custom_fields[Compliance] == True
   - tenant present
   - tenant.group == "K3G Solutions" or slug == "k3g-solutions"
4. **Split Results** — confirmed_eligible vs ineligible lists
5. **Create Job** — If all eligible, write 4 artifact files
6. **Return Response** — HTTP 200 with job_id, or 422 if any ineligible

---

## Safety Guarantees

✓ **No NetBox writes** — Only GET calls to /api/dcim/devices/ and /api/tenancy/tenants/
✓ **No device connections** — No SSH, SNMP, NETCONF
✓ **No automatic analysis** — Job artifact is local, manual review required
✓ **No ApprovalRecord or ApplyPlan creation** — Job is read-only snapshot
✓ **Token never logged** — Env var only, never in response
✓ **Read-only operation** — All safety flags set to False (except read_only=True)

---

## Next Steps (Manual)

After job is created:

1. **Review job artifacts** — Check job-request.json and COMPLIANCE-JOB-START-GATE.md
2. **Verify device list** — Confirm selected devices are correct in selected-devices.json
3. **Approve or reject** — Decision based on business rules (out of scope for this phase)
4. **If approved** — Proceed to compliance collection phase (future FASES)

---

## Environment Variables

Compliance job creation only requires:
- `NETBOX_URL` — Base URL of NetBox instance
- `NETBOX_TOKEN` — Read-only API token

No additional variables needed.

---

## Testing

```bash
python3 -m pytest tests/test_compliance_job_creation.py -v
```

18 tests covering:
- Job artifact creation
- Job ID format
- File existence and schema
- Safety dict validation
- Per-ID validation behavior
- No SSH/SNMP/NETCONF calls
- No NetBox writes

---

## References

- **FASE CANDIDATES-025** — UX Hardening: dashboard button labels, modal messaging
- **FASE CANDIDATES-026** — Endpoint Fix: per-ID validation, enrichment, job creation
- **FASE CANDIDATES-027** — Job Service: artifact creation and file writes
- **Plan:** `/Users/keslleykssantos/.claude/plans/jiggly-hatching-phoenix.md`
