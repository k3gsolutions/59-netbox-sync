"""
Simplified web UI for k3g-monitoring-iac.

Read-only compliance dashboard.
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import json

from webui.services.artifact_scanner import (
    list_reports, list_devices, list_approvals, list_apply_plans,
    list_batch_results, list_incidents, list_comparisons, safe_resolve_path
)
from webui.services.markdown_loader import load_markdown, render_markdown, load_json


ROOT = Path(__file__).parent.parent
REPORTS_DIR = ROOT / "reports"

app = FastAPI(title="k3g Compliance Dashboard v3.0", version="3.0")

# Static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# ============================================================================
# HTML Helper
# ============================================================================

def page(title: str, content: str) -> str:
    """Generate HTML page."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} — k3g Compliance</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div class="container">
        <header>
            <h1><a href="/">⚙️ k3g Compliance & Governance v3.0</a></h1>
            <nav>
                <a href="/">Dashboard</a>
                <a href="/devices">Devices</a>
                <a href="/approvals">Approvals</a>
                <a href="/incidents">Incidents</a>
                <a href="/batch">Batch Results</a>
            </nav>
        </header>

        <main>
            <h2>{title}</h2>
            {content}
        </main>

        <footer>
            <p>Read-only compliance dashboard v3.0 — No writes, no tokens</p>
        </footer>
    </div>
</body>
</html>"""


# ============================================================================
# Dashboard
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def index():
    """Dashboard home page."""
    reports = list_reports(ROOT)
    devices = list_devices(ROOT)
    approvals = list_approvals(ROOT)
    batch_results = list_batch_results(ROOT)
    incidents = list_incidents(ROOT)

    content = f"""
    <div class="cards">
        <div class="card">
            <h3>{len(devices)}</h3>
            <p>Devices with History</p>
        </div>
        <div class="card">
            <h3>{len(reports)}</h3>
            <p>Compliance Reports</p>
        </div>
        <div class="card">
            <h3>{len(approvals)}</h3>
            <p>Approval Records</p>
        </div>
        <div class="card">
            <h3>{len(incidents)}</h3>
            <p>Incidents</p>
        </div>
    </div>

    <h3>Latest Batch Result</h3>
    <p>{f'<a href="/batch-results">{batch_results[0]["name"]}</a>' if batch_results else 'No batch results'}</p>

    <h3>Quick Links</h3>
    <ul>
        <li><a href="/devices">All Devices ({len(devices)})</a></li>
        <li><a href="/approvals">Approval Records ({len(approvals)})</a></li>
        <li><a href="/incidents">Incident Reports ({len(incidents)})</a></li>
        <li><a href="/batch">Batch Results ({len(batch_results)})</a></li>
    </ul>
    """

    return page("Dashboard", content)


# ============================================================================
# Devices
# ============================================================================

@app.get("/devices", response_class=HTMLResponse)
async def devices_list():
    """List devices."""
    devices = list_devices(ROOT)

    rows = "".join([
        f'<tr><td>{d["name"]}</td><td><a href="/devices/{d["name"]}" class="button-small">Details</a></td></tr>'
        for d in devices[:20]
    ])

    content = f"""
    <table>
        <thead>
            <tr><th>Device</th><th>Actions</th></tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
    <p>Showing {len(devices)} devices</p>
    """

    return page("Devices", content)


# ============================================================================
# Approvals
# ============================================================================

@app.get("/approvals", response_class=HTMLResponse)
async def approvals_list():
    """List approvals."""
    approvals = list_approvals(ROOT)

    rows = "".join([
        f'<tr><td>{a["name"]}</td><td><span class="badge badge-{a["status"]}">{a["status"]}</span></td><td><a href="/reports/view?path={a["path"]}" class="button-small">View</a></td></tr>'
        for a in approvals[:20]
    ])

    content = f"""
    <table>
        <thead>
            <tr><th>Name</th><th>Status</th><th>Actions</th></tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
    <p>Showing {len(approvals)} approvals</p>
    """

    return page("Approvals", content)


# ============================================================================
# Incidents
# ============================================================================

@app.get("/incidents", response_class=HTMLResponse)
async def incidents_list():
    """List incidents."""
    incidents = list_incidents(ROOT)

    rows = "".join([
        f'<tr><td>{i["name"]}</td><td><a href="/reports/view?path={i["path"]}" class="button-small">View</a></td></tr>'
        for i in incidents[:20]
    ])

    content = f"""
    <table>
        <thead>
            <tr><th>Name</th><th>Actions</th></tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
    <p>Showing {len(incidents)} incidents</p>
    """

    return page("Incidents", content)


# ============================================================================
# Batch Results
# ============================================================================

@app.get("/batch", response_class=HTMLResponse)
async def batch_results():
    """List batch results."""
    results = list_batch_results(ROOT)

    rows = "".join([
        f'<tr><td>{r["name"]}</td><td><a href="/reports/view?path={r["path"]}" class="button-small">View</a></td></tr>'
        for r in results[:20]
    ])

    content = f"""
    <table>
        <thead>
            <tr><th>Name</th><th>Actions</th></tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
    <p>Showing {len(results)} batch results</p>
    """

    return page("Batch Results", content)


# ============================================================================
# Report Viewer
# ============================================================================

@app.get("/reports/view", response_class=HTMLResponse)
async def view_report(path: str):
    """View markdown report."""
    resolved = safe_resolve_path(REPORTS_DIR, path)

    if not resolved or not resolved.exists():
        return page("Error", "<p>Report not found</p>")

    content_md = load_markdown(resolved)
    if not content_md:
        return page("Error", "<p>Could not load report</p>")

    html_content = render_markdown(content_md)

    content = f"""
    <p><a href="/reports/download?path={path}" class="button">Download .md</a></p>
    <div class="report-content">
        {html_content}
    </div>
    """

    return page("Report", content)


# ============================================================================
# Download
# ============================================================================

@app.get("/reports/download")
async def download_report(path: str):
    """Download file safely."""
    resolved = safe_resolve_path(REPORTS_DIR, path)

    if not resolved or not resolved.exists():
        return JSONResponse({"error": "File not found"}, status_code=404)

    if resolved.suffix not in {".md", ".json", ".txt"}:
        return JSONResponse({"error": "File type not allowed"}, status_code=403)

    return FileResponse(resolved, filename=resolved.name)


# ============================================================================
# Health
# ============================================================================

@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok", "version": "3.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8890)
