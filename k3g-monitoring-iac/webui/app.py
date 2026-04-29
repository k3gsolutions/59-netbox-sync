"""
Web UI for k3g-monitoring-iac — Read-only compliance and governance dashboard.

No writes, no tokens, no NetBox API calls.
"""

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from pathlib import Path
import json
from typing import Optional
from datetime import datetime

from .services.artifact_scanner import (
    list_reports, list_devices, list_approvals, list_apply_plans,
    list_batch_results, list_incidents, list_comparisons, safe_resolve_path,
    normalize_report_path
)
from .services.markdown_loader import load_markdown, render_markdown, load_json
from .services.report_index import load_index, get_latest_report, parse_report_metrics


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
    # Normalize path (accepts both "file.md" and "reports/file.md")
    normalized = normalize_report_path(path)
    if not normalized:
        return JSONResponse({"error": "Invalid path"}, status_code=400)

    resolved = safe_resolve_path(REPORTS_DIR, normalized)

    if not resolved or not resolved.exists():
        return JSONResponse({"error": "File not found"}, status_code=404)

    # Block downloads of sensitive files
    if "payload.local" in str(resolved) or "raw" in str(resolved):
        return JSONResponse({"error": "File blocked"}, status_code=403)

    if resolved.suffix not in {".md", ".json", ".txt"}:
        return JSONResponse({"error": "File type not allowed"}, status_code=403)

    return FileResponse(resolved, media_type="text/plain", filename=resolved.name)


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

    context = {
        "request": request,
        "title": f"Service Engagement: {device}",
        "device": device,
        "files": files,
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

    context = {
        "request": request,
        "title": f"Week 1 Responses: {device}",
        "device": device,
        "validation_file": validation_file,
        "validation_content": validation_content,
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

    context = {
        "request": request,
        "title": f"Week 2 Candidates: {device}",
        "device": device,
        "candidates_file": candidates_file,
        "candidates_content": candidates_content,
    }

    return templates.TemplateResponse("week2_candidates.html", context)


@app.get("/service-engagement/{device}/week2-review", response_class=HTMLResponse)
async def week2_review(request: Request, device: str):
    """Week 2 review board — ready for human review."""
    compliance_dir = REPORTS_DIR / "pilot-device-compliance"
    review_dir = compliance_dir / "week2-review"
    review_file = None
    review_content = None
    decisions_file = None

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

    context = {
        "request": request,
        "title": f"Week 2 Review Board: {device}",
        "device": device,
        "review_file": review_file,
        "review_content": review_content,
        "decisions_file": decisions_file,
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
                    drafts.append({
                        "name": draft_file.name,
                        "object_key": draft_data.get("object_key", ""),
                        "status": draft_data.get("status", ""),
                        "action": draft_data.get("action", ""),
                        "created_at": draft_data.get("created_at", ""),
                        "path": str(draft_file.relative_to(REPORTS_DIR)),
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
# Response edit forms (FASE 3.9.3)
# ============================================================================

from .services.response_forms import (
    save_response_csv, save_response_audit, update_edit_audit_log, get_latest_response
)
from .services.validators import (
    validate_subinterface_response, validate_bgp_response, validate_ip_response
)

@app.get("/service-engagement/{device}/responses/edit", response_class=HTMLResponse)
async def response_edit_form(request: Request, device: str):
    """Display response edit form."""
    context = {
        "request": request,
        "title": f"Response Edit: {device}",
        "device": device,
        "service_types": [
            'customer-internet', 'customer-l2vpn', 'customer-l3vpn', 'customer-transport',
            'carrier-transit', 'carrier-peering', 'ix-public', 'cdn-cache',
            'infra-backbone', 'infra-management'
        ],
        "criticalities": ['platinum', 'gold', 'silver', 'bronze'],
        "statuses": ['pending', 'answered', 'needs_clarification', 'blocked', 'rejected'],
    }
    return templates.TemplateResponse("response_edit.html", context)

@app.post("/service-engagement/{device}/responses/edit", response_class=JSONResponse)
async def response_edit_submit(request: Request, device: str):
    """Submit response edit form."""
    try:
        data = await request.json()
        team = data.get('team')
        object_type = data.get('object_type', '')

        if not team:
            return JSONResponse({"error": "team required"}, status_code=400)

        # Validate based on type
        if object_type == 'subinterface':
            valid, errors = validate_subinterface_response(data)
        elif object_type == 'bgp_peer':
            valid, errors = validate_bgp_response(data)
        elif object_type == 'ip_address':
            valid, errors = validate_ip_response(data)
        else:
            return JSONResponse({"error": f"unknown object_type: {object_type}"}, status_code=400)

        if not valid:
            return JSONResponse({
                "success": False,
                "errors": errors
            }, status_code=400)

        # Save CSV
        success, csv_path = save_response_csv(team, data, ROOT)
        if not success:
            return JSONResponse({
                "success": False,
                "error": f"Failed to save CSV: {csv_path}"
            }, status_code=500)

        # Save audit
        save_response_audit(team, data, ROOT)

        # Update audit log
        fields_changed = [k for k, v in data.items() if v and k not in ['team', 'object_type']]
        update_edit_audit_log(team, data.get('object_key', ''), fields_changed, 'valid', ROOT)

        return JSONResponse({
            "success": True,
            "message": f"Response saved to {csv_path}",
            "csv_path": csv_path,
            "device": device
        })

    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


# ============================================================================
# Health check
# ============================================================================

@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok", "version": "3.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8890)
