# Week 1 Metadata Collection — 4WNET-MNS-KTG-RX

**Week:** 2026-04-29 to 2026-05-08 (Week 1)
**Device:** 4WNET-MNS-KTG-RX (ID: 1890)
**FASE:** 2.11
**Status:** Ready to distribute to teams

---

## Objective

Collect missing metadata from 3 responsible teams to enrich 6 service candidate items from `missing_metadata` to `ready_for_review` status.

---

## Scope

- **Collection Only** — No writes, no approvals, no automation
- **Manual Enrichment** — Teams provide metadata via response format
- **Validation** — Each response checked against acceptance criteria
- **Output:** Week 2 (2026-05-09) ready for ApprovalRecord creation

---

## Service Candidates to Enrich

| # | Type | Item | Responsible Team | Status | Target |
|---|------|------|------------------|--------|--------|
| 1 | subinterface | Eth-Trunk0.10 | Service Team | pending | Week 1 |
| 2 | subinterface | Eth-Trunk0.147 | Service Team | pending | Week 1 |
| 3 | subinterface | Eth-Trunk0.1580 | Service Team | pending | Week 1 |
| 4 | subinterface | Eth-Trunk0.1589 | Service Team | pending | Week 1 |
| 5 | subinterface | Eth-Trunk0.1606 | Service Team | pending | Week 1 |
| 6 | ip_address | 192.0.2.1/30 | Network Ops | pending | Week 1 |
| 7 | bgp_peer | 203.0.113.1 | BGP Team | pending | Week 1 |

---

## Service Team — Subinterfaces (5 items)

### Items to Enrich

| # | Object Key | Parent | VLAN | Status |
|---|------------|--------|------|--------|
| 1 | Eth-Trunk0.10 | Eth-Trunk0 ✅ | [TBD] | pending |
| 2 | Eth-Trunk0.147 | Eth-Trunk0 ✅ | [TBD] | pending |
| 3 | Eth-Trunk0.1580 | Eth-Trunk0 ✅ | [TBD] | pending |
| 4 | Eth-Trunk0.1589 | Eth-Trunk0 ✅ | [TBD] | pending |
| 5 | Eth-Trunk0.1606 | Eth-Trunk0 ✅ | [TBD] | pending |

### Required Fields

| Field | Type | Required | Example | Notes |
|-------|------|----------|---------|-------|
| tenant | string | YES | internet, mpls, corporate | Service domain |
| service_type | enum | YES | circuit, L3VPN, MPLS, BGP, static | Service classification |
| criticality | enum | YES | high, medium, low | SLA/rollback priority |
| owner | string | YES | [name/email] | Service owner |
| description | string | NO | Internet circuit to ISP-A | Service purpose |
| qinq_vlan | int | NO | 200 | Inner VLAN if double-tagged |

### Response Format

**Return via:** Email or [RESPONSE_CHANNEL]

```
Device: 4WNET-MNS-KTG-RX
Submitted By: [YOUR_NAME]
Date: 2026-04-29
Team: Service Team

| Object Key | Tenant | Service Type | Criticality | Owner | Description | Status |
|------------|--------|--------------|-------------|-------|-------------|--------|
| Eth-Trunk0.10 | [VALUE] | [VALUE] | [VALUE] | [YOUR_NAME] | [optional] | ✓ |
| Eth-Trunk0.147 | [VALUE] | [VALUE] | [VALUE] | [YOUR_NAME] | [optional] | ✓ |
| Eth-Trunk0.1580 | [VALUE] | [VALUE] | [VALUE] | [YOUR_NAME] | [optional] | ✓ |
| Eth-Trunk0.1589 | [VALUE] | [VALUE] | [VALUE] | [YOUR_NAME] | [optional] | ✓ |
| Eth-Trunk0.1606 | [VALUE] | [VALUE] | [VALUE] | [YOUR_NAME] | [optional] | ✓ |
```

### Acceptance Criteria

Item advances to Week 2 ONLY if:
- [x] All required fields filled
- [x] Values match organizational standards
- [x] Owner identified
- [x] Tenant valid (known domain)
- [x] Service type from approved list
- [x] Criticality set (high/medium/low)
- [x] No naming conflicts
- [x] Parent interface exists (already verified ✅)

---

## Network Operations — IP Address (1 item)

### Item to Enrich

| # | Object | Current Status | Discovered From |
|---|--------|-----------------|-----------------|
| 1 | 192.0.2.1/30 | Exists on device | Inventory audit |

### Required Fields

| Field | Type | Required | Example | Notes |
|-------|------|----------|---------|-------|
| interface | string | YES | GigabitEthernet0/5/0 | Must exist on device |
| vrf | string | YES | internet, management | VRF scope |
| tenant | string | NO | internet, mpls | Service tenant |
| description | string | NO | Link to customer-a | IP purpose |
| owner | string | YES | [name/email] | Responsible person |

### Response Format

**Return via:** Email or [RESPONSE_CHANNEL]

```
Device: 4WNET-MNS-KTG-RX
Submitted By: [YOUR_NAME]
Date: 2026-04-29
Team: Network Operations

IP Address: 192.0.2.1/30

| Field | Value | Status |
|-------|-------|--------|
| Interface | [VALUE] | ✓ |
| VRF | [VALUE] | ✓ |
| Tenant (Optional) | [VALUE] | ✓ |
| Description (Optional) | [VALUE] | ✓ |
| Owner | [YOUR_NAME] | ✓ |
```

### Acceptance Criteria

Item advances to Week 2 ONLY if:
- [x] Interface provided + exists on device
- [x] VRF provided + matches device config
- [x] Owner identified
- [x] Consistent with device inventory
- [x] No conflicts with existing IPs

---

## BGP Team — BGP Peer (1 item)

### Item to Enrich

| # | Object | Current Status | Remote IP |
|---|--------|-----------------|-----------|
| 1 | 203.0.113.1 | Ready for enrichment | 203.0.113.1 |

### Required Fields

| Field | Type | Required | Example | Notes |
|-------|------|----------|---------|-------|
| remote_asn | int | YES | 65000, 15169 | BGP AS number |
| remote_bgp_group | string | YES | ISP-Uplink-1, Customer-B | Logical grouping |
| policy_intent | string | NO | local_as 65001, allow_as_in | BGP policies |
| criticality | string | NO | high, medium, low | Service criticality |
| owner | string | YES | [name/email] | BGP owner |

### Response Format

**Return via:** Email or [RESPONSE_CHANNEL]

```
Device: 4WNET-MNS-KTG-RX
Submitted By: [YOUR_NAME]
Date: 2026-04-29
Team: BGP Operations

BGP Peer: 203.0.113.1

| Field | Value | Status |
|--------|-------|--------|
| Remote ASN | [VALUE] | ✓ |
| BGP Group | [VALUE] | ✓ |
| Policy Intent (Optional) | [VALUE] | ✓ |
| Criticality (Optional) | [VALUE] | ✓ |
| Owner | [YOUR_NAME] | ✓ |
```

### Acceptance Criteria

Item advances to Week 2 ONLY if:
- [x] Remote ASN provided + valid (1-4294967295)
- [x] BGP group assigned + matches org structure
- [x] Owner identified
- [x] Documented in BGP design
- [x] No conflicts with existing peers

---

## Timeline & Milestones

### Week 1 (2026-04-29 to 2026-05-08)

| Day | Activity | Owner | Status |
|-----|----------|-------|--------|
| Mon 2026-04-29 | Engagement package distributed | Lead | PENDING |
| Tue-Wed | Teams collect + validate metadata | Teams | PENDING |
| Thu EOD | Response deadline | Teams | PENDING |
| Fri 2026-05-03 | Review + escalation if needed | Reviewer | PENDING |

### Week 2 (2026-05-09 to 2026-05-15)

| Day | Activity | Owner | Status |
|-----|----------|-------|--------|
| Mon 2026-05-09 | Technical review of responses | Reviewer | BLOCKED |
| Tue | Create ApprovalRecords | Reviewer | BLOCKED |
| Wed | Dry-run validation | Ops | BLOCKED |
| Thu | Risk assessment | Approver | BLOCKED |
| Fri | Recommendations ready | Approver | BLOCKED |

### Week 3+ (2026-05-16+)

| Day | Activity | Owner | Status |
|-----|----------|-------|--------|
| Week 3 | Approval decisions | Approver | BLOCKED |
| Week 4+ | Batch execution + verification | Ops | BLOCKED |

---

## Response Tracking

### Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| pending | Not yet answered | Follow up |
| answered | Received, not validated | Review |
| needs_clarification | Response incomplete | Request update |
| validated | All criteria met | Advance to Week 2 |
| blocked | Cannot be enriched | Escalate |
| rejected | Does not meet criteria | Request re-submission |

### Tracking Table

| Object Key | Team | Submitted | Status | Notes |
|------------|------|-----------|--------|-------|
| Eth-Trunk0.10 | Service Team | [DATE] | pending | [NOTES] |
| Eth-Trunk0.147 | Service Team | [DATE] | pending | [NOTES] |
| Eth-Trunk0.1580 | Service Team | [DATE] | pending | [NOTES] |
| Eth-Trunk0.1589 | Service Team | [DATE] | pending | [NOTES] |
| Eth-Trunk0.1606 | Service Team | [DATE] | pending | [NOTES] |
| 192.0.2.1/30 | Network Ops | [DATE] | pending | [NOTES] |
| 203.0.113.1 | BGP Team | [DATE] | pending | [NOTES] |

---

## Support & Escalation

### Questions During Week 1

**Contact:** [LEAD_EMAIL] or [SUPPORT_CHANNEL]

**Common Issues:**
- Q: How do I know if my tenant is valid?
- A: Check organizational service domains list or ask [SERVICE_LEAD]

- Q: What if the interface doesn't exist yet?
- A: This blocks Week 2. Escalate to [INFRASTRUCTURE_LEAD]

- Q: Can I submit partial data?
- A: No. All required fields needed before advancing to Week 2.

### Escalation Path

If blocked:
1. Contact team lead
2. Request clarification from [LEAD]
3. Escalate to [SUPERVISOR] by [DATE]

---

## Security & Compliance

✅ No automatic approvals
✅ All responses manually reviewed
✅ Audit trail of all submissions
✅ Zero API calls to NetBox
✅ Zero tokens used
✅ Zero writes during collection

---

## See Also

- `service-owner-engagement-package.md` — Detailed engagement instructions
- `docs/46-service-owner-engagement.md` — Process documentation
- `service-candidate-readiness-test.md` — Analysis output
- `service-candidate-enrichment-plan.md` — Gap analysis

---

**Status:** Ready for Week 1 distribution
**Target Completion:** 2026-05-03 (responses) → 2026-05-09 (Week 2 ready)
