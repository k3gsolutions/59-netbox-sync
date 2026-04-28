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
    list_batch_results, list_incidents, list_comparisons, safe_resolve_path
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

    context = {
        "request": request,
        "title": "Compliance Dashboard",
        "total_devices": len(devices),
        "total_reports": len(reports),
        "total_approvals": len(approvals),
        "total_incidents": len(incidents),
        "latest_report": latest_report,
        "latest_batch": batch_results[0] if batch_results else None,
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
    resolved = safe_resolve_path(REPORTS_DIR, path)

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
    resolved = safe_resolve_path(REPORTS_DIR, path)

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
async def approvals_list(request: Request):
    """List all approval records."""
    approvals = list_approvals(ROOT)

    context = {
        "request": request,
        "title": "Approvals",
        "approvals": approvals,
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
async def apply_plans_list(request: Request):
    """List apply plans."""
    apply_plans = list_apply_plans(ROOT)

    context = {
        "request": request,
        "title": "Apply Plans",
        "apply_plans": apply_plans,
    }

    return templates.TemplateResponse("apply_plans.html", context)


# ============================================================================
# Batch Results
# ============================================================================

@app.get("/batch-results", response_class=HTMLResponse)
async def batch_results_list(request: Request):
    """List batch apply results."""
    results = list_batch_results(ROOT)

    context = {
        "request": request,
        "title": "Batch Results",
        "results": results,
    }

    return templates.TemplateResponse("batch_results.html", context)


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
    """Simple search across markdown files."""
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
                    # Find matching lines
                    lines = content.split("\n")
                    matching_lines = [
                        (i, line) for i, line in enumerate(lines)
                        if q.lower() in line.lower()
                    ]

                    rel_path = md_file.relative_to(ROOT)
                    results.append({
                        "file": str(rel_path),
                        "path": str(rel_path),
                        "matches": len(matching_lines),
                        "preview": matching_lines[0][1][:100] if matching_lines else "",
                    })
            except Exception:
                pass

    context = {
        "request": request,
        "title": "Search Results",
        "query": q,
        "results": results[:20],
    }

    return templates.TemplateResponse("search.html", context)


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
