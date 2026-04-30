# Controlled Operation Index

## 1. Overall Status
- Status: BLOCKED
- Total Cycles: 3
- Measured at: 2026-04-30T16:44:49.717002+00:00

## 2. Cycle Summary

| Cycle | Device | Status | Items | Handoff | Next Action |
|-------|--------|--------|-------|---------|-------------|
| cycle-001 | 4WNET-MNS-KTG-RX | closed_with_restrictions | 0/3 | READY_WITH_RESTRICTIONS | Revisar restrições antes de ampliar |
| cycle-002 | 4WNET-MNS-KTG-RX | closed_with_restrictions | 0/3 | CYCLE_CLOSED_WITH_RESTRICTIONS | Revisar restrições antes de ampliar |
| cycle-003 | 4WNET-MNS-KTG-RX | action_required | 0/3 | N/A | Bloquear novo ciclo |

## 3. Detailed Status

### cycle-001 — 4WNET-MNS-KTG-RX

- **Status:** closed_with_restrictions
- **Device ID:** 1890
- **Max Items:** 3
- **Total Items Processed:** 0
- **Allowed Methods:** POST
- **Forbidden Methods:** PATCH, DELETE
- **Handoff Decision:** READY_WITH_RESTRICTIONS
- **Closure Decision:** N/A
- **Artifacts:** cycle-001/CYCLE-001-SCOPE.json, cycle-001/CYCLE-001-STATUS.json, cycle-001/cycle-001-handoff-decision.json
- **Next Action:** Revisar restrições antes de ampliar

---

### cycle-002 — 4WNET-MNS-KTG-RX

- **Status:** closed_with_restrictions
- **Device ID:** 1890
- **Max Items:** 3
- **Total Items Processed:** 0
- **Allowed Methods:** POST
- **Forbidden Methods:** PATCH, DELETE
- **Handoff Decision:** CYCLE_CLOSED_WITH_RESTRICTIONS
- **Closure Decision:** CYCLE_CLOSED_WITH_WARNINGS
- **Artifacts:** cycle-002/CYCLE-002-SCOPE.json, cycle-002/CYCLE-002-STATUS.md, cycle-002/cycle-002-handoff-decision.json, cycle-002/real-write-execution/closure/cycle-002-closure-summary.json
- **Next Action:** Revisar restrições antes de ampliar

---

### cycle-003 — 4WNET-MNS-KTG-RX

- **Status:** action_required
- **Device ID:** 1890
- **Max Items:** 3
- **Total Items Processed:** 0
- **Allowed Methods:** POST
- **Forbidden Methods:** PATCH, DELETE
- **Handoff Decision:** N/A
- **Closure Decision:** CYCLE_CLOSED_ACTION_REQUIRED
- **Artifacts:** cycle-003/CYCLE-003-SCOPE.json, cycle-003/real-write-execution/closure/cycle-003-closure-summary.json
- **Next Action:** Bloquear novo ciclo

---

## 4. Key Artifacts

Cycles and their essential files:
- Scopes in `cycle-*/cycle-*-scope.json` or `cycle-*/CYCLE-*-SCOPE.json`
- Handoff decisions in `cycle-*/cycle-*-handoff-decision.json`
- Final archives in `cycle-*/final-archive/manifest.json`
- Closure summaries in `cycle-*/real-write-execution/closure/` or `cycle-*/final-archive/`

---
Index built at 2026-04-30T16:44:49.717002+00:00
