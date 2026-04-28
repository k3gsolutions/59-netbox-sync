# Staged Apply Contract — FASE 1.8

Contratos de entrada/saída para staged apply futuro.

## 1. ApplyPlan — Contrato de Entrada

ApplyPlan é gerado por `build_staged_apply_plan.py` a partir de ApprovalRecord com status=dry_run_passed.

### Estrutura

```json
{
  "apply_plan_id": "uuid",
  "approval_id": "c9363dfb-af3d-4a75-80c2-6936c36e4ecd",
  "import_plan_id": "8ffbabe3-ca0b-457d-920f-b960a073b62d",
  "device": "4WNET-MNS-KTG-RX",
  "device_id": 1890,
  "object_type": "interface",
  "object_key": "Eth-Trunk0",
  "action": "safe_create_staged",
  "category": "base_inventory",
  "confidence": "exact",
  "target_endpoint": "/api/dcim/interfaces/",
  "method": "POST",
  "staged_payload": {
    "device": 1890,
    "name": "Eth-Trunk0",
    "type": "lag",
    "enabled": true,
    "mtu": 1500,
    "description": "Base LAG interface",
    "tags": [
      {"name": "discovery:netops_netbox_sync"},
      {"name": "discovery:staged"},
      {"name": "source:device"},
      {"name": "approval:c9363dfb"}
    ],
    "custom_fields": {
      "discovery_source": "device_inventory",
      "discovery_status": "staged",
      "discovery_confidence": "exact",
      "import_plan_id": "8ffbabe3-ca0b-457d-920f-b960a073b62d",
      "approval_id": "c9363dfb-af3d-4a75-80c2-6936c36e4ecd"
    }
  },
  "payload_hash": "sha256:abc123...",
  "readiness_status": "ready",
  "readiness_checks": [
    {
      "check": "approval_id_present",
      "result": "PASSED",
      "details": "approval_id: c9363dfb-af3d-4a75-80c2-6936c36e4ecd"
    },
    {
      "check": "status_dry_run_passed",
      "result": "PASSED",
      "details": "status: dry_run_passed"
    },
    {
      "check": "action_safe_create_staged",
      "result": "PASSED",
      "details": "action: safe_create_staged"
    },
    {
      "check": "object_type_supported",
      "result": "PASSED",
      "details": "interface: supported"
    },
    {
      "check": "no_secrets_in_payload",
      "result": "PASSED",
      "details": "0 forbidden patterns found"
    },
    {
      "check": "tags_staged_present",
      "result": "PASSED",
      "details": "discovery:staged tag present"
    },
    {
      "check": "object_not_exists",
      "result": "NOT_CHECKED",
      "details": "Requires NetBox API call (not done in dry-run)"
    }
  ],
  "blocked_reasons": [],
  "generated_at": "2026-04-28T10:45:00Z",
  "generated_by_tool": "build_staged_apply_plan.py",
  "generated_by_version": "1.0",
  "write_policy": {
    "requires_write_token": true,
    "write_token_provided": false,
    "write_token_validated": false,
    "real_apply_enabled": false,
    "write_policy_enforced": "STAGE_ONLY_NO_ACTIVE"
  },
  "metadata": {
    "dry_run_report_path": "reports/pilot-device-compliance/approvals/pending/dry-run-c9363dfb.md",
    "dry_run_timestamp": "2026-04-28T06:36:18Z",
    "dry_run_hash": "sha256:abc123...",
    "netbox_readiness_check_performed": false,
    "notes": "Ready for staged import. Requires write token validation before apply."
  }
}
```

### Campos Obrigatórios

| Campo | Tipo | Descrição |
|-------|------|-----------|
| apply_plan_id | UUID | Identificador único |
| approval_id | UUID | Referência ao ApprovalRecord |
| import_plan_id | UUID | Referência ao ImportPlan |
| device | String | Hostname do equipamento |
| device_id | Integer | NetBox device ID |
| object_type | String | interface, ip_address, vrf, vlan, bgp_peer |
| object_key | String | Identificador único (Eth-Trunk0, 10.0.0.1/24) |
| action | String | safe_create_staged (ou safe_update_staged no futuro) |
| category | String | base_inventory ou service |
| confidence | String | exact, normalized, possible, ambiguous, none |
| target_endpoint | String | /api/dcim/interfaces/, etc |
| method | String | POST (PATCH/DELETE nunca) |
| staged_payload | Object | Payload para NetBox (sem secrets) |
| payload_hash | String | SHA256 do staged_payload |
| readiness_status | String | ready, blocked, simulated |
| generated_at | ISO8601 | Timestamp de geração |
| write_policy.real_apply_enabled | Boolean | Sempre false em FASE 1.9 |
| write_policy.write_token_provided | Boolean | Sempre false em FASE 1.9 |

### Campos Proibidos

❌ Nunca incluir:
- password
- token
- secret
- api_key
- ssh_key
- credential
- auth_token
- bearer_token

---

## 2. StagedPayload — Contrato

Payload sugerido para criar objeto no NetBox, pronto para future POST.

### Exemplo: Interface

```json
{
  "device": 1890,
  "name": "Eth-Trunk0",
  "type": "lag",
  "enabled": true,
  "mtu": 1500,
  "description": "Base LAG interface",
  "tags": [
    {"name": "discovery:netops_netbox_sync"},
    {"name": "discovery:staged"},
    {"name": "source:device"},
    {"name": "approval:c9363dfb"}
  ],
  "custom_fields": {
    "discovery_source": "device_inventory",
    "discovery_status": "staged",
    "discovery_confidence": "exact",
    "import_plan_id": "8ffbabe3-ca0b-457d-920f-b960a073b62d",
    "approval_id": "c9363dfb-af3d-4a75-80c2-6936c36e4ecd"
  }
}
```

### Validações

✅ Sempre incluir:
- device (ID)
- name
- type
- enabled
- tags com discovery:staged
- custom_fields.approval_id
- custom_fields.discovery_status = staged

❌ Nunca incluir:
- secrets
- passwords
- tokens
- active status
- date_created
- last_updated
- site (deixar NetBox inferir de device)

---

## 3. ApplyReadinessCheck — Contrato

Checklist de validação executado por `validate_staged_apply_plan.py`.

```json
{
  "check": "approval_id_present",
  "result": "PASSED",
  "severity": "CRITICAL",
  "details": "approval_id present and valid UUID format",
  "timestamp": "2026-04-28T10:45:00Z"
}
```

### Check Names e Lógica

| Check | Severity | Logic |
|-------|----------|-------|
| approval_id_present | CRITICAL | approval_id ≠ null, valid UUID |
| approval_id_matches | CRITICAL | approval_id = ApplyPlan.approval_id |
| status_dry_run_passed | CRITICAL | ApprovalRecord.status = dry_run_passed |
| action_safe_create_staged | CRITICAL | action = safe_create_staged |
| object_type_supported | CRITICAL | object_type ∈ {interface} (FASE 1.9) |
| object_type_not_readonly | CRITICAL | Não é IP, VRF, VLAN, BGP (FASE 1.9) |
| confidence_valid | CRITICAL | confidence ∈ {exact, normalized} |
| payload_has_no_secrets | CRITICAL | Nenhum forbidden pattern |
| tags_staged_present | CRITICAL | discovery:staged em tags |
| tags_approval_present | CRITICAL | approval:<id> em tags |
| custom_fields_valid | CRITICAL | discovery_source, discovery_status, approval_id |
| method_is_post | CRITICAL | method = POST (nunca PATCH/DELETE) |
| endpoint_is_valid | CRITICAL | endpoint começar com /api/ |
| object_not_exists | WARNING | Objeto não existe no NetBox (requer API, não checado em dry-run) |
| naming_follows_pattern | CRITICAL | Padrão válido (base interface rules) |
| service_naming_valid | CRITICAL | Service: base.vlan_id pattern |
| write_policy_enforced | CRITICAL | real_apply_enabled=false |
| write_token_not_provided | CRITICAL | write_token_provided=false |

### Result Values

- **PASSED**: Check passou
- **FAILED**: Check falhou, apply bloqueado
- **WARNING**: Check com problema, mas não bloqueia
- **NOT_CHECKED**: Requer API call (será feito em FASE 2.0)
- **SKIPPED**: Check não aplicável para este object_type

---

## 4. ApplyPlan Validation (Exemplo)

```json
{
  "validate_result": {
    "plan_id": "uuid",
    "approval_id": "c9363dfb-af3d-4a75-80c2-6936c36e4ecd",
    "validation_passed": true,
    "passed_count": 14,
    "failed_count": 0,
    "warning_count": 1,
    "not_checked_count": 1,
    "blocked_reasons": [],
    "warnings": [
      "object_not_exists check not performed (requires NetBox API)"
    ],
    "readiness_status": "ready",
    "can_apply": true,
    "validated_at": "2026-04-28T10:45:15Z",
    "exit_code": 0
  }
}
```

Exit codes:
- 0: Válido, pronto para apply (futuro)
- 1: Inválido, apply bloqueado

---

## 5. Apply Simulation (Exemplo)

Resultado de `simulate_staged_apply.py`.

```json
{
  "simulation": {
    "apply_plan_id": "uuid",
    "approval_id": "c9363dfb-af3d-4a75-80c2-6936c36e4ecd",
    "simulated_at": "2026-04-28T10:45:30Z",
    "simulation_result": "would_create_staged",
    "real_apply_executed": false,
    "predicted_response": {
      "status_code": 201,
      "message": "Created",
      "predicted_netbox_id": null,
      "notes": "ID would be assigned by NetBox on real POST"
    },
    "predicted_state_after_apply": {
      "approval_status": "applied_staged",
      "state_history_entry": {
        "from": "dry_run_passed",
        "to": "applied_staged",
        "by": "staged_apply_executor",
        "at": "2026-04-28T10:45:30Z",
        "reason": "Staged import executed via /compliance/apply"
      }
    },
    "rollback_hint": "DELETE /api/dcim/interfaces/{netbox_id}/",
    "security_notes": [
      "No real API call made",
      "No object actually created",
      "Token not used",
      "Simulation only"
    ]
  }
}
```

---

## 6. Códigos de Erro/Bloqueio

Valores possíveis em `blocked_reasons[]`.

### Críticos (Bloqueiam Apply)

```
APPROVAL_NOT_DRY_RUN_PASSED
  → status ≠ dry_run_passed

APPROVAL_NOT_FOUND
  → approval_id não existe

UNSUPPORTED_OBJECT_TYPE
  → interface: suportado
  → ip_address: não suportado em FASE 1.9
  → vrf/vlan/bgp: não suportado

UNSUPPORTED_ACTION
  → action ≠ safe_create_staged
  → ação é blocked/ignore/needs_review

SECRET_DETECTED
  → password, token, secret, api_key em payload

PAYLOAD_MISSING_REQUIRED_FIELD
  → device, name, type ausentes

OBJECT_ALREADY_EXISTS
  → objeto já existe no NetBox como active

OBJECT_TYPE_READONLY
  → BGP peer, circuit, etc (pode quebrar coisas)

AMBIGUOUS_MATCH
  → multiple objects match criteria

SERVICE_NAMING_INVALID
  → service interface: naming não é base.vlan_id

DRY_RUN_REPORT_MISSING
  → dry-run report não encontrado

DRY_RUN_REPORT_FAILED
  → dry-run report mostra erros

PAYLOAD_HASH_MISMATCH
  → payload foi alterado após dry-run

TOKEN_POLICY_NOT_VALIDATED
  → write token não validado (será FASE 2.0)

CONFIDENCE_NOT_EXACT_OR_NORMALIZED
  → confidence é ambiguous/possible/none

NAMING_DOES_NOT_FOLLOW_PATTERN
  → interface name inválido

APPLY_NOT_IMPLEMENTED
  → staged apply ainda não disponível (FASE 1.9)
```

---

## 7. Exemplo Completo: Fluxo de Eth-Trunk0

### 1. ApprovalRecord com status=dry_run_passed

```json
{
  "approval_id": "c9363dfb-...",
  "status": "dry_run_passed",
  "device": "4WNET-MNS-KTG-RX",
  "proposal": {
    "object_type": "interface",
    "object_key": "Eth-Trunk0",
    "action": "safe_create_staged",
    "confidence": "exact"
  }
}
```

### 2. Gerar ApplyPlan

```bash
python3 tools/local/build_staged_apply_plan.py \
  --approval reports/.../approvals/approved/approval-c9363dfb-*.json
```

Gera: `approval-c9363dfb-...-apply-plan.json`

### 3. Validar ApplyPlan

```bash
python3 tools/local/validate_staged_apply_plan.py \
  --plan reports/.../apply-plan.json
```

Retorna: exit code 0 (válido)

### 4. Renderizar para Markdown

```bash
python3 tools/local/render_staged_apply_plan.py \
  --plan reports/.../apply-plan.json
```

Gera: `approval-c9363dfb-...-apply-plan.md`

### 5. Simular Staged Apply

```bash
python3 tools/local/simulate_staged_apply.py \
  --plan reports/.../apply-plan.json
```

Gera: `approval-c9363dfb-...-apply-simulation.md`

Resultado: would_create_staged, real_apply_executed=false

### 6. Futuro: Apply Real (FASE 2.0)

```bash
POST /compliance/apply
{
  "approval_id": "c9363dfb-...",
  "plan_id": "uuid"
}
```

Resultado: objeto criado no NetBox com tag staged.

---

## 8. Garantias

✅ **FASE 1.9:**
- Zero API real
- Zero NetBox writes
- Apenas geração de ApplyPlan
- Apenas validação local
- Apenas simulação
- real_apply_enabled=false

✅ **FASE 2.0:**
- Escrita real
- Token write validado
- Apenas criação (POST)
- Nunca DELETE
- Nunca UPDATE de active
- Auditoria completa

---

## Referências

- [Staged Apply Design](./27-staged-apply-design.md)
- [Approval State Management](./26-approval-state-management.md)
- [ApprovalRecord Schema](./24-approval-record-schema.md)
