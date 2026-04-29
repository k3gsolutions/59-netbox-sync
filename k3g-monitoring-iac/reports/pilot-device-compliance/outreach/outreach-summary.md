# Week 1 Outreach Summary — 4WNET-MNS-KTG-RX

**Generated:** 2026-04-29
**Device:** 4WNET-MNS-KTG-RX (device_id: 1890)
**Status:** Ready to send outreach messages

---

## Objetivo

Coletar metadados faltantes para service candidates. Sem respostas, sem Week 2 review. Sem Week 2 review, sem ApprovalRecords.

---

## Timeline

| Data | Atividade | Responsável |
|------|-----------|-------------|
| 2026-04-29 | Gerar outreach pack | K3G Team |
| 2026-05-02 | Distribuir mensagens + CSVs | K3G Team |
| 2026-05-02 a 2026-05-08 | Times preenchem respostas | Service/Network/BGP Teams |
| 2026-05-08 | Prazo final EOD | Teams |
| 2026-05-09 | Validar respostas | K3G Team |
| 2026-05-09+ | Week 2 review board | K3G Team |

---

## Teams & Responsabilidades

### 1. Service Team

**Itens:** 5 subinterfaces
- Eth-Trunk0.10
- Eth-Trunk0.147
- Eth-Trunk0.1580
- Eth-Trunk0.1589
- Eth-Trunk0.1606

**Campos requeridos:**
- tenant (domínio de negócio)
- service_type (circuito, L3VPN, etc.)
- criticality (high/medium/low)
- owner (responsável)
- evidence (referência da política)

**Arquivo:** service-team-response.csv
**Status:** Não iniciado
**Contato:** [Service Team Lead]

### 2. Network Ops

**Itens:** 1 IP address
- 192.0.2.1/30

**Campos requeridos:**
- interface (interface do device)
- VRF (routing context)
- owner (responsável)
- evidence (referência de design)

**Arquivo:** network-ops-response.csv
**Status:** Não iniciado
**Contato:** [Network Ops Lead]

### 3. BGP Team

**Itens:** 1 BGP peer
- 203.0.113.1

**Campos requeridos:**
- remote_asn (ASN remoto)
- remote_bgp_group (grupo BGP)
- owner (responsável)
- evidence (referência de política)

**Arquivo:** bgp-team-response.csv
**Status:** Não iniciado
**Contato:** [BGP Team Lead]

---

## O Que Responder

### Subinterfaces (Service Team)

```
object_key,tenant,service_type,criticality,owner,evidence
Eth-Trunk0.10,[domínio],[tipo],[high/medium/low],[pessoa],[link/doc]
```

### IP Addresses (Network Ops)

```
object_key,interface,vrf,owner,evidence
192.0.2.1/30,[interface],[vrf],[pessoa],[link/doc]
```

### BGP Peers (BGP Team)

```
object_key,remote_asn,remote_bgp_group,owner,evidence
203.0.113.1,[asn],[grupo],[pessoa],[link/doc]
```

---

## Como Responder

1. Receber arquivo CSV vazio (template)
2. Preencher linhas com valores reais
3. Verificar: sem espaços vazios, sem caracteres especiais
4. Salvar: UTF-8, sem alterações de coluna
5. Enviar para: reports/pilot-device-compliance/week1-responses/

---

## Prazo

**Crítico:** 2026-05-08 EOD

Respostas após prazo = bloqueadas até fase seguinte.

---

## Validação

Após prazo, K3G Team valida:
- Campos obrigatórios preenchidos
- Valores válidos (sem secrets, sem caracteres inválidos)
- Naming consistency

Resultado: week1-response-validation.md

---

## Próximo Passo

Após validação:
- Itens "validated" → Week 2 review board
- Itens "needs_clarification" → Retorno para times
- Itens "still_pending" → Escalação
- Itens "blocked" → Investigação

---

## Contatos

- **K3G Lead:** [Name/Email]
- **Service Team Lead:** [Name/Email]
- **Network Ops Lead:** [Name/Email]
- **BGP Team Lead:** [Name/Email]

---

## Referências

- week1-metadata-collection.md (descrição detalhada)
- week1-metadata-collection-template.csv (templates por time)
- service-owner-engagement-package.md (contexto detalhado)

---

## Status Atual

| Status | Count | Items |
|--------|-------|-------|
| Still Pending | 7 | All items |
| Validated | 0 | None |
| Needs Clarification | 0 | None |

→ Aguardando respostas dos times.

