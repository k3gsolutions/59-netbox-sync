# FASE 3.10.2 - Web UI Auto Local Pipeline

**Goal:** save a response, run safe local validation, and expose the next step.

## Flow

1. Save local response
2. Update CSV and audit JSON
3. Run Week 1 validation locally
4. Update outreach snapshot
5. Generate Week 2 activation gate
6. Prepare Week 2 review board only when ready

## UI Actions

- `Salvar`
- `Salvar e fechar`
- `Finalizar respostas e preparar Week 2`

## Endpoints

- `POST /service-engagement/{device}/responses/run-validation`
- `POST /service-engagement/{device}/responses/finalize`

## Safety

- Local only
- No NetBox writes
- No apply
- No `/sync`
- No ApprovalRecord auto-create
- No ApplyPlan auto-create
