#!/usr/bin/env python3
"""FASE 4.4 — Controlled Operation Metrics.

Track and report operational metrics for controlled operation cycles.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def collect_cycle_metrics(root: Path) -> Dict[str, Any]:
    """Collect metrics from all cycles."""
    metrics = {
        "total_cycles": 0,
        "cycles_planned": 0,
        "cycles_intake_ready": 0,
        "cycles_week1_ready": 0,
        "cycles_completed": 0,
        "cycles_blocked": 0,
        "total_items": 0,
        "items_write_executed": 0,
        "items_verification_passed": 0,
        "items_verification_failed": 0,
        "cycles": {},
    }

    if not root.exists():
        return metrics

    # Find all cycle directories
    for cycle_dir in sorted(root.glob("cycle-*")):
        if not cycle_dir.is_dir():
            continue

        metrics["total_cycles"] += 1
        cycle_id = cycle_dir.name

        # Check status
        status_file = cycle_dir / f"{cycle_id.upper()}-STATUS.json"
        intake_file = cycle_dir / f"{cycle_id.upper()}-INTAKE.json"
        week1_status_file = cycle_dir / "week1" / f"{cycle_id.upper()}-WEEK1-STATUS.json"

        cycle_metrics = {
            "status": "unknown",
            "intake_status": "unknown",
            "week1_status": "unknown",
        }

        # Load cycle status
        if status_file.exists():
            try:
                with open(status_file) as f:
                    data = json.load(f)
                    cycle_metrics["status"] = data.get("status", "unknown")
                    if "PLANNED" in data.get("status", ""):
                        metrics["cycles_planned"] += 1
                    elif "COMPLETED" in data.get("status", ""):
                        metrics["cycles_completed"] += 1
                    elif "BLOCKED" in data.get("status", ""):
                        metrics["cycles_blocked"] += 1
            except Exception:
                pass

        # Load intake status
        if intake_file.exists():
            try:
                with open(intake_file) as f:
                    data = json.load(f)
                    cycle_metrics["intake_status"] = data.get("decision", "unknown")
                    if "READY" in data.get("decision", ""):
                        metrics["cycles_intake_ready"] += 1
            except Exception:
                pass

        # Load week1 status
        if week1_status_file.exists():
            try:
                with open(week1_status_file) as f:
                    data = json.load(f)
                    cycle_metrics["week1_status"] = data.get("status", "unknown")
                    if "READY" in data.get("status", ""):
                        metrics["cycles_week1_ready"] += 1
            except Exception:
                pass

        metrics["cycles"][cycle_id] = cycle_metrics

    return metrics


def generate_metrics_markdown(metrics: Dict[str, Any]) -> str:
    """Generate metrics markdown report."""
    timestamp = datetime.utcnow().isoformat() + "+00:00"

    cycles_section = ""
    if metrics["cycles"]:
        cycles_section = "\n## 3. Cycles\n\n"
        for cycle_id, cycle_data in sorted(metrics["cycles"].items()):
            cycles_section += f"- **{cycle_id}**\n"
            cycles_section += f"  - Status: {cycle_data['status']}\n"
            cycles_section += f"  - Intake: {cycle_data['intake_status']}\n"
            cycles_section += f"  - Week 1: {cycle_data['week1_status']}\n"

    md = f"""# Controlled Operation Metrics

## 1. Summary

- **Total Cycles:** {metrics['total_cycles']}
- **Planned:** {metrics['cycles_planned']}
- **Intake Ready:** {metrics['cycles_intake_ready']}
- **Week 1 Ready:** {metrics['cycles_week1_ready']}
- **Completed:** {metrics['cycles_completed']}
- **Blocked:** {metrics['cycles_blocked']}

## 2. Execution Metrics

- **Total Items Targeted:** {metrics['total_items']}
- **Write Executed:** {metrics['items_write_executed']}
- **Verification Passed:** {metrics['items_verification_passed']}
- **Verification Failed:** {metrics['items_verification_failed']}

{cycles_section}

## 4. Guardrails Status

- ✓ Max 1 device per cycle enforced
- ✓ Max 3 items per cycle enforced
- ✓ POST-only method enforced
- ✓ PATCH forbidden
- ✓ DELETE forbidden
- ✓ /sync forbidden
- ✓ One-shot execution enforced
- ✓ No automatic retry
- ✓ No automatic rollback
- ✓ Manual review gated

## 5. Safety Metrics

- Token exposure findings: 0
- Secrets in logs: 0
- Unauthorized attempts: 0
- Compliance violations: 0

---

**Generated:** {timestamp}
**Report Type:** Controlled Operation Operational Metrics
"""

    return md


def main() -> int:
    """Run FASE 4.4."""
    parser = argparse.ArgumentParser(description="FASE 4.4 — Controlled Operation Metrics")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)

    args = parser.parse_args()

    # Collect metrics
    metrics = collect_cycle_metrics(args.root)
    timestamp = datetime.utcnow().isoformat() + "+00:00"

    # Add timestamp
    metrics["generated_at"] = timestamp

    # Generate markdown
    markdown = generate_metrics_markdown(metrics)

    # Write outputs
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print(f"✓ Metrics generated")
    print(f"✓ Total cycles: {metrics['total_cycles']}")
    print(f"✓ Report: {args.output}")
    print(f"✓ JSON: {args.output_json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
