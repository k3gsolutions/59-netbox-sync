# ApprovalRecord Schema — FASE 1.4

Esquema conceitual do registro de aprovação para futuro Staged Import.

## Modelo JSON completo

```json
{
  "approval_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "import_plan_id": "e5b6f42c-1234-5678-9abc-def012345678",
  "device": "4WNET-MNS-KTG-RX",
  "device_id": 123,
  "generated_at": "2026-04-28T10:00:00Z",

  "proposal": {
    "object_type": "interface",
    "object_key": "Eth-Trunk0",
    "code": "INTERFACE_MISSING_IN_NETBOX",
    "action": "safe_create_staged",
    "category": "base_inventory",
    "confidence": "exact",
    "naming_compliant": true,
    "reason": "Base interface inventory (physical/LAG/management)",
    "preferred_next_step": "Revisar payload sugerido e aplicar staged import"
  },

  "evidence": {
    "device_ssh": {
      "interface_name": "Eth-Trunk0",
      "status": "up",
      "description": "LAG trunk"
    },
    "netbox_search": {
      "search_results": 0,
      "search_method": "name=Eth-Trunk0",
      "status": "not_found"
    }
  },

  "review": {
    "status": "approved",
    "reviewed_by": "netops-admin@example.com",
    "reviewed_at": "2026-04-28T14:30:00Z",
    "decision": "approve",
    "comment": "Base infrastructure interface. Standard LAG. Safe to import.",
    "changes_requested": [],
    "changes_requested_count": 0,
    "expected_netbox_payload": {
      "name": "Eth-Trunk0",
      "type": "lag",
      "enabled": true,
      "mtu": 1500,
      "tags": [
        "discovery:netops_netbox_sync",
        "discovery:staged",
        "inventory:base-interface"
      ]
    }
  },

  "audit": {
    "created_at": "2026-04-28T10:00:00Z",
    "updated_at": "2026-04-28T14:30:00Z",
    "created_by": "compliance-engine",
    "report_path": "reports/pilot-device-compliance/current/4WNET-MNS-KTG-RX-compliance-report.md",
    "report_timestamp": "2026-04-28T09:45:00Z",
    "evidence_hash": "sha256:a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
    "import_plan_hash": "sha256:z9y8x7w6v5u4t3s2r1q0p9o8n7m6l5k4j3i2h1g0f"
  },

  "future_staging": {
    "dry_run_id": null,
    "dry_run_status": null,
    "dry_run_passed_at": null,
    "applied_at": null,
    "applied_by": null,
    "staged_import_id": null,
    "deployment_timestamp": null
  },

  "metadata": {
    "version": "1.0",
    "source": "ImportPlan",
    "priority": "normal",
    "requires_2fa": false,
    "requires_2_approvers": false,
    "sla_hours": 24,
    "ttl_days": 90
  }
}
```

## Estrutura por seção

### approval_id

Identificador único do registro de aprovação.

```json
{
  "approval_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
}
```

Tipo: UUID v4
Gerado por: approval engine
Imutável: sim
Único: sim

### import_plan_id

Identificador do ImportPlan que gerou esta proposta.

```json
{
  "import_plan_id": "e5b6f42c-1234-5678-9abc-def012345678"
}
```

Tipo: UUID v4
Referência: ImportPlan.id
Permite: rastrear qual plano gerou a proposta

### device / device_id

Identificadores do dispositivo.

```json
{
  "device": "4WNET-MNS-KTG-RX",
  "device_id": 123
}
```

Tipo: string, int
device: hostname da equipment
device_id: NetBox DCIM ID

### proposal

Cópia da proposta do ImportPlanItem.

```json
{
  "proposal": {
    "object_type": "interface",
    "object_key": "Eth-Trunk0",
    "code": "INTERFACE_MISSING_IN_NETBOX",
    "action": "safe_create_staged",
    "category": "base_inventory",
    "confidence": "exact",
    "naming_compliant": true,
    "reason": "Base interface inventory (physical/LAG/management)",
    "preferred_next_step": "Revisar payload sugerido e aplicar staged import"
  }
}
```

Campos:
- `object_type`: tipo NetBox (interface, ip_address, vrf, vlan, etc)
- `object_key`: identificador único (Eth-Trunk0, 10.0.0.1/24, etc)
- `code`: código de divergência
- `action`: safe_create_staged | needs_review | blocked | ignore
- `category`: base_inventory | service | (null)
- `confidence`: exact | normalized | possible | ambiguous | none
- `naming_compliant`: true se segue naming convention
- `reason`: motivo da classificação
- `preferred_next_step`: ação recomendada

### evidence

Dados que respaldam a proposta.

```json
{
  "evidence": {
    "device_ssh": {
      "interface_name": "Eth-Trunk0",
      "status": "up",
      "description": "LAG trunk",
      "mtu": 1500,
      "members": ["GigabitEthernet0/5/0", "GigabitEthernet0/5/1"]
    },
    "netbox_search": {
      "search_results": 0,
      "search_method": "name=Eth-Trunk0",
      "status": "not_found"
    },
    "compliance_summary": {
      "total_divergences": 161,
      "missing_in_netbox_count": 59,
      "severity": "medium"
    }
  }
}
```

Estrutura livre, cópia de ImportPlanItem.evidence

**Proibido:**
- Senhas
- Tokens API
- Raw device configs
- Credenciais SSH

### review

Decisão humana de revisão.

```json
{
  "review": {
    "status": "approved",
    "reviewed_by": "netops-admin@example.com",
    "reviewed_at": "2026-04-28T14:30:00Z",
    "decision": "approve",
    "comment": "Base infrastructure interface. Standard LAG. Safe to import.",
    "changes_requested": [],
    "changes_requested_count": 0,
    "expected_netbox_payload": { ... }
  }
}
```

Campos:
- `status`: approved | rejected | changes_requested | deferred | expired
- `reviewed_by`: e-mail ou identificador do revisor
- `reviewed_at`: timestamp ISO8601
- `decision`: approve | reject | request_changes | defer | expire
- `comment`: motivo em texto livre
- `changes_requested`: array de mudanças solicitadas
- `changes_requested_count`: número de mudanças solicitadas
- `expected_netbox_payload`: payload que será criado no NetBox

### audit

Rastreabilidade e integridade.

```json
{
  "audit": {
    "created_at": "2026-04-28T10:00:00Z",
    "updated_at": "2026-04-28T14:30:00Z",
    "created_by": "compliance-engine",
    "report_path": "reports/pilot-device-compliance/current/4WNET-MNS-KTG-RX-compliance-report.md",
    "report_timestamp": "2026-04-28T09:45:00Z",
    "evidence_hash": "sha256:a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
    "import_plan_hash": "sha256:z9y8x7w6v5u4t3s2r1q0p9o8n7m6l5k4j3i2h1g0f"
  }
}
```

Campos:
- `created_at`: quando approval foi gerado
- `updated_at`: última modificação
- `created_by`: sistema ou usuário que criou
- `report_path`: caminho do arquivo de compliance usado
- `report_timestamp`: quando compliance foi executado
- `evidence_hash`: SHA256 do conteúdo do relatório
- `import_plan_hash`: SHA256 do ImportPlan JSON

**Uso:** prevenir tampering

### future_staging

Campos vazios agora, preenchidos quando staged import for implementado.

```json
{
  "future_staging": {
    "dry_run_id": null,
    "dry_run_status": null,
    "dry_run_passed_at": null,
    "applied_at": null,
    "applied_by": null,
    "staged_import_id": null,
    "deployment_timestamp": null
  }
}
```

Será preenchido com:
- `dry_run_id`: resultado de validação pré-escrita
- `dry_run_status`: success | failed
- `dry_run_passed_at`: timestamp da validação
- `applied_at`: quando staged import foi aplicado
- `applied_by`: quem aplicou
- `staged_import_id`: ID do staged object no NetBox
- `deployment_timestamp`: timestamp da aplicação

### metadata

Metadados de operação.

```json
{
  "metadata": {
    "version": "1.0",
    "source": "ImportPlan",
    "priority": "normal",
    "requires_2fa": false,
    "requires_2_approvers": false,
    "sla_hours": 24,
    "ttl_days": 90
  }
}
```

Campos:
- `version`: schema version
- `source`: sempre "ImportPlan" nesta fase
- `priority`: normal | high | critical
- `requires_2fa`: se aprovação precisa de 2FA
- `requires_2_approvers`: se precisa de 2 aprovadores
- `sla_hours`: prazo de aprovação (em horas)
- `ttl_days`: dias até expiração do registro

## Exemplos

### Exemplo 1: Aprovação de Base Interface

```json
{
  "approval_id": "abc123",
  "import_plan_id": "xyz789",
  "device": "4WNET-MNS-KTG-RX",
  "device_id": 123,

  "proposal": {
    "object_type": "interface",
    "object_key": "Eth-Trunk0",
    "action": "safe_create_staged",
    "category": "base_inventory",
    "confidence": "exact"
  },

  "review": {
    "status": "approved",
    "reviewed_by": "netops-admin@example.com",
    "reviewed_at": "2026-04-28T14:30:00Z",
    "decision": "approve",
    "comment": "Standard LAG, matches naming. Safe to import."
  },

  "audit": {
    "created_at": "2026-04-28T10:00:00Z",
    "evidence_hash": "sha256:abc..."
  }
}
```

### Exemplo 2: Rejeição de Service Interface (Naming Inválido)

```json
{
  "approval_id": "def456",
  "import_plan_id": "xyz789",
  "device": "4WNET-MNS-KTG-RX",
  "device_id": 123,

  "proposal": {
    "object_type": "interface",
    "object_key": "Bad.Naming",
    "action": "needs_review",
    "code": "INTERFACE_MISSING_IN_NETBOX",
    "confidence": "exact",
    "naming_compliant": false
  },

  "review": {
    "status": "rejected",
    "reviewed_by": "netops-admin@example.com",
    "reviewed_at": "2026-04-28T14:45:00Z",
    "decision": "reject",
    "comment": "Invalid subinterface pattern. Must be base.vlan_id (e.g., Eth-Trunk0.1580)"
  }
}
```

### Exemplo 3: Request Changes para Service

```json
{
  "approval_id": "ghi789",
  "import_plan_id": "xyz789",
  "device": "4WNET-MNS-KTG-RX",
  "device_id": 123,

  "proposal": {
    "object_type": "interface",
    "object_key": "Eth-Trunk0.1580",
    "action": "safe_create_staged",
    "category": "service"
  },

  "review": {
    "status": "changes_requested",
    "reviewed_by": "netops-admin@example.com",
    "reviewed_at": "2026-04-28T14:50:00Z",
    "decision": "request_changes",
    "changes_requested": [
      "Specify tenant (e.g., operator-name)",
      "Clarify service_type (e.g., L2VPN, L3VPN)",
      "Add description with customer ID"
    ],
    "comment": "Service interface requires tenant and service_type. Please update ImportPlan and resubmit."
  }
}
```

## Campos obrigatórios

SEMPRE:
- `approval_id`
- `import_plan_id`
- `device`
- `device_id`
- `proposal.object_type`
- `proposal.object_key`
- `proposal.action`
- `review.status`
- `review.decision`
- `audit.created_at`

QUANDO APROVADO:
- `review.reviewed_by`
- `review.reviewed_at`
- `review.comment`
- `review.expected_netbox_payload`

QUANDO REJEITADO:
- `review.reviewed_by`
- `review.reviewed_at`
- `review.comment`

## Campos PROIBIDOS

NUNCA adicionar:

- `password` — credenciais SSH
- `token` — API tokens
- `secret` — senhas NetBox
- `api_key` — API keys
- `raw_config` — configuração bruta do device
- `ssh_connection_string` — strings com credenciais
- `plaintext_credentials` — qualquer tipo

## Validação

Ao salvar ApprovalRecord:

```python
def validate_approval_record(record: dict) -> bool:
    """Validate before persisting."""
    required_fields = [
        "approval_id", "import_plan_id", "device", "device_id",
        "proposal", "review", "audit"
    ]

    # Check required
    for field in required_fields:
        assert field in record, f"Missing {field}"

    # Check forbidden
    forbidden = ["password", "token", "secret", "api_key", "raw_config"]
    record_str = json.dumps(record)
    for pattern in forbidden:
        assert pattern not in record_str.lower(), f"Forbidden field: {pattern}"

    # Check approval decision
    assert record["review"]["decision"] in [
        "approve", "reject", "request_changes", "defer", "expire"
    ]

    # Check if rejected, has comment
    if record["review"]["decision"] == "reject":
        assert "comment" in record["review"]
        assert len(record["review"]["comment"]) > 0

    return True
```

## Armazenamento

### Arquivo local

```
reports/pilot-device-compliance/approvals/
  pending/
    approval-4WNET-MNS-KTG-RX-2026-04-28T10:00:00Z.json
  approved/
    approval-4WNET-MNS-KTG-RX-2026-04-28T14:30:00Z.json
  rejected/
    approval-bad-naming-2026-04-28T14:45:00Z.json
```

### Banco de dados (futuro)

```sql
CREATE TABLE approvals (
  approval_id UUID PRIMARY KEY,
  import_plan_id UUID,
  device VARCHAR(255),
  device_id INTEGER,
  proposal JSONB,
  review JSONB,
  audit JSONB,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  FOREIGN KEY (import_plan_id) REFERENCES import_plans(id)
);

CREATE TABLE audit_logs (
  id SERIAL PRIMARY KEY,
  approval_id UUID,
  event VARCHAR(255),
  timestamp TIMESTAMP,
  user_id VARCHAR(255),
  details JSONB,
  FOREIGN KEY (approval_id) REFERENCES approvals(approval_id)
);
```

---

## Referências

- Approval Workflow Design (./23-approval-workflow-design.md)
- ImportPlan design (netops_netbox_sync/docs/FASE_1_3_IMPORT_PLAN.md)
