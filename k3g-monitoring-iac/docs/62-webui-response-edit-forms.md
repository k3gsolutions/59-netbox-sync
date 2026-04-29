# FASE 3.9.3 — Web UI Response Edit Forms

> Superseded by `docs/62-webui-response-form.md` in FASE 3.10.

**Date:** 2026-04-29
**Status:** ✅ COMPLETE
**Files Created:** 
- webui/services/validators.py
- webui/services/response_forms.py
- webui/templates/response_edit.html
**Files Updated:**
- webui/app.py (new routes)

## Objetivo

Permitir que times (Service, Network Ops, BGP) preencham/editem informações faltantes diretamente na Web UI, salvando respostas localmente em CSV/JSON sem escrita em NetBox.

## Importante

**Esta é edição LOCAL apenas, sem NetBox write:**
- POST salva em: `reports/pilot-device-compliance/week1-responses/`
- Nenhuma chamada NetBox API
- Nenhuma criação automática ApprovalRecord
- Nenhuma criação automática ApplyPlan
- Nenhum /sync call
- Nenhuma alteração equipamento

## Rotas Implementadas

### GET /service-engagement/{device}/responses/edit
Display formulário de edição com campos por time.

**Response:** HTML form com 3 fieldsets (Service Team, Network Ops, BGP Team)

### POST /service-engagement/{device}/responses/edit
Submit formulário com validação client-side + server-side.

**Request Body:** JSON com campos do formulário

**Response:** JSON
```json
{
  "success": true,
  "message": "Response saved to ...",
  "csv_path": "/path/to/csv"
}
```

ou erro:
```json
{
  "success": false,
  "errors": ["field: error message", ...]
}
```

## Campos por Time/Object Type

### Service Team (subinterface)
- object_key* (nome interface)
- tenant* (cliente/tenant)
- service_type* (customer-internet, customer-l3vpn, etc.)
- criticality (platinum/gold/silver/bronze)
- owner* (responsável)
- evidence* (ticket/contrato/ref)
- notes (opcional)

**Status válidos:** pending, answered, needs_clarification, blocked, rejected

### Network Ops (IP address)
- object_key* (IP ou descrição)
- interface* (nome interface válida)
- vrf* (_public_ ou VRF name)
- service_relation (tenant/serviço relacionado)
- owner* (responsável)
- evidence* (ticket/ref)
- notes (opcional)

### BGP Team (BGP peer)
- object_key* (peer name)
- remote_asn* (1-4294967295)
- remote_bgp_group* (slug válido)
- policy_intent* (BGP policy objectives)
- owner* (responsável)
- criticality (platinum/gold/silver/bronze)
- notes (opcional)

**\* = required se status=answered**

## Validações Implementadas

### Server-side (validators.py)

1. **Service Type**
   - Valores permitidos: customer-internet, customer-l2vpn, etc.
   - Requerido se status=answered

2. **Criticality**
   - Valores: platinum, gold, silver, bronze
   - Requerido quando aplicável

3. **Owner**
   - Min 3 chars, max 100
   - Requerido se status=answered

4. **Evidence**
   - Min 5 chars, max 500
   - Requerido se status=answered

5. **Remote ASN (BGP)**
   - Numérico, 1-4294967295
   - Requerido se status=answered

6. **Remote BGP Group**
   - Regex: `^[a-zA-Z0-9\-_.]+$`
   - Requerido se status=answered

7. **Interface**
   - Patterns: Eth-TrunkX, GigabitEthernetX/X/X, LoopBackX, etc.
   - Requerido se status=answered

8. **VRF**
   - Alphanumeric + hyphen/underscore
   - ou "_public_"
   - Requerido se status=answered

9. **Blocked Keywords**
   - Bloqueados: password, token, secret, api_key, ssh_key, private_key
   - Validação em todos campos

10. **Status**
    - Valores: pending, answered, needs_clarification, blocked, rejected

### Client-side (response_edit.html)
- Real-time validation visual
- Required attribute em HTML5
- Maxlength enforcement

## Salvamento de Dados

### CSV (response_forms.py: save_response_csv)
**Path:** `reports/pilot-device-compliance/week1-responses/{team}-response.csv`

Colunas:
- timestamp (ISO8601)
- team
- object_key
- status
- tenant, service_type, criticality, owner, evidence
- remote_asn, remote_bgp_group, policy_intent
- interface, vrf
- notes

### Audit JSON (response_forms.py: save_response_audit)
**Path:** `reports/pilot-device-compliance/week1-responses/{team}-response.audit.json`

Estrutura:
```json
[
  {
    "timestamp": "2026-04-29T12:34:56+00:00",
    "team": "service-team",
    "object_key": "Eth-Trunk1",
    "data": { ... },
    "source": "webui_form"
  }
]
```

### Audit Log (response_forms.py: update_edit_audit_log)
**Path:** `reports/pilot-device-compliance/week1-responses/edit-audit-log.md`

Markdown com:
- Timestamp
- Team
- Object changed
- Fields changed
- Validation result
- Source

## UX Features

### Form Display
- Fieldset agrupado por time
- Show/hide dinâmico baseado em team selecionado
- Validação visual em tempo real

### Buttons
- "Save Response Locally"
- "Clear Form"

### Success Message
- Badge verde com path do CSV
- Sugere rodar validate_week1_responses.py

### Error Display
- Lista vermelha com erros por campo
- Não submete se erros

## Segurança

### Protection
- ✅ safe_resolve_path bloqueado (path traversal)
- ✅ Blocked keywords detectados (password/token/secret)
- ✅ Nenhum arquivo upload (fixed output path)
- ✅ HTML escaped (Jinja2)
- ✅ Request JSON parsed safe
- ✅ Localhost only (127.0.0.1:8890)

### O que NÃO faz
- ❌ Não cria ApprovalRecord
- ❌ Não cria ApplyPlan
- ❌ Não chama NetBox API
- ❌ Não faz /sync
- ❌ Não executa apply
- ❌ Não edita equipamento

## Testing

### Testes em test_webui_safety.py

```bash
python3 tools/local/test_webui_safety.py
```

Testes incluem:
1. Validator service_type
2. Validator remote_asn
3. Blocked keywords detection
4. Allowed POST routes (only /service-engagement/{device}/responses/edit)

### Manual Testing

```bash
# 1. Start Web UI
python3 -m uvicorn webui.app:app --host 127.0.0.1 --port 8890

# 2. Visit form
curl http://127.0.0.1:8890/service-engagement/4WNET-MNS-KTG-RX/responses/edit

# 3. Submit response
curl -X POST http://127.0.0.1:8890/service-engagement/4WNET-MNS-KTG-RX/responses/edit \
  -H "Content-Type: application/json" \
  -d '{
    "team": "service-team",
    "object_type": "subinterface",
    "object_key": "Eth-Trunk1",
    "status": "answered",
    "tenant": "Customer A",
    "service_type": "customer-internet",
    "criticality": "gold",
    "owner": "John Doe",
    "evidence": "Ticket #12345",
    "notes": "Test submission"
  }'

# 4. Check CSV created
cat reports/pilot-device-compliance/week1-responses/service-team-response.csv
```

## Limitações

- No file upload (fixed paths only)
- Max 500 chars evidence/policy_intent
- No batch submit (one-by-one)
- No editing existing responses (append only to CSV)
- No delete functionality

## Próximas Fases

- Response validation script (validate_week1_responses.py)
- Manual human review dashboard
- Comparison before/after service metadata collection
- Integration com approval workflow (Week 2)

## Confirmações

- ✅ POST permitido ONLY para /service-engagement/{device}/responses/edit
- ✅ Todos outros POSTs bloqueados
- ✅ Local save apenas (week1-responses/)
- ✅ Nenhuma NetBox API call
- ✅ Nenhuma ApprovalRecord auto-creation
- ✅ Validação server-side + client-side
- ✅ Audit trail completa
- ✅ Path traversal bloqueado
- ✅ Blocked keywords detectados
- ✅ Secrets não armazenados
