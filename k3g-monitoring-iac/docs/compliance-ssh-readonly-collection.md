# Compliance SSH Read-Only Collection

## Goal

Allow controlled SSH collection only after the job gate, collection plan, and safety validation are ready.

## Policy

- Protocol: `ssh`
- Auth: environment variables only
- Required env vars: `COMPLIANCE_SSH_USERNAME`, `COMPLIANCE_SSH_PASSWORD`
- Optional env vars: `COMPLIANCE_SSH_PORT`, `COMPLIANCE_SSH_TIMEOUT`, `COMPLIANCE_SSH_PREFLIGHT_TCP_CHECK`
- Allowed commands: `display`, `show`
- Forbidden commands: `system-view`, `configure`, `commit`, `save`, `delete`, `undo`, `shutdown`, `reboot`, `reset`, `patch`, `sync`

Policy file:

`policies/compliance/ssh-readonly-collection-policy.yaml`

## Preflight

Route:

- `POST /compliance/jobs/{job_id}/collection/ssh-preflight`

Behavior:

- validates the gate, plan, and safety artifacts
- checks SSH environment variables
- blocks if any command is forbidden
- does not connect to devices

Outputs:

- `collection-results/ssh-preflight.json`
- `collection-results/SSH-PREFLIGHT.md`

## Vendor Profiles

Command sets are selected by vendor/model before SSH execution.

- default fallback: `default-readonly`
- Huawei NE8000: `huawei-ne8000-readonly`
- collection plan stores the selected profile and planned commands

## Controlled SSH Execution

Route:

- `POST /compliance/jobs/{job_id}/collection/ssh-execute`

Behavior:

- runs only after preflight is ready
- uses `paramiko`
- connects once per device
- executes only planned read-only commands
- saves raw output and metadata under `collection-results/devices/<device_id>/raw/`
- blocks forbidden commands before connection

Outputs:

- `collection-results/ssh-collection-result.json`
- `collection-results/SSH-COLLECTION-RESULT.md`
- `collection-results/devices/<device_id>/raw/*.txt`
- `collection-results/devices/<device_id>/raw/*.meta.json`
- `collection-results/devices/<device_id>/redacted/*.txt`
- `collection-results/devices/<device_id>/redacted/*.meta.json`
- `collection-results/parser-manifest.json`
- `collection-results/PARSER-STAGING.md`

## Raw Validation

Route:

- `GET /compliance/jobs/{job_id}/collection/raw-validation`

Behavior:

- validates that raw outputs match planned commands
- blocks sensitive markers such as passwords, tokens, config mode strings, `/sync`, `ApprovalRecord`, and `ApplyPlan`
- returns a local validation artifact only
- warns when sensitive findings were redacted

Outputs:

- `collection-results/raw-output-safety-validation.json`
- `collection-results/RAW-OUTPUT-SAFETY-VALIDATION.md`

## Safety

- No NetBox write
- No `/sync`
- No NETCONF
- No SNMP write
- No config mode
- No ApprovalRecord
- No ApplyPlan
- No automatic retry
- No password logging or saving
