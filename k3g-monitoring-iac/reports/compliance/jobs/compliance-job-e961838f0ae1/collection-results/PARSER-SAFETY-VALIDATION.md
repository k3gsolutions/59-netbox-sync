# PARSER-SAFETY-VALIDATION

## Job ID
`compliance-job-e961838f0ae1`

## Decision
`PARSER_SAFETY_VALID_WITH_WARNINGS`

## Checks
- parser_result_exists: True
- parsed_inventory_exists: True
- netbox_write_false: True
- ssh_not_called: True
- approval_record_absent: True
- apply_plan_absent: True

## Warnings
- parser artifact mentions netbox
- display bgp peer output is empty
- display ip routing-table protocol bgp skipped
- display route-policy output is empty
- 1 commands skipped

## Issues
- none

## Safety
- parser only
- no SSH
- no NetBox
- no ApprovalRecord
- no ApplyPlan
- raw not displayed in UI
