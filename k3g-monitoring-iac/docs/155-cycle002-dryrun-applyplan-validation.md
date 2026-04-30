# Cycle-002 Dry-Run ApplyPlan Validation

## Goal
Check the dry-run ApplyPlan structure before any later gate.

## Rules
- No execution
- No NetBox write
- No token
- No automatic apply

## Checks
- cycle_id
- mode
- status
- safety flags
- execution policy
- forbidden methods/targets

## Result
- Valid plans stay local only
- Invalid plans stay blocked
