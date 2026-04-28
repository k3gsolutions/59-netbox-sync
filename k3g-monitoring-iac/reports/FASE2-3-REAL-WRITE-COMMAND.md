# Real NetBox Write Command — FASE 2.3 Batch Apply

**Status:** Prepared but NOT executed
**Batch ID:** 33423d0a
**Items:** 2 (Eth-Trunk1, GigabitEthernet0/5/0)
**Date:** 2026-04-28T17:31:00Z
**Validated:** ✅ All dry-runs and negative tests passed

## Prerequisites

1. ✅ Dry-run validation passed
2. ✅ All ApplyPlans validated (readiness_status=ready)
3. ✅ BatchApplyPlan validated
4. ⚠️ NETBOX_WRITE_TOKEN must be provided at execution time
5. ⚠️ NetBox tags must exist (discovery:staged, source:device, discovery:netops_netbox_sync)

## Command to Execute Real Write

```bash
# Set token in environment (NOT in command line)
export NETBOX_WRITE_TOKEN="your-token-here"

# Execute batch apply with real write
python3 tools/local/apply_batch_staged_netbox_objects.py \
  --batch-plan reports/pilot-device-compliance/approvals/approved/batch-apply-plan.json \
  --netbox-url https://docs.k3gsolutions.com.br \
  --confirm-batch-id 33423d0a \
  --operator "your-name-here" \
  --confirm-real-write-batch
```

## Safety Checks (Automatic)

- ✅ All-or-none preflight validation
- ✅ Object existence check (GET /api/dcim/interfaces/)
- ✅ Tag existence check (GET /api/extras/tags/)
- ✅ Payload validation (no secrets)
- ✅ Item-by-item execution (stops on first failure)

## Expected Result

- **Status:** batch_applied (all items created as staged)
- **Output file:** batch-apply-result-33423d0a.md
- **Location:** reports/pilot-device-compliance/approvals/applied/

## Post-Apply Actions

1. Verify items in NetBox UI
2. Run compliance report: `/compliance/analyze/report`
3. Archive compliance report
4. Generate comparison (before/after)
5. Re-run service candidate readiness analysis

## Rollback (If Needed)

If needed, delete staged objects via NetBox UI or API:

```bash
# Delete Eth-Trunk1 (if created)
curl -X DELETE https://docs.k3gsolutions.com.br/api/dcim/interfaces/<id>/ \
  -H "Authorization: Token $NETBOX_WRITE_TOKEN"

# Delete GigabitEthernet0/5/0 (if created)
curl -X DELETE https://docs.k3gsolutions.com.br/api/dcim/interfaces/<id>/ \
  -H "Authorization: Token $NETBOX_WRITE_TOKEN"
```

## Documentation References

- Batch Apply Design: docs/31-controlled-batch-staged-apply.md
- Batch Apply Runbook: docs/32-batch-apply-runbook.md
- Service Candidate Readiness: docs/33-service-candidate-readiness.md
- First Staged Write: docs/30-first-staged-netbox-write.md
