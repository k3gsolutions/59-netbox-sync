# Service Candidate Enrichment Workflow

**Status:** Draft
**Date:** 2026-04-29
**FASE:** 2.9
**Security:** Read-only analysis, no writes, no tokens

---

## Objective

Prepare enrichment strategy for service candidates without executing writes. Service candidates are network objects that depend on service/tenant metadata to transition from `needs_review` to `safe_create_staged`.

---

## Scope

### Included
- Service candidate classification analysis
- Readiness assessment by type
- Missing metadata identification
- Enrichment workflow design
- Risk assessment
- Manual intervention points
- Approval prerequisites

### Not Included
- Automatic writes to NetBox
- Automatic approval generation
- Service candidate creation
- /sync execution
- Equipment configuration

---

## Background

### Inventory Classification

**Base Inventory** (safe_create_staged without service context)
- Physical interfaces (Eth-Trunk0, GigabitEthernet0/5/0)
- VRFs (if standalone)
- VLANs (if documented)
- BGP peers (with remote_as present)

**Service Candidates** (needs_review → requires enrichment)
- Subinterfaces (depend on parent + service/tenant)
- IPs on service interfaces
- Secondary VLANs
- BGP peer sessions (if remote_as missing)
- Policy/QoS objects

### Why Enrichment

Service candidates cannot be `safe_create_staged` until:
1. **Parent relationship confirmed** — subinterface parent exists
2. **Tenant assigned** — service belongs to known tenant
3. **Service type documented** — circuit type, criticality, SLA
4. **Naming validated** — service:tenant:type naming convention
5. **IP/VRF context** — IP assignment and VRF scope

---

## Readiness Categories

### 1. Ready for Review
- All required fields present
- Naming convention matches
- Parent/dependencies satisfied
- No conflicts with existing objects

**Example:** Subinterface `eth0.100:internet:critical` with parent eth0, tenant=internet, criticality=high

### 2. Missing Tenant
- Object identified but tenant not documented
- Naming suggests service but no tenant assignment
- Requires manual enrichment before approval

**Example:** Subinterface without tenant field

### 3. Missing Service Type
- Tenant known but service type/criticality not set
- Prevents risk classification
- Required for approval decision

**Example:** Subinterface with tenant but no criticality/circuit_type

### 4. Missing Criticality
- Tenant and service known but criticality not set
- Prevents SLA/rollback decision
- Common for service candidates

### 5. Naming Failed
- Name violates service naming convention
- Prevents automatic `safe_create_staged` classification
- Requires manual review + renaming decision

**Example:** Subinterface with invalid naming pattern

### 6. Parent Missing
- Subinterface references non-existent parent
- Cannot create without parent existing
- Blocks creation until parent added

**Example:** Subinterface eth0.100 but eth0 does not exist

### 7. IP/VRF Missing
- IP address exists but VRF context unclear
- VLAN missing for tagged interface
- Required for full inventory context

### 8. BGP Metadata Missing
- BGP peer without remote_as, remote_bgp_group, or description
- Insufficient to validate peer relationship
- Requires additional discovery

### 9. Blocked
- Object has explicit block reason (incompatibility, security, etc.)
- Cannot transition to `safe_create_staged`
- Requires exception/override process

### 10. Ignored
- Object flagged for manual review later
- Not in critical path
- Can be deferred

---

## Enrichment Fields by Type

### Subinterface
| Field | Required | Notes |
|-------|----------|-------|
| parent | Yes | Physical interface must exist |
| vlan | Yes | Outer VLAN for tagged |
| qinq_vlan | No | Inner VLAN if double-tagged |
| tenant | Yes | Service tenant (manual enrichment) |
| service_type | Yes | e.g., circuit, L3VPN, MPLS |
| criticality | Yes | high/medium/low |
| description | Recommended | Service description |
| name | Yes | Must match `parent.N:service:tenant` pattern |

### IP Address
| Field | Required | Notes |
|-------|----------|-------|
| address | Yes | CIDR format |
| vrf | Yes | VRF scope |
| interface | Yes | Parent interface |
| tenant | Recommended | Service tenant if not interface-wide |
| description | Recommended | IP purpose |

### BGP Peer
| Field | Required | Notes |
|-------|----------|-------|
| name | Yes | Peer identifier |
| remote_asn | Yes | BGP AS number |
| remote_address | Yes | Peer IP |
| remote_bgp_group | Yes | Logical grouping (ISP, customer, etc.) |
| tenant | Recommended | Service tenant |
| description | Recommended | Peer purpose/circuit |

---

## Enrichment Process

### 1. Discovery
- Audit device inventory (NETCONF/SSH)
- Compare with NetBox current state
- Identify missing or divergent objects
- Classify by type and readiness

### 2. Analysis
- Parse ImportPlan
- Count by category
- Identify primary blockers
- Group by tenant/service

### 3. Engagement
- Present to service owners
- Request missing metadata
- Validate naming conventions
- Document enrichment decisions

### 4. Approval
- Create ApprovalRecord with enriched data
- Risk assessment (BAIXO/MÉDIO/ALTO)
- Approval decision (approve/defer/reject)
- Generate evidence/justification

### 5. Execution
- Validate enriched payload
- Dry-run execution
- Real POST with monitoring
- Compliance verification

---

## Risk Assessment

### By Readiness

| Category | Risk | Action |
|----------|------|--------|
| Ready for Review | BAIXO | Expedite to approval |
| Missing Tenant | MÉDIO | Manual enrichment required |
| Missing Service Type | MÉDIO | Owner engagement |
| Naming Failed | MÉDIO | Convention review |
| Parent Missing | ALTO | Dependency resolution |
| Blocked | ALTO | Exception process |

---

## Security Considerations

1. **No Automatic Approval** — Service candidates never auto-approve
2. **Tenant Validation** — Confirm tenant ownership before approval
3. **Naming Audit** — Prevent injections via service naming
4. **Access Control** — Service enrichment limited to service owners
5. **Audit Trail** — All enrichment decisions logged

---

## Timeline

**FASE 2.9** (Current)
- Analysis & readiness reporting
- Gap identification
- Owner engagement plan

**FASE 2.10** (Future)
- Enrichment manual process
- Owner-driven metadata input
- Validation workflow

**FASE 2.11+** (Future)
- Approval queue management
- Batch approval workflows
- Approval templates for service types

---

## Success Criteria

✅ Service candidates categorized by readiness
✅ Blockers identified and prioritized
✅ Enrichment requirements documented
✅ Owner engagement plan established
✅ No automatic changes to inventory
✅ Audit trail complete

---

## See Also

- FASE 1.3 — ImportPlan design
- FASE 1.4 — Approval workflow
- docs/23-approval-workflow-design.md
- tools/local/analyze_service_candidate_readiness.py
