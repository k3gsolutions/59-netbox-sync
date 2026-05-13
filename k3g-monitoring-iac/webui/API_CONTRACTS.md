# Netbox_Sync — API Contracts

## 1. GET /compliance/eligible-tenants
- **Response**: `[{ id, name, slug, device_count, description }]`

## 2. GET /compliance/eligible-devices?tenant_id=X
- **Response**: `[{ id, name, role, manufacturer, model, site, primary_ip }]`

## 3. GET /compliance/eligible-contexts
- **Response**: `[{ id, label, icon, description, collection_method }]`
  - `collection_method`: snmp | ssh | netbox

## 4. POST /compliance/analyze-guided
- **Request**: `{ tenant_id, device_id, contexts: [] }`
- **Response**: 
  ```json
  {
    "device": {},
    "tenant": {},
    "status": "ok|attention|failed",
    "summary": { "approved": 0, "warning": 0, "failed": 0 },
    "findings": [{ "status": "string", "context": "string", "item": "string", "title": "string", "details": {} }],
    "collection_notes": []
  }
  ```

## 5. POST /compliance/analyze-file
- **Request**: `FormData { file, platform, device_name, contexts: JSON }`
- **Response**:
  ```json
  {
    "device": {},
    "tenant": {},
    "status": "string",
    "mode": "file",
    "platform": "string",
    "summary": {},
    "findings": [],
    "collection_notes": []
  }
  ```

## 6. POST /api/sync/netbox
- **Response**: `{ synced_tenants, synced_devices, errors }`

## 7. GET /api/tenants
- **Response**: `[{ id, name, slug, group_name, snmp_community }]`

## 8. GET /api/devices?tenant_id=X
- **Response**: `[{ id, name, tenant_id, platform, ... }]`
