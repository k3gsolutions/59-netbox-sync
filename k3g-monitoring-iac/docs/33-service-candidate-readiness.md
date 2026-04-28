# Service Candidate Readiness Analysis

## 1. Objetivo

Preparar análise de readiness para service candidates, **sem escrita no NetBox**.

FASE 2.4 é read-only. Apenas validação e classificação.

## 2. O que é Service Candidate

Service Candidate = interface/objeto que representa serviço monitorável, não apenas base infrastructure.

Exemplos:
- Eth-Trunk0.1580 (subinterface de serviço com VLAN)
- GigabitEthernet0/0/100 com IP 192.0.2.1/30
- BGP peer 203.0.113.1 com AS 65001
- L2VPN PE com VLAN tagging
- Virtual-Circuit com CIR/EIR

## 3. Diferença: Base Inventory vs Service

### Base Inventory
- Eth-Trunk0, GigabitEthernet0/0/0, etc
- Sem "." no nome
- Sem IP aplicado (ou management apenas)
- Sem VRF de serviço
- Sem description de cliente/operadora
- Não precisa de naming convention
- Pode ter INTERFACE_DESCRIPTION_MISMATCH (review apenas)

### Service Candidate
- Subinterface com "." (Eth-Trunk0.1580)
- Ou interface com IP de serviço
- Ou interface com VRF de cliente
- Ou description contém cliente/operadora/CDN
- Precisa de naming convention válida (SERVICE_SLUG)
- Precisa de tenant, service_type, criticality
- Precisa de parent interface válido
- BGP peers, circuitos, L2VPN

## 4. Campos Obrigatórios por Tipo

### Subinterface (base.vlan)

Obrigatório:
- ✅ parent_interface (base, ex: Eth-Trunk0)
- ✅ vlan_id (numérico, 1-4094)
- ✅ service_type (definido)
- ✅ tenant (identificado)

Opcional mas recomendado:
- description (SERVICE_SLUG padrão)
- criticality (production, staging, etc)
- monitoring_enabled
- IPs associados

### BGP Peer

Obrigatório:
- ✅ remote_address (IP válido)
- ✅ remote_as (numérico)
- ✅ address_family (ipv4 ou ipv6)
- ✅ description (padrão de naming)

Opcional:
- local_as
- import_policy
- export_policy

### IP Address

Obrigatório:
- ✅ address (CIDR válido)
- ✅ interface ou vrf (associação)

Opcional:
- description
- role (loopback, anycast, etc)
- status (active, reserved, etc)

## 5. Classificação de Readiness

### ready_for_review
Pode prosseguir para aprovação humana no futuro.

Critérios:
- ✅ Todos os campos obrigatórios presentes
- ✅ Naming válido (SERVICE_SLUG ou padrão)
- ✅ Nenhum conflito com existente no NetBox
- ✅ Identificação clara
- ✅ Evidência suficiente

### missing_required_metadata
Faltam campos obrigatórios.

Exemplos:
- BGP sem remote_as
- Subinterface sem tenant
- IP sem interface
- Description vazia quando obrigatório

Ação: Enriquecer metadados antes de retentar.

### naming_failed
Naming convention inválida.

Exemplos:
- Eth-Trunk0.abc (vlan_id não numérico)
- description não segue SERVICE_SLUG
- BGP description ambígua
- Interface name com caracteres inválidos

Ação: Corrigir naming antes de retentar.

### ambiguous
Múltiplas interpretações possíveis.

Exemplos:
- Parent interface não encontrada no NetBox
- Múltiplos matches para mesmo nome
- Conflito com objeto existente
- IP sem contexto de interface/VRF

Ação: Esclarecer contexto antes de retentar.

### blocked
Impossível prosseguir sem ação manual.

Exemplos:
- Parent interface não existe
- Naming inválido E conflito existente
- Identificação impossível
- Dependência não resolvida

Ação: Investigação manual necessária.

### ignored
Intencionalmente ignorado.

Exemplos:
- Não é service candidate (é base inventory)
- Não se aplica a staging
- Fora de escopo (deprecated, temp, etc)

Ação: Nenhuma.

## 6. Script: analyze_service_candidate_readiness.py

Entrada:
- ImportPlan JSON ou relatório Markdown
- Device name
- Opcionalmente: lista de service_types permitidos

Comando:

```bash
python3 tools/local/analyze_service_candidate_readiness.py \
  --import-plan reports/pilot-device-compliance/import-plan-4WNET.json \
  --output reports/pilot-device-compliance/service-candidate-readiness.md \
  --device 4WNET-MNS-KTG-RX
```

Processamento:
1. Carregar ImportPlan
2. Filtrar service candidates (bloquear base_inventory)
3. Para cada candidato:
   - Validar campos obrigatórios
   - Validar naming convention
   - Detectar conflitos no NetBox (read-only GET)
   - Classificar readiness
4. Gerar relatório Markdown

Validações por tipo:
- Subinterfaces: parent, vlan, service_type, tenant
- BGP: remote_address, remote_as, description
- IPs: address, interface/vrf, validity
- Circuitos: providername, service_id (se aplicável)

Segurança:
- ✅ Zero writes
- ✅ Zero token write
- ✅ Zero deletions
- ✅ Read-only GETs apenas (status codes)
- ✅ Nenhum secret em output

## 7. Relatório Output

Estrutura:

```
# Service Candidate Readiness — 4WNET-MNS-KTG-RX

## 1. Resumo
- Total service candidates: N
- ready_for_review: N
- missing_required_metadata: N
- naming_failed: N
- ambiguous: N
- blocked: N
- ignored: N

## 2. Ready for Review
Tabela com colunas:
- #
- object_type
- object_key
- service_type
- tenant
- confidence
- notes

Cada item pode prosseguir para ApprovalRecord humano.

## 3. Missing Required Metadata
Tabela:
- #
- object_type
- object_key
- missing_fields (array)
- recommended_action

## 4. Naming Failed
Tabela:
- #
- object_type
- object_key
- current_value
- expected_pattern
- recommended_action

## 5. Ambiguous
Tabela:
- #
- object_type
- object_key
- ambiguity_reason
- possible_matches (array)
- recommended_action

## 6. Blocked
Tabela:
- #
- object_type
- object_key
- reason
- investigation_needed

## 7. Ignored
Tabela:
- #
- object_type
- object_key
- reason (not service, out of scope, etc)

## 8. Observações Finais
- read-only;
- não cria ApprovalRecords;
- não cria ApplyPlans;
- não escreve no NetBox;
- próximos passos recomendados.
```

## 8. Segurança

✅ Zero writes
✅ Zero token write
✅ Zero deletions
✅ Zero aplicação em equipamento
✅ Nenhum secret em output
✅ Read-only apenas (GET)

## 9. Próximas Fases

Após FASE 2.4:

**FASE 2.5 — Service Candidate Enrichment**
- Web UI ou script para enriquecer metadados
- Validar tenant/service_type
- Atualizar naming
- Esclarecer ambiguidades
- Ainda read-only no NetBox

**FASE 2.6 — Service Candidate Approval Design**
- ApprovalRecord para service candidates
- Regras mais estritas que base_inventory
- Aprovação humana obrigatória
- Validação de dependências

**FASE 2.7 — Service Candidate Staged Import**
- ApplyPlan para service candidates
- Validation contra SERVICE_SLUG
- Validation contra tenant/service_type
- Ainda com dry-run obrigatório
- Staged import (status=planned)

## 10. Critério de Sucesso FASE 2.4

✅ Script criado e testado (fakes)
✅ Relatório gerado com classificações
✅ Resumo acurado dos service candidates
✅ Campos obrigatórios validados
✅ Naming convention verificado
✅ Zero writes confirmado
✅ Zero token write confirmado
✅ Zero equipamento afetado

## Referências

- [Controlled Batch Staged Apply Design](./31-controlled-batch-staged-apply.md)
- [Batch Apply Runbook](./32-batch-apply-runbook.md)
- [Approval Record Schema](./24-approval-record-schema.md)
