# Compliance Job Review and Collection Plan

## Goal

Turn a prepared compliance job into a reviewed, read-only collection plan without starting collection.

## Phases

### FASE COMPLIANCE-JOB-001

Review dashboard only:

- `GET /compliance/jobs`
- `GET /compliance/jobs/{job_id}`
- Show status, selected devices, safety block, and start gate markdown
- Provide a visual action to prepare the read-only collection gate

### FASE COMPLIANCE-JOB-002

Explicit collection start gate:

- `POST /compliance/jobs/{job_id}/collection/start-gate`
- Payload: `operator`, `confirm`
- Validate job status, selected devices, original safety, and absence of ApprovalRecord / ApplyPlan
- Write `collection-start-gate.json`
- Write `COLLECTION-START-GATE.md`

### FASE COMPLIANCE-JOB-003

Read-only collection plan:

- `POST /compliance/jobs/{job_id}/collection/plan`
- Requires `collection-start-gate.json` to be `COLLECTION_START_GATE_READY`
- Produce one plan entry per device
- Write `collection-plan.json`
- Write `COLLECTION-PLAN.md`

### FASE COMPLIANCE-COLLECT-001–003

Local simulation only:

- `POST /compliance/jobs/{job_id}/collection/execute`
- `GET /compliance/jobs/{job_id}/collection/validation`
- `collection-results/` with planned commands and safety validation
- no real device connection
- no NetBox write
- no `/sync`
- no ApprovalRecord
- no ApplyPlan

### FASE COMPLIANCE-COLLECT-004–007

Controlled SSH path:

- `POST /compliance/jobs/{job_id}/collection/ssh-preflight`
- `POST /compliance/jobs/{job_id}/collection/ssh-execute`
- `GET /compliance/jobs/{job_id}/collection/raw-validation`
- SSH env policy and read-only command policy enforced before connection
- raw outputs validated locally after execution
- no NetBox write, no `/sync`, no config mode, no ApprovalRecord, no ApplyPlan

## Device Plan Rules

Each device plan must include:

- `device_id`
- `name`
- `primary_ip4`
- `platform`
- `manufacturer`
- `model`
- `allowed_collection_methods`: `ssh_read_only`, `snmp_read_only`
- `forbidden_methods`: `netconf_write`, `cli_config`, `netbox_write`, `sync`
- `command_policy`: show/display only, no configure/system-view, no commit/save
- `expected_outputs`: interfaces, bgp, vrf, route-policy, prefix-list, snmp, system info

## Safety

- No SSH, SNMP, or NETCONF execution
- No NetBox writes
- No `/sync`
- No ApprovalRecord creation
- No ApplyPlan creation
- No automatic collection start

## Artifacts

Job artifacts live under:

`reports/compliance/jobs/<job_id>/`

Required files in this phase:

- `job-request.json`
- `selected-devices.json`
- `eligibility-recheck.json`
- `COMPLIANCE-JOB-START-GATE.md`
- `collection-start-gate.json`
- `COLLECTION-START-GATE.md`
- `collection-plan.json`
- `COLLECTION-PLAN.md`
- `collection-results/collection-execution.json`
- `collection-results/COLLECTION-EXECUTION.md`
- `collection-results/collection-safety-validation.json`
- `collection-results/COLLECTION-SAFETY-VALIDATION.md`
