#!/usr/bin/env python3
"""ApplyPlan Readiness Gate — Validate if proposed approvals can advance.

Does NOT create ApplyPlan. Only validates readiness.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def check_approval_record(approval_file: Path) -> tuple[bool, str]:
    """Check if approval record is valid for ApplyPlan."""
    try:
        with open(approval_file, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return False, f"Invalid JSON: {e}"

    # Status must be proposed/pending
    status = data.get("status", "").lower()
    if status not in ("proposed", "pending"):
        return False, f"Invalid status: {status} (must be proposed/pending)"

    # Cannot be approved or applied
    if status in ("approved", "applied"):
        return False, f"Already {status}"

    # Must have reviewer
    if not data.get("reviewer"):
        return False, "No reviewer"

    # Must have evidence_hash
    if not data.get("evidence_hash"):
        return False, "No evidence_hash"

    # Must have source evidence (draft or payload)
    if not (data.get("source_draft") or data.get("proposed_payload")):
        return False, "No source evidence (missing source_draft or proposed_payload)"

    # No ApplyPlan should exist yet
    if data.get("apply_plan"):
        return False, "ApplyPlan already exists"

    # Check for secrets
    payload_str = json.dumps(data.get("proposed_payload", {}))
    secrets = ["token", "password", "secret", "netbox_write"]
    if any(s in payload_str.lower() for s in secrets):
        return False, "Secrets detected in payload"

    # Must have safety flags
    flags = data.get("safety", {}) or data.get("safety_flags", {})
    if not (flags.get("no_netbox_write") and flags.get("no_apply_plan_created")):
        return False, "Missing safety flags (no_netbox_write, no_apply_plan_created)"

    return True, "Valid"


def generate_report(
    device: str,
    device_id: str,
    approvals_dir: Path,
    policy_baseline: Path,
    output_file: Path,
) -> None:
    """Generate ApplyPlan readiness gate report."""

    # Load approvals
    eligible = []
    not_eligible = []

    if approvals_dir.exists():
        for approval_file in approvals_dir.glob("approval-*.json"):
            valid, reason = check_approval_record(approval_file)
            if valid:
                try:
                    with open(approval_file) as f:
                        data = json.load(f)
                    eligible.append({
                        "file": approval_file.name,
                        "approval_id": data.get("approval_id", "?"),
                        "object_type": data.get("object_type", "?"),
                        "object_key": data.get("object_key", "?"),
                    })
                except Exception:
                    pass
            else:
                not_eligible.append({
                    "file": approval_file.name,
                    "reason": reason,
                })

    # Determine decision
    if len(eligible) == 0:
        decision = "NOT_READY_FOR_APPLYPLAN"
        reason = "No eligible ApprovalRecords found"
    else:
        decision = "READY_FOR_APPROVAL_REVIEW"
        reason = f"{len(eligible)} ApprovalRecords ready for review"

    # Generate report
    lines = [
        "# Gate de Prontidão para ApplyPlan",
        f"",
        f"**Device:** {device} (ID: {device_id})",
        f"**Data:** {datetime.now().isoformat()}",
        f"",
        f"## 1. Decisão",
        f"",
        f"### {decision}",
        f"{reason}",
        f"",
        f"## 2. Resumo",
        f"",
        f"- Total ApprovalRecords: {len(eligible) + len(not_eligible)}",
        f"- Elegíveis para ApplyPlan: {len(eligible)}",
        f"- Não elegíveis: {len(not_eligible)}",
        f"",
    ]

    if eligible:
        lines.extend([
            f"## 3. ApprovalRecords Elegíveis",
            f"",
            f"| Approval ID | Object Type | Object Key | Status |",
            f"|---|---|---|---|",
        ])
        for item in eligible:
            lines.append(f"| {item['approval_id']} | {item['object_type']} | {item['object_key']} | proposed |")
        lines.append("")

    if not_eligible:
        lines.extend([
            f"## 4. Não Elegíveis",
            f"",
            f"| Arquivo | Motivo |",
            f"|---|---|",
        ])
        for item in not_eligible:
            lines.append(f"| {item['file']} | {item['reason']} |")
        lines.append("")

    lines.extend([
        f"## 5. Segurança",
        f"",
        f"✓ Nenhuma escrita NetBox",
        f"✓ Nenhum ApplyPlan criado",
        f"✓ Nenhum ApprovalRecord aprovado automaticamente",
        f"",
        f"## 6. Próxima Fase",
        f"",
        f"Se **{decision}** for READY:",
        f"- FASE 2.40: Manual Approval Review",
        f"",
        f"Se NOT_READY:",
        f"- Corrigir ApprovalRecords ou decisões",
        f"",
    ])

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report: {output_file}")
    print(f"Decision: {decision}")


def main() -> int:
    """Run gate."""
    parser = argparse.ArgumentParser(
        description="ApplyPlan Readiness Gate — Validate before ApplyPlan creation"
    )
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--approvals-dir", type=Path, required=True)
    parser.add_argument("--policy-baseline", type=Path)
    parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()

    generate_report(
        args.device,
        args.device_id,
        args.approvals_dir,
        args.policy_baseline,
        args.output,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
