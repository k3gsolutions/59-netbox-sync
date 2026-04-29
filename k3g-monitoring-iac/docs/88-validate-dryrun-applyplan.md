# FASE 2.43 — Validate Dry-Run ApplyPlan

## Overview

**FASE 2.43** validates ApplyPlan structure before any execution.

Decisions:
- DRYRUN_APPLYPLAN_VALID
- DRYRUN_APPLYPLAN_VALID_WITH_WARNINGS
- DRYRUN_APPLYPLAN_INVALID

Output:
- Validation report
- Decision recorded
- No execution or NetBox writes

## Tool: validate_dryrun_applyplan.py

```bash
python3 tools/local/validate_dryrun_applyplan.py \
  --apply-plan reports/pilot-device-compliance/apply-plans/dry-run/dryrun-<uuid>.json \
  --device "4WNET-MNS-KTG-RX" \
  --device-id 1890 \
  --output reports/pilot-device-compliance/apply-plans/DRYRUN-APPLYPLAN-VALIDATION-REPORT.md
```

## Validation Checks

### ApplyPlan Structure
- mode=dry_run
- status=generated
- device, device_id correct
- source_approval_records present

### Safety Flags (ALL required)
- dry_run_only=true
- no_netbox_write=true
- no_token_required=true
- no_apply_execution=true
- manual_execution_gate_required=true
- generated_from_approved_records=true

### Execution Policy
- can_execute_real_write=false (BLOCKER if true)
- requires_next_gate=true
- forbidden_methods: no PATCH/DELETE
- forbidden_targets: no /sync, equipment, ssh

### Items
- approval_id present (BLOCKER if missing)
- proposed_payload present (BLOCKER if missing)
- evidence_hash present (BLOCKER if missing)
- No secrets in payload (BLOCKER if found)

## Security

✓ Read-only validation
✓ No NetBox writes
✓ No token usage
✓ No execution
