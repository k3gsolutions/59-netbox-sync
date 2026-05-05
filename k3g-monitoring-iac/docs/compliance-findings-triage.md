# Compliance Findings Triage

Local-only triage for `compliance-job-e961838f0ae1`.
Uses the existing comparison snapshot (`findings_total = 105`); SSH auth is only relevant for a future recoleta.

## Goal

Separate parser noise, policy-too-strict cases, and items that still need human review.

## Buckets

- `likely_parser_noise`: header/legend artifacts, incomplete parsing, suspicious object names.
- `likely_policy_too_strict`: Huawei-valid interface names that collide with internal naming policy.
- `needs_human_review`: BGP state, missing peer metadata, route-policy missing, prefix-list missing.
- `remediation_candidate`: only when evidence is strong and the action is metadata/documentation review.
- `blocked_from_remediation`: no strong evidence, parser warnings, or operational risk too high.

## Artifacts

- `reports/compliance/jobs/compliance-job-e961838f0ae1/triage/findings-triage.json`
- `reports/compliance/jobs/compliance-job-e961838f0ae1/triage/FINDINGS-TRIAGE.md`
- `reports/compliance/jobs/compliance-job-e961838f0ae1/triage/virtual-ethernet-review.json`
- `reports/compliance/jobs/compliance-job-e961838f0ae1/triage/VIRTUAL-ETHERNET-REVIEW.md`

## Safety

- No NetBox write
- No `/sync`
- No SSH/SNMP/NETCONF
- No ApprovalRecord
- No ApplyPlan
- No automatic remediation
