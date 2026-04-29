# FASE 3.17 — Web UI Policy Visibility

**Status:** ✓ COMPLETO

## Objetivo

Exibir na Web UI as policies ativas e seus impactos, para operador entender por que um campo foi bloqueado ou alertado.

## Rotas HTTP (GET only)

### GET /policies

Lista 13 policies compliance.

**Resposta:** JSON com políticas, status validação, descrição PT-BR.

### GET /policies/{policy_name}

Visualiza policy específica (whitelist enforced).

**Whitelist (13):**
- discovery-elements
- dependency-map
- naming-conventions
- snmp-policy
- interface-policy
- vrf-policy
- bgp-policy
- route-policy-policy
- ip-prefix-policy
- community-policy
- as-path-policy
- comments-policy
- compliance-severity-policy

**Resposta:** YAML renderizado + status + descrição PT-BR.

**Segurança:**
- Path whitelist
- Secrets mascarados em resposta ([MASKED])
- Sem edição/upload
- Sem POST

### GET /policies/impact

Mostra relatório de impacto (FASE 2.34).

**Resposta:** JSON com impact_report, baseline_report, reports paths.

## Segurança

✓ Apenas GET — sem estado mutabledo
✓ Whitelist de policies
✓ Mascaramento de secrets
✓ Sem upload/edição via Web UI
✓ Sem POST
✓ Path traversal protegido

## Próximos Passos

- Adicionar card no dashboard inicial
- Link para /policies
- Link para /policies/impact
