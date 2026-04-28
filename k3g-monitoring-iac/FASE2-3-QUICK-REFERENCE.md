# FASE 2.3 & 2.4 — Quick Reference

## Commands Reference

### Execute Real NetBox Write

```bash
# 1. Set token (replace with actual token)
export NETBOX_WRITE_TOKEN="your-token-here"

# 2. Run batch apply
python3 tools/local/apply_batch_staged_netbox_objects.py \
  --batch-plan reports/pilot-device-compliance/approvals/approved/batch-apply-plan.json \
  --netbox-url https://docs.k3gsolutions.com.br \
  --confirm-batch-id 33423d0a \
  --operator "your-name" \
  --confirm-real-write-batch
```

### Dry-Run Mode (No Writes)

```bash
# Run without --confirm-real-write-batch to test
python3 tools/local/apply_batch_staged_netbox_objects.py \
  --batch-plan reports/pilot-device-compliance/approvals/approved/batch-apply-plan.json \
  --netbox-url https://docs.k3gsolutions.com.br \
  --confirm-batch-id 33423d0a \
  --operator "your-name"
```

### Service Candidate Readiness Analysis

```bash
# Analyze ImportPlan for service candidates
python3 tools/local/analyze_service_candidate_readiness.py \
  --import-plan reports/pilot-device-compliance/import-plan-4WNET-MNS-KTG-RX.md \
  --output reports/pilot-device-compliance/service-candidate-readiness.md \
  --device "4WNET-MNS-KTG-RX"
```

---

## Files Location

### Validation Reports
- `reports/FASE2-3-VALIDATION-REPORT.md` — Complete test results
- `reports/FASE2-3-REAL-WRITE-COMMAND.md` — Prepared real-write command

### Approval Records (approved/)
- `approval-4WNET-MNS-KTG-RX-fb0a50b3-*.json` — Eth-Trunk1
- `approval-4WNET-MNS-KTG-RX-d1dce466-*.json` — GigabitEthernet0/5/0

### ApplyPlans (approved/)
- `apply-plan-fb0a50b3-20260428T173011.json` — Eth-Trunk1 (JSON)
- `apply-plan-fb0a50b3.md` — Eth-Trunk1 (Markdown)
- `apply-plan-d1dce466-20260428T173011.json` — GigabitEthernet0/5/0 (JSON)
- `apply-plan-d1dce466.md` — GigabitEthernet0/5/0 (Markdown)

### Batch (approved/)
- `batch-apply-plan.json` — BatchApplyPlan (2 items, batch_id=33423d0a)
- `batch-apply-plan.md` — BatchApplyPlan (Markdown)

### Results (applied/)
- `batch-apply-result-33423d0a.md` — Dry-run result

### FASE 2.4 (Service Candidate Readiness)
- `service-candidate-readiness-test.md` — Analysis output
- `import-plan-test-readiness.json` — Test data

---

## Batch Plan Details

**Batch ID:** 33423d0a
**Items:** 2
- Item 1: Eth-Trunk1 (approval=fb0a50b3)
- Item 2: GigabitEthernet0/5/0 (approval=d1dce466)

**Validation Status:** ✓ Ready

**Gates Passed:** 7/7
- total_items <= max_items ✓
- batch size <= 2 (pilot limit) ✓
- all items are interface/base_inventory ✓
- method = POST ✓
- no PATCH/DELETE ✓
- approval_ids unique ✓
- object_keys unique ✓

---

## Safety Checklist

Before executing real write:

- [ ] NETBOX_WRITE_TOKEN obtained
- [ ] NetBox tags verified (discovery:staged, source:device)
- [ ] Batch ID confirmed: 33423d0a
- [ ] Operator name ready
- [ ] Network connectivity to NetBox verified
- [ ] Backup of current NetBox state taken (optional)

---

## Rollback Plan

If needed after real write:

```bash
# Delete created objects (if any)
export NETBOX_WRITE_TOKEN="your-token"

# Delete Eth-Trunk1
curl -X DELETE https://docs.k3gsolutions.com.br/api/dcim/interfaces/{id}/ \
  -H "Authorization: Token $NETBOX_WRITE_TOKEN"

# Delete GigabitEthernet0/5/0
curl -X DELETE https://docs.k3gsolutions.com.br/api/dcim/interfaces/{id}/ \
  -H "Authorization: Token $NETBOX_WRITE_TOKEN"
```

---

## Documentation

- [Batch Apply Design](docs/31-controlled-batch-staged-apply.md)
- [Batch Apply Runbook](docs/32-batch-apply-runbook.md)
- [Service Candidate Readiness](docs/33-service-candidate-readiness.md)
- [First Staged Write](docs/30-first-staged-netbox-write.md)
- [Approval Workflow Design](docs/23-approval-workflow-design.md)

---

## Test Results Summary

✅ All tests passed
- 24/24 Python scripts: valid syntax
- 122/122 documentation links: valid
- 3/3 negative tests: passed
- Dry-run execution: successful (0 writes)
- FASE 2.4 script: working correctly

**Ready for production execution when authorized.**
