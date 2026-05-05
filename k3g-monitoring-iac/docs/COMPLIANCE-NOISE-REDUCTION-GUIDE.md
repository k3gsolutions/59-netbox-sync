# Compliance Noise Reduction Guide

Guidelines for reducing false positives and policy-too-strict findings in compliance checks.

Date: 2026-05-05  
Project: K3G Monitoring & IaC  
Context: Huawei NE8000 router fleet  

---

## Overview

Compliance policies can be too strict, creating false positives that distract from real issues. This guide categorizes findings and recommends when to adjust policy vs. when to require human review.

**Three Categories:**

1. **Parser Noise** — Data extraction artifacts, not actual config issues
2. **Policy Too Strict** — Policy overgeneralized for this context
3. **Needs Human Review** — Real finding, requires human judgment

---

## Virtual-Ethernet Interface Findings

### Finding: Virtual-Ethernet*.100 State Mismatch

**Current Policy:** ERROR if state != up

**Actual Behavior:**
- Virtual-Ethernet is logical interface (not hardware port)
- State may not match physical port state
- 100 is VLAN subinterface ID
- Down state can be temporary (admin down for maintenance, vlan disabled, etc.)

**Recommendation:**
```yaml
finding_type: interface_state_mismatch
interface_pattern: "Virtual-Ethernet.*\\.[0-9]+"
current_severity: error
recommended_severity: warning
reason: "Logical subinterfaces have state independent of physical port"
action: "Change from error → warning in policy"
```

**Policy Change:**
```yaml
interface_state_validation:
  technical_interface:
    - Virtual-Ethernet
    - Eth-Trunk
    - LoopBack
    - NULL
    - Tunnel
    - Vlanif
  severity: warning_only
  note: "Technical interfaces state may not match hardware"
```

---

## Interface Naming Findings

### Finding: Interface Description Invalid/Missing

**Current Policy:** ERROR if description missing or invalid

**Actual Behavior:**
- Technical interfaces (NULL, Loop, MEth) don't need customer descriptions
- Auto-generated names acceptable for technical use
- Customer description needed only on customer-facing interfaces

**Recommendation:**
```yaml
finding_type: interface_description_invalid
interface_type: technical
current_severity: error
recommended_severity: warning
reason: "Technical interfaces may not require customer naming"
interfaces_affected:
  - "NULL" (null interface)
  - "LoopBack" (loopback)
  - "MEth" (management ethernet)
  - "Eth-Trunk*" (trunk aggregation)
action: "Skip error for technical interfaces; warning if undescribed"
```

### Finding: Interface Naming Convention Not Followed

**Current Policy:** ERROR if not [SVC=X][ID=X][NAME=X][ROLE=X]

**Actual Behavior:**
- Legacy interfaces may use different naming
- Newly provisioned interfaces follow bracket format
- Mixed environment acceptable during migration

**Recommendation:**
```yaml
finding_type: interface_naming_invalid
current_severity: error
recommended_severity: policy_review_required
reason: "Mixed naming formats during transition period acceptable"
policy_options:
  1. enforce_new_only: "Only new interfaces must follow bracket format"
  2. accept_legacy: "Accept legacy names, enforce bracket format for future"
  3. per_device: "Some devices use legacy, others new; flag per-device policy"
decision: "Option 2: enforce going forward, accept existing"
```

---

## BGP Findings

### Finding: BGP Peer State Not Established

**Current Policy:** ERROR if peer state != ESTABLISHED

**Actual Behavior:**
- BGP convergence takes time (seconds to minutes)
- Maintenance windows (updates, reboot, reconfig)
- Transient issues (network blip, AS-path change, policy update)
- Multiple peers; some may be down for maintenance

**Recommendation:**
```yaml
finding_type: bgp_peer_state_not_established
current_severity: error
recommended_severity: needs_human_review
reason: |
  BGP peer state depends on:
  1. Peer device availability
  2. Network path availability
  3. BGP policy convergence
  4. Maintenance windows
  Temporary down states are expected and normal.
action: "Classify as needs_human_review (not error)"
check_needed: "Is peer down > 1 hour? Contact NOC. Is it planned maintenance? OK."
```

### Finding: BGP Peer Missing Description

**Current Policy:** ERROR if description missing

**Actual Behavior:**
- Description is documentation, not config
- Missing description is gap, not misconfiguration
- Peer still works without description

**Recommendation:**
```yaml
finding_type: bgp_peer_description_missing
current_severity: error
recommended_severity: needs_human_review
reason: "Documentation gap. Peer works without description."
action: "Classify as needs_human_review; operator reviews and adds description"
automation: "Cannot auto-generate peer descriptions (requires knowledge of peer purpose)"
```

### Finding: BGP Route Policy Missing

**Current Policy:** ERROR if no policy defined

**Actual Behavior:**
- Default BGP behavior (accept all, send all) may be intentional
- Policy definition requires understanding customer intent
- Some peers intentionally have no restrictive policy

**Recommendation:**
```yaml
finding_type: bgp_policy_missing
current_severity: error
recommended_severity: needs_human_review
reason: |
  BGP policy definition depends on:
  1. Customer requirements
  2. Traffic pattern expectations
  3. Security posture (restrict vs. permissive)
  Cannot be inferred from config alone.
action: "Classify as needs_human_review; requires human knowledge"
```

---

## Prefix List and Route Policy

### Finding: Route Policy Not Applied to Peer

**Current Policy:** WARNING if policy not applied

**Actual Behavior:**
- Default policy acceptable in permissive environments
- Some peers intentionally have no explicit policy
- Policy application depends on operational model

**Recommendation:**
```yaml
finding_type: route_policy_not_applied
current_severity: warning
recommended_severity: warning_with_context
reason: "May be intentional design"
review_needed: "Confirm with network operations if default is acceptable"
```

---

## Summary Table: Classification Changes

| Finding Type | Current | Recommended | Reason |
|--------------|---------|-------------|--------|
| Interface state mismatch (virtual/logical) | ERROR | WARNING | Logical interfaces have independent state |
| Interface naming invalid (technical) | ERROR | POLICY_REVIEW | Technical interfaces don't need customer naming |
| Interface description missing (technical) | ERROR | WARNING | Auto-generated names acceptable for technical use |
| BGP peer state not ESTABLISHED | ERROR | NEEDS_REVIEW | Temporary due to convergence/maintenance |
| BGP peer description missing | ERROR | NEEDS_REVIEW | Documentation gap; peer works without it |
| BGP policy missing | ERROR | NEEDS_REVIEW | Requires understanding customer intent |
| Route policy not applied | WARNING | WARNING | May be intentional design |

---

## Implementation Roadmap

### Phase 1: Policy Updates (Immediate)
1. Update `policies/compliance/interface-policy.yaml`
   - Technical interfaces → warning for state mismatch
   - Technical interfaces → skip customer naming errors

2. Update `policies/compliance/bgp-policy.yaml`
   - BGP peer state → needs_human_review (not error)
   - BGP description missing → needs_human_review (not error)
   - BGP policy missing → needs_human_review (not error)

### Phase 2: Re-run Compliance
1. Re-parse all collection data with updated policies
2. Generate new findings with noise reduced
3. Compare before/after findings
4. Update triage reports

### Phase 3: Operator Training
1. Document why findings are classified as needs_human_review
2. Show examples of legitimate down states, maintenance windows
3. Train on what needs immediate action vs. next business day

---

## Testing

Before applying changes:

1. Run compliance on sample device (4WNET-MNS-KTG-RX)
2. Count findings before policy change
3. Apply policy changes
4. Re-run compliance with new policy
5. Count findings after
6. Verify reduction without losing real issues

Expected Reduction: ~30-40% of findings become needs_human_review

---

## Safety

✓ Policy adjustments are **read-only** analysis  
✓ No device changes from noise reduction  
✓ Findings still captured; just reclassified  
✓ Operator training required before rollout  

---

## References

- Interface Standards: `policies/standards/interface-standards.yaml`
- BGP Standards: `policies/standards/bgp-standards.yaml`
- Current Policies: `policies/compliance/*.yaml`
- Compliance Results: `reports/compliance/jobs/*/comparison/`

---

Generated: 2026-05-05T10:00:00Z
