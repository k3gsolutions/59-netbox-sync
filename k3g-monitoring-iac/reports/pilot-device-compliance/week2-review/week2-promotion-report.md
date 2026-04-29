# Week 2 Draft Promotion Report — 4WNET-MNS-KTG-RX

**Generated:** 2026-04-29T19:22:59.242562+00:00
**Device ID:** 1890

---

## Summary

| Status | Count |
|--------|-------|
| Promoted to ApprovalRecord | 0 |
| Not promoted | 7 |
| Missing draft files | 0 |
| **Total decisions processed** | **7** |

---

## Promoted to ApprovalRecord (status: proposed)

Drafts promoted with explicit human approval:

No drafts promoted.

---

## Not Promoted (Failed Validation)

Decisions that did NOT meet promotion criteria:

| Object Key | Decision | Reviewer | Reason |
|------------|----------|----------|--------|
| Eth-Trunk0.10 | [DECISION] |  | decision=[decision], expected 'approve_for_approval_record' |
| Eth-Trunk0.147 | [DECISION] |  | decision=[decision], expected 'approve_for_approval_record' |
| Eth-Trunk0.1580 | [DECISION] |  | decision=[decision], expected 'approve_for_approval_record' |
| Eth-Trunk0.1589 | [DECISION] |  | decision=[decision], expected 'approve_for_approval_record' |
| Eth-Trunk0.1606 | [DECISION] |  | decision=[decision], expected 'approve_for_approval_record' |
| 192.0.2.1/30 | [DECISION] |  | decision=[decision], expected 'approve_for_approval_record' |
| 203.0.113.1 | [DECISION] |  | decision=[decision], expected 'approve_for_approval_record' |

---

## Promotion Criteria (ALL required)

✅ decision = "approve_for_approval_record"
✅ approval_record_allowed = true
✅ reviewer field filled
✅ reviewed_at field filled with valid ISO datetime
✅ Draft file exists and valid JSON

---

## Promoted ApprovalRecords

Location: reports/pilot-device-compliance/approvals/pending/promoted

Created ApprovalRecords have status = "proposed" (not auto-approved).

Approval workflow:
1. ApprovalRecord created with status: proposed
2. Manual approval/rejection required (separate step)
3. No automatic transitions
4. Audit trail maintained

---

## Safety Confirmations

✅ No NetBox API calls
✅ No NetBox writes
✅ No ApplyPlan created
✅ No automatic approvals
✅ Manual review required
✅ Audit trail complete

---

**Status:** Promotion complete
**Next:** Review promoted ApprovalRecords in reports/pilot-device-compliance/approvals/pending/promoted
**Then:** Proceed to approval/rejection workflow
