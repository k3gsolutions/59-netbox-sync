# Parser Safety Validation

## Goal

Validate parsed inventory artifacts before any later analysis step.

## Route

- `GET /compliance/jobs/{job_id}/parse/validation`

## Validates

- `parser-result.json` exists
- parsed inventory exists
- no `password`
- no `token`
- no `cipher`
- no `ApprovalRecord`
- no `ApplyPlan`
- no NetBox call
- no SSH call

## Decisions

- `PARSER_SAFETY_VALID`
- `PARSER_SAFETY_VALID_WITH_WARNINGS`
- `PARSER_SAFETY_INVALID`

## Safety

- local-only validation
- no writes
- raw not displayed in UI
