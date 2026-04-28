# wf-error-handler

Centraliza tratamento de erro de **todos** os workflows N8N: grava em audit_log + DLQ, alerta NOC via Evolution API.

**Acionado por:** Error Trigger node em qualquer workflow que falhe.

---

## Por que existe

- Garante audit consistente em caso de erro (workflows não fazem audit manual no caminho de erro).
- Decide se evento vai para retry (DLQ) ou só registra.
- Evita silenciosamente perder webhooks NetBox.
- Centraliza canal de alerta — mudar `wf-error-handler` muda comportamento de erro de toda a plataforma.

---

## Diagrama

```
[Error Trigger] (recebe payload do workflow que falhou)
    ↓
[Code: Classify error]
    │
    ├── retryable=true → [Postgres: INSERT webhook_dlq]
    │                      ↓
    │                   [Code: schedule next_retry_at]
    │
    └── retryable=false → [Postgres: audit "error"]
    ↓
[Code: Build alert message]
    ↓
[IF: severity high+]
    ↓
[HTTP: Evolution API send to NOC]
    ↓
END
```

---

## Nodes — detalhe

### 1. Error Trigger (trigger)
**Node type:** Error Trigger.

Quando outro workflow falha, este node recebe:
```json
{
  "execution": {
    "id": "...",
    "url": "https://n8n.k3g.internal/execution/...",
    "error": {
      "message": "...",
      "node": "...",
      "stack": "..."
    },
    "lastNodeExecuted": "...",
    "mode": "..."
  },
  "workflow": {
    "id": "...",
    "name": "wf-onboard-device"
  }
}
```

### 2. Code: Classify error
```javascript
const exec = $input.first().json.execution;
const wf = $input.first().json.workflow;
const error = exec.error || {};

// Classificação por tipo de erro
const message = (error.message || '').toLowerCase();
const stack = (error.stack || '').toLowerCase();

// Erros transitórios (retry)
const retryable = (
    message.includes('timeout') ||
    message.includes('econnrefused') ||
    message.includes('econnreset') ||
    message.includes('socket hang up') ||
    message.includes('502') ||
    message.includes('503') ||
    message.includes('504') ||
    message.includes('rate limit') ||
    message.includes('zabbix server is busy')
);

// Erros de validação (não retry — erro humano/configuração)
const validation = (
    message.includes('validation failed') ||
    message.includes('missing criticality') ||
    message.includes('missing device_purpose') ||
    message.includes('unknown role') ||
    message.includes('unknown vendor') ||
    message.includes('hmac')
);

// Severidade
let severity = 'high';
if (validation) severity = 'medium';   // ação humana, mas não urgente
if (retryable) severity = 'low';       // automatic retry

// Retry budget — quantas tentativas
const max_retries = retryable ? 5 : 0;

return [{
    json: {
        workflow_name: wf.name,
        execution_id: exec.id,
        execution_url: exec.url,
        error_message: error.message || 'unknown',
        error_node: error.node || 'unknown',
        retryable,
        validation,
        severity,
        max_retries,
        original_payload: exec.lastNodeExecuted
    }
}];
```

### 3. IF: retryable?
- **Sim:** continua para nó 4 (DLQ).
- **Não:** pula para nó 7 (audit error).

### 4. Postgres: INSERT webhook_dlq
```sql
INSERT INTO webhook_dlq (
    source, event, model, body, headers,
    status, retry_count, max_retries, next_retry_at,
    last_error_msg, last_error_code, last_attempt_at
) VALUES (
    'netbox',
    $1,                                          -- event
    $2,                                          -- model
    $3,                                          -- body (JSON)
    $4,                                          -- headers (JSON)
    'pending',
    0,
    $5,                                          -- max_retries
    NOW() + INTERVAL '30 seconds',               -- primeiro retry em 30s
    $6,                                          -- error_msg
    'transient',
    NOW()
)
RETURNING id;
```

> Nota: o body original do webhook precisa estar acessível. No `wf-netbox-router`, salve uma cópia em variável de execução. No `wf-onboard-device`, passe `original_payload` no input.

### 5. Code: schedule next_retry_at
Backoff exponencial:
```javascript
const retry_count = 0;  // primeira tentativa pelo handler
const base_seconds = 30;
const next_seconds = base_seconds * Math.pow(2, retry_count);
const next_retry = new Date(Date.now() + next_seconds * 1000);

return [{ json: {
    next_retry_at: next_retry.toISOString(),
    retry_count
}}];
```

### 6. (Outro workflow consome a DLQ)
Workflow separado **`wf-dlq-processor`** (cron 1 min):
1. SELECT da DLQ onde `status IN ('pending','retrying') AND next_retry_at < NOW() AND retry_count < max_retries`.
2. Re-dispara o sub-workflow original (Execute Workflow).
3. Se sucesso → `status='resolved'`.
4. Se falha → `retry_count++`, `next_retry_at = NOW() + 30 * 2^retry_count`.
5. Se atingiu `max_retries` → `status='abandoned'` + alerta NOC severity=high.

### 7. Postgres: audit "error"
```sql
INSERT INTO monitoring_audit_log
    (workflow, action, object_type, error_msg, error_code,
     trigger_source, correlation_id, actor)
VALUES
    ($1, 'error', 'unknown', $2, $3, 'webhook', $4, 'n8n');
```

### 8. Code: Build alert message
```javascript
const data = $('Code: Classify error').item.json;

const emoji = data.severity === 'high' ? '🚨' :
              data.severity === 'medium' ? '⚠️' : 'ℹ️';

const text = [
    `${emoji} *Erro em workflow N8N*`,
    ``,
    `*Workflow:* ${data.workflow_name}`,
    `*Node:* ${data.error_node}`,
    `*Severidade:* ${data.severity}`,
    `*Retryable:* ${data.retryable ? 'sim' : 'não'}`,
    ``,
    `*Erro:*`,
    `\`\`\``,
    data.error_message.substring(0, 500),
    `\`\`\``,
    ``,
    `*Execução:* ${data.execution_url}`
].join('\n');

return [{ json: { alert_text: text, severity: data.severity } }];
```

### 9. IF: notify?
- `severity == 'high'` → notifica imediato.
- `severity == 'medium'` → notifica em horário comercial (lógica adicional ou só registrar).
- `severity == 'low'` (retry automático) → não notifica unless DLQ atingir max_retries.

### 10. HTTP: Evolution API
```json
POST {{$env.EVOLUTION_API_URL}}/message/sendText/{{$env.EVOLUTION_INSTANCE_NOC}}
Headers:
  apikey: {{$credentials.evolution_api.apikey}}
Body:
{
  "number": "{{$env.NOC_GROUP_CHATID}}",
  "text": "={{ $json.alert_text }}"
}
```

### 11. (Opcional) Movidesk: Cria ticket
Se `severity == 'high'` E não foi resolvido em 15 min, abrir ticket via Movidesk API.

---

## Lista de erros conhecidos e classificação

| Padrão erro | Categoria | Retryable? | Notify? |
|-------------|-----------|------------|---------|
| `timeout` / `ECONNREFUSED` (NetBox/Zabbix down) | transient | sim | low até DLQ atingir max |
| `502/503/504` HTTP | transient | sim | low |
| `Validation failed: missing criticality` | validation | não | medium (operador precisa cadastrar) |
| `Unknown role: xyz` | validation | não | medium (role não está no map.yaml) |
| `Zabbix: Host already exists` | logic | não | medium (drift — alguém criou direto) |
| `HMAC invalid` | security | não | high (potencial ataque) |
| `Invalid JSON in body` | malformed | não | high (NetBox bug ou MITM) |
| `dial tcp ... no route to host` | network | sim | medium |
| `pq: duplicate key value` (Postgres) | logic | não | medium |

---

## Smoke test

### A. Forçar erro de validação
1. NetBox: criar device sem `criticality`. `monitoring_enabled=true`.
2. Webhook chega → `wf-onboard-device` falha em validate.
3. **Esperado:**
   - Audit `action=error`, `error_msg='Validation failed: missing criticality'`.
   - **Não vai para DLQ** (validation, não retryable).
   - WhatsApp NOC: ⚠️ severidade medium.

### B. Forçar erro de rede (Zabbix offline)
1. Parar Zabbix temporariamente.
2. Webhook NetBox para device válido.
3. **Esperado:**
   - DLQ recebe linha com `status=pending, max_retries=5`.
   - WhatsApp NOC: ℹ️ severity low (uma única vez por janela).
   - `wf-dlq-processor` reprocessa em 30s.
   - Subir Zabbix; reprocessamento conclui com sucesso → DLQ `status=resolved`.

### C. HMAC inválido (segurança)
1. Curl direto no webhook URL com signature errado.
2. **Esperado:**
   - Router retorna 401 (não chega no error handler porque webhook router responde antes).
   - Mas se vier de outro fluxo: severity high + alerta imediato.

### D. DLQ esgotada
1. Forçar Zabbix indisponível por > 30 min.
2. Webhook chega → DLQ.
3. Reprocessador tenta 5x com backoff (30s, 1m, 2m, 4m, 8m).
4. **Esperado:** após 5ª falha, `status=abandoned` + alerta high "DLQ abandoned: NetBox device id=X".

---

## Anti-padrões

❌ Ignorar erro silenciosamente. Sempre audit, mesmo que `severity=low`.
❌ Notificar TUDO. Erros transitórios resolvem sozinhos — não inundar NOC.
❌ Hardcoded chatid/numbers. Usar env vars.
❌ Loops de retry no próprio handler. DLQ é separada para evitar loops infinitos.
❌ Dropar payload original. Sem ele, retry é impossível.
