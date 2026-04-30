# Cycle-002 Week 1 Response Form / Response Seed

## Goal
Collect Week 1 responses for Cycle-002 without manual CSV editing.

## Supported flow
- Local response seed script writes files under `reports/controlled-operation/cycle-002/week1/responses/`
- Web UI can show the pending queue and local seed commands

## Security
- No NetBox write
- No token use
- No apply
- No `/sync`
- No ApprovalRecord official creation
- No ApplyPlan creation

## Validation
- `cycle_id` must be `cycle-002`
- `device_id` must be `1890`
- `object_key` must stay inside scope
- secret terms are blocked

