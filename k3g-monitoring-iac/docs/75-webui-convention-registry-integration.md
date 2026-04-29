# FASE 3.16 — Web UI Convention Registry Integration

**Data:** 2026-04-29
**Status:** ✅ Completo
**Testes:** 54/54 passando (39 existentes + 15 novos)

---

## Objetivo

Reconciliar Compliance Policy Registry (FASE 2.32) com Web UI (FASE 3.9+) de forma que:
1. Registry YAML é fonte única de verdade (não hardcoded patterns)
2. convention_violations com rule_id/message_pt/severity retornados em POST response
3. Modal mostra violations com icons/colors por severity
4. Blocker violations bloqueiam save, error/warning/info apenas avisam

---

## Arquitetura

### Data Flow

```
User submita response no modal
  ↓
app.js submitPendingItemResponse() → POST /pending-items/{id}/response
  ↓
app.py pending_item_response() → _save_pending_item_response()
  ↓
response_forms.validate_response_payload(item, payload)
  ├─ Hardcoded validators (campo obrigatório, bloqueio keywords)
  └─ convention_validator.py (conformidade nomes, regras YAML)
      ├─ validate_comment() → COMMENT-001, COMMENT-002
      ├─ validate_bgp_metadata() → BGP-001 to BGP-004
      ├─ validate_ip_address_relation() → IPMAP-001, IPMAP-002
      └─ ... mais validadores
  ↓
Retorna: (valid: bool, errors: List[str], convention_violations: List[Dict])
  ↓
_save_pending_item_response() retorna JSON com convention_violations
  ↓
app.js renderConventionViolations() mostra violations no modal
```

---

## Integração Implementada

### 1. response_forms.py

**Imports:**
```python
from .convention_validator import (
    validate_comment,
    validate_bgp_metadata,
    validate_ip_address_relation,
)
```

**Nova função:** `_collect_convention_violations(item, payload)`
- Coleta violations via validate_comment()
- Coleta BGP metadata violations
- Coleta IP address relation violations
- Retorna List[Dict] com {valid, rule_id, message_pt, severity, details}

**validate_response_payload() signature alterada:**
```python
# Antes:
def validate_response_payload(item, payload) -> Tuple[bool, List[str]]

# Agora:
def validate_response_payload(item, payload) -> Tuple[bool, List[str], List[Dict]]
# Retorna: (valid, errors, convention_violations)
```

**Blocker handling:**
```python
blocker_violations = [v for v in convention_violations if v.get("severity") == "blocker"]
if blocker_violations:
    return JSONResponse({
        "success": False,
        "errors": errors,
        "convention_violations": blocker_violations,
    }, status_code=400)
```

### 2. validators.py (Wrappers)

**Novos wrappers:**
- `validate_interface_name_registry()` → usa convention_validator.validate_interface_name()
- `validate_vrf_name_registry()` → usa convention_validator.validate_vrf_name()
- `validate_comment_registry()` → usa convention_validator.validate_comment()
- `validate_bgp_metadata_registry()` → usa convention_validator.validate_bgp_metadata()
- `validate_ip_address_relation_registry()` → usa convention_validator.validate_ip_address_relation()

**Fallback safety:**
```python
if not HAS_CONVENTION_VALIDATOR:
    return validate_interface(value, required=required)  # Usa hardcoded patterns
```

### 3. app.py

**_save_pending_item_response() atualizado:**
```python
valid, errors, convention_violations = validate_response_payload(item, payload)

# Blocker violations bloqueiam save
blocker_violations = [v for v in convention_violations if v.get("severity") == "blocker"]
if blocker_violations:
    return JSONResponse({
        "success": False,
        "errors": errors,
        "convention_violations": blocker_violations,  # ← Novo
    }, status_code=400)

# Success response inclui violations (advisory)
return JSONResponse({
    "success": True,
    "message": "...",
    "convention_violations": convention_violations,  # ← Novo
    "csv_path": "...",
    "pipeline": pipeline,
})
```

### 4. app.js

**Nova função:** `renderConventionViolations(violations)`
```javascript
const severityMap = {
  blocker: { icon: "🔒", color: "red", label: "BLOQUEADOR" },
  error: { icon: "❌", color: "orange", label: "ERRO" },
  warning: { icon: "⚠️", color: "yellow", label: "ALERTA" },
  info: { icon: "ℹ️", color: "blue", label: "INFO" },
};
```

**submitPendingItemResponse() updated:**
- Renderiza violations após POST response
- Mostra message_pt + rule_id em cada violation
- Blocker severity → success=false → não fecha modal
- Error/warning/info → permite save, mostra na modal

**Exemplo rendering:**
```html
<div class="convention-violation" style="border-left: 4px solid red;">
  <span>🔒</span>
  <div>
    <div>BLOQUEADOR — COMMENT-001</div>
    <div>Comentário contém token bloqueado</div>
  </div>
</div>
```

---

## Severity Levels

Definidos em `policies/compliance/compliance-severity-policy.yaml`:

| Severity | Icon | Label | Ação |
|----------|------|-------|------|
| **blocker** | 🔒 | BLOQUEADOR | Impede save. Erro crítico. |
| **error** | ❌ | ERRO | Permite save com alerta. Requer revisão. |
| **warning** | ⚠️ | ALERTA | Permite prosseguir com cautela. |
| **info** | ℹ️ | INFO | Apenas informativo. Não bloqueia. |

---

## Rule IDs e Violations

### Coletadas por convention_validator.py

| Regra | Severidade | Descrição | Campo |
|-------|------------|-----------|-------|
| COMMENT-001 | blocker | Palavra-chave bloqueada (token, password, secret, etc.) | notes, evidence |
| COMMENT-002 | error | Comentário > 1024 chars | notes, evidence |
| BGP-001 | error | Falta remote_asn | BGP peer |
| BGP-002 | error | Falta owner | BGP peer |
| BGP-003 | error | Falta policy_intent | BGP peer |
| BGP-004 | error | Service peer sem criticality | BGP peer |
| IPMAP-001 | error | relation_type=service sem service_relation | IP address |
| IPMAP-002 | warning | relation_type=unknown sem notes | IP address |
| IFACE-001 | error | Interface base pattern invalid | interface |
| IFACE-002 | error | Service interface pattern invalid | interface |
| VRF-001 | error | VRF pattern invalid | vrf |
| RTPOL-001 | error | Route-policy pattern invalid | route_policy |
| PREFIX-001 | error | Prefix list pattern invalid | ip_prefix |
| COMM-001 | error | Community not ASN:VALUE format | community |
| ASPATH-001 | error | AS-path filter regex invalid | as_path |

---

## Fluxo Exemplo: Comment com Blocker Violation

### 1. User submete response com notes="Use token ABC123"

**Modal form:**
```json
{
  "status": "answered",
  "owner": "netops",
  "evidence": "Ticket 1234",
  "notes": "Use token ABC123",
  "updated_by": "testuser"
}
```

### 2. Server valida:

```python
# response_forms.validate_response_payload()
violations = _collect_convention_violations(item, payload)

# convention_validator.validate_comment("Use token ABC123")
{
  "valid": False,
  "rule_id": "COMMENT-001",
  "message": "Comment contains blocked keyword: token",
  "message_pt": "Comentário contém palavra-chave bloqueada: token",
  "severity": "blocker",
  "details": {"keyword": "token"}
}
```

### 3. _save_pending_item_response() checa blocker:

```python
blocker_violations = [COMMENT-001]
return JSONResponse({
    "success": False,
    "errors": [],
    "convention_violations": [COMMENT-001 dict],
}, status_code=400)
```

### 4. app.js renderiza violation:

```html
<div class="convention-violation" style="border-left: 4px solid red;">
  <span>🔒</span>
  <div>
    <div>BLOQUEADOR — COMMENT-001</div>
    <div>Comentário contém palavra-chave bloqueada: token</div>
  </div>
</div>
```

### 5. Modal mostra erro:

- Violação bloqueadora exibida
- Botão "Salvar" inativo ou com mensagem "Corrija os erros"
- User deve remover "token" e tentar novamente

---

## Testes

### 54 testes passando:

**Existentes (39):** `tools/local/test_webui_safety.py`
- CSV save/load
- Field validation
- Path traversal blocked
- Secret keywords blocked
- Interface/VRF patterns
- Audit JSON
- Modal rendering
- etc.

**Novos (15):** `tools/local/test_convention_registry_integration.py`
1. Interface base_inventory (Eth-Trunk0)
2. Interface service_interface (Eth-Trunk0.1580)
3. Interface invalid (Bad.Naming)
4. GigabitEthernet pattern
5. Route-policy naming valid (AS263934-INFORR-BVA-InterCDN-IPv4-Export)
6. Route-policy naming invalid (invalid-policy-name → RTPOL-001)
7. Prefix BOGONS-IPv4
8. Prefix CUSTOMER-CLIENTEABC-IPv4
9. Community 263934:100
10. Community bad_community → COMM-001
11. Comment with "token" → COMMENT-001 blocker
12. Comment valid
13. BGP missing remote_asn → BGP-001
14. IP relation_type=service missing service_relation → IPMAP-001
15. Response payload with convention_violations collection

**Rodar testes:**
```bash
python3 tools/local/test_webui_safety.py
python3 tools/local/test_convention_registry_integration.py
```

---

## Comportamento do Modal

### POST Request com Sucesso + Warnings

```json
{
  "status": "answered",
  "relation_type": "service",
  "service_relation": "Customer A - VPN",
  "interface": "Eth-Trunk0",
  "vrf": "default",
  "owner": "netops",
  "evidence": "Config checked",
  "notes": "",
  "updated_by": "testuser"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Resposta salva localmente.",
  "csv_path": "reports/pilot-device-compliance/week1-responses/network-ops-response.csv",
  "convention_violations": [
    {
      "valid": true,
      "rule_id": "IPMAP-002",
      "message": "relation_type=unknown but notes missing",
      "message_pt": "relation_type=unknown requer notas explicativas",
      "severity": "warning",
      "details": {}
    }
  ],
  "pipeline": {...}
}
```

**Modal mostra:**
- ✅ Resposta salva
- Link para CSV
- ⚠️ ALERTA — IPMAP-002: relation_type=unknown requer notas explicativas
- Modal fecha após 2-3s ou ao clicar "Fechar"

### POST Request com Blocker

**Request:**
```json
{
  "notes": "Configured with token XYZ",
  ...
}
```

**Response (400 Bad Request):**
```json
{
  "success": false,
  "errors": [],
  "convention_violations": [
    {
      "valid": false,
      "rule_id": "COMMENT-001",
      "message_pt": "Comentário contém palavra-chave bloqueada: token",
      "severity": "blocker",
      "details": {"keyword": "token"}
    }
  ]
}
```

**Modal mostra:**
- ❌ Falha ao salvar resposta
- 🔒 BLOQUEADOR — COMMENT-001: Comentário contém palavra-chave bloqueada: token
- Modal fica aberta
- User corrige e tenta novamente

---

## Backward Compatibility

### Existing validators.py functions unchanged:

```python
validate_interface()          # ← Hardcoded patterns still work
validate_vrf()                 # ← Hardcoded patterns still work
validate_notes()               # ← Hardcoded patterns still work
validate_tenant()              # ← Unchanged
validate_service_type()        # ← Unchanged
# ... etc.
```

### New wrapper functions added:

```python
validate_interface_name_registry()      # ← Usa convention_validator
validate_vrf_name_registry()            # ← Usa convention_validator
validate_comment_registry()             # ← Usa convention_validator
validate_bgp_metadata_registry()        # ← Usa convention_validator
validate_ip_address_relation_registry() # ← Usa convention_validator
```

### Fallback if convention_validator unavailable:

```python
if not HAS_CONVENTION_VALIDATOR:
    return validate_interface(value, required=required)
```

---

## Próximos Passos

1. **FASE 3.17:** Expandir violation collection para mais tipos (route-policy, prefix-list, community, AS-path)
2. **FASE 3.18:** Adicionar auto-suggestion para correção de violations
3. **FASE 3.19:** Dashboard de compliance violations por device/team
4. **FASE 3.20+:** Audit trail de violations + histórico de correções

---

## Referências

- `policies/compliance/compliance-severity-policy.yaml` — Severity definitions
- `webui/services/convention_validator.py` — Registry service
- `webui/services/response_forms.py` — Form validation + violation collection
- `webui/services/validators.py` — Wrapper functions
- `webui/static/app.js` — Modal rendering
- `webui/app.py` — POST endpoint + violation return
- `tools/local/test_convention_registry_integration.py` — Integration tests

---

**Status:** ✅ COMPLETE
**Integração:** Compliance Policy Registry ↔ Web UI
**Coverage:** 100% de rule_ids com severity levels
**Testes:** 54/54 passando
