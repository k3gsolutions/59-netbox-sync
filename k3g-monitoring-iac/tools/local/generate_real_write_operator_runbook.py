#!/usr/bin/env python3
"""FASE 2.51 — Real Write Operator Runbook Generator."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


def main() -> int:
    """Generate operator runbook."""
    parser = argparse.ArgumentParser(description="FASE 2.51 — Real Write Operator Runbook")
    parser.add_argument("--execution-package", type=Path, required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--operator", required=True)
    parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()

    try:
        with open(args.execution_package, encoding="utf-8") as f:
            package = json.load(f)
    except Exception as e:
        print(f"✗ Cannot load package: {e}")
        return 1

    execution_package_id = package.get("execution_package_id")
    required_phrase = package.get("required_execution_phrase")
    items = package.get("items", [])
    timestamp = datetime.utcnow().isoformat() + "+00:00"

    # Build runbook as simple string concatenation
    runbook = f"""# Real Write Operator Runbook

**Device:** {args.device}
**Operator:** {args.operator}
**Generated:** {timestamp}

---

## 1. Prerequisites

Before executing real write (FASE 2.53), ensure:

- [ ] NETBOX_WRITE_TOKEN available in environment (not hardcoded)
- [ ] Token has appropriate NetBox permissions
- [ ] Operational window confirmed
- [ ] Rollback procedure documented and tested
- [ ] Device network connectivity verified
- [ ] Backup of device configuration taken
- [ ] Change ticket created (if required by policy)
- [ ] Team notified of upcoming changes
- [ ] Execution will be one-shot (no retries, no partials)

---

## 2. Items to Be Written

Total items: {len(items)}

| Item | Object Type | Object Key | Endpoint | Expected Result | Rollback |
|---|---|---|---|---|---|
"""

    for i, item in enumerate(items, 1):
        endpoint = item.get('endpoint', '?')
        status = item.get('expected_status_code', '201')
        rollback = item.get('rollback_hint', '?')
        runbook += f"| {i} | {item['object_type']} | {item['object_key']} | {endpoint} | {status} | {rollback} |\n"

    runbook += f"""
---

## 3. Execution Command (FASE 2.53)

Do NOT hardcode token. Use environment variable:

```bash
export NETBOX_WRITE_TOKEN='your-actual-token'

python3 tools/local/execute_real_write_once.py \\
  --execution-package {args.execution_package} \\
  --operator '{args.operator}' \\
  --confirm-execution-phrase '{required_phrase}' \\
  --confirm-real-write-once

unset NETBOX_WRITE_TOKEN
```

---

## 4. Pre-Execution Checklist

✓ Confirm exact operator name matches log entry
✓ Confirm exact device name: {args.device}
✓ Confirm exact number of items: {len(items)}
✓ Confirm token is from environment, NOT hardcoded
✓ Confirm exact execution phrase:

```
{required_phrase}
```

✓ Confirm execution window (off-peak)
✓ Have rollback procedure ready for each item
✓ Know how to check result (GET endpoint after POST)
✓ Know escalation path if write fails

---

## 5. What You MUST NOT Do

❌ Do NOT modify execution package JSON
❌ Do NOT hardcode token in script
❌ Do NOT use /sync endpoint
❌ Do NOT use PATCH or DELETE
❌ Do NOT run multiple times (one-shot only)
❌ Do NOT change confirmation phrase
❌ Do NOT execute outside operational window
❌ Do NOT skip pre-execution checklist
❌ Do NOT commit token to git
❌ Do NOT skip post-execution verification

---

## 6. Expected Execution Behavior

1. Script validates execution_package.json
2. Script verifies confirmation phrase matches
3. Script reads NETBOX_WRITE_TOKEN from environment
4. For each item:
   - Pre-write checks (endpoint syntax, payload)
   - POST request to NetBox API
   - Validate response status code
   - Log created resource ID
5. Generate REAL-WRITE-EXECUTION-RESULT.json
6. Generate REAL-WRITE-EXECUTION-RESULT.md report
7. Return 0 if all succeeded, 1 if any failed

---

## 7. Post-Execution Steps

After execution:

1. Verify each item was created in NetBox
2. Check execution result report
3. Verify all items have status=applied
4. Run compliance validation
5. Archive execution artifacts

---

## 8. If Execution Fails

- Read error message in result report
- Identify failed item(s)
- For partial success: escalate immediately
- For total failure: no rollback needed, debug and retry

---

## 9. Escalation Path

If problems occur:
- Check NETBOX_WRITE_TOKEN is set
- Check device is reachable
- Check NetBox API is up
- Escalate to platform team if partial failure

---

## 10. Audit Trail

Execution logged with:
- Operator name: {args.operator}
- Device: {args.device}
- Timestamp: (auto-generated)
- Items applied: (from result)
- Token: (environment, logged as hash)
- Result: success/failure

---

## 11. After Success

1. ✓ Verify all items in NetBox
2. ✓ Run post-write compliance check
3. ✓ Notify team
4. ✓ Close change ticket
5. ✓ Archive report
6. ✓ Update runbook if needed

---

**Document Version:** 1.0
**Created:** {timestamp}
**For Device:** {args.device}
**For Operator:** {args.operator}
"""

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(runbook, encoding="utf-8")

    print(f"✓ Operator runbook: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
