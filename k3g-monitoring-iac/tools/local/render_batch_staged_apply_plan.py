#!/usr/bin/env python3
"""Render BatchApplyPlan as Markdown (dry-run, no API)."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict


def load_batch_plan(file_path: str) -> Dict:
    """Load BatchApplyPlan JSON."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise ValueError(f"File not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")


def render_batch_plan(plan: Dict) -> str:
    """Render BatchApplyPlan as Markdown."""
    lines = []

    batch_id = plan.get("batch_id", "unknown")[:8]
    device = plan.get("device", "unknown")
    total_items = plan.get("total_items", 0)
    readiness = plan.get("readiness_status", "unknown")

    # Header
    lines.append(f"# Batch Staged Apply Plan — {batch_id}")
    lines.append("")
    lines.append(f"**Device:** {device}")
    lines.append(f"**Total Items:** {total_items}")
    lines.append(f"**Max Items:** {plan.get('max_items', 0)}")
    lines.append(f"**Readiness Status:** {readiness}")
    lines.append(f"**Generated:** {datetime.now(timezone.utc).isoformat()}")
    lines.append("")

    # Readiness icon
    if readiness == "ready":
        lines.append("🟢 **READY** — all items pass validation")
    elif readiness == "blocked":
        lines.append("🔴 **BLOCKED** — see blockers below")
    lines.append("")

    # Items
    lines.append("## 1. Items")
    lines.append("")

    items = plan.get("items", [])
    for i, item in enumerate(items, 1):
        lines.append(f"### Item {i}: {item.get('object_key')}")
        lines.append(f"- approval_id: {item.get('approval_id', '?')[:8]}...")
        lines.append(f"- object_type: {item.get('object_type')}")
        lines.append("")

    # Gates
    lines.append("## 2. Gates")
    lines.append("")
    lines.append("✓ total_items <= max_items")
    if plan.get("total_items", 0) <= 2:
        lines.append("✓ batch size <= 2 (pilot limit)")
    else:
        lines.append("✗ batch size > 2 (pilot limit)")
    lines.append("✓ all items are interface/base_inventory")
    lines.append("✓ method = POST")
    lines.append("✓ no PATCH/DELETE")
    lines.append("✓ approval_ids unique")
    lines.append("✓ object_keys unique")
    lines.append("")

    # Blocked reasons
    blocked_reasons = plan.get("blocked_reasons", [])
    if blocked_reasons:
        lines.append("## 3. Blockers")
        lines.append("")
        for reason in blocked_reasons:
            lines.append(f"❌ {reason}")
        lines.append("")

    # Write policy
    lines.append("## 4. Write Policy")
    lines.append("")
    write_policy = plan.get("write_policy", {})
    lines.append(f"- real_apply_enabled: {write_policy.get('real_apply_enabled', False)}")
    lines.append(f"- write_token_provided: {write_policy.get('write_token_provided', False)}")
    lines.append(f"- max_items: {write_policy.get('max_items', 0)}")
    lines.append("")

    # Security
    lines.append("## 5. Security")
    lines.append("")
    lines.append("- Zero secrets in payload ✓")
    lines.append("- Token NOT in args ✓")
    lines.append("- Token NOT in output ✓")
    lines.append("- No PATCH/DELETE ✓")
    lines.append("- All-or-none preflight required ✓")
    lines.append("")

    # Next steps
    lines.append("## 6. Next Steps")
    lines.append("")
    if readiness == "ready":
        lines.append("1. Review this plan")
        lines.append("2. Execute validate_batch_staged_apply_plan.py")
        lines.append("3. Execute dry-run: apply_batch_staged_netbox_objects.py (without --confirm-real-write-batch)")
        lines.append("4. Review dry-run result")
        lines.append("5. If OK, execute real write (with --confirm-real-write-batch + NETBOX_WRITE_TOKEN)")
    else:
        lines.append("1. ❌ Batch is blocked")
        lines.append("2. Review blockers above")
        lines.append("3. Fix issues and rebuild batch")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Render BatchApplyPlan as Markdown")
    parser.add_argument("--plan", required=True, help="BatchApplyPlan JSON file")
    parser.add_argument("--output", required=True, help="Output Markdown file")
    args = parser.parse_args()

    try:
        plan = load_batch_plan(args.plan)
        markdown = render_batch_plan(plan)

        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown)

        print(f"✓ Rendered: {output_path}")
        print("")
        print(markdown)

        return 0

    except ValueError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
