#!/usr/bin/env python3
"""FASE 4.2 — Controlled Operation Cycle Intake.

Validate cycle scope, confirm guardrails, prepare cycle for Week 1.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def load_json_safe(file_path: Path) -> Dict[str, Any]:
    """Load JSON file safely."""
    if not file_path.exists():
        return {}

    try:
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def validate_scope(scope: Dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate cycle scope against guardrails."""
    issues = []

    # Check max_items
    max_items = scope.get("max_items", 0)
    if max_items > 3:
        issues.append(f"max_items={max_items} exceeds 3-item limit")

    # Check allowed methods
    allowed = scope.get("allowed_methods", [])
    if "POST" not in allowed:
        issues.append("POST not in allowed_methods")

    # Check forbidden methods
    forbidden = scope.get("forbidden_methods", [])
    if "PATCH" not in forbidden:
        issues.append("PATCH not in forbidden_methods")
    if "DELETE" not in forbidden:
        issues.append("DELETE not in forbidden_methods")

    # Check forbidden targets
    targets = scope.get("forbidden_targets", [])
    critical_targets = ["/sync", "equipment", "ssh", "netconf"]
    for target in critical_targets:
        if target not in targets:
            issues.append(f"'{target}' not in forbidden_targets")

    # Check one-shot enforcement
    if not scope.get("one_shot_only", False):
        issues.append("one_shot_only not enforced")

    # Check no auto-retry
    if not scope.get("no_automatic_retry", False):
        issues.append("no_automatic_retry not enforced")

    # Check no auto-rollback
    if not scope.get("no_automatic_rollback", False):
        issues.append("no_automatic_rollback not enforced")

    return len(issues) == 0, issues


def validate_status(status_data: Dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate cycle status."""
    issues = []

    cycle_status = status_data.get("status", "")
    if cycle_status != "PLANNED_NOT_STARTED":
        issues.append(f"status={cycle_status} should be PLANNED_NOT_STARTED")

    return len(issues) == 0, issues


def evaluate_intake(
    scope_valid: bool,
    scope_issues: list[str],
    status_valid: bool,
    status_issues: list[str],
) -> str:
    """Evaluate intake readiness."""
    all_issues = scope_issues + status_issues

    if not scope_valid or not status_valid:
        return "CYCLE_INTAKE_BLOCKED"

    if all_issues:
        return "CYCLE_INTAKE_READY_WITH_RESTRICTIONS"

    return "CYCLE_INTAKE_READY"


def generate_intake_markdown(
    cycle_id: str, device: str, decision: str, scope: Dict[str, Any], issues: list[str]
) -> str:
    """Generate intake markdown report."""
    timestamp = datetime.utcnow().isoformat() + "+00:00"

    emoji = {
        "CYCLE_INTAKE_READY": "✓",
        "CYCLE_INTAKE_READY_WITH_RESTRICTIONS": "⚠",
        "CYCLE_INTAKE_BLOCKED": "✗",
    }.get(decision, "?")

    next_step = {
        "CYCLE_INTAKE_READY": "Proceed to Week 1 response collection via Web UI",
        "CYCLE_INTAKE_READY_WITH_RESTRICTIONS": "Review restrictions, then proceed to Week 1",
        "CYCLE_INTAKE_BLOCKED": "Resolve blocking issues before proceeding",
    }.get(decision, "Unknown")

    issues_section = ""
    if issues:
        issues_section = f"""

## 3. Issues Found

{chr(10).join(f"- {issue}" for issue in issues)}
"""

    md = f"""# {cycle_id} — Intake Validation

## 1. Decision

### {emoji} {decision}

## 2. Scope Validation

- **Device:** {device}
- **Max Items:** {scope.get("max_items", "?")}
- **Allowed Methods:** {', '.join(scope.get("allowed_methods", []))}
- **Forbidden Methods:** {', '.join(scope.get("forbidden_methods", []))}
- **One-Shot Only:** {scope.get("one_shot_only", False)}
- **No Auto-Retry:** {scope.get("no_automatic_retry", False)}
- **No Auto-Rollback:** {scope.get("no_automatic_rollback", False)}
{issues_section}

## 4. Next Step

{next_step}

---

**Cycle ID:** {cycle_id}
**Device:** {device}
**Decision:** {decision}
**Validated At:** {timestamp}
"""

    return md


def main() -> int:
    """Run FASE 4.2."""
    parser = argparse.ArgumentParser(description="FASE 4.2 — Controlled Operation Cycle Intake")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--cycle-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)

    args = parser.parse_args()

    # Load scope and status
    scope_file = args.cycle_dir / f"{args.cycle_id.upper()}-SCOPE.json"
    status_file = args.cycle_dir / f"{args.cycle_id.upper()}-STATUS.json"

    scope = load_json_safe(scope_file)
    status = load_json_safe(status_file)

    # Validate
    scope_valid, scope_issues = validate_scope(scope)
    status_valid, status_issues = validate_status(status)

    all_issues = scope_issues + status_issues
    decision = evaluate_intake(scope_valid, scope_issues, status_valid, status_issues)

    # Generate markdown
    markdown = generate_intake_markdown(args.cycle_id, args.device, decision, scope, all_issues)

    # Generate JSON
    intake_json = {
        "cycle_id": args.cycle_id,
        "device": args.device,
        "device_id": args.device_id,
        "decision": decision,
        "validated_at": datetime.utcnow().isoformat() + "+00:00",
        "scope_validation": {
            "valid": scope_valid,
            "issues": scope_issues,
        },
        "status_validation": {
            "valid": status_valid,
            "issues": status_issues,
        },
        "guardrails": {
            "max_items_enforced": scope.get("max_items", 0) <= 3,
            "post_only_enforced": "POST" in scope.get("allowed_methods", []),
            "patch_forbidden": "PATCH" in scope.get("forbidden_methods", []),
            "delete_forbidden": "DELETE" in scope.get("forbidden_methods", []),
            "sync_forbidden": "/sync" in scope.get("forbidden_targets", []),
            "equipment_forbidden": "equipment" in scope.get("forbidden_targets", []),
            "one_shot_enforced": scope.get("one_shot_only", False),
            "no_auto_retry": scope.get("no_automatic_retry", False),
            "no_auto_rollback": scope.get("no_automatic_rollback", False),
        },
    }

    # Write outputs
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(intake_json, f, indent=2)

    print(f"✓ Intake decision: {decision}")
    print(f"✓ Report: {args.output}")
    print(f"✓ JSON: {args.output_json}")

    return 0 if "READY" in decision else 1


if __name__ == "__main__":
    raise SystemExit(main())
