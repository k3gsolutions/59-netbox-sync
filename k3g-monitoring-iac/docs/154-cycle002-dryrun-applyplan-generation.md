# Cycle-002 Dry-Run ApplyPlan Generation

## Goal
Build a local dry-run ApplyPlan from approved ApprovalRecords.

## Rules
- No NetBox write
- No execution
- No token
- No PATCH/DELETE
- No `/sync`

## Output
- `reports/controlled-operation/cycle-002/apply-plans/dry-run/*.json`

## Safety
- `mode=dry_run`
- `can_execute_real_write=false`
- `requires_next_gate=true`
