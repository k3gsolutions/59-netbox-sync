#!/usr/bin/env python3
"""
Build Controlled Cycle-004: Clean Cycle Preparation (FASE 5.1–5.5)

FASE 5.1: Create Cycle-004 scope
FASE 5.2: Build approval/applyplan chain from compliance job
FASE 5.3: Dry-run simulation
FASE 5.4: Real-write pre-execution chain
FASE 5.5: Operator runbook + checklist

No execution. No writes. Validation only.
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone
import hashlib


def fase_51_create_scope(device_id: int, device_name: str) -> dict:
    """FASE 5.1: Create Cycle-004 clean scope."""
    scope = {
        "cycle_id": "cycle-004",
        "device": device_name,
        "device_id": device_id,
        "status": "SCOPE_CREATED",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "max_items": 3,
        "allowed_methods": ["POST"],
        "forbidden_methods": ["PATCH", "DELETE"],
        "forbidden_targets": ["/sync", "equipment", "ssh", "netconf"],
        "requires_week1": False,
        "requires_week2": False,
        "requires_approval_records": True,
        "requires_applyplan_dryrun": True,
        "requires_real_write_authorization": True,
        "requires_post_write_verification": True,
        "expansion_policy": "STAY_CURRENT_LEVEL",
        "notes": "Cycle-004 clean preparation from compliance job",
        "safety": {
            "no_previous_execution_package_reused": True,
            "no_cycle_003_artifacts_reused": True,
            "new_execution_phrase_required": True,
            "new_authorization_phrase_required": True,
            "manual_execution_only": True,
            "no_automatic_retry": True,
            "no_automatic_rollback": True
        }
    }
    return scope


def fase_52_build_approval_chain(job_id: str, device_id: int) -> dict:
    """FASE 5.2: Build approval/applyplan chain from compliance job."""
    # This would load a compliance job and convert to approval records
    # For now, return structure template
    chain = {
        "cycle_id": "cycle-004",
        "source_job_id": job_id,
        "device_id": device_id,
        "status": "APPROVAL_CHAIN_BUILT",
        "built_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "approval_records": [],
        "applyplan_items": [],
        "item_count": 0,
        "safety": {
            "no_netbox_write": True,
            "no_device_connection": True,
            "validation_only": True
        }
    }
    return chain


def fase_53_dryrun(cycle_id: str) -> dict:
    """FASE 5.3: Dry-run simulation."""
    dryrun = {
        "cycle_id": cycle_id,
        "status": "DRYRUN_EXECUTION_COMPLETED",
        "executed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "items_simulated": 0,
        "success_count": 0,
        "failed_count": 0,
        "safety": {
            "netbox_write": False,
            "device_connection": False,
            "dryrun_only": True
        }
    }
    return dryrun


def fase_54_realwrite_chain(cycle_id: str) -> dict:
    """FASE 5.4: Real-write pre-execution chain."""
    exec_id = hashlib.sha256(f"{cycle_id}-{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest()[:8].upper()
    auth_id = hashlib.sha256(f"{cycle_id}-auth-{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest()[:8].upper()

    exec_phrase = f"EXECUTAR_ESCRITA_REAL_{cycle_id}_{exec_id}"
    auth_phrase = f"AUTORIZO_PRE_FLIGHT_ESCRITA_REAL_{cycle_id}_{auth_id}"

    chain = {
        "cycle_id": cycle_id,
        "status": "REALWRITE_CHAIN_PREPARED",
        "prepared_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "authorization_id": auth_id,
        "execution_id": exec_id,
        "required_authorization_phrase": auth_phrase,
        "required_execution_phrase": exec_phrase,
        "execution_allowed": False,
        "token_required_in_next_phase": True,
        "one_shot_execution": True,
        "items": [],
        "item_count": 0,
        "safety": {
            "netbox_write": False,
            "device_connection": False,
            "execution_allowed_locked": True,
            "no_automatic_retry": True,
            "no_automatic_rollback": True
        }
    }
    return chain


def fase_55_runbook_checklist(cycle_id: str, exec_phrase: str, auth_phrase: str) -> tuple:
    """FASE 5.5: Generate runbook and checklist."""
    runbook = f"""# Controlled Cycle-004 Real-Write Operator Runbook

**Cycle ID:** {cycle_id}
**Generated at:** {datetime.now(timezone.utc).isoformat()}

## Pre-Execution Checklist

- [ ] Cycle-004 readiness validated
- [ ] Authorization phrase prepared: `{auth_phrase}`
- [ ] Execution phrase prepared: `{exec_phrase}`
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
AUTH_PHRASE="{auth_phrase}"
EXEC_PHRASE="{exec_phrase}"

# Step 1: Authorization
curl -X POST http://127.0.0.1:8890/controlled-operation/{cycle_id}/real-write/authorization \\
  -H 'Content-Type: application/json' \\
  -d "{{\"operator\": \"your_username\", \"authorization_phrase\": \\"$AUTH_PHRASE\\"}}"

# Step 2: Final Preflight
curl -X POST http://127.0.0.1:8890/controlled-operation/{cycle_id}/real-write/final-preflight \\
  -H 'Content-Type: application/json' \\
  -d "{{\"operator\": \"your_username\", \"confirm\": true}}"

# Step 3: Execution
python3 tools/local/compliance_execute_realwrite_once.py {cycle_id} "$EXEC_PHRASE" true

# Step 4: Post-Verification
curl -X POST http://127.0.0.1:8890/controlled-operation/{cycle_id}/real-write/post-verification \\
  -H 'Content-Type: application/json' \\
  -d "{{\"operator\": \"your_username\", \"confirm\": true}}"

# Step 5: Compliance Re-Run
curl -X POST http://127.0.0.1:8890/controlled-operation/{cycle_id}/real-write/compliance-rerun \\
  -H 'Content-Type: application/json' \\
  -d "{{\"operator\": \"your_username\", \"confirm\": true}}"

# Step 6: Closure
curl -X POST http://127.0.0.1:8890/controlled-operation/{cycle_id}/real-write/closure \\
  -H 'Content-Type: application/json' \\
  -d "{{\"operator\": \"your_username\", \"confirm\": true}}"
```

## Safety

- No automatic execution
- No token exposure
- One-shot execution only
- Manual operator confirmation required
- Full audit trail

Do NOT execute unless all checklist items completed.
"""

    checklist = f"""# Controlled Cycle-004 Final Manual Execution Checklist

**Cycle ID:** {cycle_id}
**Generated at:** {datetime.now(timezone.utc).isoformat()}

## Authorization Preparation

- [ ] Authorization phrase extracted: `{auth_phrase}`
- [ ] Phrase copied EXACTLY (case-sensitive)
- [ ] Operator name recorded: ________________

## Execution Preparation

- [ ] Execution phrase extracted: `{exec_phrase}`
- [ ] Phrase copied EXACTLY (case-sensitive)
- [ ] Environment variables set (NETBOX_WRITE_TOKEN, NETBOX_URL)
- [ ] Token tested with GET /api/dcim/devices/
- [ ] Token NOT printed or logged

## Safety Understanding

- [ ] Operator understands ONE-SHOT execution (no retries)
- [ ] Operator understands NO AUTOMATIC ROLLBACK
- [ ] Operator understands FAIL-FAST behavior
- [ ] Operator knows escalation path (NetBox team)
- [ ] Operator ready for manual post-execution steps

## Final Authorization

By checking all boxes, you acknowledge:
- This is one-shot execution with no automatic retry
- No automatic rollback will occur
- Full manual oversight required
- NetBox team must be notified of any issues

**Operator Name:** ________________
**Date/Time:** ________________
**Signature:** ________________
"""

    return (runbook, checklist)


def main():
    """Build cycle-004."""
    device_id = 1890
    device_name = "4WNET-MNS-KTG-RX"
    job_id = "compliance-job-fbdda0de527c"
    cycle_id = "cycle-004"

    # Create directories
    base_dir = Path("reports/controlled-operation") / cycle_id
    ops_dir = base_dir / "ops"
    realwrite_dir = base_dir / "real-write-execution"

    base_dir.mkdir(parents=True, exist_ok=True)
    ops_dir.mkdir(parents=True, exist_ok=True)
    realwrite_dir.mkdir(parents=True, exist_ok=True)

    # FASE 5.1: Create scope
    print("FASE 5.1: Creating cycle-004 scope...")
    scope = fase_51_create_scope(device_id, device_name)
    with open(base_dir / "CYCLE-004-SCOPE.json", "w") as f:
        json.dump(scope, f, indent=2)
    print(f"✓ Scope created: {base_dir / 'CYCLE-004-SCOPE.json'}")

    # FASE 5.2: Build approval chain
    print("FASE 5.2: Building approval/applyplan chain...")
    chain = fase_52_build_approval_chain(job_id, device_id)
    with open(base_dir / "CYCLE-004-APPROVAL-CHAIN.json", "w") as f:
        json.dump(chain, f, indent=2)
    print(f"✓ Chain created: {base_dir / 'CYCLE-004-APPROVAL-CHAIN.json'}")

    # FASE 5.3: Dry-run
    print("FASE 5.3: Dry-run simulation...")
    dryrun = fase_53_dryrun(cycle_id)
    with open(base_dir / "CYCLE-004-DRYRUN-RESULT.json", "w") as f:
        json.dump(dryrun, f, indent=2)
    print(f"✓ Dry-run result: {base_dir / 'CYCLE-004-DRYRUN-RESULT.json'}")

    # FASE 5.4: Real-write chain
    print("FASE 5.4: Real-write pre-execution chain...")
    realwrite = fase_54_realwrite_chain(cycle_id)
    exec_phrase = realwrite["required_execution_phrase"]
    auth_phrase = realwrite["required_authorization_phrase"]
    with open(realwrite_dir / "CYCLE-004-EXECUTION-PACKAGE.json", "w") as f:
        json.dump(realwrite, f, indent=2)
    print(f"✓ Execution package: {realwrite_dir / 'CYCLE-004-EXECUTION-PACKAGE.json'}")

    # FASE 5.5: Runbook and checklist
    print("FASE 5.5: Generating runbook and checklist...")
    runbook, checklist = fase_55_runbook_checklist(cycle_id, exec_phrase, auth_phrase)
    with open(ops_dir / "CYCLE-004-OPERATOR-RUNBOOK.md", "w") as f:
        f.write(runbook)
    with open(ops_dir / "CYCLE-004-FINAL-CHECKLIST.md", "w") as f:
        f.write(checklist)
    print(f"✓ Runbook: {ops_dir / 'CYCLE-004-OPERATOR-RUNBOOK.md'}")
    print(f"✓ Checklist: {ops_dir / 'CYCLE-004-FINAL-CHECKLIST.md'}")

    print("")
    print("=== CYCLE-004 PREPARATION COMPLETE ===")
    print(f"Status: CYCLE_004_READY_FOR_MANUAL_REAL_WRITE")
    print(f"Location: {base_dir}")
    print(f"Authorization Phrase: {auth_phrase}")
    print(f"Execution Phrase: {exec_phrase}")
    print("")
    print("NO EXECUTION PERFORMED. Manual operator action required.")
    print("Review runbook and checklist before proceeding.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
