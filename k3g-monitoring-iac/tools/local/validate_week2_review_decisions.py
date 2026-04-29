#!/usr/bin/env python3
"""Validate Week 2 human review decisions and emit local-only reports."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple


ALLOWED_DECISIONS = {
    "approve_for_approval_record",
    "request_changes",
    "reject",
    "defer",
    "block",
}

FORBIDDEN_TERMS = {
    "token",
    "password",
    "secret",
    "bearer",
    "authorization",
    "private key",
    "netbox_write_token",
}


def _norm(value: object) -> str:
    return str(value or "").strip()


def _lower(value: object) -> str:
    return _norm(value).lower()


def _is_iso_datetime(value: str) -> bool:
    if not value:
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def _safe_filename(object_key: str) -> str:
    return f"approval-draft-{object_key.replace('.', '-').replace('/', '-')}.json"


def _load_draft(drafts_dir: Path, object_key: str) -> Tuple[bool, Dict[str, object] | None, Path | None]:
    draft_file = drafts_dir / _safe_filename(object_key)
    if not draft_file.exists():
        return False, None, draft_file
    try:
        with draft_file.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        return False, None, draft_file
    if _lower(data.get("status")) != "draft_review":
        return False, None, draft_file
    return True, data, draft_file


def _has_forbidden_text(*values: object) -> bool:
    text = " ".join(_lower(v) for v in values if _norm(v))
    return any(term in text for term in FORBIDDEN_TERMS)


def _missing_required_fields(row: Dict[str, str], object_type: str) -> List[str]:
    required_by_type = {
        "subinterface": ["tenant", "service_type", "criticality", "owner"],
        "ip_address": ["owner"],
        "bgp_peer": ["criticality", "owner"],
    }
    missing = []
    for field in required_by_type.get(object_type, []):
        if not _norm(row.get(field)):
            missing.append(field)
    return missing


def _validate_row(row_num: int, row: Dict[str, str], drafts_dir: Path) -> Dict[str, object]:
    object_key = _norm(row.get("object_key"))
    decision = _lower(row.get("decision"))
    object_type = _lower(row.get("object_type"))
    reviewer = _norm(row.get("reviewer"))
    reviewed_at = _norm(row.get("reviewed_at"))
    approval_allowed = _lower(row.get("approval_record_allowed"))
    reason = _norm(row.get("reason"))
    notes = _norm(row.get("notes"))

    result: Dict[str, object] = {
        "row": row_num,
        "object_key": object_key,
        "object_type": object_type,
        "decision": decision,
        "reviewer": reviewer,
        "reviewed_at": reviewed_at,
        "approval_record_allowed": approval_allowed,
        "reason": reason,
        "notes": notes,
        "draft_found": False,
        "draft": None,
        "errors": [],
    }

    if not object_key:
        result["errors"].append("object_key vazio")
        return result

    if _has_forbidden_text(*row.values()):
        result["errors"].append("Valor bloqueado por segurança: token/password/secret/bearer/authorization/private key")
        return result

    draft_ok, draft_data, draft_file = _load_draft(drafts_dir, object_key)
    result["draft_found"] = bool(draft_ok)
    result["draft"] = {
        "path": str(draft_file) if draft_file else "",
        "data": draft_data or {},
    }
    if not draft_ok:
        result["errors"].append(f"Draft não encontrado ou inválido: {_safe_filename(object_key)}")
        return result

    if decision not in ALLOWED_DECISIONS:
        result["errors"].append(f"Decisão inválida: {decision or '[vazio]'}")
        return result

    if decision == "approve_for_approval_record":
        if not reviewer:
            result["errors"].append("reviewer obrigatório para aprovação")
        if not reviewed_at:
            result["errors"].append("reviewed_at obrigatório para aprovação")
        elif not _is_iso_datetime(reviewed_at):
            result["errors"].append("reviewed_at deve ser ISO 8601")
        if approval_allowed not in {"true", "1", "yes"}:
            result["errors"].append("approval_record_allowed=true obrigatório para aprovação")
        if not (reason or notes):
            result["errors"].append("reason ou notes obrigatório para aprovação")

        missing_fields = _missing_required_fields(row, object_type)
        if missing_fields:
            result["errors"].append("Campos obrigatórios ausentes: " + ", ".join(missing_fields))

        if not result["errors"]:
            result["approved_for_approval_record"] = {
                "row": row_num,
                "object_key": object_key,
                "object_type": object_type,
                "reviewer": reviewer,
                "reviewed_at": reviewed_at,
                "draft_file": str(draft_file),
                "reason": reason,
                "notes": notes,
            }
        return result

    if not (reason or notes):
        result["errors"].append("reason ou notes obrigatório para decisões não aprovadas")
    if not reviewer:
        result["errors"].append("reviewer obrigatório para revisão humana")
    if not reviewed_at:
        result["errors"].append("reviewed_at obrigatório para revisão humana")
    elif not _is_iso_datetime(reviewed_at):
        result["errors"].append("reviewed_at deve ser ISO 8601")

    result["non_approval_decision"] = {
        "row": row_num,
        "object_key": object_key,
        "decision": decision,
        "reviewer": reviewer,
        "reviewed_at": reviewed_at,
        "reason": reason or notes,
    }
    return result


def validate_decisions(decisions_file: Path, drafts_dir: Path) -> Dict[str, object]:
    results: Dict[str, object] = {
        "validated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "total_rows": 0,
        "approved_for_approval_record": [],
        "request_changes": [],
        "rejected": [],
        "deferred": [],
        "blocked": [],
        "pending_review": [],
        "invalid": [],
    }

    if not decisions_file.exists():
        results["invalid"].append({"row": 0, "issue": f"CSV não encontrado: {decisions_file}"})
        return results

    with decisions_file.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            results["invalid"].append({"row": 0, "issue": "CSV vazio"})
            return results

        for row_num, row in enumerate(reader, start=2):
            if not any(_norm(value) for value in row.values()):
                continue

            results["total_rows"] += 1
            item = _validate_row(row_num, row, drafts_dir)
            errors = item.get("errors", [])
            if errors:
                results["invalid"].append(
                    {
                        "row": row_num,
                        "object_key": item.get("object_key", ""),
                        "decision": item.get("decision", ""),
                        "errors": errors,
                    }
                )
                if not item.get("decision") or item.get("decision") not in ALLOWED_DECISIONS:
                    results["pending_review"].append(
                        {
                            "row": row_num,
                            "object_key": item.get("object_key", ""),
                            "reason": "; ".join(errors),
                        }
                    )
                continue

            decision = item["decision"]
            if decision == "approve_for_approval_record":
                results["approved_for_approval_record"].append(item["approved_for_approval_record"])
            elif decision == "request_changes":
                results["request_changes"].append(item["non_approval_decision"])
            elif decision == "reject":
                results["rejected"].append(item["non_approval_decision"])
            elif decision == "defer":
                results["deferred"].append(item["non_approval_decision"])
            elif decision == "block":
                results["blocked"].append(item["non_approval_decision"])

    return results


def _table_row(*cols: object) -> str:
    return "| " + " | ".join(_norm(col) if _norm(col) else "-" for col in cols) + " |"


def render_validation_report(results: Dict[str, object]) -> str:
    lines = [
        "# Week 2 Review Decision Validation Report",
        "",
        f"**Generated:** {results['validated_at']}",
        "",
        "## Summary",
        "",
        "| Category | Count |",
        "|---|---:|",
        f"| Total Rows | {results['total_rows']} |",
        f"| Valid Approvals | {len(results['approved_for_approval_record'])} |",
        f"| Request Changes | {len(results['request_changes'])} |",
        f"| Rejected | {len(results['rejected'])} |",
        f"| Deferred | {len(results['deferred'])} |",
        f"| Blocked | {len(results['blocked'])} |",
        f"| Pending Review | {len(results['pending_review'])} |",
        f"| Invalid | {len(results['invalid'])} |",
        "",
        "## Aprovados para Promoção",
        "",
    ]

    if results["approved_for_approval_record"]:
        lines += [
            "| Row | Object Key | Reviewer | Reviewed At | Draft |",
            "|---|---|---|---|---|",
        ]
        for item in results["approved_for_approval_record"]:
            lines.append(_table_row(item["row"], item["object_key"], item["reviewer"], item["reviewed_at"], Path(item["draft_file"]).name))
    else:
        lines.append("*(Nenhum)*")

    lines += ["", "## Request Changes", ""]
    if results["request_changes"]:
        for item in results["request_changes"]:
            lines.append(f"- Row {item['row']}: {item['object_key']} - {item['reason']}")
    else:
        lines.append("*(Nenhum)*")

    lines += ["", "## Rejeitados", ""]
    if results["rejected"]:
        for item in results["rejected"]:
            lines.append(f"- Row {item['row']}: {item['object_key']} - {item['reason']}")
    else:
        lines.append("*(Nenhum)*")

    lines += ["", "## Adiados", ""]
    if results["deferred"]:
        for item in results["deferred"]:
            lines.append(f"- Row {item['row']}: {item['object_key']} - {item['reason']}")
    else:
        lines.append("*(Nenhum)*")

    lines += ["", "## Bloqueados", ""]
    if results["blocked"]:
        for item in results["blocked"]:
            lines.append(f"- Row {item['row']}: {item['object_key']} - {item['reason']}")
    else:
        lines.append("*(Nenhum)*")

    lines += ["", "## Pendentes de Revisão", ""]
    if results["pending_review"]:
        lines.append("| Row | Object Key | Motivo |")
        lines.append("|---|---|---|")
        for item in results["pending_review"]:
            lines.append(_table_row(item["row"], item["object_key"], item["reason"]))
    else:
        lines.append("*(Nenhum)*")

    lines += ["", "## Erros", ""]
    if results["invalid"]:
        lines.append("| Row | Object Key | Decisão | Erros |")
        lines.append("|---|---|---|---|")
        for item in results["invalid"]:
            lines.append(_table_row(item["row"], item.get("object_key", ""), item.get("decision", ""), "; ".join(item.get("errors", []))))
    else:
        lines.append("*(Nenhum)*")

    lines += [
        "",
        "## Segurança",
        "",
        "- Nenhum ApprovalRecord foi criado",
        "- Nenhum ApplyPlan foi criado",
        "- Nenhuma escrita NetBox",
        "- Sem tokens em texto validado",
    ]
    return "\n".join(lines) + "\n"


def render_human_review_report(device: str, results: Dict[str, object]) -> str:
    lines = [
        f"# Relatório da Revisão Humana — Semana 2 — {device}",
        "",
        "## 1. Resumo",
        "",
        f"- total drafts: {results['total_rows']}",
        f"- approved_for_approval_record: {len(results['approved_for_approval_record'])}",
        f"- request_changes: {len(results['request_changes'])}",
        f"- rejected: {len(results['rejected'])}",
        f"- deferred: {len(results['deferred'])}",
        f"- blocked: {len(results['blocked'])}",
        f"- pending_review: {len(results['pending_review'])}",
        "",
        "## 2. Aprovados para Registro de Aprovação",
        "",
    ]

    if results["approved_for_approval_record"]:
        lines.append("| Object Type | Object Key | Time | Responsável | Status Week 2 | Restrição | Decisão | Revisor | Observações |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for item in results["approved_for_approval_record"]:
            lines.append(
                _table_row(
                    item.get("object_type", ""),
                    item.get("object_key", ""),
                    "Semana 2",
                    item.get("reviewer", ""),
                    "pronto",
                    "nenhuma",
                    "approve_for_approval_record",
                    item.get("reviewer", ""),
                    item.get("reason", "") or item.get("notes", ""),
                )
            )
    else:
        lines.append("*(Nenhum)*")

    lines += ["", "## 3. Precisam de ajuste", ""]
    if results["request_changes"]:
        lines.append("| Object Key | Motivo |")
        lines.append("|---|---|")
        for item in results["request_changes"]:
            lines.append(_table_row(item.get("object_key", ""), item.get("reason", "")))
    else:
        lines.append("*(Nenhum)*")

    lines += ["", "## 4. Rejeitados / adiados / bloqueados", ""]
    combined = results["rejected"] + results["deferred"] + results["blocked"]
    if combined:
        lines.append("| Object Key | Decisão | Motivo |")
        lines.append("|---|---|---|")
        for item in combined:
            lines.append(_table_row(item.get("object_key", ""), item.get("reason", ""), item.get("reason", "")))
    else:
        lines.append("*(Nenhum)*")

    lines += ["", "## 5. Próximas ações", ""]
    if results["approved_for_approval_record"]:
        lines.append("- Promover itens aprovados para ApprovalRecords proposed/pending.")
    else:
        lines.append("- Nenhum item pronto para promoção.")
    if results["request_changes"]:
        lines.append("- Devolver itens com ajuste para os times.")
    if combined:
        lines.append("- Manter itens bloqueados fora do fluxo.")
    lines.append("- Nenhum ApplyPlan nesta fase.")
    lines.append("- Revisão humana continua obrigatória.")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Week 2 human review decisions")
    parser.add_argument("--decisions", required=True, type=Path, help="Path to week2-review-decisions.csv")
    parser.add_argument("--drafts-dir", required=True, type=Path, help="Path to week2-approval-drafts directory")
    parser.add_argument("--output", required=True, type=Path, help="Output validation report file")
    parser.add_argument("--device", default="4WNET-MNS-KTG-RX", help="Device name")
    args = parser.parse_args()

    results = validate_decisions(args.decisions, args.drafts_dir)
    validation_report = render_validation_report(results)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(validation_report, encoding="utf-8")

    human_report = args.output.parent / "WEEK2-HUMAN-REVIEW-EXECUTION.md"
    human_report.write_text(render_human_review_report(args.device, results), encoding="utf-8")
    summary_report = args.output.parent / "week2-human-review-report.md"
    summary_report.write_text(render_human_review_report(args.device, results), encoding="utf-8")

    print(f"✓ Validation report generated: {args.output}")
    print(f"✓ Human review report generated: {human_report}")
    print(f"✓ Human summary report generated: {summary_report}")

    return 0 if not results["invalid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
