"""
Web UI for k3g-monitoring-iac — Read-only compliance and governance dashboard.

No writes, no tokens. NetBox API: GET-only /api/dcim/devices/.
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
try:
    from fastapi.templating import Jinja2Templates
except ImportError:
    class Jinja2Templates:  # type: ignore
        """Fallback when jinja2 is unavailable in the local test environment."""

        def __init__(self, directory=None):
            self.directory = directory

        def TemplateResponse(self, template_name, context):
            title = context.get("title", template_name)
            body = (
                "<html><body>"
                f"<h1>{title}</h1>"
                f"<p>Template fallback: {template_name}</p>"
                "</body></html>"
            )
            return HTMLResponse(body)
from starlette.requests import Request
import csv
import hashlib
import re
from pathlib import Path
import json
import mimetypes
from typing import Optional
from datetime import datetime, timezone

from .services.artifact_scanner import (
    list_reports, list_devices, list_approvals, list_apply_plans,
    list_batch_results, list_incidents, list_comparisons, list_proposed_approvals, safe_resolve_path,
    safe_resolve_download_path, normalize_report_path
)
from .services.markdown_loader import load_markdown, render_markdown, load_json
from .services.report_index import load_index, get_latest_report, parse_report_metrics
from .services.week2_decision_handler import Week2Decision, save_decision, load_decisions, get_item_decision
from .services.controlled_operation import (
    load_controlled_operation_index,
    load_cycle_artifact,
    load_cycle_approvals_artifacts,
    load_cycle_dryrun_applyplan_artifacts,
    load_cycle_real_write_chain_artifacts,
    load_cycle_week2_review_artifacts,
    load_cycle_week1_artifacts,
    load_cycle_week2_artifacts,
    safe_cycle_id,
    list_controlled_cycles,
)
from .services.netbox_client import (
    get_netbox_client,
    NetBoxNotConfiguredError,
    NetBoxAuthError,
    NetBoxClientError,
)
from .services.compliance_candidates import (
    list_compliance_candidates,
    is_compliance_candidate,
)
from .services.compliance_jobs import (
    create_collection_plan,
    create_collection_start_gate,
    create_compliance_job,
    get_compliance_job_safety,
    list_compliance_jobs,
    load_collection_artifacts,
    load_compliance_job,
)
from .services.compliance_compare import compare_job
from .services.compliance_huawei_ne8000_parser import parse_job_collection
from .services.compliance_parser_validation import validate_parser_outputs
from .services.compliance_collection import execute_collection_job
from .services.compliance_raw_validation import validate_raw_collection_outputs
from .services.compliance_ssh_collection import execute_ssh_readonly_collection
from .services.compliance_ssh_preflight import run_ssh_preflight


# Setup
ROOT = Path(__file__).parent.parent
REPORTS_DIR = ROOT / "reports"

app = FastAPI(title="k3g Compliance & Governance", version="3.0")

# Static files
static_dir = Path(__file__).parent / "static"
if not static_dir.exists():
    static_dir = Path.cwd() / "webui" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Templates
template_dir = Path(__file__).parent / "templates"
if not template_dir.exists():
    # Fallback if running from different directory
    template_dir = Path.cwd() / "webui" / "templates"
templates = Jinja2Templates(directory=template_dir)
if hasattr(templates, "env"):
    templates.env.filters["status_label"] = lambda value: status_label(value)


def status_label(status: str) -> str:
    labels = {
        "pending": "Pendente",
        "not_sent": "Não enviado",
        "sent": "Enviado",
        "response_missing": "Aguardando resposta",
        "partial_response": "Resposta parcial",
        "complete": "Completo",
        "overdue": "Atrasado",
        "escalation_required": "Precisa escalonar",
        "answered": "Respondido",
        "validated": "Validado",
        "ready_for_review": "Pronto para revisão",
        "needs_clarification": "Precisa de esclarecimento",
        "blocked": "Bloqueado",
        "rejected": "Rejeitado",
        "still_pending": "Ainda pendente",
        "proposed": "Proposto",
        "approved": "Aprovado",
        "changes-requested": "Solicitado ajuste",
        "applied": "Aplicado",
        "failed": "Falhou",
        "no_go": "Não liberado",
        "go": "Liberado",
        "go_with_restrictions": "Liberado com restrições",
        "go_week2_review": "Liberado para Semana 2",
        "go_with_restrictions_uat_present": "Liberado com restrições UAT",
        "keep_as_real": "Manter como real",
        "week1_response_ready": "Resposta da Semana 1 pronta",
        "week1_response_ready_with_restrictions": "Resposta da Semana 1 pronta com restrições",
        "week1_response_blocked": "Resposta da Semana 1 bloqueada",
        "week2_preparation_ready": "Semana 2 preparada",
        "week2_preparation_ready_with_restrictions": "Semana 2 preparada com restrições",
        "week2_preparation_blocked": "Semana 2 bloqueada",
        "week2_review_passed": "Revisão da Semana 2 aprovada",
        "week2_review_passed_with_restrictions": "Revisão da Semana 2 com restrições",
        "week2_review_blocked": "Revisão da Semana 2 bloqueada",
        "pending_review": "Pendente de revisão",
        "proposed_approvals_created": "Registros propostos criados",
        "proposed_approvals_created_with_restrictions": "Registros propostos criados com restrições",
        "no_proposed_approvals_created": "Nenhum registro proposto criado",
        "ready_for_manual_approval_review": "Pronto para revisão manual de aprovação",
        "ready_with_restrictions": "Pronto para revisão com restrições",
        "not_ready_for_manual_approval_review": "Não pronto para revisão manual",
        "cycle_approval_review_approved": "Revisão de aprovação aprovada",
        "cycle_approval_review_with_restrictions": "Revisão de aprovação com restrições",
        "cycle_approval_review_blocked": "Revisão de aprovação bloqueada",
        "cycle_dryrun_applyplan_generated": "ApplyPlan dry-run gerado",
        "cycle_dryrun_applyplan_valid": "ApplyPlan dry-run válido",
        "cycle_dryrun_applyplan_valid_with_warnings": "ApplyPlan dry-run válido com avisos",
        "cycle_dryrun_applyplan_invalid": "ApplyPlan dry-run inválido",
        "cycle_dryrun_execution_ready": "Gate dry-run pronto",
        "cycle_dryrun_execution_ready_with_restrictions": "Gate dry-run pronto com restrições",
        "cycle_dryrun_execution_blocked": "Gate dry-run bloqueado",
        "cycle_dryrun_simulation_passed": "Simulação dry-run aprovada",
        "cycle_dryrun_simulation_passed_with_warnings": "Simulação dry-run aprovada com avisos",
        "cycle_dryrun_simulation_failed": "Simulação dry-run falhou",
        "cycle_ready_for_real_write_review": "Pronto para revisão de escrita real",
        "cycle_ready_with_restrictions": "Pronto com restrições",
        "cycle_not_ready_for_real_write": "Não pronto para escrita real",
        "cycle_ready_for_real_write_execution_package": "Pacote de execução pronto",
        "cycle_ready_for_real_write_phase": "Pronto para fase real",
        "cycle_not_ready_for_real_write_phase": "Não pronto para fase real",
        "cycle_real_write_execution_package_valid": "Pacote de execução válido",
        "cycle_real_write_execution_package_valid_with_warnings": "Pacote de execução válido com avisos",
        "cycle_real_write_execution_package_invalid": "Pacote de execução inválido",
        "cycle_real_write_aborted_preflight_failed": "Execução real abortada na pré-validação",
        "cycle_real_write_success": "Escrita real concluída",
        "cycle_real_write_partial_failed": "Escrita real parcial com falha",
        "cycle_real_write_failed": "Escrita real falhou",
        "cycle_post_write_verification_passed": "Verificação pós-escrita aprovada",
        "cycle_post_write_verification_passed_with_drift": "Verificação pós-escrita com drift",
        "cycle_post_write_verification_failed": "Verificação pós-escrita falhou",
        "cycle_post_write_verification_not_applicable": "Verificação pós-escrita não aplicável",
        "cycle_post_write_compliance_passed": "Compliance pós-escrita aprovada",
        "cycle_post_write_compliance_passed_with_warnings": "Compliance pós-escrita com avisos",
        "cycle_post_write_compliance_failed": "Compliance pós-escrita falhou",
        "cycle_post_write_compliance_not_applicable": "Compliance pós-escrita não aplicável",
        "cycle_closed_success": "Ciclo encerrado com sucesso",
        "cycle_closed_with_warnings": "Ciclo encerrado com avisos",
        "cycle_closed_action_required": "Ciclo precisa de ação",
        "cycle_closed_not_applicable": "Ciclo não aplicável",
        "planned": "Planejado",
        "intake_ready": "Pronto para intake",
        "intake_activated": "Intake ativado",
        "intake_activated_with_restrictions": "Intake ativado com restrições",
        "week1_ready_for_responses": "Semana 1 pronta para respostas",
        "week1_intake_ready": "Intake da Semana 1 pronto",
        "week1_intake_partial": "Intake parcial da Semana 1",
        "week1_intake_blocked": "Intake bloqueado da Semana 1",
        "week1_validation_passed": "Validação da Semana 1 aprovada",
        "week1_validation_passed_with_restrictions": "Validação da Semana 1 com restrições",
        "week1_validation_blocked": "Validação da Semana 1 bloqueada",
        "in_progress": "Em andamento",
        "closed_success": "Encerrado com sucesso",
        "closed_with_restrictions": "Encerrado com restrições",
        "start_ready": "Pronto para iniciar",
        "start_blocked": "Bloqueado para início",
        "action_required": "Ação obrigatória",
    }
    value = (status or "").strip()
    return labels.get(value, value.replace("_", " ").title() if value else "N/A")


# ============================================================================
# Dashboard
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Dashboard home page."""
    latest_report = get_latest_report(ROOT)
    reports = list_reports(ROOT)
    devices = list_devices(ROOT)
    approvals = list_approvals(ROOT)
    batch_results = list_batch_results(ROOT)
    incidents = list_incidents(ROOT)
    apply_plans = list_apply_plans(ROOT)

    # Count by approval status
    approvals_pending = sum(1 for a in approvals if "pending" in a.get("path", ""))
    approvals_approved = sum(1 for a in approvals if "approved" in a.get("path", ""))

    # Batch results status
    latest_batch = batch_results[0] if batch_results else None
    batch_noop = sum(1 for b in batch_results if "NO-OP" in b.get("name", "") or "already" in b.get("name", "").lower())
    week1_execution = _week1_execution_overview("4WNET-MNS-KTG-RX")
    week2_review = _week2_review_overview("4WNET-MNS-KTG-RX")
    controlled_operation = _controlled_operation_overview()

    context = {
        "request": request,
        "title": "Compliance Dashboard",
        "total_devices": len(devices),
        "total_reports": len(reports),
        "total_approvals": len(approvals),
        "total_incidents": len(incidents),
        "total_batch_results": len(batch_results),
        "total_apply_plans": len(apply_plans),
        "approvals_pending": approvals_pending,
        "approvals_approved": approvals_approved,
        "batch_noop_count": batch_noop,
        "latest_report": latest_report,
        "latest_batch": latest_batch,
        "week1_execution": week1_execution,
        "week2_review": week2_review,
        "controlled_operation": controlled_operation,
    }

    return templates.TemplateResponse("index.html", context)


# ============================================================================
# Devices
# ============================================================================

@app.get("/devices", response_class=HTMLResponse)
async def devices_list(request: Request):
    """List all devices with history."""
    devices = list_devices(ROOT)

    context = {
        "request": request,
        "title": "Devices",
        "devices": devices,
    }

    return templates.TemplateResponse("devices.html", context)


@app.get("/devices/{device}", response_class=HTMLResponse)
async def device_detail(request: Request, device: str):
    """Device detail page."""
    # Load device history if available
    history_path = REPORTS_DIR / "pilot-device-compliance" / "history" / f"{device}.json"
    history = load_json(history_path) if history_path.exists() else None

    # Find related approvals
    approvals = list_approvals(ROOT)
    related_approvals = [a for a in approvals if device in a["path"]][:5]

    context = {
        "request": request,
        "title": f"Device: {device}",
        "device": device,
        "history": history,
        "related_approvals": related_approvals,
    }

    return templates.TemplateResponse("device.html", context)


# ============================================================================
# Reports
# ============================================================================

@app.get("/reports/view", response_class=HTMLResponse)
async def view_report(request: Request, path: str = Query(...)):
    """View markdown report safely."""
    # Normalize path (accepts both "file.md" and "reports/file.md")
    normalized = normalize_report_path(path)
    if not normalized:
        return HTMLResponse("<h1>Invalid path</h1>", status_code=400)

    resolved = safe_resolve_path(REPORTS_DIR, normalized)

    if not resolved or not resolved.exists():
        return HTMLResponse("<h1>Report not found</h1>", status_code=404)

    content = load_markdown(resolved)
    if not content:
        return HTMLResponse("<h1>Could not load report</h1>", status_code=400)

    html_content = render_markdown(content)

    context = {
        "request": request,
        "title": "Report",
        "report_path": path,
        "html_content": html_content,
    }

    return templates.TemplateResponse("report_view.html", context)


@app.get("/reports/download")
async def download_report(path: str = Query(...)):
    """Download markdown report safely."""
    normalized = normalize_report_path(path)
    if not normalized:
        return JSONResponse({"error": "Invalid path"}, status_code=400)

    resolved = safe_resolve_download_path(REPORTS_DIR, normalized)
    if not resolved:
        candidate = safe_resolve_path(REPORTS_DIR, normalized)
        if not candidate or not candidate.exists():
            return JSONResponse({"error": "File not found"}, status_code=404)
        return JSONResponse({"error": "File type not allowed"}, status_code=403)

    suffix = resolved.suffix.lower()
    media_type = {
        ".csv": "text/csv",
        ".md": "text/markdown",
        ".json": "application/json",
        ".txt": "text/plain",
        ".log": "text/plain",
    }.get(suffix, mimetypes.guess_type(resolved.name)[0] or "text/plain")
    return FileResponse(resolved, media_type=media_type, filename=resolved.name)


# ============================================================================
# Comparisons
# ============================================================================

@app.get("/comparisons", response_class=HTMLResponse)
async def comparisons_list(request: Request):
    """List device comparisons."""
    comparisons = list_comparisons(ROOT)

    context = {
        "request": request,
        "title": "Comparisons",
        "comparisons": comparisons,
    }

    return templates.TemplateResponse("comparisons.html", context)


# ============================================================================
# Approvals
# ============================================================================

@app.get("/approvals", response_class=HTMLResponse)
async def approvals_list(request: Request, status: Optional[str] = Query(None)):
    """List all approval records with optional status filter."""
    all_approvals = list_approvals(ROOT)

    # Filter by status if specified (pending, approved, rejected, etc.)
    if status:
        all_approvals = [a for a in all_approvals if status.lower() in a.get("path", "").lower()]

    context = {
        "request": request,
        "title": "Approvals",
        "approvals": all_approvals,
        "filter_status": status,
    }

    return templates.TemplateResponse("approvals.html", context)


@app.get("/approvals/{approval_id}", response_class=HTMLResponse)
async def approval_detail(request: Request, approval_id: str):
    """View single approval record."""
    approvals = list_approvals(ROOT)
    approval = None

    for a in approvals:
        if approval_id in a["name"]:
            resolved = safe_resolve_path(REPORTS_DIR, a["path"])
            if resolved:
                approval_data = load_json(resolved)
                if approval_data:
                    approval = {
                        "id": approval_id,
                        "data": approval_data,
                        "path": a["path"],
                        "status": a["status"],
                    }
                break

    if not approval:
        return HTMLResponse("<h1>Approval not found</h1>", status_code=404)

    context = {
        "request": request,
        "title": f"Approval: {approval_id}",
        "approval": approval,
    }

    return templates.TemplateResponse("approval_view.html", context)


# ============================================================================
# Apply Plans
# ============================================================================

@app.get("/apply-plans", response_class=HTMLResponse)
async def apply_plans_list(request: Request, readiness: Optional[str] = Query(None)):
    """List apply plans with optional readiness filter."""
    all_plans = list_apply_plans(ROOT)

    # Filter by readiness if specified (ready, blocked, etc.)
    if readiness:
        all_plans = [p for p in all_plans if readiness.lower() in p.get("name", "").lower()]

    context = {
        "request": request,
        "title": "Apply Plans",
        "apply_plans": all_plans,
        "filter_readiness": readiness,
    }

    return templates.TemplateResponse("apply_plans.html", context)


# ============================================================================
# Batch Results
# ============================================================================

@app.get("/batch-results", response_class=HTMLResponse)
async def batch_results_list(request: Request, result: Optional[str] = Query(None)):
    """List batch apply results with optional filter."""
    all_results = list_batch_results(ROOT)

    # Filter by result if specified
    if result:
        all_results = [r for r in all_results if result.lower() in r.get("name", "").lower()]

    context = {
        "request": request,
        "title": "Batch Results",
        "results": all_results,
        "filter_result": result,
    }

    return templates.TemplateResponse("batch_results.html", context)


@app.get("/batch-results/{batch_id}", response_class=HTMLResponse)
async def batch_result_detail(request: Request, batch_id: str):
    """View single batch result detail."""
    all_results = list_batch_results(ROOT)
    batch_result = None

    for b in all_results:
        if batch_id in b["name"] or batch_id in b.get("path", ""):
            resolved = safe_resolve_path(REPORTS_DIR, b["path"])
            if resolved and resolved.exists():
                content = load_markdown(resolved)
                html_content = render_markdown(content)
                batch_result = {
                    "id": batch_id,
                    "name": b["name"],
                    "path": b["path"],
                    "content": html_content,
                }
                break

    if not batch_result:
        return HTMLResponse("<h1>Batch result not found</h1>", status_code=404)

    context = {
        "request": request,
        "title": f"Batch: {batch_id}",
        "batch": batch_result,
    }

    return templates.TemplateResponse("batch_result_detail.html", context)


# ============================================================================
# Incidents
# ============================================================================

@app.get("/incidents", response_class=HTMLResponse)
async def incidents_list(request: Request):
    """List incident reports."""
    incidents = list_incidents(ROOT)

    context = {
        "request": request,
        "title": "Incidents",
        "incidents": incidents,
    }

    return templates.TemplateResponse("incidents.html", context)


# ============================================================================
# Search
# ============================================================================

@app.get("/search", response_class=HTMLResponse)
async def search(request: Request, q: str = Query(...)):
    """Search across markdown files with line numbers and highlighting."""
    results = []

    docs_dirs = [
        ROOT / "reports",
        ROOT / "docs",
        ROOT / "context",
    ]

    for docs_dir in docs_dirs:
        if not docs_dir.exists():
            continue

        for md_file in docs_dir.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                if q.lower() in content.lower():
                    # Find matching lines with line numbers
                    lines = content.split("\n")
                    matching_lines = [
                        {
                            "line_num": i + 1,
                            "text": line,
                            "highlighted": line.replace(q, f"<mark>{q}</mark>") if q.lower() in line.lower() else line
                        }
                        for i, line in enumerate(lines)
                        if q.lower() in line.lower()
                    ]

                    rel_path = md_file.relative_to(ROOT)
                    if matching_lines:
                        results.append({
                            "file": str(rel_path),
                            "path": str(rel_path),
                            "matches": len(matching_lines),
                            "lines": matching_lines[:3],  # Show first 3 matches
                            "preview": matching_lines[0]["text"][:150] if matching_lines else "",
                        })
            except Exception:
                pass

    # Sort by match count descending
    results.sort(key=lambda x: x["matches"], reverse=True)

    context = {
        "request": request,
        "title": "Search Results",
        "query": q,
        "results": results[:50],
        "total": len(results),
    }

    return templates.TemplateResponse("search.html", context)


# ============================================================================
# Approval Queue & Timeline
# ============================================================================

@app.get("/approval-queue", response_class=HTMLResponse)
async def approval_queue(request: Request, status: Optional[str] = Query(None), device: Optional[str] = Query(None)):
    """Approval queue with status and device filters."""
    all_approvals = list_approvals(ROOT)
    proposed_approvals = list_proposed_approvals(ROOT)

    # Apply filters
    filtered = all_approvals
    if status:
        filtered = [a for a in filtered if status.lower() in a.get("path", "").lower()]
    if device:
        filtered = [a for a in filtered if device.lower() in a.get("path", "").lower()]

    # Group by status
    pending = [a for a in filtered if "pending" in a.get("path", "")]
    approved = [a for a in filtered if "approved" in a.get("path", "")]
    applied = [a for a in filtered if "applied" in a.get("path", "")]
    rejected = [a for a in filtered if "rejected" in a.get("path", "")]

    context = {
        "request": request,
        "title": "Approval Queue",
        "pending": pending,
        "approved": approved,
        "applied": applied,
        "rejected": rejected,
        "proposed_approvals": proposed_approvals,
        "filter_status": status,
        "filter_device": device,
        "total": len(filtered),
    }

    return templates.TemplateResponse("approval_queue.html", context)


@app.get("/approval-timeline/{approval_id}", response_class=HTMLResponse)
async def approval_timeline(request: Request, approval_id: str):
    """View approval timeline with state history."""
    all_approvals = list_approvals(ROOT)
    approval = None

    for a in all_approvals:
        if approval_id in a["name"] or approval_id in a.get("path", ""):
            resolved = safe_resolve_path(REPORTS_DIR, a["path"])
            if resolved and resolved.exists():
                approval_data = load_json(resolved)
                if approval_data:
                    approval = {
                        "id": approval_id,
                        "data": approval_data,
                        "path": a["path"],
                        "status": a["status"],
                    }
                break

    if not approval:
        return HTMLResponse("<h1>Approval not found</h1>", status_code=404)

    context = {
        "request": request,
        "title": f"Approval Timeline: {approval_id}",
        "approval": approval,
    }

    return templates.TemplateResponse("approval_timeline.html", context)


# ============================================================================
# Service Engagement
# ============================================================================

@app.get("/service-engagement", response_class=HTMLResponse)
async def service_engagement(request: Request):
    """Service engagement overview."""
    # Scan for engagement files
    engagement_files = []
    compliance_dir = REPORTS_DIR / "pilot-device-compliance"

    if compliance_dir.exists():
        for f in compliance_dir.glob("*engagement*.md"):
            engagement_files.append({
                "name": f.name,
                "path": str(f.relative_to(REPORTS_DIR)),
            })
        for f in compliance_dir.glob("week1*.md"):
            engagement_files.append({
                "name": f.name,
                "path": str(f.relative_to(REPORTS_DIR)),
            })

    context = {
        "request": request,
        "title": "Service Engagement",
        "engagement_files": engagement_files[:10],
        "total_files": len(engagement_files),
    }

    return templates.TemplateResponse("service_engagement.html", context)


@app.get("/service-engagement/{device}", response_class=HTMLResponse)
async def service_engagement_device(request: Request, device: str):
    """Service engagement for specific device."""
    # Find engagement/readiness files for device
    files = {
        "engagement_package": None,
        "enrichment_plan": None,
        "readiness": None,
        "week1_collection": None,
        "week1_validation": None,
        "week2_candidates": None,
    }

    compliance_dir = REPORTS_DIR / "pilot-device-compliance"
    if compliance_dir.exists():
        for f in compliance_dir.glob("*engagement*package*.md"):
            if device.lower() in f.name.lower() or device.lower() in f.read_text().lower()[:500]:
                files["engagement_package"] = {
                    "name": f.name,
                    "path": str(f.relative_to(REPORTS_DIR)),
                }
        for f in compliance_dir.glob("*enrichment*plan*.md"):
            if device.lower() in f.name.lower() or device.lower() in f.read_text().lower()[:500]:
                files["enrichment_plan"] = {
                    "name": f.name,
                    "path": str(f.relative_to(REPORTS_DIR)),
                }
        for f in compliance_dir.glob("*readiness*.md"):
            if device.lower() in f.name.lower() or device.lower() in f.read_text().lower()[:500]:
                files["readiness"] = {
                    "name": f.name,
                    "path": str(f.relative_to(REPORTS_DIR)),
                }
        for f in compliance_dir.glob("week1*collection*.md"):
            if device.lower() in f.name.lower() or device.lower() in f.read_text().lower()[:500]:
                files["week1_collection"] = {
                    "name": f.name,
                    "path": str(f.relative_to(REPORTS_DIR)),
                }
        for f in compliance_dir.glob("week1*validation*.md"):
            if device.lower() in f.name.lower() or device.lower() in f.read_text().lower()[:500]:
                files["week1_validation"] = {
                    "name": f.name,
                    "path": str(f.relative_to(REPORTS_DIR)),
                }
        for f in compliance_dir.glob("week2*candidates*.md"):
            if device.lower() in f.name.lower() or device.lower() in f.read_text().lower()[:500]:
                files["week2_candidates"] = {
                    "name": f.name,
                    "path": str(f.relative_to(REPORTS_DIR)),
                }

    pending_items = load_pending_items(device)
    validation_assets = _load_validation_assets(device)

    context = {
        "request": request,
        "title": f"Service Engagement: {device}",
        "device": device,
        "files": files,
        "pending_items": pending_items,
        "pending_count": len(pending_items),
        "pending_counts": _count_pending_items(pending_items),
        "validation_command": _pending_validation_command(device),
        "validation_summary": validation_assets["validation_summary"],
        "validation_file": validation_assets["validation_file"],
        "gate_file": validation_assets["gate_file"],
        "intake_file": validation_assets["intake_file"],
        "snapshot_file": validation_assets["snapshot_file"],
        "week2_review_file": validation_assets["week2_review_file"],
        "uat_detected": _detect_uat_active(),
    }

    return templates.TemplateResponse("service_engagement_device.html", context)


@app.get("/service-engagement/{device}/responses", response_class=HTMLResponse)
async def service_engagement_responses(request: Request, device: str):
    """Service engagement Week 1 responses status."""
    compliance_dir = REPORTS_DIR / "pilot-device-compliance"
    validation_file = None
    validation_content = None

    if compliance_dir.exists():
        for f in compliance_dir.glob("week1*validation*.md"):
            if device.lower() in f.name.lower() or device.lower() in f.read_text().lower()[:500]:
                validation_file = {
                    "name": f.name,
                    "path": str(f.relative_to(REPORTS_DIR)),
                }
                try:
                    validation_content = f.read_text()[:2000]  # First 2000 chars
                except Exception:
                    pass

    pending_items = load_pending_items(device)
    validation_assets = _load_validation_assets(device)

    context = {
        "request": request,
        "title": f"Week 1 Responses: {device}",
        "device": device,
        "validation_file": validation_file,
        "validation_content": validation_content,
        "pending_items": pending_items,
        "pending_count": len(pending_items),
        "pending_counts": _count_pending_items(pending_items),
        "validation_command": _pending_validation_command(device),
        "validation_summary": validation_assets["validation_summary"],
        "gate_file": validation_assets["gate_file"],
        "snapshot_file": validation_assets["snapshot_file"],
        "intake_file": validation_assets["intake_file"],
        "uat_detected": _detect_uat_active(),
    }

    return templates.TemplateResponse("service_engagement_responses.html", context)


@app.get("/service-engagement/{device}/week2-candidates", response_class=HTMLResponse)
async def week2_candidates(request: Request, device: str):
    """Week 2 review candidates from Week 1 validation."""
    compliance_dir = REPORTS_DIR / "pilot-device-compliance"
    candidates_file = None
    candidates_content = None

    if compliance_dir.exists():
        for f in compliance_dir.glob("week2*candidates*.md"):
            if device.lower() in f.name.lower() or device.lower() in f.read_text().lower()[:500]:
                candidates_file = {
                    "name": f.name,
                    "path": str(f.relative_to(REPORTS_DIR)),
                }
                try:
                    candidates_content = f.read_text()[:2000]
                except Exception:
                    pass

    pending_items = load_pending_items(device)
    validation_assets = _load_validation_assets(device)

    context = {
        "request": request,
        "title": f"Week 2 Candidates: {device}",
        "device": device,
        "candidates_file": candidates_file,
        "candidates_content": candidates_content,
        "pending_items": pending_items,
        "pending_count": len(pending_items),
        "pending_counts": _count_pending_items(pending_items),
        "validation_command": _pending_validation_command(device),
        "validation_summary": validation_assets["validation_summary"],
        "gate_file": validation_assets["gate_file"],
        "intake_file": validation_assets["intake_file"],
        "uat_detected": _detect_uat_active(),
    }

    return templates.TemplateResponse("week2_candidates.html", context)


@app.get("/service-engagement/{device}/validation", response_class=HTMLResponse)
async def validation_dashboard(request: Request, device: str):
    """Response validation dashboard."""
    pending_items = load_pending_items(device)
    assets = _load_validation_assets(device)
    context = {
        "request": request,
        "title": f"Validation Dashboard: {device}",
        "device": device,
        "pending_items": pending_items,
        "pending_count": len(pending_items),
        "pending_counts": _count_pending_items(pending_items),
        "validation_summary": assets["validation_summary"],
        "validation_file": assets["validation_file"],
        "snapshot_file": assets["snapshot_file"],
        "gate_file": assets["gate_file"],
        "intake_file": assets["intake_file"],
        "week2_review_file": assets["week2_review_file"],
        "uat_detected": _detect_uat_active(),
        "validation_command": _pending_validation_command(device),
    }
    return templates.TemplateResponse("service_engagement_validation.html", context)


@app.get("/service-engagement/{device}/uat-audit", response_class=HTMLResponse)
async def uat_audit_view(request: Request, device: str):
    """UAT audit viewer."""
    audit_report = REPORTS_DIR / "pilot-device-compliance" / "WEEK1-UAT-RESPONSE-AUDIT.md"
    readiness_report = REPORTS_DIR / "pilot-device-compliance" / "WEEK1-REAL-READINESS-AFTER-UAT.md"
    report_content = audit_report.read_text(encoding="utf-8") if audit_report.exists() else None
    readiness_content = readiness_report.read_text(encoding="utf-8") if readiness_report.exists() else None
    context = {
        "request": request,
        "title": f"UAT Audit: {device}",
        "device": device,
        "audit_report": {"name": audit_report.name, "path": str(audit_report.relative_to(REPORTS_DIR))} if audit_report.exists() else None,
        "readiness_report": {"name": readiness_report.name, "path": str(readiness_report.relative_to(REPORTS_DIR))} if readiness_report.exists() else None,
        "report_content": report_content,
        "readiness_content": readiness_content,
        "uat_state": _detect_uat_state(),
    }
    return templates.TemplateResponse("service_engagement_uat_audit.html", context)


@app.post("/service-engagement/{device}/responses/run-validation", response_class=JSONResponse)
async def run_validation_endpoint(request: Request, device: str):
    """Run local-safe validation pipeline only."""
    validation = run_week1_validation(device)
    snapshot = run_outreach_snapshot(device)
    summary = validation.get("summary", parse_week1_validation_summary())
    gate = generate_activation_gate(device, summary)
    return JSONResponse({
        "success": bool(validation.get("success")) and bool(snapshot.get("success")),
        "validation": summary,
        "validation_report": validation.get("report_path"),
        "snapshot_report": snapshot.get("report_path"),
        "week2_gate": gate.get("gate"),
        "activation_gate": gate.get("path"),
    })


@app.post("/service-engagement/{device}/responses/finalize", response_class=JSONResponse)
async def finalize_responses_endpoint(request: Request, device: str):
    """Finalize local responses and prepare Week 2 when ready."""
    pipeline = run_safe_local_pipeline_after_response(device)
    return JSONResponse(pipeline)


@app.get("/service-engagement/{device}/week2-review", response_class=HTMLResponse)
async def week2_review(request: Request, device: str):
    """Week 2 review board — ready for human review."""
    compliance_dir = REPORTS_DIR / "pilot-device-compliance"
    review_dir = compliance_dir / "week2-review"
    review_file = None
    review_content = None
    decisions_file = None
    validation_assets = _load_validation_assets(device)
    gate_file = validation_assets["gate_file"]
    gate_label = "Ainda não preparado"
    if gate_file:
        try:
            gate_text = (REPORTS_DIR / gate_file["path"]).read_text(encoding="utf-8")
        except Exception:
            gate_text = ""
        if "GO_WEEK2_REVIEW_WITH_RESTRICTIONS" in gate_text:
            gate_label = "Liberado para revisão com restrições"
        elif "GO_WEEK2_REVIEW" in gate_text:
            gate_label = "Liberado para revisão"
        elif "NO_GO" in gate_text:
            gate_label = "Não liberado"
    proposed_approvals = list_proposed_approvals(ROOT)
    draft_items = []

    if review_dir.exists():
        board = review_dir / "week2-review-board.md"
        if board.exists():
            review_file = {
                "name": board.name,
                "path": str(board.relative_to(REPORTS_DIR)),
            }
            try:
                review_content = board.read_text()
            except Exception:
                pass

        decisions = review_dir / "week2-review-decisions.csv"
        if decisions.exists():
            decisions_file = {
                "name": decisions.name,
                "path": str(decisions.relative_to(REPORTS_DIR)),
            }

        drafts_dir = review_dir / "week2-approval-drafts"
        if drafts_dir.exists():
            for draft_file in drafts_dir.glob("approval-draft-*.json"):
                try:
                    draft_data = load_json(draft_file)
                except Exception:
                    draft_data = None
                if not draft_data:
                    continue
                draft_items.append({
                    "name": draft_file.name,
                    "path": str(draft_file.relative_to(REPORTS_DIR)),
                    "object_key": draft_data.get("object_key", ""),
                    "object_type": draft_data.get("object_type", ""),
                    "category": draft_data.get("category", ""),
                    "status": draft_data.get("status", ""),
                    "recommended_action": "Pode ser promovido" if draft_data.get("allowed_to_promote") else "Precisa de revisão",
                    "human_decision": "",
                })

    context = {
        "request": request,
        "title": f"Week 2 Review Board: {device}",
        "device": device,
        "review_file": review_file,
        "review_content": review_content,
        "decisions_file": decisions_file,
        "gate_file": gate_file,
        "gate_label": gate_label,
        "validation_summary": validation_assets["validation_summary"],
        "proposed_approvals": proposed_approvals,
        "draft_items": draft_items,
    }

    return templates.TemplateResponse("week2_review.html", context)


@app.get("/service-engagement/{device}/approval-drafts", response_class=HTMLResponse)
async def approval_drafts(request: Request, device: str):
    """Approval drafts (draft_review status) pending promotion."""
    compliance_dir = REPORTS_DIR / "pilot-device-compliance"
    review_dir = compliance_dir / "week2-review"
    drafts_dir = review_dir / "week2-approval-drafts"
    drafts = []

    if drafts_dir.exists():
        for draft_file in drafts_dir.glob("approval-draft-*.json"):
            try:
                draft_data = load_json(draft_file)
                if draft_data:
                    draft_status = draft_data.get("status", "")
                    drafts.append({
                        "name": draft_file.name,
                        "object_key": draft_data.get("object_key", ""),
                        "status": draft_status,
                        "action": draft_data.get("action", ""),
                        "created_at": draft_data.get("created_at", ""),
                        "path": str(draft_file.relative_to(REPORTS_DIR)),
                        "allowed_to_promote": bool(draft_data.get("allowed_to_promote")),
                        "review_state": "Aguardando decisão" if draft_status == "draft_review" else "Rascunho",
                        "badge_label": "Pode ser promovido" if draft_data.get("allowed_to_promote") else "Precisa ajuste",
                    })
            except Exception:
                pass

    context = {
        "request": request,
        "title": f"Approval Drafts: {device}",
        "device": device,
        "drafts": drafts,
        "total_drafts": len(drafts),
    }

    return templates.TemplateResponse("approval_drafts.html", context)


@app.get("/service-engagement/{device}/promotion-report", response_class=HTMLResponse)
async def promotion_report(request: Request, device: str):
    """Week 2 draft promotion report."""
    compliance_dir = REPORTS_DIR / "pilot-device-compliance"
    review_dir = compliance_dir / "week2-review"
    report_file = None
    report_content = None

    if review_dir.exists():
        report = review_dir / "week2-promotion-report.md"
        if report.exists():
            report_file = {
                "name": report.name,
                "path": str(report.relative_to(REPORTS_DIR)),
            }
            try:
                report_content = report.read_text()
            except Exception:
                pass

    context = {
        "request": request,
        "title": f"Promotion Report: {device}",
        "device": device,
        "report_file": report_file,
        "report_content": report_content,
    }

    return templates.TemplateResponse("promotion_report.html", context)


# ============================================================================
# Outreach & Operations (FASE 2.15 + 3.7)
# ============================================================================

@app.get("/outreach", response_class=HTMLResponse)
async def outreach(request: Request):
    """Week 1 outreach pack overview."""
    compliance_dir = REPORTS_DIR / "pilot-device-compliance"
    outreach_dir = compliance_dir / "outreach"
    outreach_files = []

    if outreach_dir.exists():
        for f in outreach_dir.glob("*.md"):
            outreach_files.append({
                "name": f.name,
                "path": str(f.relative_to(REPORTS_DIR)),
                "size": f.stat().st_size,
            })

    context = {
        "request": request,
        "title": "Week 1 Outreach Pack",
        "outreach_files": sorted(outreach_files, key=lambda x: x["name"]),
        "total_files": len(outreach_files),
    }

    return templates.TemplateResponse("outreach.html", context)


@app.get("/outreach/{team}", response_class=HTMLResponse)
async def outreach_team(request: Request, team: str):
    """Team-specific outreach message."""
    valid_teams = ["service-team", "network-ops", "bgp-team"]
    if team not in valid_teams:
        return HTMLResponse("<h1>Invalid team</h1>", status_code=404)

    compliance_dir = REPORTS_DIR / "pilot-device-compliance"
    outreach_dir = compliance_dir / "outreach"
    message_file = None
    message_content = None

    if outreach_dir.exists():
        msg = outreach_dir / f"message-{team}.md"
        if msg.exists():
            message_file = {
                "name": msg.name,
                "path": str(msg.relative_to(REPORTS_DIR)),
            }
            try:
                message_content = load_markdown(msg)
                if message_content:
                    message_content = render_markdown(message_content)
            except Exception:
                pass

    context = {
        "request": request,
        "title": f"Outreach: {team}",
        "team": team,
        "message_file": message_file,
        "message_content": message_content,
    }

    return templates.TemplateResponse("outreach_team.html", context)


@app.get("/outreach/status", response_class=HTMLResponse)
async def outreach_status(request: Request):
    """Week 1 response monitoring status."""
    compliance_dir = REPORTS_DIR / "pilot-device-compliance"
    outreach_dir = compliance_dir / "outreach"
    status_file = None
    status_content = None
    distribution_log = None

    if outreach_dir.exists():
        snapshot = outreach_dir / "execution" / "outreach-status-snapshot.md"
        if snapshot.exists():
            status_file = {
                "name": snapshot.name,
                "path": str(snapshot.relative_to(REPORTS_DIR)),
            }
            try:
                status_content = load_markdown(snapshot)
                if status_content:
                    status_content = render_markdown(status_content)
            except Exception:
                pass

        dist_log = outreach_dir / "execution" / "outreach-distribution-log.md"
        if dist_log.exists():
            distribution_log = {
                "name": dist_log.name,
                "path": str(dist_log.relative_to(REPORTS_DIR)),
            }

    context = {
        "request": request,
        "title": "Outreach Status",
        "status_file": status_file,
        "status_content": status_content,
        "distribution_log": distribution_log,
        "pending_device": "4WNET-MNS-KTG-RX",
        "pending_link": "/service-engagement/4WNET-MNS-KTG-RX/pending-items",
    }

    return templates.TemplateResponse("outreach_status.html", context)


@app.get("/outreach/execution-log", response_class=HTMLResponse)
async def outreach_execution_log(request: Request):
    """Outreach distribution log + checklist."""
    compliance_dir = REPORTS_DIR / "pilot-device-compliance"
    outreach_dir = compliance_dir / "outreach"
    dist_log = None
    dist_content = None
    checklist = None

    if outreach_dir.exists():
        log = outreach_dir / "execution" / "outreach-distribution-log.md"
        if log.exists():
            dist_log = {
                "name": log.name,
                "path": str(log.relative_to(REPORTS_DIR)),
            }
            try:
                dist_content = load_markdown(log)
                if dist_content:
                    dist_content = render_markdown(dist_content)
            except Exception:
                pass

        check = outreach_dir / "execution" / "manual-send-checklist.md"
        if check.exists():
            checklist = {
                "name": check.name,
                "path": str(check.relative_to(REPORTS_DIR)),
            }

    context = {
        "request": request,
        "title": "Outreach Execution Log",
        "distribution_log": dist_log,
        "distribution_content": dist_content,
        "checklist": checklist,
    }

    return templates.TemplateResponse("outreach_execution_log.html", context)


@app.get("/outreach/reminders", response_class=HTMLResponse)
async def outreach_reminders(request: Request):
    """Reminder messages index."""
    compliance_dir = REPORTS_DIR / "pilot-device-compliance"
    outreach_dir = compliance_dir / "outreach"
    reminder_plan = None
    reminders = []

    if outreach_dir.exists():
        plan = outreach_dir / "execution" / "outreach-reminder-plan.md"
        if plan.exists():
            reminder_plan = {
                "name": plan.name,
                "path": str(plan.relative_to(REPORTS_DIR)),
            }

        reminders_dir = outreach_dir / "execution" / "reminder-messages"
        if reminders_dir.exists():
            for f in reminders_dir.glob("*.md"):
                reminders.append({
                    "name": f.stem.replace("reminder-", "").replace("-", " ").title(),
                    "file": f.name,
                    "path": str(f.relative_to(REPORTS_DIR)),
                })

    context = {
        "request": request,
        "title": "Reminders & Escalation",
        "reminder_plan": reminder_plan,
        "reminders": sorted(reminders, key=lambda x: x["name"]),
        "teams": ["Service Team", "Network Ops", "BGP Team", "Escalation"],
    }

    return templates.TemplateResponse("outreach_reminders.html", context)


@app.get("/outreach/reminders/{reminder_type}", response_class=HTMLResponse)
async def outreach_reminder(request: Request, reminder_type: str):
    """Specific reminder message."""
    valid_types = ["service-team", "network-ops", "bgp-team", "escalation"]
    if reminder_type not in valid_types:
        return HTMLResponse("<h1>Invalid reminder type</h1>", status_code=404)

    compliance_dir = REPORTS_DIR / "pilot-device-compliance"
    outreach_dir = compliance_dir / "outreach"
    reminder_file = None
    reminder_content = None

    if outreach_dir.exists():
        if reminder_type == "escalation":
            file = outreach_dir / "execution" / "reminder-messages" / "escalation-template.md"
        else:
            file = outreach_dir / "execution" / "reminder-messages" / f"reminder-{reminder_type}.md"

        if file.exists():
            reminder_file = {
                "name": file.name,
                "path": str(file.relative_to(REPORTS_DIR)),
            }
            try:
                reminder_content = load_markdown(file)
                if reminder_content:
                    reminder_content = render_markdown(reminder_content)
            except Exception:
                pass

    context = {
        "request": request,
        "title": f"Reminder: {reminder_type}",
        "reminder_type": reminder_type,
        "reminder_file": reminder_file,
        "reminder_content": reminder_content,
    }

    return templates.TemplateResponse("outreach_reminder_team.html", context)


@app.get("/operations/handoff", response_class=HTMLResponse)
async def operations_handoff(request: Request):
    """Operational handoff package."""
    handoff_file = None
    handoff_content = None

    reports_dir = REPORTS_DIR
    if reports_dir.exists():
        handoff = reports_dir / "OPERATIONAL-HANDOFF-PACKAGE.md"
        if handoff.exists():
            handoff_file = {
                "name": handoff.name,
                "path": str(handoff.relative_to(REPORTS_DIR)),
            }
            try:
                handoff_content = load_markdown(handoff)
                if handoff_content:
                    handoff_content = render_markdown(handoff_content)
            except Exception:
                pass

    context = {
        "request": request,
        "title": "Operational Handoff",
        "handoff_file": handoff_file,
        "handoff_content": handoff_content,
    }

    return templates.TemplateResponse("operations_handoff.html", context)


@app.get("/operations/readiness", response_class=HTMLResponse)
async def operations_readiness(request: Request):
    """Operations readiness status."""
    readiness_files = []
    readiness_summary = None

    reports_dir = REPORTS_DIR
    if reports_dir.exists():
        # Look for readiness reports
        for f in reports_dir.glob("*readiness*.md"):
            readiness_files.append({
                "name": f.name,
                "path": str(f.relative_to(REPORTS_DIR)),
            })

    context = {
        "request": request,
        "title": "Operations Readiness",
        "readiness_files": readiness_files,
        "total_files": len(readiness_files),
    }

    return templates.TemplateResponse("operations_readiness.html", context)


# ============================================================================
# Log modal viewer (FASE 3.9.2)
# ============================================================================

@app.get("/logs/view", response_class=HTMLResponse)
async def logs_view(request: Request, path: str = ""):
    """View log file in modal-compatible JSON."""
    if not path:
        return JSONResponse({"error": "path parameter required"}, status_code=400)

    try:
        # Normalize path (accepts both "file.md" and "reports/file.md")
        normalized = normalize_report_path(path)
        if not normalized:
            return JSONResponse({"error": "Invalid path"}, status_code=400)

        resolved_path = safe_resolve_path(REPORTS_DIR, normalized)

        if not resolved_path.exists():
            return JSONResponse({"error": "file not found"}, status_code=404)

        # Size check (max 500KB)
        if resolved_path.stat().st_size > 500000:
            return JSONResponse({
                "error": "file too large (>500KB)",
                "path": path,
                "size": resolved_path.stat().st_size
            }, status_code=413)

        with open(resolved_path, 'r', encoding='utf-8') as f:
            content = f.read()

        return JSONResponse({
            "success": True,
            "path": path,
            "name": resolved_path.name,
            "size": len(content),
            "content": content
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ============================================================================
# Pending item editor (FASE 3.10)
# ============================================================================

from .services.response_forms import (
    build_pending_item_schema,
    get_pending_item,
    load_pending_items,
    save_response_audit,
    save_response_csv,
    validate_response_payload,
)
from .services.local_pipeline import (
    generate_activation_gate,
    parse_week1_validation_summary,
    prepare_week2_if_ready,
    run_outreach_snapshot,
    run_safe_local_pipeline_after_response,
    run_week1_validation,
)


def _count_pending_items(pending_items):
    counts = {
        "pending": 0,
        "answered": 0,
        "needs_clarification": 0,
        "blocked": 0,
        "rejected": 0,
    }
    for item in pending_items:
        status = item.get("current_status", "pending")
        if status not in counts:
            status = "pending"
        counts[status] += 1
    return counts


def _pending_validation_command(device: str) -> str:
    responses_dir = REPORTS_DIR / "pilot-device-compliance" / "week1-responses"
    output = REPORTS_DIR / "pilot-device-compliance" / "week1-response-validation.md"
    template = REPORTS_DIR / "pilot-device-compliance" / "week1-metadata-collection-template.csv"
    return (
        "python3 tools/local/validate_week1_responses.py "
        f"--template {template} "
        f"--responses-dir {responses_dir} "
        f"--output {output} "
        f"--device {device}"
    )


def _week1_execution_overview(device: str) -> dict:
    pending_items = load_pending_items(device)
    pending_counts = _count_pending_items(pending_items)
    assets = _load_validation_assets(device)
    summary = assets["validation_summary"]
    week2_ready = bool(assets["week2_review_file"])

    if week2_ready:
        state = "pronto para Semana 2"
    elif summary.get("needs_clarification", 0) or summary.get("blocked", 0) or summary.get("rejected", 0):
        state = "com restrições"
    elif pending_counts.get("pending", 0) > 0:
        state = "em andamento"
    elif summary.get("validated", 0) > 0:
        state = "pronto para Semana 2"
    else:
        state = "limpo"

    return {
        "state": state,
        "pending": pending_counts.get("pending", 0),
        "validated": int(summary.get("validated", 0)),
        "summary": summary,
        "week2_ready": week2_ready,
        "link": f"/service-engagement/{device}",
    }


def _week2_review_overview(device: str) -> dict:
    assets = _load_validation_assets(device)
    summary = assets["validation_summary"]
    review_dir = REPORTS_DIR / "pilot-device-compliance" / "week2-review"
    drafts_dir = review_dir / "week2-approval-drafts"
    gate_file = assets["gate_file"]
    gate_label = "Ainda não preparado"

    if gate_file:
        try:
            gate_text = (REPORTS_DIR / gate_file["path"]).read_text(encoding="utf-8")
        except Exception:
            gate_text = ""
        if "GO_WEEK2_REVIEW_WITH_RESTRICTIONS" in gate_text:
            gate_label = "Liberado para revisão com restrições"
        elif "GO_WEEK2_REVIEW" in gate_text:
            gate_label = "Liberado para revisão"
        elif "NO_GO" in gate_text:
            gate_label = "Não liberado"

    proposed = list_proposed_approvals(ROOT)
    draft_count = len(list(drafts_dir.glob("approval-draft-*.json"))) if drafts_dir.exists() else 0
    restricted = int(summary.get("needs_clarification", 0)) + int(summary.get("blocked", 0)) + int(summary.get("rejected", 0))

    return {
        "gate_label": gate_label,
        "drafts": draft_count,
        "proposed": len(proposed),
        "restricted": restricted,
        "link": f"/service-engagement/{device}/week2-review",
    }


def _controlled_operation_overview() -> dict:
    index = load_controlled_operation_index(ROOT)
    cycles = index.get("cycles", [])
    counts = {
        "planned": sum(1 for cycle in cycles if cycle.get("current_status") == "planned"),
        "closed_success": sum(1 for cycle in cycles if cycle.get("current_status") == "closed_success"),
        "closed_with_restrictions": sum(1 for cycle in cycles if cycle.get("current_status") == "closed_with_restrictions"),
        "action_required": sum(1 for cycle in cycles if cycle.get("current_status") == "action_required"),
    }
    return {
        "index": index,
        "cycles": cycles,
        "counts": counts,
        "latest_cycle": cycles[-1] if cycles else None,
        "status_label": status_label(index.get("overall_status", "")),
    }


def _find_controlled_cycle(cycle_id: str):
    safe_id = safe_cycle_id(cycle_id)
    if not safe_id:
        raise HTTPException(status_code=404, detail="cycle not found")
    cycles = list_controlled_cycles(ROOT)
    for cycle in cycles:
        if cycle.get("cycle_id") == safe_id:
            return cycle
    raise HTTPException(status_code=404, detail="cycle not found")


def _controlled_cycle_week1_context(cycle_id: str) -> dict:
    cycle = _find_controlled_cycle(cycle_id)
    assets = load_cycle_week1_artifacts(ROOT, cycle["cycle_id"])
    state_source = str(assets.get("validation_decision") or assets.get("intake_decision") or cycle.get("current_status") or "").lower()
    status_label_value = status_label(state_source)
    next_action = cycle.get("next_action", "Revisar artefatos")
    if assets.get("validation_decision"):
        if "blocked" in str(assets["validation_decision"]).lower():
            next_action = "Resolver bloqueios."
        else:
            next_action = "Abrir revisão da Semana 2."
    elif assets.get("intake_decision"):
        if assets["intake_decision"] == "WEEK1_INTAKE_READY":
            next_action = "Rodar validação local."
        else:
            next_action = "Completar respostas pendentes."
    elif assets.get("plan_file"):
        next_action = "Responder as pendências."

    return {
        "cycle": cycle,
        "assets": assets,
        "status_label_value": status_label_value,
        "next_action": next_action,
    }


def _controlled_team_slug(value: str) -> str:
    lowered = (value or "").strip().lower()
    if "service" in lowered:
        return "service"
    if "network" in lowered or "ops" in lowered:
        return "network_ops"
    if "bgp" in lowered:
        return "bgp"
    return lowered.replace("-", "_").replace(" ", "_")


def _controlled_item_id(object_key: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", (object_key or "").lower()).strip("-")
    digest = hashlib.sha1((object_key or "").encode("utf-8")).hexdigest()[:8]
    return f"{base[:48] or 'item'}-{digest}"


def _controlled_response_filename(team_slug: str) -> str:
    return {
        "service": "service-team-response.csv",
        "network_ops": "network-ops-response.csv",
        "bgp": "bgp-team-response.csv",
    }.get(team_slug, f"{team_slug}-response.csv")


def _controlled_cycle_week1_pending_context(cycle_id: str) -> dict:
    cycle = _find_controlled_cycle(cycle_id)
    cycle_dir = REPORTS_DIR / "controlled-operation" / cycle["cycle_id"]
    template_file = REPORTS_DIR / "pilot-device-compliance" / "week1-metadata-collection-template.csv"
    responses_dir = cycle_dir / "week1" / "responses"
    response_rows: dict[str, dict[str, str]] = {}

    if responses_dir.exists():
        for csv_path in responses_dir.glob("*.csv"):
            try:
                with csv_path.open("r", encoding="utf-8", newline="") as handle:
                    reader = csv.DictReader(handle)
                    for row in reader:
                        object_key = (row.get("object_key") or "").strip()
                        if object_key:
                            response_rows[object_key] = {k: (v or "").strip() for k, v in row.items()}
            except Exception:
                continue

    items = []
    if template_file.exists():
        with template_file.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if (row.get("device") or "").strip() not in {"", cycle["device"]}:
                    continue
                object_key = (row.get("object_key") or "").strip()
                if not object_key:
                    continue
                team_label = (row.get("responsible_team") or "").strip()
                team_slug = _controlled_team_slug(team_label)
                response = response_rows.get(object_key, {})
                current_status = (response.get("status") or row.get("status") or "pending").strip() or "pending"
                items.append({
                    "device": cycle["device"],
                    "device_id": cycle["device_id"],
                    "object_type": (row.get("object_type") or "").strip(),
                    "object_key": object_key,
                    "responsible_team": team_label,
                    "responsible_team_slug": team_slug,
                    "current_status": current_status,
                    "missing_fields": [part.strip() for part in (row.get("missing_fields") or "").split(",") if part.strip()],
                    "updated_by": response.get("updated_by", ""),
                    "updated_at": response.get("updated_at", ""),
                    "csv_path": str((responses_dir / _controlled_response_filename(team_slug)).relative_to(REPORTS_DIR)) if responses_dir.exists() else "",
                    "safe_item_id": _controlled_item_id(object_key),
                    "response_present": bool(response),
                })

    items.sort(key=lambda item: (item["responsible_team"], item["object_type"], item["object_key"]))
    return {
        "cycle": cycle,
        "items": items,
        "count": len(items),
        "responses_dir": str(responses_dir.relative_to(REPORTS_DIR)) if responses_dir.exists() else None,
        "seed_commands": [
            f"python3 tools/local/controlled_cycle_week1_seed_response.py --cycle-id {cycle_id} --device {cycle['device']} --device-id {cycle['device_id']} --cycle-dir reports/controlled-operation/{cycle['cycle_id']} --team service --object-type subinterface --object-key Eth-Trunk0.10 --response-status answered --tenant \"Cliente Piloto\" --service-type customer-internet --criticality gold --owner \"UAT Service Owner\" --evidence \"UAT evidence\" --notes \"UAT response\" --output-dir reports/controlled-operation/{cycle['cycle_id']}/week1",
            f"python3 tools/local/controlled_cycle_week1_seed_response.py --cycle-id {cycle_id} --device {cycle['device']} --device-id {cycle['device_id']} --cycle-dir reports/controlled-operation/{cycle['cycle_id']} --team network_ops --object-type ip_address --object-key 192.0.2.1/30 --response-status answered --interface GigabitEthernet0/5/0 --vrf _public_ --relation-type infrastructure --owner \"UAT Network Ops\" --evidence \"UAT evidence\" --notes \"UAT response\" --output-dir reports/controlled-operation/{cycle['cycle_id']}/week1",
            f"python3 tools/local/controlled_cycle_week1_seed_response.py --cycle-id {cycle_id} --device {cycle['device']} --device-id {cycle['device_id']} --cycle-dir reports/controlled-operation/{cycle['cycle_id']} --team bgp --object-type bgp_peer --object-key 203.0.113.1 --response-status answered --remote-asn 65000 --remote-bgp-group UAT-GROUP --policy-intent \"UAT policy intent\" --criticality silver --owner \"UAT BGP Owner\" --evidence \"UAT evidence\" --notes \"UAT response\" --output-dir reports/controlled-operation/{cycle['cycle_id']}/week1",
        ],
    }


def _lookup_pending_item(device: str, safe_item_id: str):
    data = get_pending_item(device, safe_item_id)
    return data["item"]


def _resolve_pending_item(device: str, payload):
    safe_item_id = payload.get("safe_item_id")
    if safe_item_id:
        return _lookup_pending_item(device, safe_item_id)

    object_key = payload.get("object_key")
    if not object_key:
        raise HTTPException(status_code=400, detail="safe_item_id or object_key required")

    for item in load_pending_items(device):
        if item.get("object_key") == object_key:
            return item

    raise HTTPException(status_code=404, detail="Unknown item")


def _save_pending_item_response(device: str, item, payload):
    payload = dict(payload or {})
    payload.setdefault("updated_by", payload.get("updated_by", ""))
    payload.setdefault("status", payload.get("status", ""))

    valid, errors, convention_violations = validate_response_payload(item, payload)

    # Check if any convention_violations are blockers
    blocker_violations = [v for v in convention_violations if v.get("severity") == "blocker"]
    if blocker_violations:
        payload["validation_errors"] = errors + [f"{v.get('rule_id')}: {v.get('message_pt')}" for v in blocker_violations]
        return JSONResponse({
            "success": False,
            "errors": errors,
            "convention_violations": blocker_violations,
        }, status_code=400)

    if not valid:
        payload["validation_errors"] = errors
        return JSONResponse({
            "success": False,
            "errors": errors,
            "convention_violations": convention_violations,
        }, status_code=400)

    team = item.get("responsible_team_slug") or item.get("responsible_team", "")
    csv_path = save_response_csv(team, item, payload, ROOT)
    audit_path = save_response_audit(team, item, payload, ROOT)
    pipeline = run_safe_local_pipeline_after_response(device)

    return JSONResponse({
        "success": True,
        "message": "Resposta salva localmente. Nenhuma alteração foi feita no NetBox.",
        "team": item.get("responsible_team"),
        "csv_path": str(csv_path.relative_to(ROOT)),
        "audit_path": str(audit_path.relative_to(ROOT)),
        "validation_status": _stringify_status(payload.get("status")),
        "device": device,
        "convention_violations": convention_violations,
        "pipeline": pipeline,
    })


def _stringify_status(value):
    return str(value or "").strip()


def _load_validation_assets(device: str):
    validation_file = REPORTS_DIR / "pilot-device-compliance" / "week1-response-validation.md"
    snapshot_file = REPORTS_DIR / "pilot-device-compliance" / "outreach" / "execution" / "outreach-status-snapshot.md"
    gate_file = REPORTS_DIR / "pilot-device-compliance" / "week2-activation-gate.md"
    intake_file = REPORTS_DIR / "pilot-device-compliance" / "week1-response-intake-report.md"
    review_dir = REPORTS_DIR / "pilot-device-compliance" / "week2-review"

    return {
        "validation_summary": parse_week1_validation_summary(validation_file),
        "validation_file": {"name": validation_file.name, "path": str(validation_file.relative_to(REPORTS_DIR))} if validation_file.exists() else None,
        "snapshot_file": {"name": snapshot_file.name, "path": str(snapshot_file.relative_to(REPORTS_DIR))} if snapshot_file.exists() else None,
        "gate_file": {"name": gate_file.name, "path": str(gate_file.relative_to(REPORTS_DIR))} if gate_file.exists() else None,
        "intake_file": {"name": intake_file.name, "path": str(intake_file.relative_to(REPORTS_DIR))} if intake_file.exists() else None,
        "week2_review_file": {"name": "week2-review-board.md", "path": str((review_dir / "week2-review-board.md").relative_to(REPORTS_DIR))} if (review_dir / "week2-review-board.md").exists() else None,
    }


def _detect_uat_state():
    responses_dir = REPORTS_DIR / "pilot-device-compliance" / "week1-responses"
    audit_dir = responses_dir / "audit"
    uat_hits = []
    for path in list(responses_dir.glob("*.csv")) + list(audit_dir.glob("*.json")):
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            continue
        if "updated_by,uat" in content.lower() or '"updated_by": "uat"' in content.lower() or " uat" in content.lower():
            uat_hits.append(path.name)
    return {
        "active": bool(uat_hits),
        "status": "active" if uat_hits else "unknown",
        "files": uat_hits,
    }


def _detect_uat_active() -> bool:
    return bool(_detect_uat_state().get("active"))


@app.get("/controlled-operation", response_class=HTMLResponse)
async def controlled_operation_overview(request: Request):
    index = load_controlled_operation_index(ROOT)
    context = {
        "request": request,
        "title": "Operação Controlada",
        "index": index,
        "cycles": index.get("cycles", []),
        "controlled_operation": _controlled_operation_overview(),
    }
    return templates.TemplateResponse("controlled_operation_overview.html", context)


@app.get("/controlled-operation/cycles", response_class=HTMLResponse)
async def controlled_operation_cycles_view(request: Request):
    index = load_controlled_operation_index(ROOT)
    context = {
        "request": request,
        "title": "Ciclos Controlados",
        "index": index,
        "cycles": index.get("cycles", []),
    }
    return templates.TemplateResponse("controlled_operation_cycles.html", context)


@app.get("/controlled-operation/{cycle_id}", response_class=HTMLResponse)
async def controlled_operation_cycle_detail(request: Request, cycle_id: str):
    cycle = _find_controlled_cycle(cycle_id)
    context = {
        "request": request,
        "title": f"Ciclo: {cycle['cycle_id']}",
        "cycle": cycle,
        "week1": load_cycle_week1_artifacts(ROOT, cycle["cycle_id"]),
        "week2": load_cycle_week2_artifacts(ROOT, cycle["cycle_id"]),
    }
    return templates.TemplateResponse("controlled_operation_cycle_detail.html", context)


@app.get("/controlled-operation/{cycle_id}/start-gate", response_class=HTMLResponse)
async def controlled_operation_start_gate(request: Request, cycle_id: str):
    cycle = _find_controlled_cycle(cycle_id)
    artifact = load_cycle_artifact(ROOT, cycle_id, "start-gate")
    return templates.TemplateResponse(
        "controlled_operation_start_gate.html",
        {"request": request, "title": f"Start gate: {cycle['cycle_id']}", "cycle": cycle, "artifact": artifact},
    )


@app.get("/controlled-operation/{cycle_id}/archive", response_class=HTMLResponse)
async def controlled_operation_archive(request: Request, cycle_id: str):
    cycle = _find_controlled_cycle(cycle_id)
    artifact = None
    try:
        artifact = load_cycle_artifact(ROOT, cycle_id, "archive")
    except Exception:
        artifact = None
    return templates.TemplateResponse(
        "controlled_operation_archive.html",
        {"request": request, "title": f"Archive: {cycle['cycle_id']}", "cycle": cycle, "artifact": artifact},
    )


@app.get("/controlled-operation/{cycle_id}/handoff", response_class=HTMLResponse)
async def controlled_operation_handoff(request: Request, cycle_id: str):
    cycle = _find_controlled_cycle(cycle_id)
    artifact = None
    try:
        artifact = load_cycle_artifact(ROOT, cycle_id, "handoff")
    except Exception:
        artifact = None
    return templates.TemplateResponse(
        "controlled_operation_handoff.html",
        {"request": request, "title": f"Handoff: {cycle['cycle_id']}", "cycle": cycle, "artifact": artifact},
    )


@app.get("/controlled-operation/{cycle_id}/week1", response_class=HTMLResponse)
async def controlled_operation_week1(request: Request, cycle_id: str):
    context = _controlled_cycle_week1_context(cycle_id)
    return templates.TemplateResponse("controlled_operation_week1.html", {"request": request, **context})


@app.get("/controlled-operation/{cycle_id}/week1/pending", response_class=HTMLResponse)
async def controlled_operation_week1_pending(request: Request, cycle_id: str):
    context = _controlled_cycle_week1_pending_context(cycle_id)
    return templates.TemplateResponse("controlled_operation_week1_pending.html", {"request": request, **context})


@app.get("/controlled-operation/{cycle_id}/week1/pending/{safe_item_id}", response_class=JSONResponse)
async def controlled_operation_week1_pending_detail(request: Request, cycle_id: str, safe_item_id: str):
    context = _controlled_cycle_week1_pending_context(cycle_id)
    for item in context["items"]:
        if item.get("safe_item_id") == safe_item_id:
            return JSONResponse({"success": True, "item": item})
    raise HTTPException(status_code=404, detail="Item not found")


@app.get("/controlled-operation/{cycle_id}/week1/intake", response_class=HTMLResponse)
async def controlled_operation_week1_intake(request: Request, cycle_id: str):
    context = _controlled_cycle_week1_context(cycle_id)
    return templates.TemplateResponse("controlled_operation_week1_intake.html", {"request": request, **context})


@app.get("/controlled-operation/{cycle_id}/week1/validation", response_class=HTMLResponse)
async def controlled_operation_week1_validation(request: Request, cycle_id: str):
    context = _controlled_cycle_week1_context(cycle_id)
    return templates.TemplateResponse("controlled_operation_week1_validation.html", {"request": request, **context})


@app.get("/controlled-operation/{cycle_id}/week2", response_class=HTMLResponse)
async def controlled_operation_week2(request: Request, cycle_id: str):
    cycle = _find_controlled_cycle(cycle_id)
    assets = load_cycle_week2_artifacts(ROOT, cycle["cycle_id"])
    return templates.TemplateResponse(
        "controlled_operation_week2.html",
        {"request": request, "title": f"Week 2: {cycle['cycle_id']}", "cycle": cycle, "assets": assets},
    )


@app.get("/controlled-operation/{cycle_id}/week2/review", response_class=HTMLResponse)
async def controlled_operation_week2_review(request: Request, cycle_id: str):
    cycle = _find_controlled_cycle(cycle_id)
    week2 = load_cycle_week2_artifacts(ROOT, cycle["cycle_id"])
    review = load_cycle_week2_review_artifacts(ROOT, cycle["cycle_id"])
    return templates.TemplateResponse(
        "controlled_operation_week2_review.html",
        {"request": request, "title": f"Revisão Semana 2: {cycle['cycle_id']}", "cycle": cycle, "week2": week2, "review": review},
    )


@app.get("/controlled-operation/{cycle_id}/approvals", response_class=HTMLResponse)
async def controlled_operation_cycle_approvals(request: Request, cycle_id: str):
    cycle = _find_controlled_cycle(cycle_id)
    approvals = load_cycle_approvals_artifacts(ROOT, cycle["cycle_id"])
    return templates.TemplateResponse(
        "controlled_operation_approvals.html",
        {"request": request, "title": f"Aprovações: {cycle['cycle_id']}", "cycle": cycle, "approvals": approvals},
    )


@app.get("/controlled-operation/{cycle_id}/approvals/readiness", response_class=HTMLResponse)
async def controlled_operation_cycle_approval_readiness(request: Request, cycle_id: str):
    cycle = _find_controlled_cycle(cycle_id)
    approvals = load_cycle_approvals_artifacts(ROOT, cycle["cycle_id"])
    return templates.TemplateResponse(
        "controlled_operation_approval_readiness.html",
        {"request": request, "title": f"Prontidão de Aprovação: {cycle['cycle_id']}", "cycle": cycle, "approvals": approvals},
    )


@app.get("/controlled-operation/{cycle_id}/approvals/manual-review", response_class=HTMLResponse)
async def controlled_operation_cycle_manual_review(request: Request, cycle_id: str):
    cycle = _find_controlled_cycle(cycle_id)
    approvals = load_cycle_approvals_artifacts(ROOT, cycle["cycle_id"])
    review = load_cycle_week2_review_artifacts(ROOT, cycle["cycle_id"])
    return templates.TemplateResponse(
        "controlled_operation_manual_review.html",
        {
            "request": request,
            "title": f"Revisão Manual: {cycle['cycle_id']}",
            "cycle": cycle,
            "approvals": approvals,
            "review": review,
        },
    )


@app.get("/controlled-operation/{cycle_id}/applyplan", response_class=HTMLResponse)
async def controlled_operation_cycle_applyplan(request: Request, cycle_id: str):
    cycle = _find_controlled_cycle(cycle_id)
    applyplans = load_cycle_dryrun_applyplan_artifacts(ROOT, cycle["cycle_id"])
    return templates.TemplateResponse(
        "controlled_operation_applyplan.html",
        {
            "request": request,
            "title": f"ApplyPlan dry-run: {cycle['cycle_id']}",
            "cycle": cycle,
            "applyplans": applyplans,
        },
    )


@app.get("/controlled-operation/{cycle_id}/applyplan/validation", response_class=HTMLResponse)
async def controlled_operation_cycle_applyplan_validation(request: Request, cycle_id: str):
    cycle = _find_controlled_cycle(cycle_id)
    applyplans = load_cycle_dryrun_applyplan_artifacts(ROOT, cycle["cycle_id"])
    return templates.TemplateResponse(
        "controlled_operation_applyplan_validation.html",
        {
            "request": request,
            "title": f"Validação ApplyPlan: {cycle['cycle_id']}",
            "cycle": cycle,
            "applyplans": applyplans,
        },
    )


@app.get("/controlled-operation/{cycle_id}/applyplan/dryrun-gate", response_class=HTMLResponse)
async def controlled_operation_cycle_applyplan_dryrun_gate(request: Request, cycle_id: str):
    cycle = _find_controlled_cycle(cycle_id)
    applyplans = load_cycle_dryrun_applyplan_artifacts(ROOT, cycle["cycle_id"])
    return templates.TemplateResponse(
        "controlled_operation_dryrun_execution_gate.html",
        {"request": request, "title": f"Dry-run gate: {cycle['cycle_id']}", "cycle": cycle, "applyplans": applyplans},
    )


@app.get("/controlled-operation/{cycle_id}/applyplan/simulation", response_class=HTMLResponse)
async def controlled_operation_cycle_applyplan_simulation(request: Request, cycle_id: str):
    cycle = _find_controlled_cycle(cycle_id)
    applyplans = load_cycle_dryrun_applyplan_artifacts(ROOT, cycle["cycle_id"])
    return templates.TemplateResponse(
        "controlled_operation_dryrun_simulation.html",
        {"request": request, "title": f"Dry-run simulation: {cycle['cycle_id']}", "cycle": cycle, "applyplans": applyplans},
    )


@app.get("/controlled-operation/{cycle_id}/applyplan/real-write-readiness", response_class=HTMLResponse)
async def controlled_operation_cycle_applyplan_real_write_readiness(request: Request, cycle_id: str):
    cycle = _find_controlled_cycle(cycle_id)
    chain = load_cycle_real_write_chain_artifacts(ROOT, cycle["cycle_id"])
    return templates.TemplateResponse(
        "controlled_operation_real_write_readiness.html",
        {"request": request, "title": f"Real-write readiness: {cycle['cycle_id']}", "cycle": cycle, "chain": chain},
    )


@app.get("/controlled-operation/{cycle_id}/real-write-authorization", response_class=HTMLResponse)
async def controlled_operation_cycle_real_write_authorization(request: Request, cycle_id: str):
    cycle = _find_controlled_cycle(cycle_id)
    chain = load_cycle_real_write_chain_artifacts(ROOT, cycle["cycle_id"])
    return templates.TemplateResponse(
        "controlled_operation_real_write_authorization.html",
        {"request": request, "title": f"Real-write authorization: {cycle['cycle_id']}", "cycle": cycle, "chain": chain},
    )


@app.get("/controlled-operation/{cycle_id}/real-write-preflight", response_class=HTMLResponse)
async def controlled_operation_cycle_real_write_preflight(request: Request, cycle_id: str):
    cycle = _find_controlled_cycle(cycle_id)
    chain = load_cycle_real_write_chain_artifacts(ROOT, cycle["cycle_id"])
    return templates.TemplateResponse(
        "controlled_operation_real_write_preflight.html",
        {"request": request, "title": f"Real-write preflight: {cycle['cycle_id']}", "cycle": cycle, "chain": chain},
    )


@app.get("/controlled-operation/{cycle_id}/real-write-package", response_class=HTMLResponse)
async def controlled_operation_cycle_real_write_package(request: Request, cycle_id: str):
    cycle = _find_controlled_cycle(cycle_id)
    chain = load_cycle_real_write_chain_artifacts(ROOT, cycle["cycle_id"])
    return templates.TemplateResponse(
        "controlled_operation_real_write_package.html",
        {"request": request, "title": f"Real-write package: {cycle['cycle_id']}", "cycle": cycle, "chain": chain},
    )


@app.get("/controlled-operation/{cycle_id}/real-write-freeze", response_class=HTMLResponse)
async def controlled_operation_cycle_real_write_freeze(request: Request, cycle_id: str):
    cycle = _find_controlled_cycle(cycle_id)
    chain = load_cycle_real_write_chain_artifacts(ROOT, cycle["cycle_id"])
    return templates.TemplateResponse(
        "controlled_operation_real_write_freeze.html",
        {"request": request, "title": f"Real-write freeze: {cycle['cycle_id']}", "cycle": cycle, "chain": chain},
    )


@app.get("/controlled-operation/{cycle_id}/real-write/execution", response_class=HTMLResponse)
async def controlled_operation_cycle_real_write_execution(request: Request, cycle_id: str):
    cycle = _find_controlled_cycle(cycle_id)
    chain = load_cycle_real_write_chain_artifacts(ROOT, cycle["cycle_id"])
    return templates.TemplateResponse(
        "controlled_operation_real_write_execution.html",
        {"request": request, "title": f"Real-write execution: {cycle['cycle_id']}", "cycle": cycle, "chain": chain},
    )


@app.get("/controlled-operation/{cycle_id}/real-write/verification", response_class=HTMLResponse)
async def controlled_operation_cycle_real_write_verification(request: Request, cycle_id: str):
    cycle = _find_controlled_cycle(cycle_id)
    chain = load_cycle_real_write_chain_artifacts(ROOT, cycle["cycle_id"])
    return templates.TemplateResponse(
        "controlled_operation_real_write_verification.html",
        {"request": request, "title": f"Real-write verification: {cycle['cycle_id']}", "cycle": cycle, "chain": chain},
    )


@app.get("/controlled-operation/{cycle_id}/real-write/compliance", response_class=HTMLResponse)
async def controlled_operation_cycle_real_write_compliance(request: Request, cycle_id: str):
    cycle = _find_controlled_cycle(cycle_id)
    chain = load_cycle_real_write_chain_artifacts(ROOT, cycle["cycle_id"])
    return templates.TemplateResponse(
        "controlled_operation_real_write_compliance.html",
        {"request": request, "title": f"Real-write compliance: {cycle['cycle_id']}", "cycle": cycle, "chain": chain},
    )


@app.get("/controlled-operation/{cycle_id}/real-write/closure", response_class=HTMLResponse)
async def controlled_operation_cycle_real_write_closure(request: Request, cycle_id: str):
    cycle = _find_controlled_cycle(cycle_id)
    chain = load_cycle_real_write_chain_artifacts(ROOT, cycle["cycle_id"])
    return templates.TemplateResponse(
        "controlled_operation_real_write_closure.html",
        {"request": request, "title": f"Real-write closure: {cycle['cycle_id']}", "cycle": cycle, "chain": chain},
    )

@app.get("/service-engagement/{device}/responses/edit", response_class=HTMLResponse)
async def response_edit_form(request: Request, device: str):
    """Compatibility page for the pending-item editor."""
    pending_items = load_pending_items(device)
    context = {
        "request": request,
        "title": f"Pending Items: {device}",
        "device": device,
        "pending_items": pending_items,
        "pending_count": len(pending_items),
        "pending_counts": _count_pending_items(pending_items),
        "validation_command": _pending_validation_command(device),
    }
    return templates.TemplateResponse("response_edit.html", context)

@app.post("/service-engagement/{device}/responses/edit", response_class=JSONResponse)
async def response_edit_submit(request: Request, device: str):
    """Compatibility POST handler for local-only response saving."""
    try:
        data = await request.json()
        item = _resolve_pending_item(device, data)
        return _save_pending_item_response(device, item, data)
    except HTTPException as exc:
        return JSONResponse({"success": False, "error": exc.detail}, status_code=exc.status_code)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.get("/service-engagement/{device}/pending-items", response_class=HTMLResponse)
async def pending_items_view(request: Request, device: str, format: Optional[str] = Query(None)):
    """Return pending items as HTML or JSON."""
    pending_items = load_pending_items(device)
    if (format or "").lower() == "json" or "application/json" in request.headers.get("accept", "").lower():
        return JSONResponse({
            "device": device,
            "count": len(pending_items),
            "summary": _count_pending_items(pending_items),
            "items": pending_items,
        })

    context = {
        "request": request,
        "title": f"Pending Items: {device}",
        "device": device,
        "pending_items": pending_items,
        "pending_count": len(pending_items),
        "pending_counts": _count_pending_items(pending_items),
        "validation_command": _pending_validation_command(device),
    }
    return templates.TemplateResponse("service_engagement_pending_items.html", context)


@app.get("/service-engagement/{device}/pending-items/{safe_item_id}", response_class=JSONResponse)
async def pending_item_detail(request: Request, device: str, safe_item_id: str):
    """Return one pending item for the modal."""
    try:
        data = get_pending_item(device, safe_item_id)
        data["validation_command"] = _pending_validation_command(device)
        return JSONResponse({"success": True, **data})
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown item")


@app.post("/service-engagement/{device}/pending-items/{safe_item_id}/response", response_class=JSONResponse)
async def pending_item_response(request: Request, device: str, safe_item_id: str):
    """Save a local response for a single pending item."""
    try:
        payload = await request.json()
        item = _lookup_pending_item(device, safe_item_id)
        return _save_pending_item_response(device, item, payload)
    except HTTPException as exc:
        return JSONResponse({"success": False, "error": exc.detail}, status_code=exc.status_code)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)




# ============================================================================
# Week 2 Review Decision (FASE 2.35)
# ============================================================================

@app.get("/service-engagement/{device}/week2-review/items", response_class=JSONResponse)
async def week2_review_items(request: Request, device: str):
    """List Week 2 review items for decision."""
    compliance_dir = REPORTS_DIR / "pilot-device-compliance"
    review_dir = compliance_dir / "week2-review"
    drafts_dir = review_dir / "week2-approval-drafts"

    items = []
    if drafts_dir.exists():
        for draft_file in drafts_dir.glob("approval-draft-*.json"):
            try:
                draft_data = load_json(draft_file)
                if not draft_data:
                    continue

                safe_item_id = draft_file.stem.replace("approval-draft-", "")
                existing_decision = get_item_decision(safe_item_id, review_dir)

                items.append({
                    "item_id": safe_item_id,
                    "object_key": draft_data.get("object_key", ""),
                    "object_type": draft_data.get("object_type", ""),
                    "source_draft": draft_file.name,
                    "status": draft_data.get("status", "pending_review"),
                    "restriction": draft_data.get("restriction", "none"),
                    "evidence": draft_data.get("evidence", ""),
                    "owner": draft_data.get("owner", ""),
                    "current_decision": existing_decision.get("decision") if existing_decision else None,
                    "allowed_actions": [
                        "approve_for_approval_record",
                        "request_changes",
                        "reject",
                        "defer",
                        "block",
                    ],
                })
            except Exception:
                pass

    return JSONResponse({
        "device": device,
        "count": len(items),
        "items": items,
    })


@app.get("/service-engagement/{device}/week2-review/items/{safe_item_id}", response_class=JSONResponse)
async def week2_review_item_detail(request: Request, device: str, safe_item_id: str):
    """Return Week 2 review item detail for modal."""
    compliance_dir = REPORTS_DIR / "pilot-device-compliance"
    review_dir = compliance_dir / "week2-review"
    drafts_dir = review_dir / "week2-approval-drafts"

    draft_file = drafts_dir / f"approval-draft-{safe_item_id}.json"
    if not draft_file.exists():
        raise HTTPException(status_code=404, detail="Item not found")

    try:
        draft_data = load_json(draft_file)
        if not draft_data:
            raise HTTPException(status_code=404, detail="Could not load item")

        existing_decision = get_item_decision(safe_item_id, review_dir)

        return JSONResponse({
            "success": True,
            "item_id": safe_item_id,
            "object_key": draft_data.get("object_key", ""),
            "object_type": draft_data.get("object_type", ""),
            "category": draft_data.get("category", ""),
            "status": draft_data.get("status", "pending_review"),
            "restriction": draft_data.get("restriction", "none"),
            "evidence": draft_data.get("evidence", ""),
            "owner": draft_data.get("owner", ""),
            "action": draft_data.get("action", ""),
            "reason": draft_data.get("reason", ""),
            "allowed_to_promote": draft_data.get("allowed_to_promote", False),
            "current_decision": existing_decision,
            "allowed_actions": [
                "approve_for_approval_record",
                "request_changes",
                "reject",
                "defer",
                "block",
            ],
        })
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e),
        }, status_code=500)


@app.post("/service-engagement/{device}/week2-review/items/{safe_item_id}/decision", response_class=JSONResponse)
async def week2_review_item_decision(request: Request, device: str, safe_item_id: str):
    """Save Week 2 review decision locally (no NetBox, no AutoApprovalRecord)."""
    try:
        payload = await request.json()

        # Validate payload
        if not payload.get("reviewer"):
            return JSONResponse({
                "success": False,
                "error": "reviewer required",
            }, status_code=400)

        if not payload.get("decision"):
            return JSONResponse({
                "success": False,
                "error": "decision required",
            }, status_code=400)

        # Build decision object
        decision = Week2Decision(
            item_id=safe_item_id,
            reviewer=payload.get("reviewer", ""),
            decision=payload.get("decision", ""),
            reason=payload.get("reason"),
            notes=payload.get("notes"),
            approval_record_allowed=payload.get("approval_record_allowed", False),
        )

        # Save
        compliance_dir = REPORTS_DIR / "pilot-device-compliance"
        review_dir = compliance_dir / "week2-review"

        success, message = save_decision(decision, review_dir)
        if not success:
            return JSONResponse({
                "success": False,
                "error": message,
            }, status_code=400)

        # Return success
        return JSONResponse({
            "success": True,
            "message": message,
            "item_id": safe_item_id,
            "decision_summary": {
                "reviewer": decision.reviewer,
                "decision": decision.decision,
                "reason": decision.reason,
                "notes": decision.notes,
                "reviewed_at": decision.reviewed_at,
                "approval_record_allowed": decision.approval_record_allowed,
            },
            "next_step": "Decisão salva localmente. Sem ApprovalRecord automático. Validação local próxima.",
            "security": {
                "no_netbox_write": True,
                "no_token": True,
                "no_apply": True,
                "no_approval_record_auto": True,
            },
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e),
        }, status_code=500)


# ============================================================================
# Compliance Policies (FASE 3.17)
# ============================================================================

POLICY_WHITELIST = {
    "discovery-elements",
    "dependency-map",
    "naming-conventions",
    "snmp-policy",
    "interface-policy",
    "vrf-policy",
    "bgp-policy",
    "route-policy-policy",
    "ip-prefix-policy",
    "community-policy",
    "as-path-policy",
    "comments-policy",
    "compliance-severity-policy",
}

POLICY_DESCRIPTIONS = {
    "discovery-elements": "Elementos e estrutura de descoberta de rede",
    "dependency-map": "Mapa de dependências entre componentes",
    "naming-conventions": "Convenções de nomenclatura obrigatórias",
    "snmp-policy": "Política SNMP e monitoramento",
    "interface-policy": "Política de interfaces de rede",
    "vrf-policy": "Política de roteamento e VRF",
    "bgp-policy": "Política BGP e roteamento dinâmico",
    "route-policy-policy": "Política de roteamento avançada",
    "ip-prefix-policy": "Política de alocação de IPs",
    "community-policy": "Política de comunidades BGP",
    "as-path-policy": "Política de caminho AS",
    "comments-policy": "Política de documentação e comentários",
    "compliance-severity-policy": "Definição de severidades de compliance",
}


@app.get("/policies", response_class=JSONResponse)
async def list_policies(request: Request):
    """List all compliance policies."""
    policies_dir = ROOT / "policies" / "compliance"
    policies = []

    for policy_name in sorted(POLICY_WHITELIST):
        policy_file = policies_dir / f"{policy_name}.yaml"
        if policy_file.exists():
            try:
                content = policy_file.read_text(encoding="utf-8")
                # Check for secrets in content
                has_secrets = any(s in content.lower() for s in ["password", "token", "secret", "key"])
                policies.append({
                    "name": policy_name,
                    "file": f"{policy_name}.yaml",
                    "path": str(policy_file.relative_to(ROOT)),
                    "description": POLICY_DESCRIPTIONS.get(policy_name, ""),
                    "status": "valid",
                    "size_bytes": policy_file.stat().st_size,
                    "mtime": policy_file.stat().st_mtime,
                    "has_secrets_marker": has_secrets,
                })
            except Exception:
                pass

    return JSONResponse({
        "total": len(policies),
        "policies": policies,
        "whitelist_count": 13,
        "status": "active",
    })


@app.get("/policies/{policy_name}", response_class=JSONResponse)
async def get_policy(request: Request, policy_name: str):
    """Get a specific policy (whitelist enforced)."""
    # Validate policy name against whitelist
    if policy_name not in POLICY_WHITELIST:
        raise HTTPException(status_code=404, detail="Policy not found or not whitelisted")

    policies_dir = ROOT / "policies" / "compliance"
    policy_file = policies_dir / f"{policy_name}.yaml"

    if not policy_file.exists():
        raise HTTPException(status_code=404, detail="Policy file not found")

    try:
        content = policy_file.read_text(encoding="utf-8")

        # Mask any obvious secrets (defense in depth)
        lines = []
        for line in content.split("\n"):
            if any(secret_word in line.lower() for secret_word in ["password", "token", "secret", "api_key"]):
                # Replace values but keep structure
                line = line.split(":")[0] + ": [MASKED]" if ":" in line else "[MASKED]"
            lines.append(line)

        masked_content = "\n".join(lines)

        return JSONResponse({
            "success": True,
            "name": policy_name,
            "description": POLICY_DESCRIPTIONS.get(policy_name, ""),
            "content": masked_content,
            "content_type": "text/yaml",
            "status": "valid",
            "whitelisted": True,
            "size_bytes": len(content),
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e),
        }, status_code=500)


@app.get("/policies/impact", response_class=JSONResponse)
async def policies_impact(request: Request):
    """Get policies impact report (from FASE 2.34)."""
    impact_file = REPORTS_DIR / "compliance-policy-impact-report.md"
    baseline_file = REPORTS_DIR / "pilot-device-compliance" / "compliance-policy-impact-baseline.md"

    impact_content = ""
    baseline_content = ""

    if impact_file.exists():
        try:
            impact_content = impact_file.read_text(encoding="utf-8")
        except Exception:
            pass

    if baseline_file.exists():
        try:
            baseline_content = baseline_file.read_text(encoding="utf-8")
        except Exception:
            pass

    return JSONResponse({
        "success": True,
        "impact_report": impact_content,
        "baseline_report": baseline_content,
        "reports": {
            "impact": str(impact_file.relative_to(ROOT)) if impact_file.exists() else None,
            "baseline": str(baseline_file.relative_to(ROOT)) if baseline_file.exists() else None,
        },
    })


# ============================================================================
# FASE 3.19 — Real Write Post-Execution Integration
# ============================================================================

@app.get("/real-write", response_class=HTMLResponse)
async def real_write_overview(request: Request):
    """Real write post-execution overview."""
    device = "4WNET-MNS-KTG-RX"
    rw_dir = REPORTS_DIR / "pilot-device-compliance" / "real-write-execution"

    execution_file = rw_dir / "REAL-WRITE-EXECUTION-RESULT.json"
    verification_file = rw_dir / "POST-WRITE-VERIFICATION-RESULT.json"
    compliance_file = rw_dir / "POST-WRITE-COMPLIANCE-RESULT.json"
    closure_file = rw_dir / "closure" / "closure-summary.json"

    execution_data = load_json(execution_file) if execution_file.exists() else {}
    verification_data = load_json(verification_file) if verification_file.exists() else {}
    compliance_data = load_json(compliance_file) if compliance_file.exists() else {}
    closure_data = load_json(closure_file) if closure_file.exists() else {}

    context = {
        "request": request,
        "title": f"Real Write Execution — {device}",
        "device": device,
        "execution": execution_data,
        "verification": verification_data,
        "compliance": compliance_data,
        "closure": closure_data,
    }

    return templates.TemplateResponse("real_write_overview.html", context)


@app.get("/real-write/execution", response_class=HTMLResponse)
async def real_write_execution(request: Request):
    """Real write execution details."""
    device = "4WNET-MNS-KTG-RX"
    rw_dir = REPORTS_DIR / "pilot-device-compliance" / "real-write-execution"

    result_file = rw_dir / "REAL-WRITE-EXECUTION-RESULT.json"
    result_md = rw_dir / "REAL-WRITE-EXECUTION-RESULT.md"

    result_data = load_json(result_file) if result_file.exists() else {}
    result_text = render_markdown(load_markdown(result_md)) if result_md.exists() else "No execution result"

    context = {
        "request": request,
        "title": f"Real Write Execution — {device}",
        "device": device,
        "result": result_data,
        "result_html": result_text,
    }

    return templates.TemplateResponse("real_write_execution.html", context)


@app.get("/real-write/verification", response_class=HTMLResponse)
async def real_write_verification(request: Request):
    """Post-write verification details."""
    device = "4WNET-MNS-KTG-RX"
    rw_dir = REPORTS_DIR / "pilot-device-compliance" / "real-write-execution"

    result_file = rw_dir / "POST-WRITE-VERIFICATION-RESULT.json"
    result_md = rw_dir / "POST-WRITE-VERIFICATION-RESULT.md"

    result_data = load_json(result_file) if result_file.exists() else {}
    result_text = render_markdown(load_markdown(result_md)) if result_md.exists() else "No verification result"

    context = {
        "request": request,
        "title": f"Post-Write Verification — {device}",
        "device": device,
        "result": result_data,
        "result_html": result_text,
    }

    return templates.TemplateResponse("real_write_verification.html", context)


@app.get("/real-write/compliance", response_class=HTMLResponse)
async def real_write_compliance(request: Request):
    """Post-write compliance details."""
    device = "4WNET-MNS-KTG-RX"
    rw_dir = REPORTS_DIR / "pilot-device-compliance" / "real-write-execution"

    result_file = rw_dir / "POST-WRITE-COMPLIANCE-RESULT.json"
    result_md = rw_dir / "POST-WRITE-COMPLIANCE-RESULT.md"

    result_data = load_json(result_file) if result_file.exists() else {}
    result_text = render_markdown(load_markdown(result_md)) if result_md.exists() else "No compliance result"

    context = {
        "request": request,
        "title": f"Post-Write Compliance — {device}",
        "device": device,
        "result": result_data,
        "result_html": result_text,
    }

    return templates.TemplateResponse("real_write_compliance.html", context)


@app.get("/real-write/closure", response_class=HTMLResponse)
async def real_write_closure(request: Request):
    """Post-write closure decision."""
    device = "4WNET-MNS-KTG-RX"
    rw_dir = REPORTS_DIR / "pilot-device-compliance" / "real-write-execution"

    closure_file = rw_dir / "closure" / "closure-summary.json"
    closure_md = rw_dir / "CLOSURE-PACKAGE.md"

    closure_data = load_json(closure_file) if closure_file.exists() else {}
    closure_text = render_markdown(load_markdown(closure_md)) if closure_md.exists() else "No closure package"

    context = {
        "request": request,
        "title": f"Real Write Closure — {device}",
        "device": device,
        "closure": closure_data,
        "closure_html": closure_text,
    }

    return templates.TemplateResponse("real_write_closure.html", context)


# Compliance candidate discovery routes
@app.get("/compliance", response_class=HTMLResponse)
async def compliance_candidates_page(request: Request):
    """Compliance > Candidatos dashboard — no auto-load."""
    error = None

    # Check if NetBox is configured
    try:
        get_netbox_client()
    except NetBoxNotConfiguredError as e:
        error = f"NetBox não configurado: {e}"
    except NetBoxAuthError:
        error = "Falha de autenticação no NetBox (401/403). Verifique o NETBOX_TOKEN."
    except NetBoxClientError as e:
        error = f"Erro ao conectar ao NetBox: {e}"

    context = {
        "request": request,
        "title": "Compliance — Candidatos",
        "error": error,
    }

    return templates.TemplateResponse("compliance_candidates.html", context)


@app.get("/compliance/candidates", response_class=JSONResponse)
async def get_compliance_candidates(
    id: Optional[int] = Query(None),
    name: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    limit: int = Query(10),
    offset: int = Query(0),
    include_rejected: bool = Query(False),
):
    """Get compliance candidates as JSON — selective search only."""
    try:
        client = get_netbox_client()
        result = list_compliance_candidates(
            client,
            device_id=id,
            name=name,
            q=q,
            limit=limit,
            offset=offset,
            include_rejected=include_rejected,
        )
        return JSONResponse(result)
    except NetBoxNotConfiguredError:
        return JSONResponse(
            {"error": "NetBox não configurado. Defina NETBOX_URL e NETBOX_TOKEN."},
            status_code=503,
        )
    except NetBoxAuthError:
        return JSONResponse(
            {"error": "Falha de autenticação no NetBox (401/403)."},
            status_code=401,
        )
    except NetBoxClientError as e:
        return JSONResponse(
            {"error": f"Erro ao conectar ao NetBox: {e}"},
            status_code=500,
        )


@app.get("/compliance/jobs", response_class=HTMLResponse)
async def compliance_jobs_list(request: Request):
    """List prepared compliance jobs."""
    jobs = list_compliance_jobs()
    context = {
        "request": request,
        "title": "Compliance Jobs",
        "jobs": jobs,
    }
    return templates.TemplateResponse("compliance_jobs.html", context)


@app.get("/compliance/jobs/{job_id}", response_class=HTMLResponse)
async def compliance_job_detail(request: Request, job_id: str):
    """Show one compliance job detail page."""
    try:
        job = load_compliance_job(job_id)
    except KeyError:
        return HTMLResponse("<h1>Job not found</h1>", status_code=404)

    context = {
        "request": request,
        "title": f"Compliance Job: {job_id}",
        "job": job,
    }
    return templates.TemplateResponse("compliance_job_detail.html", context)


@app.post("/compliance/jobs/{job_id}/collection/start-gate", response_class=JSONResponse)
async def compliance_job_collection_start_gate(job_id: str, request: Request):
    """Prepare the read-only collection start gate."""
    try:
        payload = await request.json()
    except Exception as exc:
        return JSONResponse({"success": False, "error": f"Payload inválido: {exc}"}, status_code=400)

    operator = str(payload.get("operator") or "").strip()
    confirm = bool(payload.get("confirm"))
    if not operator:
        return JSONResponse({"success": False, "error": "operator é obrigatório"}, status_code=400)
    if confirm is not True:
        return JSONResponse({"success": False, "error": "confirm deve ser true"}, status_code=400)

    try:
        result = create_collection_start_gate(job_id, operator, confirm)
    except KeyError:
        return JSONResponse({"success": False, "error": "Job não encontrado"}, status_code=404)

    status_code = 200 if result["decision"] == "COLLECTION_START_GATE_READY" else 409
    return JSONResponse({"success": True, **result}, status_code=status_code)


@app.post("/compliance/jobs/{job_id}/collection/plan", response_class=JSONResponse)
async def compliance_job_collection_plan(job_id: str):
    """Create the local read-only collection plan."""
    try:
        result = create_collection_plan(job_id)
    except KeyError:
        return JSONResponse({"success": False, "error": "Job não encontrado"}, status_code=404)

    status_code = 200 if result["decision"] == "COLLECTION_PLAN_PREPARED" else 409
    return JSONResponse({"success": True, **result}, status_code=status_code)


@app.post("/compliance/jobs/{job_id}/collection/execute", response_class=JSONResponse)
async def compliance_job_collection_execute(job_id: str, request: Request):
    """Prepare the local read-only collection simulation."""
    try:
        payload = await request.json()
    except Exception as exc:
        return JSONResponse({"success": False, "error": f"Payload inválido: {exc}"}, status_code=400)

    operator = str(payload.get("operator") or "").strip()
    confirm_read_only = bool(payload.get("confirm_read_only"))
    if not operator:
        return JSONResponse({"success": False, "error": "operator é obrigatório"}, status_code=400)
    if confirm_read_only is not True:
        return JSONResponse({"success": False, "error": "confirm_read_only deve ser true"}, status_code=400)

    try:
        result = execute_collection_job(job_id, operator, simulation_only=True)
    except KeyError:
        return JSONResponse({"success": False, "error": "Job não encontrado"}, status_code=404)
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=409)

    status_code = 200 if result["decision"] == "COLLECTION_SAFETY_VALID" else 409
    return JSONResponse({"success": True, **result}, status_code=status_code)


@app.get("/compliance/jobs/{job_id}/collection/validation", response_class=JSONResponse)
async def compliance_job_collection_validation(job_id: str):
    """Return the local safety validation artifact."""
    try:
        result = load_collection_artifacts(job_id)
    except KeyError:
        return JSONResponse({"success": False, "error": "Job não encontrado"}, status_code=404)

    if not result.get("safety_validation"):
        return JSONResponse({"success": False, "error": "Validation not found"}, status_code=404)

    return JSONResponse({"success": True, **result})


@app.post("/compliance/jobs/{job_id}/collection/ssh-preflight", response_class=JSONResponse)
async def compliance_job_collection_ssh_preflight(job_id: str, request: Request):
    """Validate SSH preflight for read-only collection."""
    try:
        payload = await request.json()
    except Exception as exc:
        return JSONResponse({"success": False, "error": f"Payload inválido: {exc}"}, status_code=400)

    operator = str(payload.get("operator") or "").strip()
    confirm_read_only = bool(payload.get("confirm_read_only"))
    if not operator:
        return JSONResponse({"success": False, "error": "operator é obrigatório"}, status_code=400)
    if confirm_read_only is not True:
        return JSONResponse({"success": False, "error": "confirm_read_only deve ser true"}, status_code=400)

    try:
        result = run_ssh_preflight(job_id, operator, confirm_read_only)
    except KeyError:
        return JSONResponse({"success": False, "error": "Job não encontrado"}, status_code=404)

    status_code = 200 if result["decision"] != "SSH_PREFLIGHT_BLOCKED" else 409
    return JSONResponse({"success": True, **result}, status_code=status_code)


@app.post("/compliance/jobs/{job_id}/collection/ssh-execute", response_class=JSONResponse)
async def compliance_job_collection_ssh_execute(job_id: str, request: Request):
    """Execute controlled SSH read-only collection."""
    try:
        payload = await request.json()
    except Exception as exc:
        return JSONResponse({"success": False, "error": f"Payload inválido: {exc}"}, status_code=400)

    operator = str(payload.get("operator") or "").strip()
    confirm_execute_read_only = bool(payload.get("confirm_execute_read_only"))
    if not operator:
        return JSONResponse({"success": False, "error": "operator é obrigatório"}, status_code=400)
    if confirm_execute_read_only is not True:
        return JSONResponse({"success": False, "error": "confirm_execute_read_only deve ser true"}, status_code=400)

    try:
        result = execute_ssh_readonly_collection(job_id, operator, confirm_execute_read_only)
    except KeyError:
        return JSONResponse({"success": False, "error": "Job não encontrado"}, status_code=404)
    except RuntimeError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=503)

    validation = {}
    if result.get("decision") in {"SSH_COLLECTION_COMPLETED", "SSH_COLLECTION_COMPLETED_WITH_ERRORS"}:
        try:
            validation = validate_raw_collection_outputs(job_id)
        except KeyError:
            validation = {}

    status_code = 200 if result["decision"] in {"SSH_COLLECTION_COMPLETED", "SSH_COLLECTION_COMPLETED_WITH_ERRORS"} else 409
    return JSONResponse({"success": True, "raw_validation": validation, **result}, status_code=status_code)


@app.get("/compliance/jobs/{job_id}/collection/raw-validation", response_class=JSONResponse)
async def compliance_job_collection_raw_validation(job_id: str):
    """Return the raw output safety validation artifact."""
    try:
        load_compliance_job(job_id)
    except KeyError:
        return JSONResponse({"success": False, "error": "Job não encontrado"}, status_code=404)

    try:
        result = validate_raw_collection_outputs(job_id)
    except KeyError:
        return JSONResponse({"success": False, "error": "Job não encontrado"}, status_code=404)

    return JSONResponse({"success": True, **result})


@app.post("/compliance/jobs/{job_id}/parse", response_class=JSONResponse)
async def compliance_job_parse(job_id: str, request: Request):
    """Run the local Huawei NE8000 parser baseline."""
    try:
        payload = await request.json()
    except Exception as exc:
        return JSONResponse({"success": False, "error": f"Payload inválido: {exc}"}, status_code=400)

    operator = str(payload.get("operator") or "").strip()
    confirm_local_parse = bool(payload.get("confirm_local_parse"))
    if not operator:
        return JSONResponse({"success": False, "error": "operator é obrigatório"}, status_code=400)
    if confirm_local_parse is not True:
        return JSONResponse({"success": False, "error": "confirm_local_parse deve ser true"}, status_code=400)

    try:
        job = load_compliance_job(job_id)
    except KeyError:
        return JSONResponse({"success": False, "error": "Job não encontrado"}, status_code=404)

    parser_manifest = job.get("parser_manifest") or {}
    raw_validation = job.get("raw_output_safety_validation") or {}
    if not parser_manifest:
        return JSONResponse({"success": False, "error": "parser manifest ausente"}, status_code=409)
    if raw_validation.get("decision") == "RAW_OUTPUT_SAFETY_INVALID":
        return JSONResponse({"success": False, "error": "raw output safety validation inválida"}, status_code=409)

    try:
        result = parse_job_collection(job_id)
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=409)
    except KeyError:
        return JSONResponse({"success": False, "error": "Job não encontrado"}, status_code=404)

    status_code = 200 if result["decision"] in {"PARSER_COMPLETED", "PARSER_COMPLETED_WITH_WARNINGS"} else 409
    return JSONResponse({"success": True, **result}, status_code=status_code)


@app.get("/compliance/jobs/{job_id}/parse/validation", response_class=JSONResponse)
async def compliance_job_parse_validation(job_id: str):
    """Return parser safety validation artifact."""
    try:
        load_compliance_job(job_id)
    except KeyError:
        return JSONResponse({"success": False, "error": "Job não encontrado"}, status_code=404)

    try:
        result = validate_parser_outputs(job_id)
    except KeyError:
        return JSONResponse({"success": False, "error": "Job não encontrado"}, status_code=404)

    status_code = 200 if result["decision"] != "PARSER_SAFETY_INVALID" else 409
    return JSONResponse({"success": True, **result}, status_code=status_code)


@app.post("/compliance/jobs/{job_id}/compare", response_class=JSONResponse)
async def compliance_job_compare(job_id: str, request: Request):
    """Compare parsed inventory to compliance policies locally."""
    try:
        payload = await request.json()
    except Exception as exc:
        return JSONResponse({"success": False, "error": f"Payload inválido: {exc}"}, status_code=400)

    operator = str(payload.get("operator") or "").strip()
    confirm_local_compare = bool(payload.get("confirm_local_compare"))
    if not operator:
        return JSONResponse({"success": False, "error": "operator é obrigatório"}, status_code=400)
    if confirm_local_compare is not True:
        return JSONResponse({"success": False, "error": "confirm_local_compare deve ser true"}, status_code=400)

    try:
        job = load_compliance_job(job_id)
    except KeyError:
        return JSONResponse({"success": False, "error": "Job não encontrado"}, status_code=404)

    parser_result = job.get("parser_result") or {}
    parser_validation = job.get("parser_safety_validation") or {}
    if not parser_result:
        return JSONResponse({"success": False, "error": "parser-result.json ausente"}, status_code=409)
    if parser_validation.get("decision") == "PARSER_SAFETY_INVALID":
        return JSONResponse({"success": False, "error": "parser safety validation inválida"}, status_code=409)

    try:
        result = compare_job(job_id)
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=409)
    except KeyError:
        return JSONResponse({"success": False, "error": "Job não encontrado"}, status_code=404)

    status_code = 200 if result["decision"] != "COMPLIANCE_COMPARE_BLOCKED" else 409
    return JSONResponse({"success": True, **result}, status_code=status_code)


@app.post("/compliance/jobs/{job_id}/findings/{finding_id}/decision", response_class=JSONResponse)
async def compliance_finding_decision(job_id: str, finding_id: str, request: Request):
    """Record decision for a single finding."""
    try:
        payload = await request.json()
    except Exception as e:
        return JSONResponse({"success": False, "error": f"Payload inválido: {e}"}, status_code=400)

    from .services.compliance_findings_review import save_finding_decision

    try:
        result = save_finding_decision(job_id, finding_id, payload)
    except KeyError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=404)

    if not result.get("success"):
        return JSONResponse(result, status_code=400)

    return JSONResponse(result, status_code=200)


@app.get("/compliance/jobs/{job_id}/findings/review-summary", response_class=JSONResponse)
async def compliance_findings_review_summary(job_id: str, request: Request):
    """Get review summary for a job."""
    from .services.compliance_findings_review import summarize_review

    try:
        result = summarize_review(job_id)
    except KeyError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=404)

    return JSONResponse({"success": True, **result}, status_code=200)


@app.post("/compliance/jobs/{job_id}/remediation/draft-eligibility", response_class=JSONResponse)
async def compliance_remediation_draft_eligibility(job_id: str, request: Request):
    """Evaluate eligibility for remediation draft creation."""
    try:
        payload = await request.json()
    except Exception as e:
        return JSONResponse({"success": False, "error": f"Payload inválido: {e}"}, status_code=400)

    confirm = payload.get("confirm_review_complete")
    if confirm is not True:
        return JSONResponse({"success": False, "error": "confirm_review_complete deve ser true"}, status_code=400)

    from .services.compliance_findings_review import evaluate_remediation_draft_eligibility

    try:
        result = evaluate_remediation_draft_eligibility(job_id)
    except KeyError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=404)

    status_code = 200 if result["decision"] == "REMEDIATION_DRAFT_ELIGIBLE" else 409
    return JSONResponse({"success": True, **result}, status_code=status_code)


@app.get("/compliance/jobs/{job_id}/remediation/drafts", response_class=JSONResponse)
async def compliance_remediation_drafts(job_id: str, request: Request):
    """Load local remediation draft artifacts for a job."""
    from .services.compliance_remediation_drafts import load_remediation_drafts

    try:
        result = load_remediation_drafts(job_id)
    except KeyError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=404)

    return JSONResponse({"success": True, **result}, status_code=200)


@app.post("/compliance/jobs/{job_id}/remediation/drafts", response_class=JSONResponse)
async def compliance_generate_remediation_drafts(job_id: str, request: Request):
    """Generate local remediation drafts only."""
    try:
        payload = await request.json()
    except Exception as exc:
        return JSONResponse({"success": False, "error": f"Payload inválido: {exc}"}, status_code=400)

    operator = str(payload.get("operator") or "").strip()
    confirm_generate_drafts = payload.get("confirm_generate_drafts")
    if not operator:
        return JSONResponse({"success": False, "error": "operator é obrigatório"}, status_code=400)
    if confirm_generate_drafts is not True:
        return JSONResponse({"success": False, "error": "confirm_generate_drafts deve ser true"}, status_code=400)

    from .services.compliance_remediation_drafts import generate_remediation_drafts

    try:
        result = generate_remediation_drafts(job_id, operator)
    except KeyError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=404)

    if not result.get("success"):
        return JSONResponse(result, status_code=409)

    return JSONResponse(result, status_code=200)


@app.get("/compliance/jobs/{job_id}/remediation/drafts/validation", response_class=JSONResponse)
async def compliance_validate_remediation_drafts(job_id: str, request: Request):
    """Validate local remediation drafts for safety."""
    from .services.compliance_remediation_validation import validate_remediation_drafts

    try:
        result = validate_remediation_drafts(job_id)
    except KeyError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=404)

    status_code = 200 if result["decision"] != "REMEDIATION_DRAFTS_UNSAFE" else 409
    return JSONResponse({"success": True, **result}, status_code=status_code)


@app.post("/compliance/jobs/{job_id}/remediation/promotion-gate", response_class=JSONResponse)
async def compliance_remediation_promotion_gate(job_id: str, request: Request):
    """Gate remediation drafts for the next approval-candidate flow."""
    try:
        payload = await request.json()
    except Exception as exc:
        return JSONResponse({"success": False, "error": f"Payload inválido: {exc}"}, status_code=400)

    operator = str(payload.get("operator") or "").strip()
    confirm_human_reviewed_drafts = payload.get("confirm_human_reviewed_drafts")
    if not operator:
        return JSONResponse({"success": False, "error": "operator é obrigatório"}, status_code=400)
    if confirm_human_reviewed_drafts is not True:
        return JSONResponse(
            {"success": False, "error": "confirm_human_reviewed_drafts deve ser true"},
            status_code=400,
        )

    from .services.compliance_remediation_drafts import evaluate_remediation_promotion_gate

    try:
        result = evaluate_remediation_promotion_gate(job_id, operator, True)
    except KeyError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=404)

    status_code = 200 if result["decision"] != "REMEDIATION_PROMOTION_BLOCKED" else 409
    return JSONResponse(result, status_code=status_code)


@app.post("/compliance/jobs/{job_id}/approval-candidates", response_class=JSONResponse)
async def compliance_build_approval_candidates(job_id: str, request: Request):
    """Build approval candidates from safe remediation drafts."""
    try:
        payload = await request.json()
    except Exception as exc:
        return JSONResponse({"success": False, "error": f"Payload inválido: {exc}"}, status_code=400)

    operator = str(payload.get("operator") or "").strip()
    confirm_build_candidates = payload.get("confirm_build_candidates")
    if not operator:
        return JSONResponse({"success": False, "error": "operator é obrigatório"}, status_code=400)
    if confirm_build_candidates is not True:
        return JSONResponse(
            {"success": False, "error": "confirm_build_candidates deve ser true"},
            status_code=400,
        )

    from .services.compliance_approval_candidates import build_approval_candidates

    try:
        result = build_approval_candidates(job_id, operator)
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=409)
    except KeyError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=404)

    return JSONResponse({"success": True, **result}, status_code=200)


@app.get("/compliance/jobs/{job_id}/approval-candidates", response_class=JSONResponse)
async def compliance_get_approval_candidates(job_id: str, request: Request):
    """Get existing approval candidates."""
    from .services.compliance_approval_candidates import load_approval_candidates

    try:
        candidates = load_approval_candidates(job_id)
        if not candidates:
            return JSONResponse(
                {"success": True, "candidates": [], "candidate_count": 0},
                status_code=200
            )
        return JSONResponse({"success": True, **candidates}, status_code=200)
    except KeyError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=404)


@app.post("/compliance/jobs/{job_id}/approval-candidates/proposal-gate", response_class=JSONResponse)
async def compliance_approval_proposal_gate(job_id: str, request: Request):
    """Validate candidates and gate to ApprovalRecord proposal."""
    try:
        payload = await request.json()
    except Exception as exc:
        return JSONResponse({"success": False, "error": f"Payload inválido: {exc}"}, status_code=400)

    operator = str(payload.get("operator") or "").strip()
    confirm_human_reviewed_candidates = payload.get("confirm_human_reviewed_candidates")
    if not operator:
        return JSONResponse({"success": False, "error": "operator é obrigatório"}, status_code=400)
    if confirm_human_reviewed_candidates is not True:
        return JSONResponse(
            {"success": False, "error": "confirm_human_reviewed_candidates deve ser true"},
            status_code=400,
        )

    from .services.compliance_approval_validation import validate_approval_candidates
    from .services.compliance_approvalrecord_proposal_gate import evaluate_approvalrecord_proposal_gate

    try:
        validation_result = validate_approval_candidates(job_id)
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=409)
    except KeyError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=404)

    # Block if unsafe
    if validation_result.get("decision") == "APPROVAL_CANDIDATES_UNSAFE":
        return JSONResponse(
            {"success": False, "validation_decision": validation_result.get("decision"), **validation_result},
            status_code=409
        )

    # Evaluate proposal gate
    try:
        gate_result = evaluate_approvalrecord_proposal_gate(job_id, operator, confirm_human_reviewed_candidates)
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=409)

    status_code = 200 if gate_result.get("decision") in ("APPROVALRECORD_PROPOSAL_READY", "APPROVALRECORD_PROPOSAL_READY_WITH_WARNINGS") else 409
    return JSONResponse({"success": True, **gate_result}, status_code=status_code)


@app.post("/compliance/jobs/{job_id}/approval-records/proposed", response_class=JSONResponse)
async def compliance_build_proposed_approval_records(job_id: str, request: Request):
    """Build proposed ApprovalRecords from approval candidates."""
    try:
        payload = await request.json()
    except Exception as exc:
        return JSONResponse({"success": False, "error": f"Payload inválido: {exc}"}, status_code=400)

    operator = str(payload.get("operator") or "").strip()
    confirm_create_proposed_records = payload.get("confirm_create_proposed_records")
    if not operator:
        return JSONResponse({"success": False, "error": "operator é obrigatório"}, status_code=400)
    if confirm_create_proposed_records is not True:
        return JSONResponse(
            {"success": False, "error": "confirm_create_proposed_records deve ser true"},
            status_code=400,
        )

    from .services.compliance_approval_records import build_proposed_approval_records

    try:
        result = build_proposed_approval_records(job_id, operator)
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=409)
    except KeyError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=404)

    return JSONResponse({"success": True, **result}, status_code=200)


@app.get("/compliance/jobs/{job_id}/approval-records/proposed/validation", response_class=JSONResponse)
async def compliance_validate_proposed_approval_records(job_id: str, request: Request):
    """Validate proposed ApprovalRecords."""
    from .services.compliance_approval_record_validation import validate_proposed_approval_records

    try:
        result = validate_proposed_approval_records(job_id)
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=409)

    status_code = 200 if result["decision"] != "PROPOSED_APPROVAL_RECORDS_UNSAFE" else 409
    return JSONResponse({"success": True, **result}, status_code=status_code)


@app.post("/compliance/jobs/{job_id}/approval-records/applyplan-candidate-gate", response_class=JSONResponse)
async def compliance_applyplan_candidate_gate(job_id: str, request: Request):
    """Gate proposed records to ApplyPlan candidate builder."""
    try:
        payload = await request.json()
    except Exception as exc:
        return JSONResponse({"success": False, "error": f"Payload inválido: {exc}"}, status_code=400)

    operator = str(payload.get("operator") or "").strip()
    confirm_human_reviewed_proposed_records = payload.get("confirm_human_reviewed_proposed_records")
    if not operator:
        return JSONResponse({"success": False, "error": "operator é obrigatório"}, status_code=400)
    if confirm_human_reviewed_proposed_records is not True:
        return JSONResponse(
            {"success": False, "error": "confirm_human_reviewed_proposed_records deve ser true"},
            status_code=400,
        )

    from .services.compliance_approval_record_validation import validate_proposed_approval_records
    from .services.compliance_approval_records import load_proposed_approval_records

    try:
        validation = validate_proposed_approval_records(job_id)
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=409)

    if validation.get("decision") == "PROPOSED_APPROVAL_RECORDS_UNSAFE":
        return JSONResponse(
            {"success": False, "validation_decision": validation.get("decision"), **validation},
            status_code=409
        )

    # Determine gate decision
    if validation.get("decision") == "PROPOSED_APPROVAL_RECORDS_SAFE":
        gate_decision = "APPLYPLAN_CANDIDATE_READY"
    else:
        gate_decision = "APPLYPLAN_CANDIDATE_READY_WITH_WARNINGS"

    gate_result = {
        "job_id": job_id,
        "status": "gate_evaluated",
        "decision": gate_decision,
        "evaluated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "evaluated_by": operator,
        "validation_decision": validation.get("decision"),
        "safety": {
            "netbox_write": False,
            "device_write": False,
            "sync_called": False,
            "approval_record_created": False,
            "apply_plan_created": False
        }
    }

    status_code = 200 if gate_decision in ("APPLYPLAN_CANDIDATE_READY", "APPLYPLAN_CANDIDATE_READY_WITH_WARNINGS") else 409
    return JSONResponse({"success": True, **gate_result}, status_code=status_code)


@app.post("/compliance/jobs/{job_id}/applyplan/candidate", response_class=JSONResponse)
async def compliance_build_applyplan_candidate(job_id: str, request: Request):
    """Build ApplyPlan candidate from proposed ApprovalRecords."""
    try:
        payload = await request.json()
    except Exception as exc:
        return JSONResponse({"success": False, "error": f"Payload inválido: {exc}"}, status_code=400)

    operator = str(payload.get("operator") or "").strip()
    confirm_build_applyplan_candidate = payload.get("confirm_build_applyplan_candidate")
    if not operator:
        return JSONResponse({"success": False, "error": "operator é obrigatório"}, status_code=400)
    if confirm_build_applyplan_candidate is not True:
        return JSONResponse(
            {"success": False, "error": "confirm_build_applyplan_candidate deve ser true"},
            status_code=400,
        )

    from .services.compliance_applyplan_candidates import build_applyplan_candidate

    try:
        result = build_applyplan_candidate(job_id, operator)
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=409)
    except KeyError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=404)

    return JSONResponse({"success": True, **result}, status_code=200)


@app.get("/compliance/jobs/{job_id}/applyplan/candidate/validation", response_class=JSONResponse)
async def compliance_validate_applyplan_candidate(job_id: str, request: Request):
    """Validate ApplyPlan candidate."""
    from .services.compliance_applyplan_validation import validate_applyplan_candidate

    try:
        result = validate_applyplan_candidate(job_id)
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=409)

    status_code = 200 if result["decision"] != "APPLYPLAN_CANDIDATE_INVALID" else 409
    return JSONResponse({"success": True, **result}, status_code=status_code)


@app.post("/compliance/jobs/{job_id}/applyplan/dry-run", response_class=JSONResponse)
async def compliance_build_dryrun_applyplan(job_id: str, request: Request):
    """Build dry-run ApplyPlan."""
    try:
        payload = await request.json()
    except Exception as exc:
        return JSONResponse({"success": False, "error": f"Payload inválido: {exc}"}, status_code=400)

    operator = str(payload.get("operator") or "").strip()
    confirm_build_dry_run = payload.get("confirm_build_dry_run")
    if not operator or confirm_build_dry_run is not True:
        return JSONResponse({"success": False, "error": "operator e confirm_build_dry_run obrigatórios"}, status_code=400)

    from .services.compliance_dryrun_applyplan import build_dryrun_applyplan

    try:
        result = build_dryrun_applyplan(job_id, operator)
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=409)

    return JSONResponse({"success": True, **result}, status_code=200)


@app.get("/compliance/jobs/{job_id}/applyplan/dry-run/validation", response_class=JSONResponse)
async def compliance_validate_dryrun_applyplan(job_id: str, request: Request):
    """Validate dry-run ApplyPlan."""
    from .services.compliance_dryrun_applyplan import validate_dryrun_applyplan

    try:
        result = validate_dryrun_applyplan(job_id)
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=409)

    status_code = 200 if result["decision"] != "DRY_RUN_APPLYPLAN_INVALID" else 409
    return JSONResponse({"success": True, **result}, status_code=status_code)


@app.post("/compliance/jobs/{job_id}/applyplan/dry-run/execute", response_class=JSONResponse)
async def compliance_execute_dryrun(job_id: str, request: Request):
    """Execute dry-run simulation."""
    try:
        payload = await request.json()
    except Exception as exc:
        return JSONResponse({"success": False, "error": f"Payload inválido: {exc}"}, status_code=400)

    operator = str(payload.get("operator") or "").strip()
    confirm_dry_run_execution = payload.get("confirm_dry_run_execution")
    if not operator or confirm_dry_run_execution is not True:
        return JSONResponse({"success": False, "error": "operator e confirm_dry_run_execution obrigatórios"}, status_code=400)

    from .services.compliance_dryrun_execution import evaluate_dryrun_execution_gate, execute_dryrun_simulation

    try:
        gate = evaluate_dryrun_execution_gate(job_id, operator)
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=409)

    if gate.get("decision") != "DRY_RUN_EXECUTION_GATE_READY":
        return JSONResponse({"success": False, "error": "Dry-run execution gate not ready"}, status_code=409)

    try:
        result = execute_dryrun_simulation(job_id, operator)
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=409)

    return JSONResponse({"success": True, **result}, status_code=200)


@app.get("/compliance/jobs/{job_id}/applyplan/dry-run/execution-validation", response_class=JSONResponse)
async def compliance_validate_dryrun_execution(job_id: str, request: Request):
    """Validate dry-run execution result."""
    from .services.compliance_dryrun_execution import validate_dryrun_execution_result

    try:
        result = validate_dryrun_execution_result(job_id)
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=409)

    status_code = 200 if result["decision"] == "DRY_RUN_VALIDATION_PASSED" else 409
    return JSONResponse({"success": True, **result}, status_code=status_code)


@app.post("/compliance/jobs/{job_id}/real-write/readiness-gate", response_class=JSONResponse)
async def compliance_realwrite_readiness_gate(job_id: str, request: Request):
    """REALWRITE-001: Evaluate real-write readiness."""
    try:
        payload = await request.json()
    except Exception as exc:
        return JSONResponse({"success": False, "error": f"Payload inválido: {exc}"}, status_code=400)

    operator = str(payload.get("operator") or "").strip()
    confirm = payload.get("confirm_ready_for_real_write_gate")
    if not operator or confirm is not True:
        return JSONResponse({"success": False, "error": "operator e confirm obrigatórios"}, status_code=400)

    from .services.compliance_realwrite_execution import evaluate_realwrite_readiness_gate

    try:
        result = evaluate_realwrite_readiness_gate(job_id, operator)
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=409)

    return JSONResponse({"success": True, **result}, status_code=200)


@app.post("/compliance/jobs/{job_id}/real-write/authorization-package", response_class=JSONResponse)
async def compliance_build_authorization_package(job_id: str, request: Request):
    """REALWRITE-002: Build authorization package with required phrase."""
    try:
        payload = await request.json()
    except Exception as exc:
        return JSONResponse({"success": False, "error": f"Payload inválido: {exc}"}, status_code=400)

    operator = str(payload.get("operator") or "").strip()
    confirm = payload.get("confirm_build_authorization_package")
    if not operator or confirm is not True:
        return JSONResponse({"success": False, "error": "operator e confirm obrigatórios"}, status_code=400)

    from .services.compliance_realwrite_execution import build_realwrite_authorization_package

    try:
        result = build_realwrite_authorization_package(job_id, operator)
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=409)

    return JSONResponse({"success": True, **result}, status_code=200)


@app.post("/compliance/jobs/{job_id}/real-write/final-preflight", response_class=JSONResponse)
async def compliance_final_preflight_gate(job_id: str, request: Request):
    """REALWRITE-003: Final Preflight Gate with phrase validation."""
    try:
        payload = await request.json()
    except Exception as exc:
        return JSONResponse({"success": False, "error": f"Payload inválido: {exc}"}, status_code=400)

    operator = str(payload.get("operator") or "").strip()
    authorization_phrase = str(payload.get("authorization_phrase") or "").strip()
    confirm = payload.get("confirm_final_preflight")
    if not operator or not authorization_phrase or confirm is not True:
        return JSONResponse({"success": False, "error": "operator, authorization_phrase, confirm obrigatórios"}, status_code=400)

    from .services.compliance_realwrite_execution import validate_realwrite_authorization

    try:
        result = validate_realwrite_authorization(job_id, operator, authorization_phrase)
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=409)

    return JSONResponse({"success": True, **result}, status_code=200)


@app.post("/compliance/jobs/{job_id}/real-write/execution-package", response_class=JSONResponse)
async def compliance_build_execution_package(job_id: str, request: Request):
    """REALWRITE-004: Build execution package (execution_allowed locked)."""
    try:
        payload = await request.json()
    except Exception as exc:
        return JSONResponse({"success": False, "error": f"Payload inválido: {exc}"}, status_code=400)

    operator = str(payload.get("operator") or "").strip()
    confirm = payload.get("confirm_build_execution_package")
    if not operator or confirm is not True:
        return JSONResponse({"success": False, "error": "operator e confirm obrigatórios"}, status_code=400)

    from .services.compliance_realwrite_execution import build_realwrite_execution_package

    try:
        result = build_realwrite_execution_package(job_id, operator)
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=409)

    return JSONResponse({"success": True, **result}, status_code=200)


@app.get("/compliance/jobs/{job_id}/real-write/execution-package/validation", response_class=JSONResponse)
async def compliance_validate_execution_package(job_id: str, request: Request):
    """REALWRITE-005: Validate execution package."""
    from .services.compliance_realwrite_execution import validate_realwrite_execution_package

    try:
        result = validate_realwrite_execution_package(job_id)
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=409)

    status_code = 200 if result["decision"] == "EXECUTION_PACKAGE_VALID" else 409
    return JSONResponse({"success": True, **result}, status_code=status_code)


@app.post("/compliance/jobs/{job_id}/real-write/freeze", response_class=JSONResponse)
async def compliance_realwrite_freeze(job_id: str, request: Request):
    """REALWRITE-006: Final no-write freeze before execution."""
    try:
        payload = await request.json()
    except Exception as exc:
        return JSONResponse({"success": False, "error": f"Payload inválido: {exc}"}, status_code=400)

    operator = str(payload.get("operator") or "").strip()
    confirm = payload.get("confirm_no_write_freeze")
    if not operator or confirm is not True:
        return JSONResponse({"success": False, "error": "operator e confirm obrigatórios"}, status_code=400)

    from .services.compliance_realwrite_execution import evaluate_realwrite_freeze

    try:
        result = evaluate_realwrite_freeze(job_id, operator)
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=409)

    return JSONResponse({"success": True, **result}, status_code=200)


@app.post("/compliance/jobs/{job_id}/real-write/post-verification", response_class=JSONResponse)
async def compliance_post_verification(job_id: str, request: Request):
    """REALWRITE-008: Post-write verification — validate created objects."""
    try:
        payload = await request.json()
    except Exception as exc:
        return JSONResponse({"success": False, "error": f"Payload inválido: {exc}"}, status_code=400)

    operator = str(payload.get("operator") or "").strip()
    confirm = payload.get("confirm_post_verification")
    if not operator or confirm is not True:
        return JSONResponse({"success": False, "error": "operator e confirm obrigatórios"}, status_code=400)

    from .services.compliance_realwrite_postwrite import evaluate_postwrite_verification

    try:
        result = evaluate_postwrite_verification(job_id, operator)
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=409)

    status_code = 200 if "NOT_APPLICABLE" in result.get("decision", "") or result.get("decision") == "POSTWRITE_VERIFICATION_PASSED" else 409
    return JSONResponse({"success": True, **result}, status_code=status_code)


@app.post("/compliance/jobs/{job_id}/real-write/compliance-rerun", response_class=JSONResponse)
async def compliance_post_compliance_rerun(job_id: str, request: Request):
    """REALWRITE-009: Post-write compliance re-run — local comparison only."""
    try:
        payload = await request.json()
    except Exception as exc:
        return JSONResponse({"success": False, "error": f"Payload inválido: {exc}"}, status_code=400)

    operator = str(payload.get("operator") or "").strip()
    confirm = payload.get("confirm_compliance_rerun")
    if not operator or confirm is not True:
        return JSONResponse({"success": False, "error": "operator e confirm obrigatórios"}, status_code=400)

    from .services.compliance_realwrite_postwrite import evaluate_postwrite_compliance_rerun

    try:
        result = evaluate_postwrite_compliance_rerun(job_id, operator)
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=409)

    status_code = 200 if "NOT_APPLICABLE" in result.get("decision", "") or result.get("decision") == "COMPLIANCE_RERUN_PASSED" else 409
    return JSONResponse({"success": True, **result}, status_code=status_code)


@app.post("/compliance/jobs/{job_id}/real-write/closure", response_class=JSONResponse)
async def compliance_closure_package(job_id: str, request: Request):
    """REALWRITE-010: Build closure package and close job."""
    try:
        payload = await request.json()
    except Exception as exc:
        return JSONResponse({"success": False, "error": f"Payload inválido: {exc}"}, status_code=400)

    operator = str(payload.get("operator") or "").strip()
    confirm = payload.get("confirm_closure")
    if not operator or confirm is not True:
        return JSONResponse({"success": False, "error": "operator e confirm obrigatórios"}, status_code=400)

    from .services.compliance_realwrite_closure import build_realwrite_closure_package

    try:
        result = build_realwrite_closure_package(job_id, operator)
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=409)

    status_code = 200
    return JSONResponse({"success": True, **result}, status_code=status_code)


@app.get("/compliance/jobs/{job_id}/ops/readiness", response_class=JSONResponse)
async def compliance_ops_readiness(job_id: str, request: Request):
    """COMPLIANCE-OPS-001: Check job readiness for real-write execution."""
    from .services.compliance_ops_readiness import validate_compliance_job_realwrite_readiness

    try:
        result = validate_compliance_job_realwrite_readiness(job_id)
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=409)

    status_code = 200 if result.get("blocker_count", 0) == 0 else 409
    return JSONResponse({"success": True, **result}, status_code=status_code)


@app.post("/compliance/analyze", response_class=JSONResponse)
async def analyze_compliance(request: Request):
    """Manual compliance start guard — re-validates eligibility, creates job artifact."""
    try:
        payload = await request.json()
    except Exception as e:
        return JSONResponse(
            {"success": False, "error": f"Payload inválido: {e}"},
            status_code=400,
        )

    device_ids = payload.get("device_ids", [])
    if not isinstance(device_ids, list) or len(device_ids) == 0:
        return JSONResponse(
            {"success": False, "error": "device_ids deve ser uma lista não vazia"},
            status_code=400,
        )

    mode = payload.get("mode", "read_only")
    triggered_by = payload.get("triggered_by", "operator")

    try:
        client = get_netbox_client()
    except NetBoxNotConfiguredError:
        return JSONResponse(
            {"error": "NetBox não configurado. Defina NETBOX_URL e NETBOX_TOKEN."},
            status_code=503,
        )
    except NetBoxAuthError:
        return JSONResponse(
            {"error": "Falha de autenticação no NetBox (401/403)."},
            status_code=401,
        )

    confirmed_eligible = []
    ineligible = []
    candidates = []

    # Per-ID validation with enrichment
    for device_id in device_ids:
        try:
            device = client.get_device_by_id(device_id)
        except (NetBoxClientError, NetBoxAuthError):
            ineligible.append(device_id)
            continue

        if not device:
            ineligible.append(device_id)
            continue

        # Enrich tenant group if missing
        device, _ = enrich_tenant_group_if_missing(device, client)

        if is_compliance_candidate(device):
            confirmed_eligible.append(device_id)
            candidates.append(normalize_compliance_candidate(device))
        else:
            ineligible.append(device_id)

    if ineligible:
        return JSONResponse(
            {
                "success": False,
                "error": f"Dispositivos perderam elegibilidade: {ineligible}",
                "ineligible": ineligible,
                "confirmed_eligible": confirmed_eligible,
            },
            status_code=422,
        )

    # Create local job artifact
    try:
        job = create_compliance_job(device_ids, candidates, triggered_by, mode)
    except Exception as e:
        return JSONResponse(
            {"success": False, "error": f"Falha ao criar job: {e}"},
            status_code=500,
        )

    return JSONResponse(
        {
            "success": True,
            "status": "COMPLIANCE_JOB_PREPARED",
            "job_id": job["job_id"],
            "confirmed_eligible": confirmed_eligible,
            "ineligible": [],
            "message": "Job local de Compliance criado para revisão. Nenhuma coleta foi iniciada.",
            "safety": {**get_compliance_job_safety(), "read_only": True, "auto_compliance_started": False, "job_only": True},
        }
    )


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok", "version": "3.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8890)
