# Service Owner Engagement Package

**Device:** 4WNET-MNS-KTG-RX (ID: 1890)
**Date:** 2026-04-29
**FASE:** 2.10
**Status:** Ready for team distribution

---

## Executive Summary

Service candidates analyzed for device 4WNET-MNS-KTG-RX:
- **Total:** 7 items
- **Ready for Review:** 1 (BGP peer)
- **Missing Metadata:** 6 (5 subinterfaces + 1 IP address)
- **Blocked:** 0
- **Naming Failed:** 0

**Action Required:** 3 teams need to provide metadata for 6 items

---

## Items Assigned to Service Team

**Responsibility:** Provide tenant, service_type, and criticality for subinterfaces

### Subinterfaces Requiring Enrichment

| # | Object Key | Parent Interface | Current Status | Fields Missing | Owner | Target Date |
|---|------------|------------------|-----------------|-----------------|-------|-------------|
| 1 | Eth-Trunk0.10 | Eth-Trunk0 ✅ | Exists in device | tenant, service_type, criticality | [YOUR_NAME] | 2026-05-02 |
| 2 | Eth-Trunk0.147 | Eth-Trunk0 ✅ | Exists in device | tenant, service_type, criticality | [YOUR_NAME] | 2026-05-02 |
| 3 | Eth-Trunk0.1580 | Eth-Trunk0 ✅ | Exists in device | tenant, service_type, criticality | [YOUR_NAME] | 2026-05-02 |
| 4 | Eth-Trunk0.1589 | Eth-Trunk0 ✅ | Exists in device | tenant, service_type, criticality | [YOUR_NAME] | 2026-05-02 |
| 5 | Eth-Trunk0.1606 | Eth-Trunk0 ✅ | Exists in device | tenant, service_type, criticality | [YOUR_NAME] | 2026-05-02 |

### Information Needed per Subinterface

```
Object Key: [e.g., Eth-Trunk0.10]
Parent Interface: [e.g., Eth-Trunk0] (already exists ✅)
VLAN: [outer VLAN number]

REQUIRED FIELDS:
Tenant: [Service/tenant name, e.g., internet, mpls, corporate, guest]
Service Type: [circuit, L3VPN, MPLS, BGP, static, VLAN, other]
Criticality: [high, medium, low]

OPTIONAL FIELDS:
Description: [Service description, purpose]
QinQ VLAN: [Inner VLAN if double-tagged, if applicable]
Comments: [Any special notes, exceptions, owner contact]
```

### Expected Approval Timeline
1. **Week 1 (2026-05-02):** Service team fills in tenant + service_type + criticality
2. **Week 2 (2026-05-09):** Review + ApprovalRecord generation
3. **Week 3+ (2026-05-16):** Approval decision + batch execution

---

## Items Assigned to Network Operations Team

**Responsibility:** Provide interface/VRF mapping for IP address

### IP Address Requiring Enrichment

| # | Object | Current Status | Fields Missing | Owner | Target Date |
|---|--------|-----------------|-----------------|-------|-------------|
| 1 | 192.0.2.1/30 | Discovered on device | interface, vrf | [YOUR_NAME] | 2026-05-02 |

### Information Needed

```
IP Address: 192.0.2.1/30

REQUIRED FIELDS:
Interface: [e.g., GigabitEthernet0/5/0, Eth-Trunk1]
VRF: [e.g., internet, management, default]

OPTIONAL FIELDS:
Service Tenant: [If service-specific, e.g., internet, mpls]
Description: [IP purpose, subnet info, notes]
Comments: [Any special considerations]
```

### Expected Approval Timeline
1. **Week 1 (2026-05-02):** Network ops confirms interface + VRF mapping
2. **Week 2 (2026-05-09):** ApprovalRecord generation
3. **Week 3+ (2026-05-16):** Approval decision + execution

---

## Items Assigned to BGP Team

**Responsibility:** Provide remote_asn and BGP group classification

### BGP Peer Ready for Review

| # | Object | Current Status | Fields Present | Fields Missing | Owner | Target Date |
|---|--------|-----------------|-----------------|-----------------|-------|-------------|
| 1 | 203.0.113.1 | Ready for Review | remote_ip, device | remote_asn, remote_bgp_group | [YOUR_NAME] | 2026-05-02 |

### Information Needed

```
BGP Peer IP: 203.0.113.1

FIELDS ALREADY KNOWN:
Device: 4WNET-MNS-KTG-RX
Remote IP: 203.0.113.1

REQUIRED FIELDS:
Remote ASN: [BGP AS number of peer]
Remote BGP Group: [Logical grouping, e.g., ISP-Uplink-1, Customer-A, Backup-ISP]

OPTIONAL FIELDS:
Description: [Circuit/peer purpose]
Policy Intent: [BGP policies, local_as, allow_as_in, etc.]
Criticality: [high, medium, low]
Comments: [Owner contact, SLA info]
```

### Expected Approval Timeline
1. **Week 1 (2026-05-02):** BGP team confirms remote_asn + group
2. **Week 2 (2026-05-09):** ApprovalRecord generation
3. **Week 3+ (2026-05-16):** Approval decision + execution

---

## Criteria for Approval Transition

Before any item can move from **missing_metadata** to **ready_for_review** → **approval**:

### Subinterfaces (Service Team)
- [x] Parent interface exists in NetBox
- [ ] Tenant assigned (REQUIRED)
- [ ] Service type documented (REQUIRED)
- [ ] Criticality level set (REQUIRED)
- [ ] Naming valid (auto-checked)
- [ ] Owner/reviewer identified
- [ ] No secrets in description

### IP Address (Network Ops)
- [ ] Interface mapped (REQUIRED)
- [ ] VRF assigned (REQUIRED)
- [ ] Consistent with device config
- [ ] Tenant assigned (OPTIONAL)
- [ ] Owner/reviewer identified

### BGP Peer (BGP Team)
- [ ] Remote ASN confirmed (REQUIRED)
- [ ] BGP group classified (REQUIRED)
- [ ] Policy documented (OPTIONAL)
- [ ] No security concerns
- [ ] Owner/reviewer identified

---

## Timeline & Next Steps

### Week 1 (2026-05-02)
- [ ] Service team: Tenant assignment collected
- [ ] Network ops: VRF/interface mapping confirmed
- [ ] BGP team: Remote ASN + group confirmed
- [ ] Target: All 6 items enriched

### Week 2 (2026-05-09)
- [ ] Technical review of enriched data
- [ ] ApprovalRecord generation
- [ ] Risk assessment (BAIXO/MÉDIO/ALTO)
- [ ] Dry-run validation

### Week 3+ (2026-05-16)
- [ ] Approval decision
- [ ] Batch execution
- [ ] Compliance verification

---

## Response Format

**For Service Team & Network Ops:**
Use the tables below and return to [CONTACT]:

```
Device: 4WNET-MNS-KTG-RX
Date Completed: 2026-04-29

| Object Key | Tenant | Service Type | Criticality | Owner | Status |
|------------|--------|--------------|-------------|-------|--------|
| Eth-Trunk0.10 | [VALUE] | [VALUE] | [VALUE] | [YOUR_NAME] | ✓ |
| (repeat for each) |
```

**For BGP Team:**
```
Device: 4WNET-MNS-KTG-RX
Date Completed: 2026-04-29

| BGP Peer | Remote ASN | BGP Group | Owner | Status |
|----------|------------|-----------|-------|--------|
| 203.0.113.1 | [VALUE] | [VALUE] | [YOUR_NAME] | ✓ |
```

---

## Blockers & Exceptions

**None identified at this time.**

All 6 items have resolvable metadata gaps. No technical blockers preventing enrichment or approval.

---

## Security Notes

✅ No automatic approvals
✅ All data enrichment is manual + reviewed
✅ Service teams confirm ownership
✅ Naming validated during approval
✅ Audit trail of all decisions recorded

---

## Support & Escalation

**Questions?** Contact [NETWORK_TEAM_LEAD] or submit to [SUPPORT_CHANNEL]

**Escalation:** If metadata unavailable or conflicting, escalate to [SUPERVISOR] by [DATE]

---

## Appendix: Related Documents

- `docs/45-service-candidate-enrichment-workflow.md` — Enrichment strategy
- `reports/.../service-candidate-enrichment-plan.md` — Gap analysis
- `reports/.../service-candidate-readiness-test.md` — Analysis output
- `CHANGELOG.md` — FASE 2.9 details

---

**Status:** Ready for distribution
**Approver:** [SIGN OFF]
**Distribution:** Service Team, Network Ops, BGP Team
