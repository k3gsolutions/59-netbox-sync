# Cycle-002 Proposed ApprovalRecords

## Purpose
Descrever a promoção apenas de drafts aprovados para ApprovalRecords com status `proposed` / `pending`.

## Inputs
- `reports/controlled-operation/cycle-002/week2/cycle-002-week2-human-review.json`
- `reports/controlled-operation/cycle-002/week2/approval-drafts/`

## Promotion Rules
- `decision=approve_for_approval_record`
- `approval_record_allowed=true`
- `reviewer` presente
- `reviewed_at` presente
- `reason` / `notes` presente
- draft existente

## Safety
- No approved state.
- No ApplyPlan.
- No NetBox write.
- Proposed only.

## Current State
- One proposed ApprovalRecord exists.
- The remaining two Week 2 items stayed out of promotion.
- Manual approval review is now the next gate.
