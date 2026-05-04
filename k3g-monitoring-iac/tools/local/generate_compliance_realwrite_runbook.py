#!/usr/bin/env python3
"""
COMPLIANCE-OPS-002: Generate Real-Write Operator Runbook

Reads readiness check and execution package.
Generates operator runbook (no tokens, CLI commands, checklist).
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone


def generate_runbook(job_id: str, jobs_base: str = "reports/compliance/jobs") -> str:
    """Generate operator runbook for real-write execution."""
    jobs_dir = Path(jobs_base)
    job_dir = jobs_dir / job_id

    # Load artifacts
    readiness_file = job_dir / "ops" / "readiness-check.json"
    exec_pkg_file = job_dir / "real-write" / "execution" / "execution-package.json"

    if not readiness_file.exists():
        raise ValueError(f"Readiness check not found for job {job_id}")

    if not exec_pkg_file.exists():
        raise ValueError(f"Execution package not found for job {job_id}")

    with open(readiness_file, "r") as f:
        readiness = json.load(f)

    with open(exec_pkg_file, "r") as f:
        exec_pkg = json.load(f)

    if readiness.get("decision") not in ["COMPLIANCE_JOB_READY_FOR_MANUAL_REAL_WRITE", "COMPLIANCE_JOB_READY_WITH_RESTRICTIONS"]:
        raise ValueError(f"Job not ready: {readiness.get('decision')}")

    # Generate runbook
    lines = []
    lines.append("# Real-Write Operator Runbook")
    lines.append("")
    lines.append(f"**Job ID:** {job_id}")
    lines.append(f"**Generated at:** {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"**Readiness:** {readiness.get('decision')}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Pre-checks
    lines.append("## Pre-Execution Checks")
    lines.append("")
    lines.append("### 1. Environment Setup")
    lines.append("")
    lines.append("```bash")
    lines.append("# Load write credentials (set by NOC/operator)")
    lines.append("source ~/.env.realwrite.local")
    lines.append("")
    lines.append("# Verify variables are set (DO NOT PRINT TOKEN)")
    lines.append("test -n \"$NETBOX_WRITE_TOKEN\" && echo 'NETBOX_WRITE_TOKEN set' || echo 'ERROR: NETBOX_WRITE_TOKEN not set'")
    lines.append("test -n \"$NETBOX_URL\" && echo 'NETBOX_URL set' || echo 'ERROR: NETBOX_URL not set'")
    lines.append("```")
    lines.append("")

    # Validate connectivity
    lines.append("### 2. Validate NetBox Connectivity")
    lines.append("")
    lines.append("```bash")
    lines.append("# Test read access (does NOT require write token, but write token is OK)")
    lines.append("curl -s -H \"Authorization: Bearer $NETBOX_WRITE_TOKEN\" \\")
    lines.append("  \"${NETBOX_URL}/api/dcim/devices/\" | head -c 100")
    lines.append("```")
    lines.append("")
    lines.append("Expected: JSON response (no errors, no token exposure)")
    lines.append("")

    # Execution package review
    lines.append("### 3. Review Execution Package")
    lines.append("")
    exec_id = exec_pkg.get("execution_package_id", "UNKNOWN")
    exec_phrase = exec_pkg.get("required_execution_phrase", "UNKNOWN")
    lines.append(f"**Execution ID:** `{exec_id}`")
    lines.append("")
    lines.append(f"**Required Execution Phrase:**")
    lines.append(f"```")
    lines.append(f"{exec_phrase}")
    lines.append(f"```")
    lines.append("")
    lines.append("⚠ **CRITICAL:** Phrase is case-sensitive. Copy EXACTLY.")
    lines.append("")

    # Items summary
    lines.append("### 4. Items to Execute")
    lines.append("")
    items = exec_pkg.get("items", [])
    for item in items:
        lines.append(f"- **{item.get('item_id')}**")
        lines.append(f"  - Method: {item.get('method')}")
        lines.append(f"  - Endpoint: {item.get('endpoint')}")
        lines.append(f"  - Object type: {item.get('object_type', 'N/A')}")
    lines.append("")

    lines.append("### 5. Final Safety Checks")
    lines.append("")
    lines.append("- [ ] Readiness decision is READY (not BLOCKED)")
    lines.append("- [ ] Execution phrase copied exactly")
    lines.append("- [ ] Endpoint does NOT contain `/sync`")
    lines.append("- [ ] Method is POST (no PATCH/DELETE)")
    lines.append("- [ ] No equipment SSH/NETCONF will be triggered")
    lines.append("- [ ] Operator aware: NO AUTOMATIC RETRY, NO AUTOMATIC ROLLBACK")
    lines.append("")

    # Execution command
    lines.append("---")
    lines.append("")
    lines.append("## Execute Real-Write")
    lines.append("")
    lines.append("### Command")
    lines.append("")
    lines.append("```bash")
    lines.append("# Set execution phrase (copy from above)")
    lines.append(f"PHRASE=\"{exec_phrase}\"")
    lines.append("")
    lines.append("# Run one-shot execution (NETBOX_WRITE_TOKEN in env, not argument)")
    lines.append(f"python3 tools/local/compliance_execute_realwrite_once.py \\")
    lines.append(f"  {job_id} \\")
    lines.append(f"  \"$PHRASE\" \\")
    lines.append(f"  true")
    lines.append("```")
    lines.append("")

    lines.append("### Output")
    lines.append("")
    lines.append("- `real-write-execution-result.json` (items with response IDs)")
    lines.append("- `REAL-WRITE-EXECUTION-RESULT.md` (human-readable summary)")
    lines.append("")

    # Post-execution
    lines.append("---")
    lines.append("")
    lines.append("## Post-Execution")
    lines.append("")
    lines.append("### 1. Verify Execution Result")
    lines.append("")
    lines.append("```bash")
    lines.append(f"cat reports/compliance/jobs/{job_id}/real-write/execution/REAL-WRITE-EXECUTION-RESULT.md")
    lines.append("```")
    lines.append("")

    lines.append("### 2. Post-Write Verification")
    lines.append("")
    lines.append("```bash")
    lines.append("curl -X POST http://127.0.0.1:8890/compliance/jobs/{job_id}/real-write/post-verification \\")
    lines.append("  -H 'Content-Type: application/json' \\")
    lines.append("  -d '{\"operator\": \"your_username\", \"confirm_post_verification\": true}'")
    lines.append("```")
    lines.append("")

    lines.append("### 3. Compliance Re-Run")
    lines.append("")
    lines.append("```bash")
    lines.append("curl -X POST http://127.0.0.1:8890/compliance/jobs/{job_id}/real-write/compliance-rerun \\")
    lines.append("  -H 'Content-Type: application/json' \\")
    lines.append("  -d '{\"operator\": \"your_username\", \"confirm_compliance_rerun\": true}'")
    lines.append("```")
    lines.append("")

    lines.append("### 4. Closure")
    lines.append("")
    lines.append("```bash")
    lines.append("curl -X POST http://127.0.0.1:8890/compliance/jobs/{job_id}/real-write/closure \\")
    lines.append("  -H 'Content-Type: application/json' \\")
    lines.append("  -d '{\"operator\": \"your_username\", \"confirm_closure\": true}'")
    lines.append("```")
    lines.append("")

    # Error handling
    lines.append("---")
    lines.append("")
    lines.append("## If Execution Fails")
    lines.append("")
    lines.append("1. **Stop.** Do not retry.")
    lines.append("2. Review execution result: `REAL-WRITE-EXECUTION-RESULT.md`")
    lines.append("3. Identify root cause.")
    lines.append("4. Do NOT attempt automatic rollback.")
    lines.append("5. Open ACTION_REQUIRED in closure package.")
    lines.append("6. Escalate to NetBox team for manual investigation.")
    lines.append("")

    # Security warnings
    lines.append("---")
    lines.append("")
    lines.append("## Security Warnings")
    lines.append("")
    lines.append("⚠ **DO NOT:**")
    lines.append("- Print or log `$NETBOX_WRITE_TOKEN`")
    lines.append("- Share token in messages/tickets")
    lines.append("- Store token in shell history (unset HISTFILE or use `set +o history`)")
    lines.append("- Retry execution if it fails (one-shot only)")
    lines.append("- Attempt automatic rollback")
    lines.append("")

    runbook_content = "\n".join(lines)
    return runbook_content


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: generate_compliance_realwrite_runbook.py <job_id> [jobs_base]")
        sys.exit(1)

    job_id = sys.argv[1]
    jobs_base = sys.argv[2] if len(sys.argv) > 2 else "reports/compliance/jobs"

    try:
        runbook = generate_runbook(job_id, jobs_base)
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Write runbook
    jobs_dir = Path(jobs_base)
    job_dir = jobs_dir / job_id
    ops_dir = job_dir / "ops"
    ops_dir.mkdir(parents=True, exist_ok=True)

    runbook_file = ops_dir / "REAL-WRITE-OPERATOR-RUNBOOK.md"
    with open(runbook_file, "w") as f:
        f.write(runbook)

    print(f"Runbook generated: {runbook_file}")
    sys.exit(0)


if __name__ == "__main__":
    main()
