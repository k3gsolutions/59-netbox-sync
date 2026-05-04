#!/usr/bin/env python3
"""
COMPLIANCE-OPS-003: Generate Final Manual Execution Checklist

Simple safety checklist before execution.
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone


def generate_final_checklist(job_id: str, jobs_base: str = "reports/compliance/jobs") -> str:
    """Generate final manual execution checklist."""
    jobs_dir = Path(jobs_base)
    job_dir = jobs_dir / job_id

    # Load execution package
    exec_pkg_file = job_dir / "real-write" / "execution" / "execution-package.json"
    if not exec_pkg_file.exists():
        raise ValueError(f"Execution package not found for job {job_id}")

    with open(exec_pkg_file, "r") as f:
        exec_pkg = json.load(f)

    # Generate checklist
    lines = []
    lines.append("# Final Manual Execution Checklist")
    lines.append("")
    lines.append(f"**Job ID:** {job_id}")
    lines.append(f"**Generated at:** {datetime.now(timezone.utc).isoformat()}")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Pre-Execution Checklist")
    lines.append("")
    lines.append("**Readiness & Package Validation:**")
    lines.append("- [ ] Job readiness check decision is READY")
    lines.append("- [ ] Execution package validation passed (EXECUTION_PACKAGE_VALID)")
    lines.append("- [ ] Final freeze decision is READY_FOR_REAL_WRITE_PHASE")
    lines.append("")

    lines.append("**Package Review:**")
    lines.append("- [ ] Endpoint reviewed and approved")
    lines.append("- [ ] Payload reviewed (no secrets visible)")
    lines.append("- [ ] Method is POST (not PATCH/DELETE)")
    lines.append("- [ ] Item count matches expectation")
    lines.append("- [ ] Endpoint does NOT contain `/sync`")
    lines.append("")

    lines.append("**Authorization & Phrase:**")
    lines.append("- [ ] Execution phrase extracted from execution-package.json")
    lines.append("- [ ] Phrase copied EXACTLY (case-sensitive)")
    lines.append("- [ ] Operator name recorded")
    lines.append("")

    lines.append("**Environment & Token:**")
    lines.append("- [ ] NETBOX_WRITE_TOKEN loaded from ~/.env.realwrite.local")
    lines.append("- [ ] NETBOX_URL set and valid")
    lines.append("- [ ] Token tested with GET /api/dcim/devices/ (read test)")
    lines.append("- [ ] Token NOT printed or logged")
    lines.append("")

    lines.append("**Execution Understanding:**")
    lines.append("- [ ] Operator aware: ONE-SHOT execution only")
    lines.append("- [ ] Operator aware: NO AUTOMATIC RETRY on failure")
    lines.append("- [ ] Operator aware: NO AUTOMATIC ROLLBACK")
    lines.append("- [ ] Operator aware: FAIL-FAST (stops on first error)")
    lines.append("- [ ] Escalation path understood (NetBox team if issues)")
    lines.append("")

    lines.append("**Post-Execution Preparation:**")
    lines.append("- [ ] Post-write verification endpoint ready")
    lines.append("- [ ] Compliance re-run endpoint ready")
    lines.append("- [ ] Closure endpoint ready")
    lines.append("- [ ] Operator knows how to check results in /ops/")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Item Details")
    lines.append("")

    items = exec_pkg.get("items", [])
    for i, item in enumerate(items, 1):
        lines.append(f"### Item {i}: {item.get('item_id')}")
        lines.append("")
        lines.append(f"- **Method:** {item.get('method')}")
        lines.append(f"- **Endpoint:** {item.get('endpoint')}")
        lines.append(f"- **Object Type:** {item.get('object_type', 'N/A')}")
        lines.append(f"- **Payload Size:** {len(json.dumps(item.get('payload', {})))} bytes")
        lines.append("")
        lines.append("- [ ] Item reviewed")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Execution Authorization")
    lines.append("")
    lines.append("By checking all boxes above and executing, you acknowledge:")
    lines.append("")
    lines.append("1. This is a ONE-SHOT operation with no retry capability")
    lines.append("2. The job readiness and package validation passed all gates")
    lines.append("3. The operator has reviewed all items and payloads")
    lines.append("4. The execution phrase is exact and case-sensitive")
    lines.append("5. The NETBOX_WRITE_TOKEN has been validated")
    lines.append("6. No automatic rollback will occur if issues arise")
    lines.append("")
    lines.append("**Operator Name:** ________________")
    lines.append("")
    lines.append("**Date/Time:** ________________")
    lines.append("")
    lines.append("**Signature/Confirmation:** ________________")
    lines.append("")

    return "\n".join(lines)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: generate_compliance_final_checklist.py <job_id> [jobs_base]")
        sys.exit(1)

    job_id = sys.argv[1]
    jobs_base = sys.argv[2] if len(sys.argv) > 2 else "reports/compliance/jobs"

    try:
        checklist = generate_final_checklist(job_id, jobs_base)
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Write checklist
    jobs_dir = Path(jobs_base)
    job_dir = jobs_dir / job_id
    ops_dir = job_dir / "ops"
    ops_dir.mkdir(parents=True, exist_ok=True)

    checklist_file = ops_dir / "FINAL-MANUAL-EXECUTION-CHECKLIST.md"
    with open(checklist_file, "w") as f:
        f.write(checklist)

    print(f"Checklist generated: {checklist_file}")
    sys.exit(0)


if __name__ == "__main__":
    main()
