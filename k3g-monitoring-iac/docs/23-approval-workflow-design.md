# Approval Workflow Design — FASE 1.4

Fluxo de aprovação humana para futuro Staged Import no NetBox, sem implementação de escrita ainda.

## 1. Princípio

Nenhuma proposta do ImportPlan será aplicada no NetBox sem aprovação explícita de humano.

```
DeviceInventory (SSH) → compliance divergences → ImportPlan (propostas)
                                                      ↓
                                            human review & approval
                                                      ↓
                                        (futuro) Staged Import no NetBox
```

O NetBox continua sendo Source of Truth.
O compliance report gera evidência.
O ImportPlan gera proposta.
O humano aprova, rejeita ou solicita mudanças.

## 2. Objetivo

Definir fluxo operacional para:
- revisar propostas com confiança e segurança
- auditar decisões humanas
- garantir que nenhum objeto fora da naming convention é importado
- garantir que nenhuma operação destrutiva (delete/update) é feita sem aprovação
- validar metadados suficientes antes de staged import

## 3. Estados da proposta

```
proposed
  ↓
(human review)
  ├→ approved
  │   ├→ dry_run_passed
  │   │   └→ (futuro) applied_staged
  │   └→ dry_run_failed
  │       └→ rejected
  ├→ needs_review (bloqueado, exige ação)
  ├→ request_changes (humano pede mudança)
  └→ rejected
```

Estados finais:
- `approved` — pronto para staged import futuro
- `rejected` — não será importado
- `needs_review_unresolved` — bloqueado indefinidamente
- `expired` — expirou prazo de aprovação

## 4. Ações permitidas

- `approve` — autorizar importação
- `reject` — rejeitar proposta
- `request_changes` — solicitar correção (ex: naming)
- `mark_as_ignored` — ignorar (não será revisado)
- `defer` — adiar revisão
- `expire` — expirar proposta se não revisada dentro de N dias

## 5. Campos mínimos do ApprovalRecord

```json
{
  "approval_id": "uuid",
  "import_plan_id": "uuid",
  "device": "4WNET-MNS-KTG-RX",
  "device_id": 123,

  "proposal": {
    "object_type": "interface",
    "object_key": "Eth-Trunk0",
    "action": "safe_create_staged",
    "category": "base_inventory",
    "code": "INTERFACE_MISSING_IN_NETBOX",
    "confidence": "exact",
    "naming_compliant": true
  },

  "review": {
    "status": "approved",
    "reviewed_at": "2026-04-28T14:30:00Z",
    "reviewed_by": "netops-admin",
    "decision": "approve",
    "comment": "Base inventory interface, safe to import",
    "evidence_hash": "sha256:abc...",
    "dry_run_id": "uuid"
  },

  "audit": {
    "created_at": "2026-04-28T10:00:00Z",
    "updated_at": "2026-04-28T14:30:00Z",
    "report_path": "reports/pilot-device-compliance/current/4WNET-MNS-KTG-RX-compliance-report.md",
    "source_timestamp": "2026-04-28T09:45:00Z",
    "changes_requested_count": 0
  }
}
```

## 6. Regras de aprovação

### ✅ Pode aprovar

Somente se TODOS os critérios forem satisfeitos:

- `action` = `safe_create_staged`
- `naming_compliant` = `true` OU `category` = `base_inventory`
- `confidence` ∈ {`exact`, `normalized`}
- Não há objeto conflitante no NetBox (dry-run validará)
- Payload sugerido está completo
- Evidência foi revisada
- Sem operações de delete
- Sem update de objeto ativo/em produção
- Não exige sobrescrever tenant/service_type existente

### ❌ Não pode aprovar

Se qualquer um destes for verdadeiro:

- `action` ≠ `safe_create_staged`
- `action` = `needs_review` (exige correção antes)
- `action` = `blocked` (dados insuficientes)
- `action` = `ignore` (não é candidato)
- `naming_compliant` = `false` (exige naming válido)
- `confidence` ∈ {`ambiguous`, `none`}
- Operação exigiria DELETE
- Operação exigiria UPDATE de objeto ativo
- BGP peer sem description
- Service object sem tenant
- Service object sem service_type
- IP address sem VRF claro

## 7. Diferença: Base Inventory vs Service

### Base Inventory (Estrutura)

Pode ser aprovado com metadados mínimos:

```json
{
  "object_type": "interface",
  "object_key": "Eth-Trunk0",
  "category": "base_inventory",
  "confidence": "exact",
  "payload": {
    "name": "Eth-Trunk0",
    "type": "lag",
    "enabled": true
  },
  "tags": [
    "discovery:netops_netbox_sync",
    "discovery:staged",
    "inventory:base-interface"
  ]
}
```

**Permissões elevadas:**
- Não requer tenant (inventário estrutural)
- Não requer service_type
- Não requer criticality
- Pode usar tags padrão discovery

### Service Candidate (Serviço)

Exige metadados completos:

```json
{
  "object_type": "interface",
  "object_key": "Eth-Trunk0.1580",
  "category": "service",
  "confidence": "exact",
  "payload": {
    "name": "Eth-Trunk0.1580",
    "type": "virtual",
    "enabled": true,
    "tenant_id": 5,
    "service_type_id": 12,
    "description": "Cliente: Operator-A"
  },
  "tags": [
    "discovery:netops_netbox_sync",
    "discovery:staged",
    "source:device",
    "tenant:operator-a"
  ]
}
```

**Restrições:**
- Tenant obrigatório
- Service_type obrigatório
- Criticality recomendado
- Description obrigatório
- Naming deve ser válido (base.vlan_id)

## 8. Fluxo operacional

### Fase 1: Geração

```
1. Executar compliance analyze
2. Gerar ImportPlan
3. Salvar em reports/pilot-device-compliance/current/
4. Gerar Markdown report
```

### Fase 2: Revisão humana

```
1. Humano abre ImportPlan report
2. Revisa seção "Safe Create Staged"
   - Base Inventory: revisar rapidamente (baixo risco)
   - Service: revisar cuidadosamente (metadados, naming)
3. Revisa seção "Revisão humana obrigatória"
   - BGP peers: validar relacionamentos
   - IPs/VRFs: validar contexto
   - Nomes inválidos: corrigir ou rejeitar
4. Revisa seção "Bloqueados"
   - Tentar desbloquear coletando mais dados
   - Ou aceitar bloqueio
5. Cria ApprovalRecord para cada item
   - status = approved
   - comment = razão da aprovação
```

### Fase 3: Dry-run (futuro)

```
1. Para cada item aprovado:
   - Montar payload NetBox
   - Validar schema
   - Verificar se objeto já existe
   - Gerar diff esperado
   - Registrar dry_run_id
2. Humano confirma dry-run
3. Só então aplicar (futuro)
```

### Fase 4: Auditoria

```
1. Registrar approval_id, reviewed_by, reviewed_at
2. Registrar evidence_hash (hash do report usado)
3. Registrar dry_run_id (se houve)
4. Manter log imutável
5. Permitir rastreamento completo
```

## 9. Dry-run obrigatório (antes de qualquer escrita)

Quando staged import for implementado, NUNCA escrever no NetBox sem validar antes:

```python
def dry_run_staged_import(approval_record, netbox_token_read_only):
    """Validate before writing."""
    # 1. Construct NetBox payload
    payload = build_netbox_payload(approval_record)

    # 2. Validate schema
    assert validate_netbox_schema(payload)

    # 3. Check if object exists
    existing = netbox.get(approval_record.object_type, name=approval_record.object_key)
    if existing:
        raise ConflictError(f"Object {object_key} already exists")

    # 4. Check permissions (read-only token can't create, but can validate)
    assert token.can_create(approval_record.object_type)

    # 5. Generate expected diff
    diff = generate_diff(existing=None, new=payload)

    # 6. Register dry-run result
    dry_run_record = {
        "dry_run_id": uuid,
        "status": "passed",
        "timestamp": now,
        "payload": payload,
        "diff": diff,
        "warnings": []
    }

    # 7. Return — do NOT post to NetBox
    return dry_run_record
```

## 10. Audit log - O que registrar

Obrigatório:

```json
{
  "timestamp": "2026-04-28T14:30:00Z",
  "event": "approval_created",
  "approval_id": "uuid",
  "device": "4WNET-MNS-KTG-RX",
  "object_type": "interface",
  "object_key": "Eth-Trunk0",
  "reviewed_by": "netops-admin",
  "action": "approved",
  "reason": "Base infrastructure",
  "evidence_hash": "sha256:abc...",
  "report_source": "compliance-report.md",
  "result": "success"
}
```

Nunca registrar:

- Senhas
- Tokens
- Raw configs
- Payloads brutos do device

## 11. Armazenamento — Fases

### Fase atual (FASE 1.4)

Local:
```
reports/pilot-device-compliance/
  approvals/
    pending/      (ApprovalRecords aguardando revisão)
    approved/     (ApprovalRecords aprovados)
    rejected/     (ApprovalRecords rejeitados)
    applied/      (ApprovalRecords com staged import aplicado — futuro)
```

Formato:
```
approval-{device}-{timestamp}.json
approval-summary-{date}.md
```

### Fase futura (FASE 1.5+)

- SQLite database: `reports/compliance.db`
- Tables: approvals, audit_logs, dry_runs
- Web UI (FASE 1.6)
- RBAC com usuário/permissão real
- Assinatura digital (optional)

## 12. Segurança

Garantias:

✅ Token read-only nunca usado para escrever
✅ Token write diferente do token read-only
✅ ApprovalRecord nunca contém credenciais
✅ Dry-run é obrigatório antes de qualquer POST/PATCH
✅ Nenhuma escrita sem approval_id registrado
✅ Audit log imutável
✅ Evidence hash previne tampering

Protocolos futuros:

- Validar assinatura digital de approval
- Requer 2 aprovadores para criticalidade alta
- Rate limit: máx 10 staged imports por hora por usuário
- Requer MFA para token de escrita

## 13. Critérios de aceite

Quando feature for implementada:

- [ ] Usuário consegue revisar ImportPlan
- [ ] Usuário consegue aprovar item seguro
- [ ] Usuário consegue rejeitar item
- [ ] Usuário consegue solicitar mudanças
- [ ] Aprovação gera ApprovalRecord persistente
- [ ] Itens blocked não podem ser aprovados
- [ ] Itens needs_review precisam de ação antes
- [ ] Objeto fora naming convention rejeitado automaticamente
- [ ] Dry-run é obrigatório antes de apply
- [ ] Audit log completo e rastreável
- [ ] Nenhuma escrita sem approval_id

## 14. Fora de escopo — FASE 1.4

- Escrita real no NetBox
- Endpoint apply
- UI web
- RBAC real (permissões por usuário)
- Banco de dados (apenas JSON local)
- Aplicar configuração em equipamento
- Promover staged para active
- Assinatura digital

---

## Referências

- ApprovalRecord Schema (./24-approval-record-schema.md)
- NetBox Staged Import Strategy (./21-netbox-staged-import-strategy.md)
- ImportPlan design (netops_netbox_sync/docs/FASE_1_3_IMPORT_PLAN.md)
