# Approval Workflow Review Prompt

Reutilizável para orientar revisão de ImportPlan e aprovação de propostas.

## 1. Contexto

Você está revisando propostas de staged import geradas automaticamente a partir de compliance analysis.

**Objetivo:** Garantir que apenas itens seguros e bem-documentados sejam aprovados.

**Restrição:** Nenhuma escrita no NetBox sem sua aprovação explícita.

## 2. Antes de começar

- [ ] Tenho acesso ao relatório de compliance?
- [ ] Entendo a topologia do device?
- [ ] Conheco a naming convention esperada?
- [ ] Sei qual é o tenant/cliente deste device?
- [ ] Tenho contexto sobre os serviços rodando neste device?

## 3. Revisar seção: Safe Create Staged — Base Inventory

**Baixo risco.** Interfaces físicas, LAGs, management.

Para cada item:

- [ ] Nome segue padrão base? (Ethernet, GigabitEthernet, Eth-Trunk, Management, etc)
- [ ] Não é subinterface (não tem ponto no nome)?
- [ ] Não carrega tenant/service_type automaticamente?
- [ ] Status está UP ou esperado na topologia?
- [ ] Não há conflito óbvio no NetBox existente?

**Decisão:**
- Aprovar: "Base infrastructure, matches topology"
- Rejeitar: (raro) Somente se conflito claro

## 4. Revisar seção: Safe Create Staged — Service Candidates

**Risco médio.** Subinterfaces, L2/L3 services.

Para cada item:

- [ ] Nome segue padrão válido? (base.vlan_id, ex: Eth-Trunk0.1580)
- [ ] Vlan ID é numérico?
- [ ] Tenant identificado? (ou presente em evidence)
- [ ] Service_type identificado? (L2VPN, L3VPN, BGP, L2-bridged, etc)
- [ ] Criticality conhecida?
- [ ] Não sobrescreve objeto existente no NetBox?
- [ ] Description indica contexto/cliente?
- [ ] Confidence é "exact" ou "normalized" (não "possible" ou "ambiguous")?

**Decisão:**
- Aprovar: "Service interface, naming valid, tenant/service_type clear"
- Rejeitar: "Naming invalid" / "Tenant/service_type missing" → request_changes

## 5. Revisar seção: Revisão Humana Obrigatória

**Alto risco.** Requer sua decisão.

Para cada item:

### 5a. BGP Peer

- [ ] Peer IP válido?
- [ ] ASN esperado?
- [ ] Description/contexto claro?
- [ ] Políticas de rota documentadas?
- [ ] Não é rota vazão/apenasreserva?

**Decisão:**
- Aprovar: "BGP peer validated, matches topology"
- Rejeitar: "Missing description" / "ASN mismatch" → request_changes
- Defer: "Needs coordination with routing team"

### 5b. IP Address / VRF

- [ ] IP em formato correto (IPv4 ou IPv6)?
- [ ] VRF esperado existe?
- [ ] Interface pai identificada?
- [ ] IPAM policy conforme (ex: não /32 em serviço)?
- [ ] Secondary IP?

**Decisão:**
- Aprovar: "IP valid, VRF matches policy"
- Rejeitar: "Invalid format" / "VRF mismatch" → request_changes

### 5c. VLAN / Service object

- [ ] VLAN ID válido (1-4094)?
- [ ] Não é reservada ou management-only?
- [ ] Descrição indica propósito?
- [ ] Tenant clear?

**Decisão:**
- Aprovar: "VLAN valid, purpose clear"
- Rejeitar: "Reserved range" / "Tenant missing" → request_changes

### 5d. Naming Inválido

- [ ] Nome segue policy?
- [ ] Pode ser corrigido facilmente?
- [ ] Humano consegue propor naming alternativo?

**Decisão:**
- Rejeitar: "Invalid naming" → request_changes com sugestão
- Defer: "Naming needs policy clarification"

## 6. Revisar seção: Bloqueados

**Não aproximar.** Dados insuficientes.

- [ ] Motivo bloqueado é válido?
- [ ] Há forma de desbloquear (ex: coletar mais dados)?
- [ ] Ignorar ou tentar resolver?

**Decisão:**
- Mark as ignored: "Insufficient metadata, will skip"
- Defer: "Try re-running compliance after network inventory update"

## 7. Revisar seção: Observações de Segurança

- [ ] Confirma que é read-only?
- [ ] Confirma que nenhuma escrita será feita?
- [ ] Confirma que nenhum comando será enviado?
- [ ] Confirma que approval precisa ser aprovado antes de apply?

## 8. Checklist final antes de salvar

- [ ] Revisou todas as seções (base, service, needs_review, blocked)?
- [ ] Documentou todas as decisões com motivo claro?
- [ ] Não recomendou itens blocked para aprovação?
- [ ] Não aprovou itens fora da naming convention?
- [ ] Registrou contexto de negócio (tenant, service type)?
- [ ] Confirmou com topo responsável (se crítico)?

## 9. Padrões de decisão

### ✅ Sempre aprovar

```
action: safe_create_staged
confidence: exact
category: base_inventory
naming_compliant: true
→ APPROVE
```

```
action: safe_create_staged
confidence: exact
category: service
naming_compliant: true
tenant_id: (found)
service_type_id: (found)
→ APPROVE
```

### ⚠️ Sempre rejeitar

```
action: needs_review
→ REJECT (exigiu revisão, não foi corrigido)
```

```
action: blocked
→ REJECT (dados insuficientes)
```

```
object_key: (fora da naming convention)
action: safe_create_staged
→ REJECT (violar regra crítica)
```

```
confidence: ambiguous
→ REJECT (incerteza muito alta)
```

### 📋 Sempre request_changes

```
action: safe_create_staged
category: service
naming_compliant: true
tenant_id: (missing)
service_type_id: (missing)
→ REQUEST_CHANGES (coletar metadados, resubmeter)
```

```
object_key: Eth-Trunk0.Bad!Name
→ REQUEST_CHANGES (fix naming to Eth-Trunk0.1580 or similar)
```

## 10. Anti-padrões — Não fazer isso

❌ **Não aprovar sem revisar evidence**
- Sempre olhar evidence/razão da proposta

❌ **Não aprovar itens fora da naming convention**
- Mesmo que pareça "óbvio", seguir regra strict

❌ **Não aprovar ambíguo**
- Se confidence ≤ ambiguous, rejeitar ou defer

❌ **Não aprovar sem confirmar que é base_inventory ou com naming válida**
- Especialmente para service interfaces

❌ **Não adicionar dados sensíveis em approval comment**
- Nada de senhas, tokens, IPs internos secretos

## 11. Template de comment

```
[Category] - [Reason] - [Risk]

Base: "Base infrastructure interface, matches topology, standard naming. Low risk. → APPROVE"

Service: "Service interface, Eth-Trunk0.1580 naming valid, tenant:operator-a confirmed. Medium risk. → APPROVE"

Reject: "Subinterface naming invalid (Bad.Naming), must follow base.vlan_id pattern. → REJECT - request_changes"

BGP: "BGP peer 10.0.0.1, peer AS verified, description provided. Validated with routing team. → APPROVE"

Blocked: "Blocked due to ambiguous metadata. Insufficient evidence to approve. → DEFER - collect more inventory data"
```

## 12. Pós-revisão (para quando staged import for implementado)

Após aprovação, sistema:
1. Gerará ApprovalRecord
2. Executará dry-run (validará payload NetBox)
3. Mostrará diff esperado
4. Aguardará sua confirmação de dry-run
5. Somente então aplicará staged import

Sua participação:
- Confirmar dry-run
- Autorizar aplicação
- Validar resultado pós-aplicação

---

## Referências

- Approval Workflow Design (../docs/23-approval-workflow-design.md)
- ApprovalRecord Schema (../docs/24-approval-record-schema.md)
- ImportPlan design (../../netops_netbox_sync/docs/FASE_1_3_IMPORT_PLAN.md)
