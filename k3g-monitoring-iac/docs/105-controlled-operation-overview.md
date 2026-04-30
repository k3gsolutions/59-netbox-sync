# Controlled Operation Overview

## Goal
Describe the local-only controlled operation model used by Cycle-001 and Cycle-002.

## Rules
- 1 device per cycle
- max 3 items per cycle
- POST only for local artifacts
- no NetBox write
- no ApplyPlan execution
- no automatic approval

## Cycle-002
- Intake activated with restrictions
- Week 1 prepared, seeded, revalidated
- Week 2 prepared, reviewed, and promoted to proposed records
- Manual approval review completed locally
- Dry-run ApplyPlan generated and validated locally

## Safety
- No token exposure
- No `/sync`
- No PATCH/DELETE
- Manual review stays mandatory
