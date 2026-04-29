#!/usr/bin/env python3
"""FASE 2.40 — List proposed ApprovalRecords for manual review."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def main() -> int:
    """List proposed approval records."""
    parser = argparse.ArgumentParser(description="List proposed ApprovalRecords")
    parser.add_argument("--device", required=True)
    parser.add_argument("--proposed-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)

    args = parser.parse_args()

    records = []
    if args.proposed_dir.exists():
        for record_file in args.proposed_dir.glob("approval-record-*.json"):
            try:
                with open(record_file, encoding="utf-8") as f:
                    record = json.load(f)
                if record.get("status") in ("proposed", "pending"):
                    records.append({
                        "file": record_file.name,
                        "approval_id": record.get("approval_record_id", "?"),
                        "object_type": record.get("object_type", "?"),
                        "object_key": record.get("object_key", "?"),
                        "reviewer": record.get("reviewer", "?"),
                    })
            except Exception:
                pass

    lines = [
        "# Registros de Aprovação Propostos",
        "",
        f"**Device:** {args.device}",
        f"**Total:** {len(records)}",
        "",
        "Aguardando revisão manual.",
        "",
    ]

    if records:
        lines.extend([
            "| Approval ID | Object Type | Object Key | Reviewer |",
            "|---|---|---|---|",
        ])
        for rec in records:
            lines.append(f"| {rec['approval_id']} | {rec['object_type']} | {rec['object_key']} | {rec['reviewer']} |")
        lines.append("")

        lines.append("## Próximo passo")
        lines.append("")
        lines.append("Comando de aprovação manual:")
        lines.append("")

        for rec in records:
            cmd = (
                f"python3 tools/local/review_proposed_approval_record.py \\\n"
                f"  --approval-record {args.proposed_dir}/{rec['file']} \\\n"
                f"  --decision approve \\\n"
                f"  --reviewer <SEU_NOME> \\\n"
                f"  --reason '<JUSTIFICATIVA>' \\\n"
                f"  --output-dir reports/pilot-device-compliance/approvals"
            )
            lines.append(f"```bash")
            lines.append(cmd)
            lines.append(f"```")
            lines.append("")
    else:
        lines.append("Nenhum registro aguardando revisão.")

    lines.append("## Segurança")
    lines.append("")
    lines.append("✓ Nenhuma escrita NetBox")
    lines.append("✓ Nenhuma criação de ApplyPlan")
    lines.append("✓ Revisão local apenas")

    output_text = "\n".join(lines)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output_text, encoding="utf-8")
        print(f"✓ List: {args.output}")
    else:
        print(output_text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
