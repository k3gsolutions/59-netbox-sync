# Cycle-002 Manual Approval Review

## Goal
Review one proposed ApprovalRecord by explicit human decision.

## Rules
- No NetBox write
- No ApplyPlan creation
- No token
- No automatic approval

## Decisions
- approve
- reject
- request_changes
- defer
- block

## Result
- Approved record copied locally into `approvals/approved/`
- Approved copy stays local only
- Status stays governed by the manual review report
