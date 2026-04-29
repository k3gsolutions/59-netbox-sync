# Week 1 Response Intake Process

**Status:** FASE 2.12
**Date:** 2026-04-29
**Version:** 1.0

---

## Overview

Process for receiving, validating, and classifying team responses to the Week 1 metadata collection initiative.

---

## Response Collection (Week 1: 2026-05-02 to 2026-05-08)

### Timeline

| Day | Activity | Owner | Status |
|-----|----------|-------|--------|
| Mon 2026-05-02 | Engagement package distributed | Lead | PENDING |
| Tue-Wed | Teams collect metadata | Teams | PENDING |
| Thu EOD | Response deadline | Teams | PENDING |
| Fri | Initial review + escalation | Reviewer | PENDING |

### Expected Responses

**Service Team:** CSV or table with 5 subinterfaces
```
Eth-Trunk0.10
Eth-Trunk0.147
Eth-Trunk0.1580
Eth-Trunk0.1589
Eth-Trunk0.1606
```

**Network Ops:** CSV or table with 1 IP
```
192.0.2.1/30
```

**BGP Team:** CSV or table with 1 BGP peer
```
203.0.113.1
```

---

## Response Format

### Acceptable Formats
- CSV file
- Markdown table
- Email table
- JSON (if structured)

### Required Columns
- object_key (what we're enriching)
- Required metadata fields (tenant, service_type, etc.)
- owner (person responsible)
- evidence (documentation reference)
- notes (any additional context)

### Response Location
**Directory:** `reports/pilot-device-compliance/week1-responses/`

**Files:**
- `service-team-response.csv`
- `network-ops-response.csv`
- `bgp-team-response.csv`

---

## Validation Process (Week 1 EOW + Week 2 Monday)

### Script
```bash
python3 tools/local/validate_week1_responses.py \
  --template reports/pilot-device-compliance/week1-metadata-collection-template.csv \
  --responses-dir reports/pilot-device-compliance/week1-responses \
  --output reports/pilot-device-compliance/week1-response-validation.md \
  --device 4WNET-MNS-KTG-RX
```

### Validation Checks

**Per Item:**
- [ ] All required fields filled
- [ ] Field values match acceptable format
- [ ] Owner identified
- [ ] Evidence provided
- [ ] No secrets/sensitive data
- [ ] Naming convention valid

**Per Team:**
- [ ] All assigned items responded
- [ ] Response format correct
- [ ] CSV/table readable
- [ ] No corruption

---

## Classification

### Status Codes

| Status | Meaning | Action |
|--------|---------|--------|
| **validated** | All criteria met | Move to Week 2 review |
| **needs_clarification** | Some fields missing/invalid | Return to team for update |
| **still_pending** | No response received yet | Follow up with team |
| **blocked** | Cannot be enriched | Escalate (service unavailable, etc.) |
| **rejected** | Response invalid/conflicting | Return with explanation |

### Validation Criteria by Type

#### Subinterface (Service Team)
- [x] Tenant present + valid (known domain)
- [x] Service type present + valid (circuit, L3VPN, etc.)
- [x] Criticality present + valid (high/medium/low)
- [x] Owner identified
- [x] Evidence provided
- [x] Parent interface exists (pre-validated ✅)
- [x] No naming conflicts

#### IP Address (Network Ops)
- [x] Interface present + exists on device
- [x] VRF present + matches device config
- [x] Owner identified
- [x] Evidence provided
- [x] Consistent with device inventory
- [x] No IP conflicts

#### BGP Peer (BGP Team)
- [x] Remote ASN present + valid (1-4294967295)
- [x] BGP group assigned + matches org structure
- [x] Owner identified
- [x] Evidence provided
- [x] Documented in BGP design
- [x] No peer conflicts

---

## Week 1 Validation Output

### Report: week1-response-validation.md

**Sections:**
1. Summary (counts by status)
2. Validated items (ready for Week 2)
3. Needs clarification (return to teams)
4. Still pending (follow up required)
5. Blocked/rejected (escalation)
6. Next steps

**Example:**
```
# Week 1 Response Validation

## Summary
| Status | Count |
|--------|-------|
| Validated | 3 |
| Needs Clarification | 2 |
| Still Pending | 2 |
| Total | 7 |

## Validated (Ready for Week 2)
- Eth-Trunk0.10 (subinterface, Service Team) ✓
- 192.0.2.1/30 (ip_address, Network Ops) ✓
- 203.0.113.1 (bgp_peer, BGP Team) ✓

## Needs Clarification
- Eth-Trunk0.147: Missing criticality level
- Eth-Trunk0.1580: Tenant not recognized

...
```

---

## Week 2 Candidates

### Document: week2-review-candidates.md

**Purpose:** List items validated in Week 1 that are ready for Week 2 review

**Populated with:**
- All items with status = "validated"
- Enriched metadata from responses
- Owner information
- Evidence references

**Note:** No automatic ApprovalRecord creation — manual review required

---

## Response Handling

### If Validated
1. ✓ Item moves to Week 2 review
2. ✓ Risk assessment conducted
3. ✓ ApprovalRecord created (manual)
4. ✓ Approval recommendation made

### If Needs Clarification
1. ⚠️ Item returned to team
2. ⚠️ Specific feedback provided
3. ⚠️ Team re-submits clarification
4. ⚠️ Re-validated in Week 2

### If Still Pending
1. ❌ Follow up with team
2. ❌ Escalate to team lead
3. ❌ Set escalation deadline
4. ❌ If no response by deadline → blocked

### If Blocked/Rejected
1. 🛑 Escalation required
2. 🛑 Document reason
3. 🛑 Decision authority review
4. 🛑 Update team with decision

---

## Success Metrics

| Metric | Target | Status |
|--------|--------|--------|
| Response rate | 100% (7/7 items) | PENDING |
| Validation completion | Week 2 Monday | PENDING |
| Validated items | > 80% | PENDING |
| Needs clarification | < 20% | PENDING |
| Zero rejections | 100% | PENDING |

---

## Escalation Matrix

| Issue | Owner | Deadline |
|-------|-------|----------|
| No response by Thu EOD | Team lead | Fri 2026-05-03 |
| Needs clarification | Original team | Tue 2026-05-06 |
| Still pending after 1 week | Supervisor | Mon 2026-05-09 |
| Blocked items | Director | Thu 2026-05-05 |

---

## Security & Compliance

✅ No automatic approvals
✅ All responses manually reviewed
✅ Audit trail of all validations
✅ Zero NetBox API calls
✅ Zero writes during intake
✅ Secrets detection (none allowed)

---

## See Also

- FASE 2.11 — Week 1 Metadata Collection Workflow
- FASE 2.12 — Week 1 Response Intake (this phase)
- FASE 2.13+ — Week 2+ processes
- reports/week1-metadata-collection.md
- reports/week1-response-validation.md
- reports/week2-review-candidates.md
