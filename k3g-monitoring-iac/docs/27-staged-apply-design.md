# Staged Apply Design — FASE 1.8

Design de processo futuro de aplicação staged no NetBox, com segurança e auditoria.

## 1. Princípio

**Staged Apply** é a fase futura que aplicará no NetBox apenas objetos aprovados, validados e em estado seguro.

Fluxo atual:
- Device → DeviceInventory (read-only)
- ImportPlan classifica divergências
- ApprovalRecord registra decisão humana
- Dry-run valida payload local

Fluxo futuro (FASE 2.0+):
- Staged Apply lê ApprovalRecord com status=dry_run_passed
- Cria objeto no NetBox com tag staged/planned
- Nunca ativa automaticamente
- Nunca faz DELETE
- Nunca sobrescreve objeto active

NetBox continua sendo Source of Truth.
Token write separado, nunca em repositório.
Auditoria completa: who, when, what, how.

## 2. Pré-requisitos para Staged Apply

Um item só pode entrar em staged apply se:

✅ **ApprovalRecord:**
- Status: `dry_run_passed`
- Action: `safe_create_staged` (não approve/reject/ignored)
- Confidence: `exact` ou `normalized`
- Evidence_hash presente
- state_history completo
- approval_id único

✅ **Dry-run Report:**
- Arquivo existe
- Exit code: 0 (PASSED)
- Payload contém tags staged
- Nenhum segredo detectado

✅ **Validação:**
- Object_type suportado
- Sem secrets em payload
- Service candidate com naming válido
- Base interface com padrão válido
- Não é blocked/ignored/needs_review

✅ **Regra de não-sobrescrita:**
- Objeto não existe no NetBox (ou existe mas é staged/planned)
- Não é UPDATE de objeto active
- Não é DELETE
- Não requer dados que não existem

## 3. Objetos Permitidos (Primeira Versão)

### Permitidos

- **interface base_inventory:**
  - Ethernet0/0/0
  - GigabitEthernet0/5/0
  - Eth-Trunk0
  - Management0/0/0
  - LoopBack0
  - Padrão: ^[a-zA-Z0-9/_.-]+$ (sem ponto = physical, com ponto = subinterface)

- **Regra relaxada para base:**
  - Sem tenant obrigatório
  - Sem service_type obrigatório
  - Sem criticality obrigatório
  - Apenas naming base válido

### Não Permitidos (Ainda)

- IP address (complexidade de VRF/assignment)
- VRF (pode quebrar routing)
- VLAN (pode quebrar segmentação)
- BGP peer (configuration-driven)
- Circuit (carrier agreement)
- L2VPN (service dependency)
- Route-policy, prefix-list, community-list
- UPDATE de objeto existente (até FASE 2.5)
- DELETE (nunca automático)
- Interface service (subinterface com dependência)

## 4. Métodos Futuros por Objeto

### Interface Missing in NetBox

**Endpoint futuro:**
```
POST /api/dcim/interfaces/
```

**Método:** POST (create only)

**Body esperado:**
```json
{
  "device": 1890,
  "name": "Eth-Trunk0",
  "type": "lag",
  "enabled": true,
  "mtu": 1500,
  "description": "Base LAG interface",
  "tags": [
    {
      "name": "discovery:netops_netbox_sync"
    },
    {
      "name": "discovery:staged"
    },
    {
      "name": "source:device"
    },
    {
      "name": "approval:c9363dfb"
    }
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

**Status esperado no NetBox:**
- Criado com status staged/planned
- Nunca active por padrão
- Requer ação manual para ativar

## 5. Regras de Bloqueio

Bloquear staged apply se:

```
❌ approval_id ausente
❌ status ≠ dry_run_passed
❌ action ≠ safe_create_staged
❌ object_type não suportado
❌ confidence ∉ {exact, normalized}
❌ payload contém forbidden pattern (password, token, secret, api_key, ssh)
❌ operação é PATCH/DELETE
❌ objeto já existe no NetBox como active
❌ service interface sem naming válido
❌ required fields ausentes (device, name, type)
❌ dry-run report não existe
❌ dry-run report mostra FAILED
❌ ApprovalRecord alterado após dry-run
❌ token write ausente
❌ token write igual ao token read-only
❌ matching device ambíguo
```

## 6. Dry-run Obrigatório

Antes de qualquer escrita futura no NetBox:

1. **Resolver Endpoint**
   - Mapear object_type → API endpoint
   - Validar versão NetBox
   - Validar custom_fields support

2. **Montar Payload**
   - Campos obrigatórios presentes
   - Tipos de dados corretos
   - Tags bem formadas
   - Custom fields nomeados corretamente

3. **Validar Método**
   - Apenas POST permitido
   - Nenhum PATCH/DELETE
   - Headers corretos (não enviados)

4. **Validar Tags Staged**
   - Tags discovery:staged presentes
   - Tag approval:<approval_id> presente
   - Tag source:device presente
   - Sem tags de estado active

5. **Validar Custom Fields**
   - discovery_source válido
   - discovery_status = staged
   - discovery_confidence ∈ {exact, normalized}
   - approval_id matches ApprovalRecord
   - import_plan_id matches

6. **Verificar Existência**
   - Objeto não existe no NetBox
   - Ou existe como staged/planned (pode sobrescrever)
   - Nunca sobrescreve active

7. **Gerar Fingerprint**
   - Hash SHA256 do payload
   - Incluir approval_id
   - Comparar com dry_run_hash
   - Se diferente: bloquear (ApprovalRecord mudou)

8. **Registrar Resultado**
   - Gerar relatório em Markdown
   - Incluir timestamp
   - Nenhuma escrita real no NetBox

## 7. Audit Trail Completo

Toda futura aplicação deve registrar:

```json
{
  "apply_audit": {
    "approval_id": "c9363dfb-...",
    "apply_plan_id": "uuid",
    "applied_by": "usuario@empresa.com",
    "applied_at": "2026-04-28T...",
    "target_endpoint": "/api/dcim/interfaces/",
    "method": "POST",
    "payload_hash": "sha256:abc...",
    "dry_run_hash": "sha256:abc...",
    "result": "created",
    "netbox_object_id": 12345,
    "response_status": 201,
    "rollback_hint": "DELETE /api/dcim/interfaces/12345/"
  }
}
```

State_history também atualizado:
```json
{
  "from": "dry_run_passed",
  "to": "applied_staged",
  "by": "staged_apply_executor",
  "at": "2026-04-28T...",
  "tool_version": "1.0",
  "reason": "Staged import executed via /compliance/apply"
}
```

## 8. Estados Futuros (Não Implementar Ainda)

### Estados depois FASE 1.9

- **dry_run_passed** (final FASE 1.7)
- **apply_ready** (FASE 1.9 output)
- **apply_blocked** (FASE 1.9 bloqueado)
- **apply_simulated** (FASE 1.9 simulação)

### Estados muito futuros (FASE 2.0+)

- **applied_staged** (criado no NetBox com tag staged)
- **apply_failed** (erro ao criar)
- **rollback_required** (erro pós-apply)

Não implementar ainda.

## 9. Garantias de Segurança

✅ **Read-only agora:**
- Nenhuma API real
- Nenhuma escrita NetBox
- Nenhum token write
- Apenas validação local

✅ **Write policy futuro:**
- Token write separado, nunca em código
- Token read-only nunca tem permissão write
- Validar token antes de aplicar
- Falhar se tokens iguais

✅ **Sem delete automático:**
- Nunca DELETE
- Nunca PATCH de active
- Criar como staged/planned
- Requer ação manual para ativar

✅ **Sem sobrescrita:**
- Verificar objeto não existe
- Se existe como staged: permitir UPDATE com PATCH
- Se existe como active: BLOQUEAR
- Logging completo

✅ **Auditoria completa:**
- Who: reviewed_by, applied_by
- When: reviewed_at, applied_at
- What: approval_id, object_type, object_key
- How: payload_hash, dry_run_hash
- Result: result, netbox_object_id
- Rollback: rollback_hint

## 10. Fora de Escopo (FASE 1.8)

❌ Escrita real no NetBox
❌ Token write real
❌ Endpoint HTTP /compliance/apply
❌ UI (será FASE 2.0)
❌ RBAC/autenticação
❌ Apply em lote
❌ UPDATE/DELETE
❌ BGP/VRF/VLAN configuration
❌ Aplicar configuração em equipamento

## 11. Critérios de Aceite (FASE 1.8)

✅ Design documentado
✅ Objetos permitidos/bloqueados claros
✅ Regras de segurança claras
✅ Dry-run obrigatório explicado
✅ Audit trail design definido
✅ Staged apply ainda não implementado (FASE 1.9)
✅ Nenhuma API chamada
✅ Nenhuma escrita NetBox
✅ Contratos de entrada/saída definidos

## 12. Próxima Fase (FASE 1.9)

FASE 1.9 implementará:
- **build_staged_apply_plan.py**: gerar ApplyPlan local
- **validate_staged_apply_plan.py**: validar ApplyPlan
- **render_staged_apply_plan.py**: Markdown
- **simulate_staged_apply.py**: simular resultado

Tudo local. Zero API. Zero NetBox writes.

## Referências

- [Approval State Management](./26-approval-state-management.md)
- [ApprovalRecord Schema](./24-approval-record-schema.md)
- [Approval Dry-Run](./25-approval-dry-run.md)
