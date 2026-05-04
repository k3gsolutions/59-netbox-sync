# Controlled Cycle-004 Real-Write Operator Runbook

**Cycle ID:** cycle-004
**Generated at:** 2026-05-04T17:35:12.572806+00:00

## Pre-Execution Checklist

- [ ] Cycle-004 readiness validated
- [ ] Authorization phrase prepared: `AUTORIZO_PRE_FLIGHT_ESCRITA_REAL_cycle-004_6EF720EC`
- [ ] Execution phrase prepared: `EXECUTAR_ESCRITA_REAL_cycle-004_EC4AD22E`
- [ ] NETBOX_WRITE_TOKEN loaded from ~/.env.realwrite.local
- [ ] NETBOX_URL validated with GET /api/
- [ ] Endpoint reviewed (no /sync, no equipment targets)
- [ ] Payload reviewed (no secrets visible)
- [ ] Operator aware: ONE-SHOT execution only
- [ ] Operator aware: NO AUTOMATIC RETRY
- [ ] Operator aware: NO AUTOMATIC ROLLBACK

## Execution Command

```bash
# Set phrases
AUTH_PHRASE="AUTORIZO_PRE_FLIGHT_ESCRITA_REAL_cycle-004_6EF720EC"
EXEC_PHRASE="EXECUTAR_ESCRITA_REAL_cycle-004_EC4AD22E"

# Step 1: Authorization
curl -X POST http://127.0.0.1:8890/controlled-operation/cycle-004/real-write/authorization \
  -H 'Content-Type: application/json' \
  -d "{"operator": "your_username", "authorization_phrase": \"$AUTH_PHRASE\"}"

# Step 2: Final Preflight
curl -X POST http://127.0.0.1:8890/controlled-operation/cycle-004/real-write/final-preflight \
  -H 'Content-Type: application/json' \
  -d "{"operator": "your_username", "confirm": true}"

# Step 3: Execution
python3 tools/local/compliance_execute_realwrite_once.py cycle-004 "$EXEC_PHRASE" true

# Step 4: Post-Verification
curl -X POST http://127.0.0.1:8890/controlled-operation/cycle-004/real-write/post-verification \
  -H 'Content-Type: application/json' \
  -d "{"operator": "your_username", "confirm": true}"

# Step 5: Compliance Re-Run
curl -X POST http://127.0.0.1:8890/controlled-operation/cycle-004/real-write/compliance-rerun \
  -H 'Content-Type: application/json' \
  -d "{"operator": "your_username", "confirm": true}"

# Step 6: Closure
curl -X POST http://127.0.0.1:8890/controlled-operation/cycle-004/real-write/closure \
  -H 'Content-Type: application/json' \
  -d "{"operator": "your_username", "confirm": true}"
```

## Safety

- No automatic execution
- No token exposure
- One-shot execution only
- Manual operator confirmation required
- Full audit trail

Do NOT execute unless all checklist items completed.
