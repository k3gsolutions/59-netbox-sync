# wf-netbox-router

Entry point de **todos** os webhooks NetBox. Valida HMAC, deduplica, classifica evento, dispara sub-workflow apropriado.

**Tempo de execução alvo:** < 500ms (responde 200 ao NetBox imediato; processamento real é assíncrono via `Execute Workflow`).

---

## Diagrama de fluxo

```
[Webhook]
    ↓
[Code: Validate HMAC] ─── inválido ──→ [Respond 401] ──→ END
    ↓
[Postgres: INSERT dedup] ── conflito ──→ [Respond 200 "duplicate"] ──→ END
    ↓
[Code: Generate correlation_id]
    ↓
[Postgres: audit "received"]
    ↓
[Switch: classify event+model]
    │
    ├── dcim.device + create/update → [Execute wf-onboard-device]
    ├── dcim.device + delete         → [Execute wf-decommission-device]
    ├── circuits.circuit + create/update → [Execute wf-onboard-circuit]
    ├── circuits.circuit + delete    → [Execute wf-decommission-circuit]
    ├── tenancy.tenant + create      → [Execute wf-onboard-tenant]
    ├── dcim.interface + update      → [Execute wf-onboard-interface]
    └── default                      → [Postgres: audit "skipped"]
    ↓
[Respond 200 "queued"]
    ↓
END (resposta) — sub-workflows continuam em background
```

---

## Nodes — passo a passo

### 1. Webhook (trigger)
| Campo | Valor |
|-------|-------|
| HTTP Method | POST |
| Path | `netbox-router` |
| Authentication | None (HMAC validado no próximo node) |
| Response Mode | When last node finishes |
| Response Code | 200 |
| Response Headers | `Content-Type: application/json` |

URL pública: `https://n8n.k3g.internal/webhook/netbox-router`

### 2. Code: Validate HMAC
**Node type:** Code (JavaScript) — `Run Once for All Items`

```javascript
const crypto = require('crypto');

const secret = $env.NETBOX_WEBHOOK_SECRET;
if (!secret) throw new Error('NETBOX_WEBHOOK_SECRET not set');

const signatureHeader = $input.first().json.headers['x-hook-signature'];
if (!signatureHeader) {
    return [{ json: { hmac_valid: false, reason: 'missing-signature' } }];
}

// NetBox envia HMAC-SHA512 do body bruto
const body = JSON.stringify($input.first().json.body);
const expected = crypto
    .createHmac('sha512', secret)
    .update(body)
    .digest('hex');

const valid = crypto.timingSafeEqual(
    Buffer.from(signatureHeader),
    Buffer.from(expected)
);

return [{
    json: {
        hmac_valid: valid,
        body: $input.first().json.body,
        headers: $input.first().json.headers
    }
}];
```

### 3. IF: HMAC valid?
**Condition:** `{{ $json.hmac_valid }}` is true

- **False branch:** Respond to Webhook (status 401, body `{"error":"invalid-hmac"}`) → END
- **True branch:** continua

### 4. Postgres: INSERT dedup (com ON CONFLICT)
**Operation:** Execute Query
**Query:**
```sql
INSERT INTO webhook_dedup (request_id, correlation_id, event_summary)
VALUES (
    $1,
    gen_random_uuid(),
    $2
)
ON CONFLICT (request_id) DO NOTHING
RETURNING request_id, correlation_id;
```
**Parameters:**
- `$1`: `{{ $json.headers['x-request-id'] || $json.headers['x-hook-delivery'] || $now }}`
- `$2`: `{{ $json.body.event }} {{ $json.body.model }} id={{ $json.body.data.id }}`

### 5. IF: Already processed?
**Condition:** `{{ $json.length === 0 }}` (RETURNING vazio = conflict)

- **True (duplicate):** Respond 200 `{"status":"duplicate","action":"ignored"}` → END
- **False:** continua com `correlation_id` retornado

### 6. Set: payload normalizado
**Node type:** Edit Fields (Set)

```json
{
  "correlation_id": "={{ $json.correlation_id }}",
  "event": "={{ $('Code: Validate HMAC').item.json.body.event }}",
  "model": "={{ $('Code: Validate HMAC').item.json.body.model }}",
  "object_id": "={{ $('Code: Validate HMAC').item.json.body.data.id }}",
  "object_data": "={{ $('Code: Validate HMAC').item.json.body.data }}",
  "username": "={{ $('Code: Validate HMAC').item.json.body.username }}",
  "request_id": "={{ $('Code: Validate HMAC').item.json.headers['x-request-id'] }}"
}
```

### 7. Postgres: audit "received"
```sql
INSERT INTO monitoring_audit_log
    (workflow, action, object_type, netbox_id, trigger_source,
     correlation_id, actor)
VALUES
    ('wf-netbox-router', 'noop', $1, $2, 'webhook', $3, $4);
```
Parâmetros: `model`, `object_id`, `correlation_id`, `username`.

### 8. Switch: classify event+model
**Node type:** Switch
**Mode:** Expression
**Expression:** `{{ $json.model }}_{{ $json.event }}`

Regras:

| Output | Match | Sub-workflow |
|--------|-------|--------------|
| 0 | `dcim.device_created` | wf-onboard-device |
| 1 | `dcim.device_updated` | wf-onboard-device |
| 2 | `dcim.device_deleted` | wf-decommission-device |
| 3 | `circuits.circuit_created` | wf-onboard-circuit |
| 4 | `circuits.circuit_updated` | wf-onboard-circuit |
| 5 | `circuits.circuit_deleted` | wf-decommission-circuit |
| 6 | `tenancy.tenant_created` | wf-onboard-tenant |
| 7 | `tenancy.tenant_updated` | wf-onboard-tenant |
| 8 | `dcim.interface_updated` | wf-onboard-interface |
| Default | * | (audit skipped) |

> **Sprint 1**: implemente apenas outputs 0, 1, 2 (device). O resto vai para `wf-onboard-stub` que apenas grava audit `skipped`.

### 9. Execute Workflow (cada branch)
**Node type:** Execute Workflow
**Mode:** Run once with all items
**Source:** Database (workflow ID)
**Wait for sub-workflow:** **NO** — fire and forget

Pass data:
```json
{
  "correlation_id": "={{ $json.correlation_id }}",
  "event": "={{ $json.event }}",
  "object_id": "={{ $json.object_id }}",
  "object_data": "={{ $json.object_data }}",
  "dry_run": "={{ $env.DRY_RUN === 'true' }}"
}
```

### 10. Respond to Webhook
**Status:** 200
**Body:**
```json
{
  "status": "queued",
  "correlation_id": "={{ $json.correlation_id }}",
  "model": "={{ $json.model }}",
  "event": "={{ $json.event }}"
}
```

### 11. Error Trigger (workflow-level)
**Node type:** Error Trigger (separado, conecta a wf-error-handler)

Quando qualquer node acima falha, dispara `wf-error-handler` com payload original + erro.

---

## Smoke test

### A. Sem HMAC válido
```bash
curl -X POST https://n8n.k3g.internal/webhook/netbox-router \
  -H 'Content-Type: application/json' \
  -d '{"event":"created","model":"dcim.device","data":{"id":1}}'
```
**Esperado:** 401 `{"error":"invalid-hmac"}`.
**Verificar:** Nada gravado em audit_log.

### B. Com HMAC válido (gerar com script abaixo)
```bash
SECRET="$(grep NETBOX_WEBHOOK_SECRET .env | cut -d= -f2)"
BODY='{"event":"updated","model":"dcim.device","data":{"id":1,"name":"test"}}'
SIG=$(echo -n "$BODY" | openssl dgst -sha512 -hmac "$SECRET" | awk '{print $2}')

curl -X POST https://n8n.k3g.internal/webhook/netbox-router \
  -H 'Content-Type: application/json' \
  -H "X-Hook-Signature: $SIG" \
  -H "X-Request-ID: test-$(date +%s)" \
  -d "$BODY"
```
**Esperado:** 200 `{"status":"queued",...}`.
**Verificar:**
- `webhook_dedup` tem 1 linha.
- `monitoring_audit_log` tem 1 linha com `workflow='wf-netbox-router', action='noop'`.

### C. Mesmo request_id 2x
Repetir o curl B com mesmo `X-Request-ID`.
**Esperado 2ª vez:** 200 `{"status":"duplicate"}`.

### D. Stub do sub-workflow
Antes de implementar `wf-onboard-device`, criar stub que grava audit `skipped`. Garante que router está chamando corretamente.

---

## Performance esperada

- p50: < 100ms
- p95: < 300ms
- p99: < 500ms

Se ultrapassar, revisar query Postgres e timeouts.
