# FASE 3.12 - Web UI Response Validation Dashboard

**Goal:** show Week 1 intake progress and the local Week 2 activation state.

## Route

- `GET /service-engagement/{device}/validation`

## Shows

- validation summary counts
- pending items table
- links to CSV, audit, validation report, activation gate, and Week 2 review board
- `UAT detected` indicator

## Actions

- `Rodar validação local`
- `Finalizar respostas e preparar Week 2`
- `Editar pendência`

## Safety

- Read-only dashboard
- No NetBox writes
- No approval automation
- No apply automation
