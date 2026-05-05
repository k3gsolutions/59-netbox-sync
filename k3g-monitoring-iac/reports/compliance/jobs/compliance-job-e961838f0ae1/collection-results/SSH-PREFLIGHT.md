# SSH-PREFLIGHT

## Job ID
`compliance-job-e961838f0ae1`

## Decision
`SSH_PREFLIGHT_READY_CONFIG_ONLY`

## TCP Check Enabled
`False`

## Preconditions
- start_gate_ready: True
- plan_prepared: True
- safety_valid: True
- confirm_read_only: True

## Issues
- none

## Safety
- password_saved=false
- password_logged=false
- commands_executed=false
- netbox_write=false
- sync_called=false
