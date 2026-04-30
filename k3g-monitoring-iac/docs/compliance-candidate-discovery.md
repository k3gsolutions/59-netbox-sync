# Compliance Candidate Discovery (FASES CANDIDATES-001–004)

## Objective

Identify and enumerate devices eligible for compliance analysis directly from NetBox.
No analysis is triggered automatically. Users manually select devices and confirm before
any operations begin.

---

## Eligibility Rules

A device qualifies as a compliance candidate if **ALL** of these are true:

| Gate | Condition | Notes |
|------|-----------|-------|
| 1 | `status == "active"` | String `"active"` or dict `{"value": "active", ...}` |
| 2 | `custom_fields["Compliance"] == True` | Case-insensitive key lookup; must be boolean `True` |
| 3 | `tenant` is present | Device must have a tenant assigned |
| 4 | `tenant.group.name == "K3G Solutions"` or `tenant.group.slug == "k3g-solutions"` | Exact match or slug match |

**Example eligible device:**
```json
{
  "id": 1890,
  "name": "4WNET-MNS-KTG-RX",
  "status": "active",
  "custom_fields": {"Compliance": true},
  "tenant": {
    "name": "K3G Solutions",
    "group": {"name": "K3G Solutions"}
  }
}
```

---

## Configuration

### Environment Variables

Set these to enable candidate discovery:

```bash
export NETBOX_URL="https://docs.k3gsolutions.com.br"
export NETBOX_TOKEN="your-read-only-token"
export K3G_SOLUTIONS_TENANT_GROUP_ID="123"  # Optional, for ID-based tenant group check
```

### Token Requirements

- **Permission**: Read-only access to `/api/dcim/devices/`
- **Scope**: No write, no sync, no other endpoints
- **Storage**: Environment variable only — never logged, never returned in responses

---

## API Endpoints

### `GET /compliance`

HTML dashboard listing eligible devices.

**Response**: HTML page with:
- Safety banner: "Listagem somente leitura. Nenhuma conexão com equipamento foi iniciada."
- Table of candidates with checkboxes
- "Iniciar Compliance" button (disabled until selection)
- Confirmation modal before POST to `/compliance/analyze`
- Error message if NetBox not configured

---

### `GET /compliance/candidates`

JSON API returning candidate list + safety block.

**Query Parameters**:
- `limit` (int, default 100): Max results per page
- `offset` (int, default 0): Pagination offset
- `site` (str, optional): Filter by site slug
- `role` (str, optional): Filter by role slug
- `tenant_group` (str, optional): Filter by tenant group

**Response** (200 OK):
```json
{
  "count": 1,
  "results": [
    {
      "id": 1890,
      "name": "4WNET-MNS-KTG-RX",
      "status": "active",
      "tenant": "K3G Solutions",
      "tenant_group": "K3G Solutions",
      "compliance_enabled": true,
      "primary_ip4": "192.0.2.1/32",
      "primary_ip6": null,
      "site": "MNS",
      "role": "Router",
      "manufacturer": "Huawei",
      "model": "NE8000",
      "candidate_reason": [
        "device_active",
        "compliance_enabled",
        "tenant_present",
        "tenant_group_match"
      ]
    }
  ],
  "safety": {
    "read_only": true,
    "netbox_write": false,
    "device_connection": false,
    "auto_compliance_started": false
  }
}
```

**Errors**:
- 503 (NetBox not configured)
- 401 (Authentication failure)
- 500 (Request or parsing error)

---

### `POST /compliance/analyze`

Manual start guard. Re-validates device eligibility before confirming.

**Request**:
```json
{
  "device_ids": [1890],
  "mode": "read_only",
  "triggered_by": "operator"
}
```

**Response** (200 OK — all eligible):
```json
{
  "success": true,
  "confirmed_eligible": [1890],
  "ineligible": [],
  "message": "Dispositivos confirmados elegíveis. Análise pode prosseguir.",
  "safety": {
    "read_only": true,
    "netbox_write": false,
    "device_connection": false
  }
}
```

**Response** (422 — device lost eligibility):
```json
{
  "success": false,
  "error": "Dispositivos perderam elegibilidade ou não encontrados",
  "missing": [],
  "ineligible": [1890]
}
```

---

## Workflow

1. **User navigates to `/compliance`**
   - Dashboard fetches eligible candidates from NetBox via `GET /compliance/candidates`
   - Table displays only devices passing all 4 gates
   - "Iniciar Compliance" button starts disabled

2. **User selects one or more devices**
   - Checkbox selection enables button
   - Selected count displayed

3. **User clicks "Iniciar Compliance"**
   - Modal confirmation appears
   - Shows:
     - List of selected devices
     - Safety guarantees (no write, no SSH, no SNMP, read-only)
   - User must click "Iniciar" to proceed

4. **Modal confirms → POST to `/compliance/analyze`**
   - Backend re-validates all device IDs are still eligible
   - If any device lost eligibility, 422 returned with `ineligible` list
   - If all pass, 200 returned with confirmed list
   - User sees success message or error

---

## Safety Guarantees

All responses include a `safety` block confirming:

```json
"safety": {
  "read_only": true,                    // No NetBox writes
  "netbox_write": false,                // No POST/PATCH/DELETE on NetBox
  "device_connection": false,           // No SSH/Telnet to devices
  "auto_compliance_started": false      // No automatic analysis
}
```

---

## Implementation Details

### Services

- **`webui/services/netbox_client.py`**: GET-only HTTP client for NetBox API
  - Reads `NETBOX_URL` + `NETBOX_TOKEN` from environment
  - Raises `NetBoxNotConfiguredError`, `NetBoxAuthError`, `NetBoxClientError`

- **`webui/services/compliance_candidates.py`**: Eligibility logic
  - `get_status_value(device)` — extract status (handles string + dict)
  - `get_custom_field_bool(device, *names)` — case-insensitive field lookup
  - `get_tenant_group_name(device)` — extract tenant group (name/slug/id)
  - `is_compliance_candidate(device)` — apply all 4 gates
  - `normalize_compliance_candidate(device)` — shape for API response
  - `list_compliance_candidates(client, limit, offset, filters)` — full pipeline

### Routes in `app.py`

- `GET /compliance` — HTML dashboard (server-side rendered)
- `GET /compliance/candidates` — JSON API
- `POST /compliance/analyze` — Eligibility re-check gate

### Templates

- `webui/templates/compliance_candidates.html` — Dashboard with table + modal + vanilla JS

---

## Testing

### Unit Tests

```bash
python3 -m pytest tests/unit/test_compliance_candidates.py -v
```

11 pure Python tests covering:
- Status value extraction (string + dict formats)
- Custom field lookup (case-insensitive)
- Tenant group extraction
- All 4 eligibility gates individually
- Normalized response shape

### API Tests

```bash
python3 -m pytest tests/test_compliance_candidates_api.py -v
```

9 API tests covering:
- Route status codes
- Response structure (count, results, safety block)
- Filtering to only eligible devices
- No SSH/SNMP/NetBox write calls
- Error handling (not configured, auth error, etc.)

### Manual Testing

1. Set env vars:
   ```bash
   export NETBOX_URL="https://..."
   export NETBOX_TOKEN="..."
   ```

2. Start webui:
   ```bash
   cd webui
   python3 -m uvicorn app:app --reload
   ```

3. Navigate to `http://localhost:8000/compliance` (or configured port)

4. Verify:
   - Dashboard loads
   - Devices appear if eligible
   - Selection works
   - Modal appears on click
   - POST confirms or rejects eligibility

---

## Notes

- **Eligibility is re-checked** on each `/compliance/analyze` call — device states in NetBox can change
- **No state is persisted** — the feature is stateless (read-only)
- **Token never exposed** — it stays in environment variable, never logged or returned
- **No sync calls** — `/sync` endpoint is never called
- **No device connections** — SSH/Telnet/SNMP are not used

---

## Related FASES

- **FASE CANDIDATES-001**: Service module + eligibility logic
- **FASE CANDIDATES-002**: NetBox client + JSON API
- **FASE CANDIDATES-003**: Dashboard UI + manual selection
- **FASE CANDIDATES-004**: Manual start guard (revalidation gate)
