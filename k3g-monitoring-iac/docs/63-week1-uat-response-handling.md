# FASE 2.25 - Week 1 UAT Response Handling

**Goal:** separate controlled UAT responses from real Week 1 intake.

## Modes

- `report` - detect UAT artifacts and write audit/readiness reports
- `archive` - move all-UAT artifacts to `week1-responses/uat-archive/<timestamp>/`
- `keep-as-real` - keep the current files and record an explicit decision
- `reset` - remove all-UAT artifacts with confirmation

## Detection

- `updated_by=uat`
- `notes` contains `UAT`
- `owner` contains `UAT`
- `evidence` contains `UAT`
- audit JSON entries with `updated_by=uat`

## Reports

- `reports/pilot-device-compliance/WEEK1-UAT-RESPONSE-AUDIT.md`
- `reports/pilot-device-compliance/WEEK1-REAL-READINESS-AFTER-UAT.md`

## Safety

- No NetBox writes
- No apply
- No `/sync`
- No ApprovalRecord auto-create
- No ApplyPlan auto-create
- No silent removal

## Multi-cycle follow-up

- UAT cleanup remains separate from controlled multi-cycle reporting.
- The read-only operation index still keeps Cycle-001 and Cycle-002 visible.
