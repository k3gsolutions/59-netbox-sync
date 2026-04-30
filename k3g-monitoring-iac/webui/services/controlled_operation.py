"""Controlled operation read-only helpers."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except Exception:  # pragma: no cover - fallback only
    yaml = None  # type: ignore


CYCLERE = re.compile(r"^cycle-\d+$")


def safe_cycle_id(cycle_id: str) -> Optional[str]:
    value = (cycle_id or "").strip().lower()
    return value if CYCLERE.fullmatch(value) else None


def load_json_safe(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_text_safe(path: Path, limit: int = 4000) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")[:limit]
    except Exception:
        return ""


def first_existing(base: Path, names: List[str]) -> Optional[Path]:
    for name in names:
        candidate = resolve_case_insensitive(base, name)
        if candidate is not None:
            return candidate
    return None


def resolve_case_insensitive(base: Path, relative_path: str) -> Optional[Path]:
    current = base
    for part in Path(relative_path).parts:
        if part in {".", ""}:
            continue
        if part == "..":
            return None
        if not current.exists():
            return None
        match = None
        lower_part = part.lower()
        for child in current.iterdir():
            if child.name.lower() == lower_part:
                match = child
                break
        if match is None:
            return None
        current = match
    return current


def load_yaml_or_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        if path.suffix.lower() in {".yaml", ".yml"} and yaml is not None:
            with open(path, "r", encoding="utf-8") as handle:
                return yaml.safe_load(handle) or {}
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def scan_sensitive_terms(directory: Path) -> List[str]:
    hits: List[str] = []
    blocked_terms = [
        "netbox_write_token",
        "authorization: token",
        "token=",
        "password=",
        "secret=",
        "private key",
        "bearer",
    ]
    if not directory.exists():
        return hits
    for path in directory.rglob("*"):
        if not path.is_file():
            continue
        lowered_name = path.name.lower()
        if any(term.replace("=", "") in lowered_name for term in ["token", "password", "secret"]):
            hits.append(path.name)
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore").lower()
        except Exception:
            continue
        if any(term in content for term in blocked_terms):
            hits.append(path.name)
    return sorted(set(hits))


def cycle_status_files(cycle_dir: Path) -> Dict[str, Optional[Path]]:
    return {
        "scope": first_existing(cycle_dir, [
            f"{cycle_dir.name}-scope.json",
            f"{cycle_dir.name.upper()}-SCOPE.json",
        ]),
        "status": first_existing(cycle_dir, [
            f"{cycle_dir.name}-STATUS.md",
            f"{cycle_dir.name.upper()}-STATUS.md",
            f"{cycle_dir.name}-STATUS.json",
            f"{cycle_dir.name.upper()}-STATUS.json",
        ]),
        "handoff": first_existing(cycle_dir, [
            f"{cycle_dir.name}-handoff-decision.json",
            f"{cycle_dir.name.upper()}-HANDOFF-DECISION.json",
        ]),
        "manifest": first_existing(cycle_dir, [
            "final-archive/manifest.json",
            "real-write-execution/archive/manifest.json",
            "archive/manifest.json",
            "final-archive/FINAL-ARCHIVE-MANIFEST.json",
        ]),
        "closure": first_existing(cycle_dir, [
            "final-archive/closure-summary.json",
            "real-write-execution/closure/closure-summary.json",
            "real-write-execution/closure/cycle-001-closure-summary.json",
            f"real-write-execution/closure/{cycle_dir.name}-closure-summary.json",
        ]),
    }


def _extract_status_text(status_path: Optional[Path]) -> str:
    if not status_path or not status_path.exists():
        return ""
    if status_path.suffix.lower() == ".json":
        data = load_json_safe(status_path)
        for key in ("status", "decision", "current_status", "gate"):
            value = str(data.get(key) or "").strip()
            if value:
                return value
        return ""
    return load_text_safe(status_path, 2000)


def summarize_cycle(cycle_dir: Path) -> Dict[str, Any]:
    files = cycle_status_files(cycle_dir)
    scope = load_json_safe(files["scope"]) if files["scope"] else {}
    handoff = load_json_safe(files["handoff"]) if files["handoff"] else {}
    manifest = load_json_safe(files["manifest"]) if files["manifest"] else {}
    closure = load_json_safe(files["closure"]) if files["closure"] else {}
    status_text = _extract_status_text(files["status"])
    status_text_lower = status_text.lower()
    handoff_decision = str(handoff.get("decision") or "").strip()
    closure_decision = str(closure.get("decision") or closure.get("closure_decision") or "").strip()

    if "start_blocked" in status_text_lower:
        current_status = "action_required"
    elif "week1_response_blocked" in status_text_lower or "week2_preparation_blocked" in status_text_lower:
        current_status = "action_required"
    elif "week1_response_ready_with_restrictions" in status_text_lower or "week1_response_ready" in status_text_lower:
        current_status = "week1_ready"
    elif "week1_validation_blocked" in status_text_lower or "week1_intake_blocked" in status_text_lower:
        current_status = "action_required"
    elif "week1_validation_passed" in status_text_lower or "week1_validation_passed_with_restrictions" in status_text_lower:
        current_status = "week2_ready"
    elif "week2_review_passed" in status_text_lower:
        current_status = "approvals_ready"
    elif "approval_readiness_gate_ready" in status_text_lower or "ready_for_manual_approval_review" in status_text_lower:
        current_status = "approvals_ready"
    elif "proposed_approvals_created" in status_text_lower:
        current_status = "approvals_ready"
    elif "week2_preparation_ready_with_restrictions" in status_text_lower or "week2_preparation_ready" in status_text_lower:
        current_status = "week2_ready"
    elif "week1_intake_ready" in status_text_lower or "week1_ready_for_responses" in status_text_lower or "week1_intake_partial" in status_text_lower:
        current_status = "week1_ready"
    elif "intake_activated" in status_text_lower:
        current_status = "intake_ready"
    elif "start_ready" in status_text_lower:
        current_status = "planned"
    elif "action_required" in status_text_lower or "action_required" in handoff_decision.lower() or "action_required" in closure_decision.lower():
        current_status = "action_required"
    elif "closed_success" in status_text_lower or "ready_for_controlled_operation" in handoff_decision.lower() or "success" in closure_decision.lower():
        current_status = "closed_success"
    elif "with_restrictions" in status_text_lower or "restrictions" in handoff_decision.lower() or "restrictions" in closure_decision.lower():
        current_status = "closed_with_restrictions"
    elif "start_ready" in status_text_lower or "planned_not_started" in status_text_lower or scope.get("status") == "PLANNED_NOT_STARTED":
        current_status = "planned"
    elif manifest:
        current_status = "executed"
    else:
        current_status = "intake_ready"

    next_action = {
        "planned": "Planejar Week 1",
        "intake_ready": "Preparar Week 1",
        "week1_ready": "Coletar respostas",
        "week2_ready": "Revisão humana",
        "approvals_ready": "Gerar ApplyPlan dry-run",
        "applyplan_ready": "Executar simulação dry-run",
        "real_write_ready": "Aguardar autorização",
        "executed": "Verificar pós-escrita",
        "closed_success": "Iniciar próximo ciclo",
        "closed_with_restrictions": "Revisar restrições antes de ampliar",
        "action_required": "Bloquear novo ciclo",
    }.get(current_status, "Revisar artefatos")

    key_artifacts = [str(path.relative_to(cycle_dir.parent)) for path in [files["scope"], files["status"], files["handoff"], files["manifest"], files["closure"]] if path]

    return {
        "cycle_id": cycle_dir.name,
        "device": scope.get("device", "unknown"),
        "device_id": scope.get("device_id", "unknown"),
        "current_status": current_status,
        "handoff_decision": handoff_decision,
        "closure_decision": closure_decision,
        "total_items": int(manifest.get("artifact_count") or manifest.get("total_artifacts") or 0),
        "max_items": int(scope.get("max_items") or 0),
        "allowed_methods": scope.get("allowed_methods", []),
        "forbidden_methods": scope.get("forbidden_methods", []),
        "forbidden_targets": scope.get("forbidden_targets", []),
        "requires_week1": bool(scope.get("requires_week1", False)),
        "requires_week2": bool(scope.get("requires_week2", False)),
        "requires_approval_records": bool(scope.get("requires_approval_records", False)),
        "requires_applyplan_dryrun": bool(scope.get("requires_applyplan_dryrun", False)),
        "requires_real_write_authorization": bool(scope.get("requires_real_write_authorization", False)),
        "requires_post_write_verification": bool(scope.get("requires_post_write_verification", False)),
        "next_action": next_action,
        "key_artifacts": key_artifacts,
        "scope_file": str(files["scope"].relative_to(cycle_dir.parent)) if files["scope"] else None,
        "status_file": str(files["status"].relative_to(cycle_dir.parent)) if files["status"] else None,
        "handoff_file": str(files["handoff"].relative_to(cycle_dir.parent)) if files["handoff"] else None,
        "manifest_file": str(files["manifest"].relative_to(cycle_dir.parent)) if files["manifest"] else None,
        "closure_file": str(files["closure"].relative_to(cycle_dir.parent)) if files["closure"] else None,
        "sensitive_hits": scan_sensitive_terms(cycle_dir),
    }


def load_cycle_week1_artifacts(root: Path, cycle_id: str) -> Dict[str, Any]:
    safe_id = safe_cycle_id(cycle_id)
    if not safe_id:
        raise KeyError("invalid cycle id")
    cycle_dir = root / safe_id
    if not cycle_dir.exists():
        cycle_dir = root / "reports" / "controlled-operation" / safe_id
    if not cycle_dir.exists():
        raise KeyError("cycle not found")

    week1_dir = cycle_dir / "week1"
    if not week1_dir.exists():
        week1_dir = cycle_dir

    files = {
        "plan": first_existing(week1_dir, [
            f"{safe_id.upper()}-WEEK1-PLAN.md",
            f"{safe_id}-week1-plan.md",
        ]),
        "status": first_existing(week1_dir, [
            f"{safe_id.upper()}-WEEK1-STATUS.md",
            f"{safe_id}-week1-status.md",
        ]),
        "intake": first_existing(week1_dir, [
            f"{safe_id.upper()}-WEEK1-INTAKE.md",
            f"{safe_id}-week1-intake.md",
        ]),
        "intake_json": first_existing(week1_dir, [
            f"{safe_id}-week1-intake.json",
            f"{safe_id.upper()}-WEEK1-INTAKE.JSON",
        ]),
        "validation": first_existing(week1_dir, [
            f"{safe_id.upper()}-WEEK1-VALIDATION.md",
            f"{safe_id}-week1-validation.md",
        ]),
        "validation_json": first_existing(week1_dir, [
            f"{safe_id}-week1-validation.json",
            f"{safe_id.upper()}-WEEK1-VALIDATION.JSON",
        ]),
        "responses_dir": week1_dir / "responses",
        "audit_dir": week1_dir / "audit",
    }

    def _file_payload(path: Optional[Path]) -> Optional[Dict[str, Any]]:
        if not path or not path.exists():
            return None
        if path.suffix.lower() == ".json":
            return {
                "name": path.name,
                "path": str(path.relative_to(cycle_dir.parent)),
                "content": load_json_safe(path),
            }
        return {
            "name": path.name,
            "path": str(path.relative_to(cycle_dir.parent)),
            "content": load_text_safe(path, 12000),
        }

    intake_json = load_json_safe(files["intake_json"]) if files["intake_json"] else {}
    validation_json = load_json_safe(files["validation_json"]) if files["validation_json"] else {}

    return {
        "cycle_id": safe_id,
        "cycle_dir": str(cycle_dir.relative_to(cycle_dir.parent)),
        "week1_dir": str(week1_dir.relative_to(cycle_dir.parent)),
        "plan_file": _file_payload(files["plan"]),
        "status_file": _file_payload(files["status"]),
        "intake_file": _file_payload(files["intake"]),
        "intake_json_file": _file_payload(files["intake_json"]),
        "validation_file": _file_payload(files["validation"]),
        "validation_json_file": _file_payload(files["validation_json"]),
        "responses_dir": str(files["responses_dir"].relative_to(cycle_dir.parent)) if files["responses_dir"].exists() else None,
        "audit_dir": str(files["audit_dir"].relative_to(cycle_dir.parent)) if files["audit_dir"].exists() else None,
        "intake_summary": intake_json.get("summary", {}),
        "intake_decision": intake_json.get("decision"),
        "validation_summary": validation_json.get("summary", {}),
        "validation_decision": validation_json.get("decision"),
        "command_prepare": f"python3 tools/local/controlled_cycle_week1_prepare_v2.py --cycle-id {safe_id} --device {load_json_safe(cycle_dir / f'{safe_id.upper()}-SCOPE.json').get('device', '4WNET-MNS-KTG-RX')} --device-id {load_json_safe(cycle_dir / f'{safe_id.upper()}-SCOPE.json').get('device_id', '1890')} --cycle-dir reports/controlled-operation/{safe_id} --output-dir reports/controlled-operation/{safe_id}/week1",
        "command_intake": f"python3 tools/local/controlled_cycle_week1_response_intake_v2.py --cycle-id {safe_id} --device 4WNET-MNS-KTG-RX --device-id 1890 --cycle-dir reports/controlled-operation/{safe_id} --responses-dir reports/controlled-operation/{safe_id}/week1/responses --output reports/controlled-operation/{safe_id}/week1/{safe_id.upper()}-WEEK1-INTAKE.md --output-json reports/controlled-operation/{safe_id}/week1/{safe_id}-week1-intake.json",
        "command_validation": f"python3 tools/local/controlled_cycle_week1_validate_v2.py --cycle-id {safe_id} --device 4WNET-MNS-KTG-RX --device-id 1890 --cycle-dir reports/controlled-operation/{safe_id} --responses-dir reports/controlled-operation/{safe_id}/week1/responses --policy-registry policies/compliance --output reports/controlled-operation/{safe_id}/week1/{safe_id.upper()}-WEEK1-VALIDATION.md --output-json reports/controlled-operation/{safe_id}/week1/{safe_id}-week1-validation.json",
    }


def load_cycle_week2_artifacts(root: Path, cycle_id: str) -> Dict[str, Any]:
    safe_id = safe_cycle_id(cycle_id)
    if not safe_id:
        raise KeyError("invalid cycle id")
    cycle_dir = root / safe_id
    if not cycle_dir.exists():
        cycle_dir = root / "reports" / "controlled-operation" / safe_id
    if not cycle_dir.exists():
        raise KeyError("cycle not found")

    week2_dir = cycle_dir / "week2"
    if not week2_dir.exists():
        week2_dir = cycle_dir / "week2-review"

    files = {
        "plan": first_existing(week2_dir, [
            f"{safe_id.upper()}-WEEK2-PLAN.md",
            f"{safe_id}-week2-plan.md",
        ]),
        "board": first_existing(week2_dir, [
            f"{safe_id.upper()}-WEEK2-REVIEW-BOARD.md",
            f"{safe_id}-week2-review-board.md",
            "week2-review-board.md",
        ]),
        "decisions": first_existing(week2_dir, [
            f"{safe_id.upper()}-WEEK2-DECISIONS.csv",
            f"{safe_id}-week2-decisions.csv",
            "week2-review-decisions.csv",
        ]),
        "status": first_existing(week2_dir, [
            f"{safe_id.upper()}-WEEK2-STATUS.md",
            f"{safe_id}-week2-status.md",
            f"{safe_id.upper()}-WEEK2-STATUS.json",
            f"{safe_id}-week2-status.json",
        ]),
        "status_json": first_existing(week2_dir, [
            f"{safe_id.upper()}-WEEK2-STATUS.json",
            f"{safe_id}-week2-status.json",
        ]),
        "drafts_dir": week2_dir / "approval-drafts",
    }

    def _file_payload(path: Optional[Path]) -> Optional[Dict[str, Any]]:
        if not path or not path.exists():
            return None
        if path.suffix.lower() == ".json":
            return {
                "name": path.name,
                "path": str(path.relative_to(cycle_dir.parent)),
                "content": load_json_safe(path),
            }
        return {
            "name": path.name,
            "path": str(path.relative_to(cycle_dir.parent)),
            "content": load_text_safe(path, 12000),
        }

    status_json = load_json_safe(files["status_json"]) if files["status_json"] else {}
    draft_items: List[Dict[str, Any]] = []
    if files["drafts_dir"].exists():
        for draft_file in sorted(files["drafts_dir"].glob("approval-draft-*.json")):
            draft_data = load_json_safe(draft_file)
            if not draft_data:
                continue
            draft_items.append({
                "name": draft_file.name,
                "path": str(draft_file.relative_to(cycle_dir.parent)),
                "object_key": draft_data.get("object_key", ""),
                "object_type": draft_data.get("object_type", ""),
                "team": draft_data.get("responsible_team", draft_data.get("category", "")),
                "status": draft_data.get("status", ""),
                "allowed_to_promote": bool(draft_data.get("allowed_to_promote", False)),
            })

    return {
        "cycle_id": safe_id,
        "cycle_dir": str(cycle_dir.relative_to(cycle_dir.parent)),
        "week2_dir": str(week2_dir.relative_to(cycle_dir.parent)),
        "plan_file": _file_payload(files["plan"]),
        "board_file": _file_payload(files["board"]),
        "decisions_file": _file_payload(files["decisions"]),
        "status_file": _file_payload(files["status"]),
        "status_json_file": _file_payload(files["status_json"]),
        "drafts_dir": str(files["drafts_dir"].relative_to(cycle_dir.parent)) if files["drafts_dir"].exists() else None,
        "status_summary": status_json.get("summary", {}),
        "status_decision": status_json.get("decision"),
        "draft_items": draft_items,
        "command_prepare": f"python3 tools/local/controlled_cycle_week2_prepare_v2.py --cycle-id {safe_id} --device {load_json_safe(cycle_dir / f'{safe_id.upper()}-SCOPE.json').get('device', '4WNET-MNS-KTG-RX')} --device-id {load_json_safe(cycle_dir / f'{safe_id.upper()}-SCOPE.json').get('device_id', '1890')} --cycle-dir reports/controlled-operation/{safe_id} --week1-validation reports/controlled-operation/{safe_id}/week1/{safe_id}-week1-validation.json --output-dir reports/controlled-operation/{safe_id}/week2",
    }


def load_cycle_week2_review_artifacts(root: Path, cycle_id: str) -> Dict[str, Any]:
    safe_id = safe_cycle_id(cycle_id)
    if not safe_id:
        raise KeyError("invalid cycle id")
    cycle_dir = root / "reports" / "controlled-operation" / safe_id
    week2_dir = cycle_dir / "week2"
    review_md = week2_dir / f"{safe_id.upper()}-WEEK2-HUMAN-REVIEW.md"
    review_json = week2_dir / f"{safe_id}-week2-human-review.json"
    return {
        "review_file": {
            "name": review_md.name,
            "path": str(review_md.relative_to(cycle_dir.parent)),
            "content": load_text_safe(review_md, 20000) if review_md.exists() else "",
        } if review_md.exists() else None,
        "review_json_file": {
            "name": review_json.name,
            "path": str(review_json.relative_to(cycle_dir.parent)),
            "content": load_json_safe(review_json) if review_json.exists() else {},
        } if review_json.exists() else None,
        "decision": (load_json_safe(review_json).get("decision") if review_json.exists() else ""),
        "summary": (load_json_safe(review_json).get("summary") if review_json.exists() else {}),
        "has_restrictions": bool(load_json_safe(review_json).get("has_restrictions")) if review_json.exists() else False,
    }


def load_cycle_approvals_artifacts(root: Path, cycle_id: str) -> Dict[str, Any]:
    safe_id = safe_cycle_id(cycle_id)
    if not safe_id:
        raise KeyError("invalid cycle id")
    cycle_dir = root / "reports" / "controlled-operation" / safe_id
    approvals_root = cycle_dir / "approvals"
    approvals_dir = approvals_root / "pending"
    approved_dir = approvals_root / "approved"
    readiness_md = cycle_dir / "approvals" / f"{safe_id.upper()}-APPROVAL-READINESS-GATE.md"
    readiness_json = cycle_dir / "approvals" / f"{safe_id}-approval-readiness-gate.json"
    records: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for candidate_dir in [approvals_dir, approved_dir, approved_dir / "approved"]:
        if not candidate_dir.exists():
            continue
        for json_file in sorted(candidate_dir.glob("*.json")):
            marker = str(json_file.resolve())
            if marker in seen:
                continue
            seen.add(marker)
            record = load_json_safe(json_file)
            if not record:
                continue
            review = record.get("review") or {}
            records.append({
                "name": json_file.name,
                "path": str(json_file.relative_to(cycle_dir.parent)),
                "approval_id": record.get("approval_id") or json_file.stem,
                "object_key": record.get("object_key") or record.get("proposal", {}).get("object_key", ""),
                "object_type": record.get("object_type") or record.get("proposal", {}).get("object_type", ""),
                "status": record.get("status") or "proposed",
                "state": record.get("state") or "proposed",
                "reviewer": review.get("reviewed_by") or "",
                "reviewed_at": review.get("reviewed_at") or "",
                "origin": record.get("source_week2_review") or record.get("source_draft") or "",
                "safety": record.get("safety_confirmations") or {},
            })
    return {
        "approvals_dir": str(approvals_dir.relative_to(cycle_dir.parent)) if approvals_dir.exists() else None,
        "approved_dir": str(approved_dir.relative_to(cycle_dir.parent)) if approved_dir.exists() else None,
        "readiness_file": {
            "name": readiness_md.name,
            "path": str(readiness_md.relative_to(cycle_dir.parent)),
            "content": load_text_safe(readiness_md, 20000) if readiness_md.exists() else "",
        } if readiness_md.exists() else None,
        "readiness_json_file": {
            "name": readiness_json.name,
            "path": str(readiness_json.relative_to(cycle_dir.parent)),
            "content": load_json_safe(readiness_json) if readiness_json.exists() else {},
        } if readiness_json.exists() else None,
        "readiness_decision": (load_json_safe(readiness_json).get("decision") if readiness_json.exists() else ""),
        "readiness_summary": (load_json_safe(readiness_json).get("summary") if readiness_json.exists() else {}),
        "records": records,
    }


def load_cycle_dryrun_applyplan_artifacts(root: Path, cycle_id: str) -> Dict[str, Any]:
    safe_id = safe_cycle_id(cycle_id)
    if not safe_id:
        raise KeyError("invalid cycle id")
    cycle_dir = root / "reports" / "controlled-operation" / safe_id
    applyplan_dir = cycle_dir / "apply-plans" / "dry-run"
    generation_md = cycle_dir / "apply-plans" / f"{safe_id.upper()}-DRYRUN-APPLYPLAN-GENERATION.md"
    generation_json = cycle_dir / "apply-plans" / f"{safe_id}-dryrun-applyplan-generation.json"
    validation_md = cycle_dir / "apply-plans" / f"{safe_id.upper()}-DRYRUN-APPLYPLAN-VALIDATION.md"
    validation_json = cycle_dir / "apply-plans" / f"{safe_id}-dryrun-applyplan-validation.json"
    plans: List[Dict[str, Any]] = []
    if applyplan_dir.exists():
        for json_file in sorted(applyplan_dir.glob("*.json")):
            plan = load_json_safe(json_file)
            if not plan:
                continue
            plans.append({
                "name": json_file.name,
                "path": str(json_file.relative_to(cycle_dir.parent)),
                "apply_plan_id": plan.get("apply_plan_id") or json_file.stem,
                "mode": plan.get("mode") or "",
                "status": plan.get("status") or "",
                "generated_at": plan.get("generated_at") or "",
                "item_count": len(plan.get("items") or []),
                "source_approval_records": plan.get("source_approval_records") or [],
                "execution_policy": plan.get("execution_policy") or {},
            })
    return {
        "applyplans_dir": str(applyplan_dir.relative_to(cycle_dir.parent)) if applyplan_dir.exists() else None,
        "generation_file": {
            "name": generation_md.name,
            "path": str(generation_md.relative_to(cycle_dir.parent)),
            "content": load_text_safe(generation_md, 20000) if generation_md.exists() else "",
        } if generation_md.exists() else None,
        "generation_json_file": {
            "name": generation_json.name,
            "path": str(generation_json.relative_to(cycle_dir.parent)),
            "content": load_json_safe(generation_json) if generation_json.exists() else {},
        } if generation_json.exists() else None,
        "validation_file": {
            "name": validation_md.name,
            "path": str(validation_md.relative_to(cycle_dir.parent)),
            "content": load_text_safe(validation_md, 20000) if validation_md.exists() else "",
        } if validation_md.exists() else None,
        "validation_json_file": {
            "name": validation_json.name,
            "path": str(validation_json.relative_to(cycle_dir.parent)),
            "content": load_json_safe(validation_json) if validation_json.exists() else {},
        } if validation_json.exists() else None,
        "generation_decision": (load_json_safe(generation_json).get("decision") if generation_json.exists() else ""),
        "validation_decision": (load_json_safe(validation_json).get("decision") if validation_json.exists() else ""),
        "plans": plans,
    }


def load_cycle_real_write_chain_artifacts(root: Path, cycle_id: str) -> Dict[str, Any]:
    safe_id = safe_cycle_id(cycle_id)
    if not safe_id:
        raise KeyError("invalid cycle id")
    cycle_dir = root / "reports" / "controlled-operation" / safe_id
    approved_dir = cycle_dir / "approvals" / "approved"
    compat_approved_dir = approved_dir / "approved"
    auth_dir = cycle_dir / "real-write-authorization"
    exec_dir = cycle_dir / "real-write-execution"
    closure_dir = exec_dir / "closure"

    def _payload(path: Path) -> Optional[Dict[str, Any]]:
        if not path.exists():
            return None
        if path.suffix.lower() == ".json":
            return {
                "name": path.name,
                "path": str(path.relative_to(cycle_dir.parent)),
                "content": load_json_safe(path),
            }
        return {
            "name": path.name,
            "path": str(path.relative_to(cycle_dir.parent)),
            "content": load_text_safe(path, 20000),
        }

    approved_records: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for candidate_dir in [approved_dir, compat_approved_dir]:
        if not candidate_dir.exists():
            continue
        for record_file in sorted(candidate_dir.glob("*.json")):
            marker = str(record_file.resolve())
            if marker in seen:
                continue
            seen.add(marker)
            record = load_json_safe(record_file)
            if not record:
                continue
            approved_records.append({
                "name": record_file.name,
                "path": str(record_file.relative_to(cycle_dir.parent)),
                "approval_id": record.get("approval_id") or record_file.stem,
                "status": record.get("status") or "",
                "state": record.get("state") or "",
                "approved_by": record.get("approved_by") or "",
                "approved_at": record.get("approved_at") or "",
                "approval_reason": record.get("approval_reason") or "",
                "evidence_hash": record.get("evidence_hash") or "",
                "proposed_payload": record.get("proposed_payload") or {},
                "state_history": record.get("state_history") or [],
            })

    return {
        "approved_dir": str(approved_dir.relative_to(cycle_dir.parent)) if approved_dir.exists() else None,
        "approved_records": approved_records,
        "dryrun_execution_gate_file": _payload(cycle_dir / "apply-plans" / f"{safe_id.upper()}-DRYRUN-EXECUTION-GATE.md"),
        "dryrun_execution_gate_json_file": _payload(cycle_dir / "apply-plans" / f"{safe_id}-dryrun-execution-gate.json"),
        "simulation_file": _payload(cycle_dir / "apply-plans" / f"{safe_id.upper()}-DRYRUN-SIMULATION-RESULT.md"),
        "simulation_json_file": _payload(cycle_dir / "apply-plans" / f"{safe_id}-dryrun-simulation-result.json"),
        "readiness_file": _payload(cycle_dir / "apply-plans" / f"{safe_id.upper()}-REAL-WRITE-READINESS-GATE.md"),
        "readiness_json_file": _payload(cycle_dir / "apply-plans" / f"{safe_id}-real-write-readiness-gate.json"),
        "authorization_report_file": _payload(auth_dir / f"{safe_id.upper()}-REAL-WRITE-AUTHORIZATION-PACKAGE.md"),
        "authorization_request_file": _payload(auth_dir / "authorization_request.json"),
        "preflight_report_file": _payload(auth_dir / f"{safe_id.upper()}-REAL-WRITE-FINAL-PREFLIGHT-GATE.md"),
        "preflight_json_file": _payload(auth_dir / f"{safe_id}-real-write-final-preflight-gate.json"),
        "execution_report_file": _payload(exec_dir / f"{safe_id.upper()}-REAL-WRITE-EXECUTION-PACKAGE.md"),
        "execution_package_file": _payload(exec_dir / "execution_package.json"),
        "execution_validation_file": _payload(exec_dir / f"{safe_id.upper()}-REAL-WRITE-EXECUTION-PACKAGE-VALIDATION.md"),
        "execution_validation_json_file": _payload(exec_dir / f"{safe_id}-real-write-execution-package-validation.json"),
        "freeze_report_file": _payload(exec_dir / f"{safe_id.upper()}-FINAL-NO-WRITE-FREEZE-CHECK.md"),
        "freeze_json_file": _payload(exec_dir / f"{safe_id}-final-no-write-freeze-check.json"),
        "execution_result_file": _payload(exec_dir / f"{safe_id.upper()}-REAL-WRITE-EXECUTION-RESULT.md"),
        "execution_result_json_file": _payload(exec_dir / f"{safe_id.upper()}-REAL-WRITE-EXECUTION-RESULT.json"),
        "post_write_verification_file": _payload(exec_dir / f"{safe_id.upper()}-POST-WRITE-VERIFICATION-RESULT.md"),
        "post_write_verification_json_file": _payload(exec_dir / f"{safe_id.upper()}-POST-WRITE-VERIFICATION-RESULT.json"),
        "post_write_compliance_file": _payload(exec_dir / f"{safe_id.upper()}-POST-WRITE-COMPLIANCE-RERUN.md"),
        "post_write_compliance_json_file": _payload(exec_dir / f"{safe_id.upper()}-POST-WRITE-COMPLIANCE-RERUN.json"),
        "closure_report_file": _payload(closure_dir / f"{safe_id.upper()}-CLOSURE-PACKAGE.md"),
        "closure_json_file": _payload(closure_dir / f"{safe_id}-closure-summary.json"),
    }


def list_controlled_cycles(root: Path) -> List[Dict[str, Any]]:
    base = root
    if not base.exists():
        return []
    if not any(d.is_dir() and d.name.startswith("cycle-") for d in base.iterdir()):
        candidate = root / "reports" / "controlled-operation"
        if candidate.exists():
            base = candidate
    if not base.exists():
        return []
    cycles = [d for d in base.iterdir() if d.is_dir() and d.name.startswith("cycle-")]
    return sorted((summarize_cycle(cycle_dir) for cycle_dir in cycles), key=lambda x: x["cycle_id"])


def load_controlled_operation_index(root: Path) -> Dict[str, Any]:
    candidates = [
        root / "controlled-operation-index.json",
        root / "reports" / "controlled-operation" / "controlled-operation-index.json",
    ]
    for index_path in candidates:
        if index_path.exists():
            data = load_json_safe(index_path)
            if data:
                return data
    cycles = list_controlled_cycles(root)
    return {
        "measured_at": "",
        "total_cycles": len(cycles),
        "overall_status": "IN_PROGRESS" if cycles else "UNKNOWN",
        "cycles": cycles,
    }


def load_cycle_artifact(root: Path, cycle_id: str, artifact: str) -> Dict[str, Any]:
    safe_id = safe_cycle_id(cycle_id)
    if not safe_id:
        raise KeyError("invalid cycle id")
    cycle_dir = root / safe_id
    if not cycle_dir.exists():
        cycle_dir = root / "reports" / "controlled-operation" / safe_id
    if not cycle_dir.exists():
        raise KeyError("cycle not found")

    files = cycle_status_files(cycle_dir)
    mapping = {
        "start-gate": first_existing(cycle_dir, [f"{safe_id.upper()}-START-GATE.md", f"{safe_id}-start-gate.md"]),
        "archive": files["manifest"] or first_existing(cycle_dir, ["final-archive/ARCHIVE.md", "real-write-execution/archive/ARCHIVE.md"]),
        "handoff": files["handoff"],
        "status": files["status"],
    }
    path = mapping.get(artifact)
    if not path or not path.exists():
        raise KeyError("artifact not found")
    return {
        "path": path,
        "content": load_text_safe(path, 20000),
        "name": path.name,
    }
