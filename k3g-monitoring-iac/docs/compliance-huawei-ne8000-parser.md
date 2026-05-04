# Huawei NE8000 Parser Baseline

## Goal

Parse local redacted SSH outputs for Huawei NE8000 devices without any device connection or NetBox write.

## Parser

- `webui/services/compliance_huawei_ne8000_parser.py`

## Inputs

- `reports/compliance/jobs/<job_id>/collection-results/parser-manifest.json`
- `reports/compliance/jobs/<job_id>/collection-results/devices/<device_id>/redacted/`
- `reports/compliance/jobs/<job_id>/collection-results/devices/<device_id>/raw/` only when raw is allowed by the local safety gate

## Outputs

- `reports/compliance/jobs/<job_id>/collection-results/devices/<device_id>/parsed/parsed-inventory.json`
- `reports/compliance/jobs/<job_id>/collection-results/devices/<device_id>/parsed/PARSED-INVENTORY.md`
- `reports/compliance/jobs/<job_id>/collection-results/parser-result.json`
- `reports/compliance/jobs/<job_id>/collection-results/PARSER-RESULT.md`

## Safety

- local-only parsing
- no SSH, SNMP, NETCONF
- no NetBox write
- no `/sync`
- no ApprovalRecord
- no ApplyPlan
- raw content is not shown in the UI
