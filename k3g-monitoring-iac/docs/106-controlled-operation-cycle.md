# Controlled Operation Cycle

## Goal
Explain the controlled cycle model used by this repo.

## Rules
- 1 device per cycle
- max 3 items per cycle
- POST only for local response intake
- no PATCH, DELETE, `/sync`, NetBox write, ApprovalRecord auto-create, or ApplyPlan auto-create

## Cycle flow
1. Intake gate
2. Week 1 preparation
3. Week 1 response intake
4. Week 1 validation
5. Week 2 preparation
6. Human review
7. Promotion only after explicit human decision
8. Manual approval review
9. Dry-run ApplyPlan generation
10. Dry-run ApplyPlan validation

## Cycle-002
- Intake activated with restrictions
- Week 1 responses seeded locally
- Week 1 re-validation passed
- Week 2 preparation ready
- Week 2 decision seeded for controlled test
- Week 2 re-review passed with restrictions
- 1 proposed ApprovalRecord created
- Approval readiness gate is ready for manual approval review
- Manual approval review approved the proposed record locally
- Dry-run ApplyPlan generated and validated locally
