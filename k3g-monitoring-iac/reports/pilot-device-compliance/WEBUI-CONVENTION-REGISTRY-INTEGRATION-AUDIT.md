# Auditoria de Integração Web UI × Registry

**Fase:** FASE 3.16
**Data:** 2026-04-29
**Objetivo:** Reconciliar Compliance Policy Registry (FASE 2.32) com Web UI (FASE 3.9+)

---

## 1. Arquivos Auditados

| Arquivo | Tipo | Linhas | Status |
|---------|------|--------|--------|
| `webui/services/response_forms.py` | Validation | 815 | Hardcoded patterns |
| `webui/services/validators.py` | Validators | 317 | Hardcoded patterns + rules |
| `webui/static/app.js` | Client | 440 | No convention_violations handling |
| `webui/services/convention_validator.py` | Registry service | 497 | ✅ Pronto, não importado |
| `policies/compliance/*.yaml` | Registry | 13 files | ✅ Válido, não usado |

---

## 2. Integrações Encontradas

### 2.1 response_forms.py → validators.py

**Imports:**
```python
from .validators import (
    CRITICALITIES,
    SERVICE_TYPES,
    STATUSES,
    contains_blocked_keywords,
    validate_criticality,
    validate_evidence,
    validate_interface,  # ← Hardcoded patterns
    validate_notes,       # ← Hardcoded patterns
    validate_owner,
    validate_policy_intent,
    validate_remote_asn,
    validate_remote_bgp_group,
    validate_relation_type,
    validate_service_relation,
    validate_service_type,
    validate_status,
    validate_tenant,
    validate_vrf,
)
```

**Função chave:** `validate_response_payload()` (linha 363)
- Chama `validate_interface()`, `validate_vrf()`, `validate_notes()`
- Estas funções usam regex hardcoded, NÃO consultam registry YAML
- Sem `convention_violations` no retorno JSON

### 2.2 validators.py (Hardcoded Patterns)

**Linhas 6-26:** BLOCKED_KEYWORDS duplicado
```python
BLOCKED_KEYWORDS = {
    "password", "token", "secret", "netbox_write_token",
    "private key", "bearer", "authorization", "api_key", "ssh_key", "private_key"
}
```
→ Deve importar de `convention_validator.validate_comment()`

**Linhas 138-153:** Interface patterns hardcoded
```python
patterns = [
    r'^Eth-Trunk\d+(\.\d+)?$',
    r'^GigabitEthernet\d+/\d+/\d+(\.\d+)?$',
    r'^LoopBack\d+$',
    r'^Vlanif\d+$',
    r'^10GE\d+/\d+/\d+$',
]
```
→ Deve importar de `convention_validator.classify_interface()` + `validate_interface_name()`

**Linhas 155-167:** VRF patterns hardcoded
```python
if not re.match(r'^[a-zA-Z0-9\-_]+$', value):
    return False, "VRF must contain only alphanumeric, hyphen, underscore"
```
→ Deve importar de `convention_validator.validate_vrf_name()`

**Linhas 169-176:** Notes validation sem rule_id
```python
if contains_blocked_keywords(value):
    return False, "Notes contain blocked keywords"
```
→ Deve importar de `convention_validator.validate_comment()`

### 2.3 app.js (Client-side)

**Linhas 2-10:** BLOCKED_TERMS duplicado
```javascript
const BLOCKED_TERMS = [
    "token", "password", "secret", "netbox_write_token",
    "private key", "bearer", "authorization"
];
```

**Linhas 154-157:** checkBlockedTerms() duplicado
```javascript
function checkBlockedTerms(value) {
    const lower = String(value || "").toLowerCase();
    return BLOCKED_TERMS.some((term) => lower.includes(term));
}
```

**Linhas 223-228:** Bloqueio de campos com validation hardcoded
```javascript
Object.entries(payload).forEach(([field, value]) => {
    if (String(value || "").trim() && checkBlockedTerms(value)) {
        setFieldError(field, `${field} contém palavra bloqueada`);
        ok = false;
    }
});
```

**NÃO trata `convention_violations` JSON:**
- Após POST response (linha 361-377), apenas mostra `data.errors` genéricos
- Não renderiza `convention_violations` com severity/rule_id
- Não respeita `severity=blocker` para impedir save

---

## 3. Regras Ainda Hardcoded

### 3.1 Interface Validation

| Local | Padrão | Esperado |
|-------|--------|----------|
| `validators.py:138-153` | `^Eth-Trunk\d+(\.\d+)?$` | `convention_validator.classify_interface()` |
| `app.js:238-250` | `/^Eth-Trunk\d+(\.\d+)?$/` | Mesmo validator Python |
| `response_forms.py:188` | Usa `validate_interface()` | Usa `convention_validator.validate_interface_name()` |

**Duplicação:** 3 locais (Python + JS)

### 3.2 VRF Validation

| Local | Padrão | Esperado |
|-------|--------|----------|
| `validators.py:155-167` | `^[a-zA-Z0-9\-_]+$` | `convention_validator.validate_vrf_name()` |
| `app.js:252-258` | `/^(_public_\|default\|[a-zA-Z0-9_-]+)$/` | Mesmo |
| `response_forms.py:425-428` | Usa `validate_vrf()` | Usa `convention_validator.validate_vrf_name()` |

**Duplicação:** 3 locais
**Discrepância:** `app.js` permite `_public_` e `default` que `validators.py` não explícita

### 3.3 Blocked Keywords

| Local | Palavras | Esperado |
|-------|----------|----------|
| `validators.py:6-17` | 10 keywords | `convention_validator.validate_comment()` |
| `app.js:2-10` | 7 keywords | Mesmo (incompleto!) |
| `response_forms.py:107-115` | 8 keywords | Mesmo |

**Discrepância:** `app.js` falta `api_key`, `ssh_key`, `private_key`
→ Permite blocker violations passar!

### 3.4 Route-Policy, Community, AS-Path, Prefix-List

**Não existem em validators.py nem app.js**
- Hardcoded em `convention_validator.py` apenas
- NÃO integrado ao Web UI
- BGP response não valida nome de route-policy
- Network Ops não valida prefix-list names

---

## 4. Conflitos Encontrados

### 4.1 Missing Severity Levels

**Em validators.py:**
```python
return False, "Interface format invalid: {value}"  # Sem rule_id, sem severity
```

**Em convention_validator.py:**
```python
{
    "valid": False,
    "rule_id": "IFACE-001",
    "message": "...",
    "message_pt": "...",
    "severity": "error",  # blocker/error/warning/info
    "details": {...}
}
```

**Impacto:** Web UI não sabe se erro é blocker (impede save) ou warning (permite save)

### 4.2 Missing PT-BR Messages

**Em validators.py:**
```python
return False, "VRF name pattern invalid"  # ← EN-only
```

**Em convention_validator.py:**
```python
"message_pt": "Padrão de nome VRF inválido"  # ← PT-BR
```

**Impacto:** Modal mostra apenas EN para compliance violations, confundindo operadores

### 4.3 No convention_violations in Response JSON

**response_forms.py:363-473** → `validate_response_payload()` retorna:
```python
Tuple[bool, List[str]]  # errors apenas
```

**Esperado:**
```python
{
    "success": bool,
    "errors": [...],  # Validation errors (PT-BR)
    "convention_violations": [
        {
            "valid": False,
            "rule_id": "COMMENT-001",
            "message_pt": "Comentário contém token bloqueado",
            "severity": "blocker",
            "details": {...}
        }
    ],
    "csv_path": "...",
    "message": "..."
}
```

---

## 5. Correções Aplicadas

✅ **Este é um relatório de auditoria. Correções serão aplicadas em PARTE 2-6.**

**Plano:**

| PARTE | Ação | Status |
|-------|------|--------|
| 2 | response_forms.py: importar convention_validator, retornar convention_violations | Pendente |
| 3 | validators.py: criar wrappers para convention_validator funcs | Pendente |
| 4 | app.js: renderizar convention_violations com severity/icons/colors | Pendente |
| 5 | Testes: 15 novos testes para integração | Pendente |
| 6 | Docs: docs/75-webui-convention-registry-integration.md | Pendente |

---

## 6. Resultado Final

### Status: ❌ NÃO INTEGRADO

**Achados principais:**

1. **Registry existe mas isolado**
   - `convention_validator.py` criado em FASE 2.32 ✅
   - 13 YAML files criados em FASE 2.32 ✅
   - **Mas: Nenhum arquivo Web UI importa convention_validator**

2. **Hardcoded patterns em 3 locais**
   - validators.py (patterns, blocked_keywords)
   - app.js (patterns, blocked_terms)
   - response_forms.py (usa validators.py hardcoded)

3. **Sem severity/rule_id no fluxo**
   - validators.py retorna Tuple[bool, str] genérica
   - app.js não sabe se erro bloqueia save ou avisa
   - convention_violations não são enviados no POST response

4. **Discrepâncias**
   - app.js tem 7 blocked_terms, validators.py tem 10
   - app.js permite `_public_` em VRF, validators.py não explicita
   - response_forms.py usa validators.py, nunca usa convention_validator.py

5. **Falta integração para BGP metadata**
   - Route-policy names nunca validadas
   - Prefix-list names nunca validadas
   - Community filters nunca validadas
   - AS-path filters nunca validados

### Próximos passos (PARTE 2-6):
1. response_forms.py importa convention_validator, valida naming rules, retorna convention_violations
2. validators.py cria wrappers para convention_validator (wrappers que retornam Tuple[bool, str] para compatibilidade)
3. app.js renderiza convention_violations com rule_id, message_pt, severity icons/colors
4. Testes confirmam 39+15/54 testes passando
5. Documentação explicar integração

---

**Auditoria concluída por:** convention_validator.py audit scan
**Validação:** grep + read across 5 arquivos chave
**Recomendação:** Proceder com PARTE 2 (response_forms.py integration)
