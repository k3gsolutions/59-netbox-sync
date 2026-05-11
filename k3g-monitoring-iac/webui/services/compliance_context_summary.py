"""Human summary builder for operational compliance contexts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .compliance_context_classifier import classify_job_contexts
from .compliance_context_standard_validator import STATUS_LABELS, validate_job_contexts
from .compliance_jobs import JOBS_BASE


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _safe_job_dir(job_id: str, jobs_base: Optional[Path] = None) -> Path:
    return (jobs_base or JOBS_BASE) / job_id


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def build_context_summary(job_id: str, jobs_base: Optional[Path] = None) -> dict[str, Any]:
    """Generate analysis/context-summary.json from context validation."""
    job_dir = _safe_job_dir(job_id, jobs_base)
    inventory = _load_json(job_dir / "analysis" / "context-inventory.json") or classify_job_contexts(job_id, jobs_base)
    validation = _load_json(job_dir / "analysis" / "context-validation.json") or validate_job_contexts(job_id, jobs_base)

    contexts: dict[str, dict[str, Any]] = {}
    for device in validation.get("devices") or []:
        for context in device.get("contexts") or []:
            context_id = str(context.get("context_id") or "")
            bucket = contexts.setdefault(
                context_id,
                {
                    "context_id": context_id,
                    "label": context.get("label"),
                    "description": context.get("description"),
                    "optional": bool(context.get("optional")),
                    "devices": 0,
                    "items_count": 0,
                    "statuses": {key: 0 for key in STATUS_LABELS},
                    "status_label": context.get("status_label"),
                    "human_summary": "",
                },
            )
            bucket["devices"] += 1
            bucket["items_count"] += int(context.get("items_count") or 0)
            status = str(context.get("status") or "")
            bucket["statuses"][status] = bucket["statuses"].get(status, 0) + 1
            if status != "WITHIN_STANDARD":
                bucket["status_label"] = context.get("status_label")
    for bucket in contexts.values():
        bucket["human_summary"] = _human_context_summary(bucket)

    payload = {
        "job_id": job_id,
        "generated_at": _now(),
        "layer": "post_parser_pre_compare",
        "summary": {
            "devices": len(validation.get("devices") or []),
            "contexts_total": sum(sum(bucket["statuses"].values()) for bucket in contexts.values()),
            "statuses": validation.get("summary", {}).get("statuses") or {},
        },
        "contexts": list(contexts.values()),
        "inventory_summary": inventory.get("summary") or {},
        "safety": {
            "netbox_write": False,
            "sync_called": False,
            "apply_plan_created": False,
            "approval_record_created": False,
            "ssh_write": False,
            "config_mode": False,
            "netconf_write": False,
            "snmp_write": False,
        },
        "files": {"context_summary": str(job_dir / "analysis" / "context-summary.json")},
    }
    _dump_json(job_dir / "analysis" / "context-summary.json", payload)
    return payload


def _human_context_summary(bucket: dict[str, Any]) -> str:
    label = bucket.get("label") or bucket.get("context_id")
    items_count = int(bucket.get("items_count") or 0)
    statuses = bucket.get("statuses") or {}
    if statuses.get("OUT_OF_STANDARD"):
        return f"{label}: existe diferenca frente ao padrao declarado."
    if statuses.get("NEEDS_STANDARDIZATION"):
        return f"{label}: precisa de padrao operacional mais claro antes de validar automaticamente."
    if statuses.get("INFORMATIONAL_ALERT"):
        return f"{label}: alerta informativo, sem bloqueio do fluxo."
    return f"{label}: {items_count} item(ns) dentro do padrao conhecido."
