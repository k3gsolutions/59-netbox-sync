# Week 1 Response Tracker — 4WNET-MNS-KTG-RX

**Device:** 4WNET-MNS-KTG-RX (device_id: 1890)
**Timeline:** 2026-05-02 to 2026-05-08
**Generated:** 2026-04-29
**Status:** Awaiting Responses

---

## Summary

| Status | Count |
|--------|-------|
| Not Started | 3 teams |
| Partial | 0 teams |
| Complete | 0 teams |
| Overdue | 0 teams |
| **Total Expected** | **3 CSVs** |

---

## Response Status by Team

### 1. Service Team

| Field | Value |
|-------|-------|
| **Team** | Service Team |
| **Total Items** | 5 subinterfaces |
| **Response File** | service-team-response.csv |
| **Status** | 🔴 NOT_STARTED |
| **Last Update** | — |
| **Items Responded** | 0/5 |
| **Items Pending** | 5/5 (Eth-Trunk0.10, Eth-Trunk0.147, Eth-Trunk0.1580, Eth-Trunk0.1589, Eth-Trunk0.1606) |
| **Blocker** | Awaiting response |
| **Next Action** | Send message + template |
| **Deadline** | 2026-05-08 EOD |

**Messages:**
- message-service-team.md (sent 2026-04-29)

**Template Columns:**
```
object_key,tenant,service_type,criticality,owner,evidence
```

**Expected Responses:**
- Eth-Trunk0.10: (pending)
- Eth-Trunk0.147: (pending)
- Eth-Trunk0.1580: (pending)
- Eth-Trunk0.1589: (pending)
- Eth-Trunk0.1606: (pending)

---

### 2. Network Ops

| Field | Value |
|-------|-------|
| **Team** | Network Ops |
| **Total Items** | 1 IP address |
| **Response File** | network-ops-response.csv |
| **Status** | 🔴 NOT_STARTED |
| **Last Update** | — |
| **Items Responded** | 0/1 |
| **Items Pending** | 1/1 (192.0.2.1/30) |
| **Blocker** | Awaiting response |
| **Next Action** | Send message + template |
| **Deadline** | 2026-05-08 EOD |

**Messages:**
- message-network-ops.md (sent 2026-04-29)

**Template Columns:**
```
object_key,interface,vrf,owner,evidence
```

**Expected Responses:**
- 192.0.2.1/30: (pending)

---

### 3. BGP Team

| Field | Value |
|-------|-------|
| **Team** | BGP Team |
| **Total Items** | 1 BGP peer |
| **Response File** | bgp-team-response.csv |
| **Status** | 🔴 NOT_STARTED |
| **Last Update** | — |
| **Items Responded** | 0/1 |
| **Items Pending** | 1/1 (203.0.113.1) |
| **Blocker** | Awaiting response |
| **Next Action** | Send message + template |
| **Deadline** | 2026-05-08 EOD |

**Messages:**
- message-bgp-team.md (sent 2026-04-29)

**Template Columns:**
```
object_key,remote_asn,remote_bgp_group,owner,evidence
```

**Expected Responses:**
- 203.0.113.1: (pending)

---

## Overall Timeline

```
2026-04-29: Outreach pack gerado
            ↓
2026-05-02: Mensagens enviadas + CSVs distribuídos
            ↓
2026-05-02 a 2026-05-08: Teams preenchem respostas
            ↓
2026-05-08 EOD: Prazo final
            ↓
2026-05-09: Validação automática + revisão humana
            ↓
2026-05-09+: Week 2 review board gerado
```

---

## Escalation Rules

### If No Response by 2026-05-06

- Send reminder email
- Contact team lead directly
- Update tracker status → ESCALATED

### If Partial Response by 2026-05-08

- Mark as PARTIAL
- Request completion by 2026-05-09 09:00
- Block full validation until complete

### If No Response by 2026-05-08 EOD

- Mark as OVERDUE
- Block items → still_pending status
- Escalate to director level
- Plan follow-up in Week 2

---

## Validation Checklist

For each response received:

- [ ] File exists (correct name, correct location)
- [ ] CSV format valid (UTF-8, no corruption)
- [ ] All required columns present
- [ ] All rows have values (no empty fields)
- [ ] No secrets/sensitive data
- [ ] No special characters (ASCII only)
- [ ] Values match validation criteria
- [ ] Record in tracker

---

## Next Phases

### Phase 1: Response Collection (2026-05-02 to 2026-05-08)
- Distribuir mensagens
- Acompanhar responses
- Enviar reminders se necessário
- Atualizar tracker

### Phase 2: Validation (2026-05-09)
- Validação automática (formato)
- Revisão humana (valores)
- Gerar validation report (week1-response-validation.md)
- Classificar: validated, needs_clarification, still_pending, blocked

### Phase 3: Week 2 Review (2026-05-09+)
- Gerar review board (prepare_week2_review.py)
- Review + risk assessment
- Decisões humanas
- Promotion para ApprovalRecords

---

## Contacts

| Role | Name | Email | Team |
|------|------|-------|------|
| K3G Lead | [Name] | [email] | K3G Team |
| Service Lead | [Name] | [email] | Service Team |
| Ops Lead | [Name] | [email] | Network Ops |
| BGP Lead | [Name] | [email] | BGP Team |

---

## Notes

- Zero NetBox writes durante Week 1
- Nenhum token requerido
- Todas as CSVs lidas localmente
- Nenhuma automatização de approval
- Auditoria completa das respostas
- Resposta é pré-requisito para Week 2

---

**Status:** Ready to deploy outreach pack.
**Owner:** K3G Team
**Last Updated:** 2026-04-29T[TIME]

