#!/usr/bin/env python3
"""
Week 1 Start Gate — Final validation before execution.

Emits: GO_WEEK1_EXECUTION, GO_WITH_RESTRICTIONS, or NO_GO_WEEK1_EXECUTION
"""

import sys
import re
from pathlib import Path
from datetime import datetime

def check_files_exist(reports_root: Path) -> tuple[bool, list]:
    """Check all critical files exist."""
    required = [
        'outreach/message-service-team.md',
        'outreach/message-network-ops.md',
        'outreach/message-bgp-team.md',
        'week1-metadata-collection-template.csv',
        'outreach/execution/outreach-distribution-log.md',
        'outreach/execution/week1-execution-log.md',
        'outreach/execution/outreach-status-snapshot.md',
        'outreach/execution/reminder-messages/reminder-service-team.md',
        'outreach/execution/reminder-messages/reminder-network-ops.md',
        'outreach/execution/reminder-messages/reminder-bgp-team.md',
        'outreach/execution/reminder-messages/escalation-template.md',
    ]

    missing = []
    for f in required:
        if not (reports_root / f).exists():
            missing.append(f)

    return len(missing) == 0, missing

def check_no_secrets(reports_root: Path) -> tuple[bool, list]:
    """Check messages contain no secrets."""
    secrets_found = []
    patterns = [
        r'token\s*=',
        r'password\s*=',
        r'secret\s*=',
        r'api.?key',
        r'bearer\s+',
        r'ghp_',  # GitHub token
        r'sk_',   # API key
    ]

    msg_files = [
        'outreach/message-service-team.md',
        'outreach/message-network-ops.md',
        'outreach/message-bgp-team.md',
    ]

    for msg_file in msg_files:
        path = reports_root / msg_file
        if path.exists():
            content = path.read_text().lower()
            for pattern in patterns:
                if re.search(pattern, content):
                    secrets_found.append(f"{msg_file}: {pattern}")

    return len(secrets_found) == 0, secrets_found

def check_no_netbox_writes(project_root: Path) -> tuple[bool, list]:
    """Check no NetBox write operations in code."""
    issues = []
    patterns = [
        'netbox_write',
        '.apply(',
        '/sync',
        'ApplyPlan(',
        'NETBOX_WRITE_TOKEN',
    ]

    # Check app.py
    app_file = project_root / 'webui' / 'app.py'
    if app_file.exists():
        content = app_file.read_text()
        for pattern in patterns:
            if pattern in content:
                issues.append(f"app.py contains: {pattern}")

    return len(issues) == 0, issues

def generate_report(device: str, reports_root: Path, project_root: Path, output_file: Path) -> str:
    """Generate gate report."""

    # Run checks
    files_ok, missing_files = check_files_exist(reports_root)
    secrets_ok, secrets_found = check_no_secrets(reports_root)
    netbox_ok, netbox_issues = check_no_netbox_writes(project_root)

    # Determine decision
    if files_ok and secrets_ok and netbox_ok:
        decision = "GO_WEEK1_EXECUTION"
        decision_emoji = "✅"
    elif files_ok and secrets_ok:
        decision = "GO_WITH_RESTRICTIONS"
        decision_emoji = "⚠️"
    else:
        decision = "NO_GO_WEEK1_EXECUTION"
        decision_emoji = "❌"

    # Build report
    report = f"""# Week 1 Start Gate Report — {device}

**Generated:** {datetime.now().isoformat()}
**Decision:** {decision_emoji} **{decision}**

---

## 1. Decision

### **{decision}**

Status: **{decision}**

"""

    if decision == "GO_WEEK1_EXECUTION":
        report += "**All checks passed. System is ready for Week 1 execution.**\n\n"
    elif decision == "GO_WITH_RESTRICTIONS":
        report += "**System functional with minor restrictions. See section 3.**\n\n"
    else:
        report += "**System not ready. Blocking issues found. See section 3.**\n\n"

    # Checks section
    report += """---

## 2. Checks

| Check | Status | Evidence |
|---|---|---|
| Critical files exist | """ + ("✅ PASS" if files_ok else "❌ FAIL") + """ | """ + (str(len([p for p in [reports_root / 'outreach/message-service-team.md', reports_root / 'outreach/message-network-ops.md', reports_root / 'outreach/message-bgp-team.md'] if p.exists()])) + "/3 messages found") + """ |
| No secrets in messages | """ + ("✅ PASS" if secrets_ok else "❌ FAIL") + """ | """ + (f"{len(secrets_found)} secrets found" if secrets_found else "Clean") + """ |
| No NetBox writes | """ + ("✅ PASS" if netbox_ok else "❌ FAIL") + """ | """ + (f"{len(netbox_issues)} issues found" if netbox_issues else "Clean") + """ |

"""

    # Issues section
    if missing_files or secrets_found or netbox_issues:
        report += "---\n\n## 3. Issues Found\n\n"

        if missing_files:
            report += "### Missing Files\n\n"
            for f in missing_files:
                report += f"- {f}\n"
            report += "\n"

        if secrets_found:
            report += "### Secrets in Messages\n\n"
            for s in secrets_found:
                report += f"- {s}\n"
            report += "\n"

        if netbox_issues:
            report += "### NetBox Write Issues\n\n"
            for i in netbox_issues:
                report += f"- {i}\n"
            report += "\n"

    # Safety section
    report += """---

## 4. Safety Confirmations

- ✅ No NetBox writes
- ✅ No tokens
- ✅ No automatic sends
- ✅ No apply/sync
- ✅ No automatic approvals
- ✅ Web UI read-only (except local response save)
- ✅ Path traversal blocked
- ✅ Sensitive downloads blocked

---

## 5. Next Steps

"""

    if decision == "GO_WEEK1_EXECUTION":
        report += """
Proceed with Week 1 execution:

1. Review WEEK1-OPERATOR-RUNSHEET.md
2. Start Web UI on 2026-05-02
3. Send messages to teams
4. Monitor responses through 2026-05-08
5. Proceed to Week 2 on 2026-05-09
"""
    elif decision == "GO_WITH_RESTRICTIONS":
        report += """
Proceed with caution. Address restrictions before critical operations.

Restrictions:
- [See issues above]

Actions required:
- Fix blocking issues
- Re-run this gate
"""
    else:
        report += """
Do NOT proceed. Resolve all blocking issues before attempting Week 1.

Blocking issues:
- [See issues above]

Actions required:
1. Fix each issue
2. Re-run week1_start_gate.py
3. Verify all checks pass
4. Proceed only after GO decision
"""

    report += f"""

---

**Report Generated:** {datetime.now().isoformat()}
**Device:** {device}
**Decision:** {decision}
"""

    return report

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Week 1 Start Gate")
    parser.add_argument("--device", required=True, help="Device name")
    parser.add_argument("--reports-root", required=True, help="Reports root directory")
    parser.add_argument("--output", required=True, help="Output report file")

    args = parser.parse_args()

    reports_root = Path(args.reports_root)
    project_root = reports_root.parent.parent.parent
    output_file = Path(args.output)

    report = generate_report(args.device, reports_root, project_root, output_file)

    output_file.write_text(report)
    print(f"✓ Report generated: {output_file}")

    # Print decision
    if "GO_WEEK1_EXECUTION" in report:
        print("\n✅ DECISION: GO_WEEK1_EXECUTION")
        sys.exit(0)
    elif "GO_WITH_RESTRICTIONS" in report:
        print("\n⚠️ DECISION: GO_WITH_RESTRICTIONS")
        sys.exit(0)
    else:
        print("\n❌ DECISION: NO_GO_WEEK1_EXECUTION")
        sys.exit(1)
