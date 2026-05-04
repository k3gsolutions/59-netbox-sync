# Compliance Read-Only Collection Simulation

## Goal

Simulate collection after job review and collection plan. No real connectivity.

## Next Layer

SSH read-only collection now has a controlled path with preflight, guarded execution, and raw output validation.
See [compliance-ssh-readonly-collection.md](compliance-ssh-readonly-collection.md).
It also adds vendor command profiles, redaction, and parser staging.

## Routes

- `POST /compliance/jobs/{job_id}/collection/execute`
- `GET /compliance/jobs/{job_id}/collection/validation`
- `POST /compliance/jobs/{job_id}/collection/ssh-preflight`
- `POST /compliance/jobs/{job_id}/collection/ssh-execute`
- `GET /compliance/jobs/{job_id}/collection/raw-validation`

## Payload

```json
{
  "operator": "Keslley",
  "confirm_read_only": true
}
```

## Rules

- `simulation_only=true`
- no SSH
- no SNMP
- no NETCONF
- no NetBox write
- no `/sync`
- no ApprovalRecord
- no ApplyPlan

## Outputs

Artifacts under:

`reports/compliance/jobs/<job_id>/collection-results/`

Files:

- `collection-execution.json`
- `COLLECTION-EXECUTION.md`
- `collection-safety-validation.json`
- `COLLECTION-SAFETY-VALIDATION.md`
- `devices/<device_id>/planned-commands.json`
- `devices/<device_id>/raw/.gitkeep`
- `devices/<device_id>/parsed/.gitkeep`

## Planned Commands

Huawei read-only commands:

- `display version`
- `display current-configuration`
- `display interface brief`
- `display ip interface brief`
- `display bgp peer`
- `display bgp routing-table`
- `display route-policy`
- `display ip ip-prefix`
- `display snmp-agent sys-info`

Forbidden tokens:

- `system-view`
- `configure`
- `commit`
- `save`
- `reset`
- `reboot`
- `delete`
- `undo`
- `shutdown`
- `patch`
- `sync`
