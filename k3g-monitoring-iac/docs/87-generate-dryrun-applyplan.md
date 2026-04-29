# FASE 2.42 — Generate Dry-Run ApplyPlan

## Overview

**FASE 2.42** generates ApplyPlan from approved ApprovalRecords in dry-run mode.

Requirements:
- Readiness gate READY_FOR_DRYRUN_APPLYPLAN or READY_WITH_RESTRICTIONS
- ApprovalRecords status=approved with state_history including approved_for_dry_run_applyplan
- No secrets in payloads

Output:
- ApplyPlan JSON (mode=dry_run, status=generated)
- Generation report
- Zero NetBox writes

## Tool: generate_dryrun_applyplan.py

```bash
python3 tools/local/generate_dryrun_applyplan.py \
  --device "4WNET-MNS-KTG-RX" \
  --device-id 1890 \
  --approved-dir reports/pilot-device-compliance/approvals/approved \
  --readiness-gate reports/pilot-device-compliance/approvals/DRYRUN-APPLYPLAN-READINESS-GATE.md \
  --output-dir reports/pilot-device-compliance/apply-plans/dry-run \
  --report reports/pilot-device-compliance/apply-plans/DRYRUN-APPLYPLAN-GENERATION-REPORT.md
```

## ApplyPlan Structure

- apply_plan_id: UUID
- mode: dry_run
- status: generated
- device, device_id: Target device
- items: List of objects to be created
- safety_flags:
  - dry_run_only=true
  - no_netbox_write=true
  - no_token_required=true
  - no_apply_execution=true
  - manual_execution_gate_required=true
  - generated_from_approved_records=true
- execution_policy:
  - can_execute_real_write=false
  - requires_next_gate=true
  - allowed_methods: [POST]
  - forbidden_methods: [PATCH, DELETE]
  - forbidden_targets: [/sync, equipment, ssh, netconf]

## Security

✓ No NetBox writes
✓ mode=dry_run enforced
✓ can_execute_real_write=false
✓ Requires next gate
✓ All items verified
✓ No secrets allowed
