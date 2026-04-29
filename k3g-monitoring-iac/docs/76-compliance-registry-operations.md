# FASE 2.33 — Compliance Registry Operationalization

**Data:** 2026-04-29
**Status:** ✅ Completo
**Objetivo:** Transformar Compliance Policy Registry em rotina operacional

---

## 1. Visão Geral

Compliance Policy Registry é a **fonte única de verdade** para validação de:
- Naming conventions (interfaces, VRF, route-policies, prefixes, etc.)
- Metadata requirements (BGP peers, IP addresses, service types)
- Severity levels (blocker/error/warning/info)
- Blocked keywords (token, password, secret)

**Responsabilidade:**
- Network Engineering: define convenção técnica
- NOC: usa e reporta inconsistências
- Compliance owner: aprova mudança
- Operator: roda validação

---

## 2. Arquitetura

### Arquivos Oficiais

| Arquivo | Propósito |
|---------|-----------|
| `policies/compliance/discovery-elements.yaml` | VRP element definitions + discovery commands |
| `policies/compliance/naming-conventions.yaml` | Regex patterns for interface, VRF, route-policy, prefix, community |
| `policies/compliance/interface-policy.yaml` | Service interface requirements |
| `policies/compliance/vrf-policy.yaml` | VRF naming + structure |
| `policies/compliance/bgp-policy.yaml` | BGP peer metadata requirements |
| `policies/compliance/route-policy-policy.yaml` | Route-policy validation |
| `policies/compliance/ip-prefix-policy.yaml` | Prefix list naming |
| `policies/compliance/community-policy.yaml` | Community format + filters |
| `policies/compliance/as-path-policy.yaml` | AS-path filter regex |
| `policies/compliance/snmp-policy.yaml` | SNMP version + blocked communities |
| `policies/compliance/comments-policy.yaml` | Comment field constraints |
| `policies/compliance/compliance-severity-policy.yaml` | Severity levels + overrides |
| `policies/compliance/dependency-map.yaml` | Cross-element dependencies |

### Validadores

| Arquivo | Função |
|---------|--------|
| `webui/services/convention_validator.py` | 19 funções de validação, carrega YAML |
| `webui/services/validators.py` | Wrappers para Web UI (backward compat) |
| `webui/services/response_forms.py` | Coleta convention_violations em forms |
| `tools/local/validate_compliance_policies.py` | Audita YAML (13/13 files) |
| `tools/local/test_compliance_policy_registry.py` | Unit tests (15/15) |
| `tools/local/test_convention_registry_integration.py` | Integration + fallback tests (17/17) |

---

## 3. Quando Alterar uma Policy

### Exemplos de Mudança

1. **Novo padrão de naming:** novo service_type adicionar em `interface-policy.yaml`
2. **Exceção SNMP:** adicionar exceção em `snmp-policy.yaml`
3. **Nova severidade:** alterar `compliance-severity-policy.yaml`
4. **Novo tipo de interface:** adicionar padrão em `naming-conventions.yaml`
5. **Dependência cruzada:** atualizar `dependency-map.yaml`

---

## 4. Processo de Alteração

### Passo 1: Criar Branch

```bash
git checkout -b ops/registry-update-xxxxx
```

### Passo 2: Alterar YAML

Exemplo — adicionar novo padrão de interface:

```yaml
# policies/compliance/naming-conventions.yaml
interface:
  base_inventory_patterns:
    - "^Eth-Trunk\\d+$"
    - "^GigabitEthernet\\d+/\\d+/\\d+$"
    - "^10GE\\d+/\\d+/\\d+$"
    - "^25GE\\d+/\\d+/\\d+$"  # ← NOVO
    - "^LoopBack\\d+$"
    - "^NULL\\d+$"
    - "^Vlanif\\d+$"
```

### Passo 3: Validar Syntax

```bash
python3 tools/local/validate_compliance_policies.py
```

Esperado:
```
Results: 13/13 files valid
```

### Passo 4: Rodar Testes

```bash
python3 tools/local/test_compliance_policy_registry.py
python3 tools/local/test_convention_registry_integration.py
python3 tools/local/test_webui_safety.py
```

Esperado: 15/15 + 17/17 + 39/39 = 71/71 passando

### Passo 5: Gerar Relatório de Impacto

```bash
python3 tools/local/compliance_policy_impact_report.py \
  --device 4WNET-MNS-KTG-RX \
  --reports-root reports/pilot-device-compliance \
  --output reports/compliance-policy-impact-report.md
```

Analisa:
- Quantos itens passam hoje
- Quantos passariam com nova policy
- Quantos virariam blocker/error/warning

Exemplo output:
```
## Impacto da Mudança

### Resumo
- Items analisados: 127
- Passariam hoje: 115
- Passariam após mudança: 116
- Novos blockers: 0
- Novos errors: 1 (requer ação)
- Novos warnings: 2 (informativo)

### Items afetados por RTPOL-001
| Object | Tipo | Ação |
| Peer-AS64512 | bgp_peer | ERRO: violação nova |
| Policy-X | route_policy | OK: validaria depois |
```

### Passo 6: Revisão Humana

1. **Compliance owner** revisa relatório de impacto
2. Valida se breaking change é aceitável
3. Aprova ou solicita ajustes
4. Aprova PR

### Passo 7: Commit

```bash
git commit -m "ops: Update naming-conventions.yaml - add 25GE pattern

RATIONALE:
- New 25GE interface hardware deployed in Q2 2026
- Added 25GE\d+/\d+/\d+ to base_inventory_patterns
- Impact: 0 blockers, 0 errors (backcompat)
- No changes to Web UI or validators
- Reviewed by Network Engineering + Compliance

VALIDATION:
- validate_compliance_policies.py: 13/13 ✓
- test_compliance_policy_registry.py: 15/15 ✓
- test_convention_registry_integration.py: 17/17 ✓
- test_webui_safety.py: 39/39 ✓
- impact_report: 0 new violations

Co-Authored-By: Network Engineering <neteng@company.com>
"
```

---

## 5. Impact Analysis Tool

### Uso

```bash
python3 tools/local/compliance_policy_impact_report.py \
  --device 4WNET-MNS-KTG-RX \
  --reports-root reports/pilot-device-compliance \
  --output reports/compliance-policy-impact-report.md
```

### Output: compliance-policy-impact-report.md

```markdown
# Relatório de Impacto das Policies de Compliance

## 1. Resumo Executivo

- **Policies carregadas:** 13/13 YAML files
- **Items analisados:** 127 (76 responses + 51 proposed approvals)
- **Validações corridas:** 2024 (interface, VRF, route-policy, BGP metadata, etc.)

### Resultado Antes da Mudança
- Blockers: 2
- Errors: 8
- Warnings: 15
- Passando: 102

### Resultado Após Mudança (simulado)
- Blockers: 2 (sem mudança)
- Errors: 9 (+1 novo RTPOL-001)
- Warnings: 15 (sem mudança)
- Passando: 101 (-1)

### Decisão
❌ Mudança recomendada com ação:
- Solucionar novo error em Peer-AS64512
- Validar impacto em week2 review board

## 2. Violações por Regra

| Rule ID | Sev | Antes | Depois | Δ | Items |
|---------|-----|-------|--------|---|-------|
| COMMENT-001 | blocker | 2 | 2 | 0 | notes_contain_token_x2 |
| IFACE-001 | error | 1 | 1 | 0 | Bad.Naming |
| VRF-001 | error | 2 | 2 | 0 | vrf_too_long |
| RTPOL-001 | error | 5 | 6 | +1 | Peer-AS64512 (NEW) |
| IPMAP-001 | error | 0 | 0 | 0 | - |
| BGP-001 | error | 0 | 0 | 0 | - |
| **TOTAL** | | **8** | **9** | **+1** | |

## 3. Items Afetados Detalhado

### Novo Error: RTPOL-001

| Device | Object | Field | Valor | Rule | Antes | Depois | Ação |
|--------|--------|-------|-------|------|-------|--------|------|
| router1 | Peer-AS64512 | remote_bgp_group | invalid-name | RTPOL-001 | valid | ERROR | Renomear ou exceptuar |

## 4. Recomendações

### Para Approve
- [ ] Contatar Network Team sobre Peer-AS64512
- [ ] Corrigir remote_bgp_group ou documentar exceção
- [ ] Re-executar impact report após correção

### Para Reject
- [ ] Manter policy anterior
- [ ] Abrir issue para review de mudança
- [ ] Agendmeetng com compliance owner + network eng

## 5. Segurança

✓ Nenhuma escrita NetBox
✓ Nenhum apply
✓ Nenhum /sync
✓ Registry é read-only
✓ Mudança é documentation + local validation
```

---

## 6. Segurança

### Proibido

❌ Colocar segredo em policy (tokens, senhas, etc.)
❌ Colocar comunidade real sensível
❌ Policy executar ação no equipamento
❌ Silent fallback a hardcoded patterns
❌ Modificar policy sem revisão

### Permitido

✅ Usar placeholders (customer_name_here)
✅ Bloquear palavras (public, private)
✅ Adicionar novos padrões
✅ Ajustar severidade
✅ Documentar exceções

### Validação Contínua

```bash
# Rodar regularmente
python3 tools/local/validate_compliance_policies.py && \
python3 tools/local/test_compliance_policy_registry.py && \
python3 tools/local/test_convention_registry_integration.py && \
python3 tools/local/test_webui_safety.py
```

---

## 7. Responsabilidades

### Network Engineering
- Define convenção técnica (padrões naming, metadata requirements)
- Propõe mudança via pull request
- Fornece rationale + impact analysis
- Aprova mudança

### NOC (Network Operations Center)
- Usa registry para validação local
- Reporta violações à Compliance
- Executa `validate_compliance_policies.py` antes de salvar
- Bloqueia saves com REGISTRY-001 blocker

### Compliance Owner
- Revisa mudança proposta
- Analisa impact report
- Aprova ou rejeita mudança
- Mantém audit trail de decisions

### Operator (Web UI User)
- Vê violations durante resposta
- Corrige ou documenta exceção
- Pode continuar se warning/info, não se blocker
- Valida local antes de approvals

---

## 8. Fluxo Completo Exemplo

### Cenário: Nova Severidade para BGP-001

**Network Engineering:**
```yaml
# compliance-severity-policy.yaml
rule_severity_overrides:
  BGP-001: warning  # ← Mudado de error para warning
```

**Passo 1: Validar**
```bash
python3 tools/local/validate_compliance_policies.py
# Results: 13/13 files valid ✓
```

**Passo 2: Impacto**
```bash
python3 tools/local/compliance_policy_impact_report.py \
  --device 4WNET-MNS-KTG-RX \
  --reports-root reports/pilot-device-compliance
```

Output:
```
### Resultado Antes
- BGP-001 errors: 3

### Resultado Depois
- BGP-001 errors: 0
- BGP-001 warnings: 3
```

**Passo 3: Review**
- Compliance owner aprova
- Breaking change: error → warning (reduce restriction)
- Safe to proceed

**Passo 4: Merge**
- PR merge
- CHANGELOG updated
- Web UI automatically uses novo registry

**Passo 5: Operação**
- Week 1 responses com BGP-001 agora mostram ⚠️ warning
- Users podem continuar salvar (não blocker mais)
- Audit trail rastreia mudança

---

## 9. Monitoramento

### Métricas Úteis

```bash
# Contar violações por rule
python3 -c "
import json
from pathlib import Path

audit_dir = Path('reports/pilot-device-compliance/week1-responses/audit')
for audit_file in audit_dir.glob('*.json'):
    with open(audit_file) as f:
        data = json.load(f)
    for entry in data:
        if entry.get('validation_result', {}).get('errors'):
            print(f\"{entry['timestamp']}: {entry['object_key']} - {entry['validation_result']['errors']}\")
"
```

### Dashboard Ideal (Futuro)

- [ ] Gráfico de violations over time
- [ ] Rule violations por team
- [ ] Breaking changes vs improvements
- [ ] Audit trail de policy changes
- [ ] Auto-notify on new violations

---

## 10. Changelog + Roadmap

### Changelog Template

```markdown
## [RELEASE_DATE]

### Registry Updated
- Added 25GE interface pattern
- Changed BGP-001 severity to warning
- Reviewed 127 items, impact: 0 new blockers

### Merged PRs
- ops/registry-update-25ge-pattern #XXX

### Authors
- Network Engineering Team
- Compliance Review
```

### Próximos Passos (FASE 2.34+)

- [ ] Auto-generate impact report on PR
- [ ] Slack notification on registry change
- [ ] Auto-comment on PRs with impact summary
- [ ] Dashboard de compliance violations
- [ ] Historical trend analysis
- [ ] Exception management system

---

## Referências

- `policies/compliance/compliance-severity-policy.yaml` — Severity levels
- `webui/services/convention_validator.py` — Validator engine
- `tools/local/validate_compliance_policies.py` — YAML validation
- `tools/local/compliance_policy_impact_report.py` — Impact analysis
- `docs/75-webui-convention-registry-integration.md` — Web UI integration

---

**Status:** ✅ Operational
**Approval Chain:** Network Eng → Compliance Owner → PR Merge
**Safety:** Registry-first, zero NetBox writes, fallback hardening
