# CYCLE-002 — Week 1 Plan

## 1. Objective
Collect responses locally for Cycle 002 Week 1.

## 2. Scope

- Device: 4WNET-MNS-KTG-RX
- Device ID: 1890
- Max items: 3
- Allowed methods: POST
- Forbidden methods: PATCH, DELETE
- Forbidden targets: /sync, equipment, ssh, netconf

## 3. Teams

- Service: subinterface response
- Network Ops: IP mapping response
- BGP: peer response

## 4. Response Rules

- Save locally only
- No NetBox write
- No apply
- No sync
- No retry automation
- No rollback automation

## 5. How to Respond

1. Open the Web UI or write a local response file.
2. Fill only the fields for your team.
3. Save response in `responses/`.
4. Validate locally.

## 6. Guardrails

- POST only
- PATCH forbidden
- DELETE forbidden
- /sync forbidden
- equipment forbidden
- ssh forbidden
- netconf forbidden

## 7. Next Step

Collect responses.

---

**Prepared at:** 2026-04-30T02:36:09.463263+00:00
