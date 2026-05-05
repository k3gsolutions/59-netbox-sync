# Baseline Standards for K3G Solutions Network

Auto-generated operational standards based on device inventory and policy requirements.

Date: 2026-05-05  
Project: K3G Monitoring & IaC  
Target Platform: Huawei NE8000 series routers

---

## Files

### Interface Standards
**File:** `interface-standards.yaml`

Naming convention for customer-facing interfaces:
```
[SVC=CUST][ID=10492][NAME=EMPRESA-ABC][ROLE=INET][LOC=MNS-DC01][CAP=500M]
```

**Format:** Bracket key=value pairs
- `SVC`: Service type (CUST, IX, MPLS, MGMT)
- `ID`: Customer/service ID
- `NAME`: Customer name (uppercase, max 20 chars)
- `ROLE`: Interface role (INET, MPLS, IX, MGMT)
- `LOC`: Location code (optional)
- `CAP`: Capacity/bandwidth (optional)

**Legacy Support:** Pipe-separated format deprecated but still accepted
```
CUST|10492|EMPRESA-ABC|INET|MNS-DC01|500M
```

**Technical Interfaces:** No customer naming required
- Virtual-Ethernet
- Eth-Trunk
- LoopBack
- NULL
- MEth
- Tunnel
- Vlanif

### BGP Standards
**File:** `bgp-standards.yaml`

Requirements for BGP peers:
- Description required: `[AS|PEER-ID]: [Description]`
- Remote AS required
- MD5 password required (not logged)
- Address family specified
- Peer state: prefer ESTABLISHED (warning if not)
- Route policies defined
- Prefix lists where applicable

**Finding Classification:**
- BGP peer state not established → needs_human_review (temp issues expected)
- BGP policy missing → needs_human_review (customer intent required)
- BGP peer description missing → needs_human_review (documentation gap)

---

## Noise Reduction Rules

### Interface Standards
| Finding | Classification | Reason |
|---------|----------------|--------|
| Interface state mismatch (technical) | warning | NULL, Tunnel, Loop have special state semantics |
| Interface state mismatch (logical) | warning | Logical interfaces independent of hardware |
| Interface naming invalid (technical) | policy_too_strict | Technical interfaces don't need customer naming |
| Interface description missing (technical) | warning | May not require customer-level description |

### BGP Standards
| Finding | Classification | Reason |
|---------|----------------|--------|
| BGP peer state not ESTABLISHED | needs_human_review | Temporary due to maintenance/convergence |
| BGP peer description missing | needs_human_review | Documentation gap, not config error |
| BGP policy missing | needs_human_review | Requires understanding customer intent |

---

## Application

These standards are used for:
1. **Compliance validation:** Check device configs against standards
2. **Finding classification:** Reduce noise by understanding context
3. **Remediation planning:** Prioritize items needing human review vs. automation
4. **Documentation:** Generate expected vs. actual baseline reports

---

## Customization

Standards are defined per Tenant Group and Device Type:
- K3G Solutions / Huawei NE8000 (this file)
- Other vendors/groups (future)

To update standards:
1. Edit YAML files in this directory
2. Re-run compliance job with new standards
3. Compare findings before/after
4. Commit and deploy

---

## Safety

✓ Standards are **read-only** configuration  
✓ Used for **validation only**, no writes  
✓ **No device changes** from standards comparison  
✓ **Manual approval** required for any remediation  

---

Generated: 2026-05-05T10:00:00Z
