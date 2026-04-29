# Service Owner Engagement Process

**Status:** FASE 2.10
**Date:** 2026-04-29
**Version:** 1.0

---

## Objective

Establish structured process for engaging service teams, network operations, and BGP teams to enrich metadata for service candidates before approval and execution.

---

## Background

Service candidates are network objects discovered on devices that require additional metadata (tenant, service_type, criticality, etc.) to transition from `needs_review` to `ready_for_review` and then to approval.

### Why Engagement?

- **Tenant Assignment** → Determines cost center, SLA, approval tier
- **Service Type** → Affects risk assessment, rollback strategy
- **Criticality** → Drives approval urgency and monitoring
- **Interface/VRF Mapping** → Validates configuration consistency
- **BGP Metadata** → Enables peer validation and policy application

---

## Process Overview

### Phase 1: Preparation (FASE 2.10)
- Analyze service candidates
- Identify metadata gaps
- Create engagement package
- **Artifacts:**
  - service-owner-engagement-package.md
  - docs/46-service-owner-engagement.md (this document)
  - reports/.../service-candidate-enrichment-plan.md

### Phase 2: Engagement (FASE 2.10+)
- Distribute to teams
- Collect metadata
- Validate responses
- **Timeline:** Week 1 (2026-05-02)

### Phase 3: Review (FASE 2.10+)
- Technical review
- Create ApprovalRecords
- Dry-run validation
- **Timeline:** Week 2 (2026-05-09)

### Phase 4: Execution (FASE 2.10+)
- Approval decision
- Batch execution
- Compliance verification
- **Timeline:** Week 3+ (2026-05-16)

---

## Roles & Responsibilities

### Service Team Lead
- **Responsible for:** Tenant assignment, service_type, criticality
- **Timeline:** Week 1
- **Deliverable:** Enrichment table (5 subinterfaces)
- **Criteria:**
  - Tenant must match known service domains
  - Service type must be from approved list (circuit, L3VPN, MPLS, BGP, etc.)
  - Criticality must be high/medium/low

### Network Operations Lead
- **Responsible for:** Interface/VRF mapping (IP addresses)
- **Timeline:** Week 1
- **Deliverable:** Enrichment table (1 IP)
- **Criteria:**
  - Interface must exist on device
  - VRF must match device configuration
  - Mapping must be validated against running config

### BGP Team Lead
- **Responsible for:** Remote ASN, BGP group classification
- **Timeline:** Week 1
- **Deliverable:** Enrichment table (1 BGP peer)
- **Criteria:**
  - Remote ASN must be valid BGP number
  - BGP group must match organizational grouping
  - Peer must be documented in BGP design

---

## Engagement Package Contents

**File:** `reports/pilot-device-compliance/service-owner-engagement-package.md`

### Sections
1. Executive Summary (total items, breakdown by status)
2. Service Team Tasks (5 subinterfaces, required fields, timeline)
3. Network Ops Tasks (1 IP address, required fields, timeline)
4. BGP Team Tasks (1 BGP peer, required fields, timeline)
5. Criteria for Approval Transition (checklist per object type)
6. Timeline & Next Steps (weekly milestones)
7. Response Format (standardized tables for replies)
8. Support & Escalation (contacts, escalation path)

---

## Enrichment Fields Reference

### Tenant Field
- **Type:** String
- **Required:** Yes (for service_candidates)
- **Examples:** internet, mpls, corporate, guest, managed-service
- **Validation:** Must match known service domains in organization

### Service Type Field
- **Type:** String (enum)
- **Required:** Yes (for service_candidates)
- **Valid Values:** circuit, L3VPN, MPLS, BGP, static, VLAN, VRF
- **Examples:** internet (circuit), MPLS (VPN), BGP (peer)

### Criticality Field
- **Type:** String (enum)
- **Required:** Yes (for service_candidates)
- **Valid Values:** high, medium, low
- **Impact:** Determines approval tier, SLA, rollback strategy

### Interface Field (IP)
- **Type:** String
- **Required:** Yes (for IP addresses)
- **Format:** Interface name from device (e.g., GigabitEthernet0/5/0)
- **Validation:** Must exist on device

### VRF Field (IP)
- **Type:** String
- **Required:** Yes (for IP addresses)
- **Examples:** internet, management, default, customer-a
- **Validation:** Must match device running config

### Remote ASN Field (BGP)
- **Type:** Integer
- **Required:** Yes (for BGP peers)
- **Range:** 1-4294967295 (valid BGP AS range)
- **Examples:** 65000 (private), 15169 (Google), 8452 (Telenor)

### Remote BGP Group Field
- **Type:** String
- **Required:** Yes (for BGP peers)
- **Examples:** ISP-Uplink, Customer-A, Backup-Link
- **Purpose:** Logical grouping for policy application

---

## Timeline

### Week 1 (2026-05-02 to 2026-05-08)
- Monday: Distribute engagement package
- Tuesday-Wednesday: Teams collect/validate metadata
- Thursday: Responses deadline (EOD)
- Friday: Initial review + escalation if needed

### Week 2 (2026-05-09 to 2026-05-15)
- Monday: Technical review of enriched data
- Tuesday: Create ApprovalRecords
- Wednesday: Dry-run validation
- Thursday: Risk assessment
- Friday: Approval recommendations ready

### Week 3+ (2026-05-16+)
- Week 3: Approval decisions
- Week 4: Batch execution
- Week 4+: Compliance verification

---

## Response Handling

### Acceptable Responses
- ✅ All required fields filled
- ✅ Values match organizational standards
- ✅ Owner/reviewer identified
- ✅ Signed off by team lead

### Requires Clarification
- ⚠️ Partial fields (missing some required data)
- ⚠️ Non-standard values (need explanation)
- ⚠️ Conflicting data (inconsistent with device config)
- ⚠️ No owner identified

### Escalation Needed
- ❌ Missing response (team didn't respond)
- ❌ Cannot enrich (metadata unavailable)
- ❌ Conflict (organizational disagreement)
- ❌ Security concerns (name injection, etc.)

---

## Approval Transition Rules

### Subinterface Ready for Approval
- [x] Parent interface exists ✅
- [x] Tenant assigned
- [x] Service type documented
- [x] Criticality set
- [x] Naming valid
- [x] Owner identified

### IP Address Ready for Approval
- [x] Interface mapped
- [x] VRF assigned
- [x] Consistent with device
- [x] Owner identified

### BGP Peer Ready for Approval
- [x] Remote ASN confirmed
- [x] BGP group classified
- [x] Documented in BGP design
- [x] Owner identified

---

## Security Considerations

### Data Validation
- ✅ Reject inputs with special characters or injections
- ✅ Validate enum fields against approved lists
- ✅ Check consistency with device running config

### Audit Trail
- ✅ Record who submitted enrichment
- ✅ Record when data was collected
- ✅ Store original responses (read-only archive)
- ✅ Track all modifications

### Manual Review
- ✅ No automatic approvals of service candidates
- ✅ All enrichment requires human validation
- ✅ Cross-team review for conflicts

---

## Success Metrics

**FASE 2.10 Success:**
- [ ] Engagement package distributed to 3 teams
- [ ] 100% of required metadata collected
- [ ] 0 items escalated for conflict
- [ ] All responses reviewed + documented

**FASE 2.10+ Success:**
- [ ] 6 items transition from missing_metadata → ready_for_review
- [ ] ApprovalRecords generated with enriched data
- [ ] Dry-run validation passes
- [ ] Batch execution succeeds

---

## See Also

- FASE 2.9 — Service Candidate Enrichment Readiness (analysis)
- FASE 2.10 — Service Owner Engagement (this phase)
- FASE 2.11 — Service Candidate Approval Batch (future)
- docs/45-service-candidate-enrichment-workflow.md
- reports/.../service-owner-engagement-package.md
- reports/.../service-candidate-enrichment-plan.md
