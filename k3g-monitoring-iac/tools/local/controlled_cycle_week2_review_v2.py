#!/usr/bin/env python3
"""FASE 4.41 - Cycle-002 Week 2 Human Review.

Local, read-only validation of Week 2 human decisions.
No NetBox write. No token. No ApplyPlan.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ALLOWED_DECISIONS = {
    "approve_for_approval_record",
    "request_changes",
    "rejected",
    "deferred",
    "blocked",
    "pending_review",
}


def safe_text(value: Any) -> str:
    return str(value or "").strip()


def truthy(value: Any) -> bool:
    return safe_text(value).lower() in {"true", "1", "yes", "y"}


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def sanitize_item_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", safe_text(value))


def draft_path_for(drafts_dir: Path, item_id: str) -> Path:
    return drafts_dir / f"approval-draft-{sanitize_item_id(item_id)}.json"


def validate_row(row: Dict[str, str], drafts_dir: Path) -> tuple[bool, List[str], str]:
    issues: List[str] = []
    decision = safe_text(row.get("decision"))
    reviewer = safe_text(row.get("reviewer"))
    reviewed_at = safe_text(row.get("reviewed_at"))
    reason = safe_text(row.get("reason"))
    notes = safe_text(row.get("notes"))
    allowed = truthy(row.get("approval_record_allowed"))
    item_id = safe_text(row.get("item_id") or row.get("object_key") or row.get("object_id"))
    decision_lower = decision.lower()

    if decision_lower not in ALLOWED_DECISIONS and decision_lower != "pending":
        issues.append(f"invalid decision: {decision}")

    if not reviewer:
        if decision_lower not in {"pending_review", "pending"}:
            issues.append("reviewer required")
    if not reviewed_at:
        if decision_lower not in {"pending_review", "pending"}:
            issues.append("reviewed_at required")
    else:
        try:
            datetime.fromisoformat(reviewed_at.replace("Z", "+00:00"))
        except Exception:
            issues.append("reviewed_at not valid ISO datetime")

    if decision_lower == "approve_for_approval_record":
        if not allowed:
            issues.append("approval_record_allowed must be true for approve_for_approval_record")
        if not (reason or notes):
            issues.append("reason or notes required for approve_for_approval_record")
    elif decision_lower == "request_changes":
        if not notes:
            issues.append("notes required for request_changes")
    elif decision_lower in {"rejected", "blocked"}:
        if not reason:
            issues.append(f"reason required for {decision_lower}")
    elif decision_lower == "deferred":
        if not notes:
            issues.append("notes required for deferred")

    draft_file = draft_path_for(drafts_dir, item_id)
    if not item_id:
        issues.append("item_id/object_key required")
    elif not draft_file.exists():
        issues.append(f"draft missing: {draft_file.name}")

    if decision_lower in {"pending_review", "pending"} and not issues:
        return True, issues, "pending_review"

    valid = len(issues) == 0
    if valid and decision_lower == "approve_for_approval_record":
        return True, issues, "approved_for_approval_record"
    if valid and decision_lower == "request_changes":
        return True, issues, "request_changes"
    if valid and decision_lower == "rejected":
        return True, issues, "rejected"
    if valid and decision_lower == "deferred":
        return True, issues, "deferred"
    if valid and decision_lower == "blocked":
        return True, issues, "blocked"
    if decision_lower in {"pending_review", "pending"}:
        return True, issues, "pending_review"
    return False, issues, "blocked"


def classify_review(rows: List[Dict[str, str]], drafts_dir: Path) -> tuple[str, List[Dict[str, Any]]]:
    items: List[Dict[str, Any]] = []
    invalid_found = False
    approved_count = 0
    pending_count = 0
    restriction_count = 0

    for row in rows:
        valid, issues, classification = validate_row(row, drafts_dir)
        if not valid:
            invalid_found = True
            classification = "blocked"

        if classification == "approved_for_approval_record":
            approved_count += 1
        elif classification == "pending_review":
            pending_count += 1
        elif classification in {"request_changes", "rejected", "deferred", "blocked"}:
            restriction_count += 1

        items.append(
            {
                "item_id": safe_text(row.get("item_id")),
                "object_key": safe_text(row.get("object_key")),
                "object_type": safe_text(row.get("object_type")),
                "responsible_team": safe_text(row.get("responsible_team")),
                "decision": safe_text(row.get("decision")),
                "classification": classification,
                "reviewer": safe_text(row.get("reviewer")),
                "reviewed_at": safe_text(row.get("reviewed_at")),
                "approval_record_allowed": truthy(row.get("approval_record_allowed")),
                "notes": safe_text(row.get("notes")),
                "reason": safe_text(row.get("reason")),
                "restriction": safe_text(row.get("restriction")),
                "issues": issues,
            }
        )

    if invalid_found or approved_count == 0:
        decision = "WEEK2_REVIEW_BLOCKED"
    elif pending_count > 0 or restriction_count > 0:
        decision = "WEEK2_REVIEW_PASSED_WITH_RESTRICTIONS"
    else:
        decision = "WEEK2_REVIEW_PASSED"

    return decision, items


def render_report(cycle_id: str, device: str, decision: str, items: List[Dict[str, Any]]) -> str:
    timestamp = datetime.utcnow().isoformat() + "+00:00"
    approved = sum(1 for item in items if item["classification"] == "approved_for_approval_record")
    pending = sum(1 for item in items if item["classification"] == "pending_review")
    blocked = sum(1 for item in items if item["classification"] == "blocked")
    return "\n".join(
        [
            f"# Execução da Revisão Humana — Semana 2 — {device}",
            "",
            "## 1. Contexto",
            f"- Cycle: {cycle_id}",
            f"- Decision: {decision}",
            "- Sem escrita NetBox",
            "- Sem ApplyPlan",
            "- Sem aprovação automática",
            "",
            "## 2. Itens em revisão",
            "",
            "| Object Type | Object Key | Time | Responsável | Status Week 1 | Restrição | Decisão | Revisor | Observações |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        + [
            f"| {item['object_type']} | {item['object_key']} | {item['responsible_team']} | {item['reviewer'] or 'Pendente'} | {item['classification']} | {item['restriction'] or '-'} | {item['classification']} | {item['reviewer'] or '-'} | {item['notes'] or item['reason'] or '-'} |"
            for item in items
        ]
        + [
            "",
            "## 3. Resultado",
            f"- total revisado: {len(items)}",
            f"- aprovado para Registro de Aprovação: {approved}",
            f"- precisa de ajuste: {pending}",
            f"- rejeitado: {sum(1 for item in items if item['classification'] == 'rejected')}",
            f"- adiado: {sum(1 for item in items if item['classification'] == 'deferred')}",
            f"- bloqueado: {blocked}",
            f"- pendente de revisão: {pending}",
            "",
            "## 4. Próximas ações",
            "- se houver aprovados: promover para ApprovalRecords proposed/pending",
            "- se houver ajustes: devolver ao time",
            "- se houver bloqueios: manter fora do fluxo",
            "- nenhum ApplyPlan nesta fase",
            "",
            f"**Cycle ID:** {cycle_id}",
            f"**Device:** {device}",
            f"**Generated:** {timestamp}",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="FASE 4.41 — Cycle-002 Week 2 Human Review")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--cycle-dir", type=Path, required=True)
    parser.add_argument("--week2-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()

    board = args.week2_dir / f"{args.cycle_id.upper()}-WEEK2-REVIEW-BOARD.md"
    decisions_csv = args.week2_dir / f"{args.cycle_id.upper()}-WEEK2-DECISIONS.csv"
    drafts_dir = args.week2_dir / "approval-drafts"
    status_md = args.week2_dir / f"{args.cycle_id.upper()}-WEEK2-STATUS.md"
    status_json = args.week2_dir / f"{args.cycle_id.upper()}-WEEK2-STATUS.json"

    errors: List[str] = []
    if not board.exists():
        errors.append("week2 review board missing")
    rows = load_csv(decisions_csv)
    if not rows:
        errors.append("decisions csv empty or missing")
    if not drafts_dir.exists():
        errors.append("approval drafts dir missing")

    decision, items = classify_review(rows, drafts_dir) if not errors else ("WEEK2_REVIEW_BLOCKED", [])
    if errors:
        decision = "WEEK2_REVIEW_BLOCKED"
    elif decision == "WEEK2_REVIEW_PASSED":
        pass
    elif decision == "WEEK2_REVIEW_PASSED_WITH_RESTRICTIONS":
        pass
    else:
        decision = "WEEK2_REVIEW_BLOCKED"

    report = render_report(args.cycle_id, args.device, decision, items)
    output_json = {
        "cycle_id": args.cycle_id,
        "device": args.device,
        "device_id": args.device_id,
        "decision": decision,
        "reviewed_at": datetime.utcnow().isoformat() + "+00:00",
        "errors": errors,
        "summary": {
            "total": len(items),
            "approved_for_approval_record": sum(1 for item in items if item["classification"] == "approved_for_approval_record"),
            "request_changes": sum(1 for item in items if item["classification"] == "request_changes"),
            "rejected": sum(1 for item in items if item["classification"] == "rejected"),
            "deferred": sum(1 for item in items if item["classification"] == "deferred"),
            "blocked": sum(1 for item in items if item["classification"] == "blocked"),
            "pending_review": sum(1 for item in items if item["classification"] == "pending_review"),
        },
        "items": items,
        "has_restrictions": bool(errors) or any(item["classification"] != "approved_for_approval_record" for item in items),
        "no_netbox_write": True,
        "no_apply_plan": True,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(output_json, indent=2), encoding="utf-8")

    status_md.write_text(f"# {args.cycle_id.upper()} — Week 2 Status\n\nStatus: {decision}\n", encoding="utf-8")
    status_json.write_text(json.dumps({"cycle_id": args.cycle_id, "status": decision, "updated_at": output_json["reviewed_at"]}, indent=2), encoding="utf-8")

    cycle_status = args.cycle_dir / f"{args.cycle_id.upper()}-STATUS.md"
    cycle_status.write_text(f"# {args.cycle_id.upper()}\n\nStatus: {decision}\n", encoding="utf-8")

    print(f"✓ Week 2 review decision: {decision}")
    print(f"✓ Report: {args.output}")
    print(f"✓ JSON: {args.output_json}")
    return 0 if decision != "WEEK2_REVIEW_BLOCKED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
