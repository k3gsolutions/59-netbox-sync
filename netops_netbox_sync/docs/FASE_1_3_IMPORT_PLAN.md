# ImportPlan Read-Only — FASE 1.3

Classificação de divergências em ações de importação (sem writes ao NetBox).

## Visão geral

ImportPlan analisa cada divergência do compliance e classifica em:
- **safe_create_staged** — candidatos a importação automática
- **needs_review** — requer decisão humana
- **blocked** — não pode importar (dados insuficientes)
- **ignore** — não é candidato de importação

Nenhuma escrita no NetBox. Nenhuma execução. Apenas recomendações.

## Schemas

### ImportAction (enum)
```
safe_create_staged
needs_review
blocked
ignore
```

### ConfidenceLevel (enum)
```
exact        — alta confiança (validação bem definida)
normalized   — confiança média (após normalização)
possible     — confiança baixa (incerteza)
ambiguous    — muito baixa (não claro)
none         — não aplicável
```

### ImportPlanItem
```json
{
  "action": "safe_create_staged",
  "object_type": "interface",
  "object_key": "ge-0/0/0",
  "code": "INTERFACE_MISSING_IN_NETBOX",
  "reason": "Candidato a staged import (naming válida)",
  "evidence": {
    "interface": "ge-0/0/0",
    "status": "up"
  },
  "naming_compliant": true,
  "confidence": "exact",
  "preferred_next_step": "Revisar payload sugerido e aplicar staged import"
}
```

### ImportPlan
```json
{
  "device": "router-1",
  "device_id": 456,
  "generated_at": "2026-04-28T12:34:56Z",
  "source": "compliance",
  "total_items": 5,
  "safe_create_staged_count": 1,
  "needs_review_count": 2,
  "blocked_count": 1,
  "ignore_count": 1,
  "items": [...]
}
```

## Regras de classificação

### 1. Sem contexto de objeto

Se divergência não tiver `object_type` ou `object_key`:
- Se code termina com `_MISSING_IN_NETBOX` → **needs_review** (sem ID claro)
- Senão → **ignore** (divergência agregada)

### 2. Missing on device

Se code termina com `_MISSING_ON_DEVICE`:
- → **needs_review** (objeto no NetBox, faltando no device = problema no device)

### 3. Description non-compliant

Se code = `DESCRIPTION_NON_COMPLIANT`:
- → **needs_review** (correção requer intervenção)

### 4. BGP peers

Se object_type = `bgp_peer`:
- → **needs_review** (relacionamentos complexos, sempre requer revisão)

### 5. Metadata ambígua

Se scope ∈ {`unknown`, `ambiguous`} ou metadata insuficiente:
- → **blocked** (não pode processar)

### 6. Missing in NetBox — Interfaces

Se code termina com `_MISSING_IN_NETBOX` E object_type = `interface`:

**6a. Base infrastructure (física, LAG, management):**
- Padrões: `Eth-Trunk0`, `Ethernet0/0/0`, `GigabitEthernet0/5/0`, `10GE...`, `100GE...`, `Management`, etc
- → **safe_create_staged** (confiança: exact)
- Motivo: `base_interface_inventory`
- Nota: Não requer naming de serviço

**6b. Service interface/subinterface com naming válido:**
- Subinterfaces (contêm ponto): `Eth-Trunk0.1580`, `GigabitEthernet0/5/0.100`
- Interfaces com descrição de serviço/cliente
- Interfaces com IP/VRF/VLAN aplicado
- → **safe_create_staged** (confiança: exact)
- Motivo: `service_interface_conforme`

**6c. Service interface com naming inválido:**
- Subinterface ou service com caracteres inválidos
- → **needs_review** (confiança: exact)
- Motivo: `naming_convention_failed`
- Não pode virar `safe_create_staged`

**6d. Interface desconhecida (nem base nem service claro):**
- → Validar naming convention
- Se inválido → **needs_review**
- Se válido → **safe_create_staged**

### 7. Missing in NetBox — Outros tipos

Se code termina com `_MISSING_IN_NETBOX` E object_type ≠ `interface`:

**7a. Naming inválida:**
- → **needs_review** com reason=`naming_convention_failed`
- (NUNCA vira `safe_create_staged`)

**7b. Naming válida, tipo elegível:**
- Tipos elegíveis: `ip_address`, `vrf`, `vlan`
- → **safe_create_staged** (confiança: exact)

**7c. Naming válida, tipo não elegível:**
- → **needs_review** (tipo requer análise específica)

### 8. Padrão default

Tudo mais → **needs_review** com confiança: `possible`

## Base Interface Inventory

Interfaces base/físicas podem ser importadas sem naming de serviço:

**Base patterns (sempre safe_create_staged se missing):**
- Eth-Trunk, ae, bundle-ether (LAGs)
- Ethernet, GigabitEthernet, FastEthernet (físicas)
- 10GE, 25GE, 40GE, 100GE (velocidades altas)
- Management, mgmt, mgt (gerência)
- LoopBack + número (loopback puro)

**Exemplos:**
- `Eth-Trunk0` → safe_create_staged (base)
- `GigabitEthernet0/5/0` → safe_create_staged (base)
- `100GE1/0/1` → safe_create_staged (base)
- `Management0` → safe_create_staged (base)
- `LoopBack0` → safe_create_staged (base)

**NÃO base (requerem naming ou análise):**
- Subinterfaces com ponto: `Eth-Trunk0.100`
- Interfaces virtuais: `Vlan100`, `irb`, `Virtual`
- NULL/NULL0 (ignoradas)

## Validação de naming convention

### interface
Pattern para base: `^[a-zA-Z0-9/_-]+$` (ponto não permitido)
Pattern para service: `^[a-zA-Z0-9/_.-]+$` (ponto permitido para subinterfaces)

Exemplos válidos base:
- `ge-0/0/0`
- `GigabitEthernet0/0/0`
- `eth0`
- `Eth-Trunk0`

Exemplos válidos service:
- `Eth-Trunk0.1580`
- `GigabitEthernet0/5/0.100`

Exemplos inválidos:
- `Invalid@Name`
- `Bad!Interface`

### ip_address
Validar como IPv4 ou IPv6 (com ou sem CIDR).

Exemplos válidos:
- `10.0.0.1/24`
- `192.168.1.1`
- `2001:db8::1/64`

### vrf
Pattern: `^[a-zA-Z0-9_-]+$`

Exemplos válidos:
- `prod_vrf`
- `vrf-internal`
- `mgmt`

### vlan
Numeric ID entre 1-4094.

Exemplos válidos:
- `100`
- `1`
- `4094`

### bgp_peer
Validar como IPv4 ou IPv6.

## Endpoints

### POST /compliance/import-plan

Executar análise e retornar ImportPlan em JSON.

Request (igual a `/compliance/analyze`):
```json
{
  "device": {
    "host": "10.0.0.1",
    "username": "admin",
    "password": "secret",
    "port": 22
  },
  "device_id": 456,
  "netbox": {
    "url": "http://netbox:8080",
    "token": "...",
    "verify_ssl": false
  }
}
```

Response:
```json
{
  "device": "router-1",
  "device_id": 456,
  "generated_at": "2026-04-28T12:34:56Z",
  "source": "compliance",
  "total_items": 5,
  "safe_create_staged_count": 1,
  "needs_review_count": 2,
  "blocked_count": 1,
  "ignore_count": 1,
  "items": [...]
}
```

### POST /compliance/import-plan/report

Executar análise e retornar relatório em Markdown.

Request: igual a acima.

Response: Markdown com 6 seções:
1. Resumo
2. Safe create staged
3. Revisão humana obrigatória
4. Bloqueados
5. Ignorados
6. Observações de segurança

## Garantias de segurança

✅ **Read-only**
- Nenhuma conexão ao NetBox para escrita
- Nenhuma stagd import executada
- Nenhum comando enviado ao device
- Nenhum token de escrita utilizado

✅ **Sem credenciais**
- Nenhuma senha ou token no output
- Nenhum payload com secrets

✅ **Sem operações destrutivas**
- Nunca gera ação de DELETE
- Nunca gera UPDATE automático em objeto existente
- Sempre requer aprovação humana para write

## Exemplos

### Exemplo 1: Interface missing com naming válido

Input (divergência):
```json
{
  "code": "INTERFACE_MISSING_IN_NETBOX",
  "severity": "medium",
  "scope": "interfaces",
  "object_type": "interface",
  "object_key": "ge-0/0/0",
  "evidence": {"interface": "ge-0/0/0", "status": "up"}
}
```

Output (item):
```json
{
  "action": "safe_create_staged",
  "object_type": "interface",
  "object_key": "ge-0/0/0",
  "naming_compliant": true,
  "confidence": "exact",
  "preferred_next_step": "Revisar payload sugerido e aplicar staged import"
}
```

### Exemplo 2: Interface missing com naming inválido

Input:
```json
{
  "code": "INTERFACE_MISSING_IN_NETBOX",
  "object_type": "interface",
  "object_key": "Bad@Interface"
}
```

Output:
```json
{
  "action": "needs_review",
  "object_key": "Bad@Interface",
  "reason": "Fora da naming convention (interface: Bad@Interface)",
  "naming_compliant": false,
  "confidence": "exact",
  "preferred_next_step": "Validar naming convention antes de importar"
}
```

### Exemplo 3: BGP peer

Input:
```json
{
  "code": "BGP_PEER_MISSING_IN_NETBOX",
  "object_type": "bgp_peer",
  "object_key": "10.0.0.1"
}
```

Output:
```json
{
  "action": "needs_review",
  "object_type": "bgp_peer",
  "reason": "BGP peer: relacionamentos complexos, requer revisão manual",
  "confidence": "possible",
  "preferred_next_step": "Validar BGP configuration e relacionamentos"
}
```

## Testes

27 testes cobrindo:
- ✅ Interface missing com naming válido/inválido
- ✅ IP address, VRF, VLAN missing (safe_create_staged)
- ✅ BGP peer (always needs_review)
- ✅ Missing on device (needs_review)
- ✅ Description non-compliant (needs_review)
- ✅ Divergências agregadas (ignore)
- ✅ Metadata ambígua (blocked)
- ✅ Nenhuma ação delete gerada
- ✅ Markdown renderiza todas as seções
- ✅ Segurança: read-only, sem credenciais

Rodar:
```bash
PYTHONPATH=. pytest app/tests/test_import_plan*.py -q
```

## Próximos passos

- FASE 1.3.1 — Web UI para revisar ImportPlan
- FASE 1.4 — Staged import com aprovação humana
- FASE 1.5 — CI integration para gerar planos automaticamente

## Observações

- Nenhuma mudança no NetBox até aprovação humana
- Todas as recomendações são reversíveis
- Relatório é imutável (read-only)
- Pode ser auditado completamente
