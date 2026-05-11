import os

ROOT = os.path.dirname(os.path.abspath(__file__))

SRC_HTML = os.path.join(ROOT, "webui/compliance.html")
SRC_CSS = os.path.join(ROOT, "webui/compliance.css")
SRC_JS = os.path.join(ROOT, "webui/compliance.js")

DEST_HTML = os.path.join(ROOT, "k3g-monitoring-iac/webui/templates/compliance_candidates.html")
DEST_CSS = os.path.join(ROOT, "k3g-monitoring-iac/webui/static/compliance_guided.css")
DEST_JS = os.path.join(ROOT, "k3g-monitoring-iac/webui/static/compliance_guided.js")

# 1. Copy CSS and JS
with open(SRC_CSS, "r") as f:
    css_content = f.read()
# Avoid css conflicts with main app
css_content = css_content.replace(".app-header {", ".wizard-app-header {")
for selector in (
    ".sidebar-logo-icon",
    ".sidebar-logo-text",
    ".sidebar-status",
    ".sidebar-footer",
    ".sidebar-link",
    ".sidebar-icon",
    ".sidebar-logo",
    ".sidebar-nav",
    ".sidebar",
):
    css_content = css_content.replace(selector, f"body:not(.app-layout) {selector}")
while "body:not(.app-layout) body:not(.app-layout)" in css_content:
    css_content = css_content.replace("body:not(.app-layout) body:not(.app-layout)", "body:not(.app-layout)")
css_content = css_content.replace("/* ── Main ── */\n.app-main {", "/* ── Main ── */\nbody:not(.app-layout) .app-main {")
css_content = css_content.replace(
    "  background: var(--bg);\n}\n\n/* ── Header ── */",
    "  background: var(--bg);\n}\n\nbody.app-layout .app-main,\nbody.app-layout .app-content {\n  min-width: 0;\n}\n\n/* ── Header ── */",
)
css_content = css_content.replace(
    ".wizard-container {\n  padding: 28px 32px 48px;\n  max-width: 920px;\n  width: 100%;\n  flex: 1;\n}",
    ".wizard-container {\n  padding: 20px 24px 40px;\n  width: 100%;\n  max-width: 100%;\n  flex: 1;\n  min-width: 0;\n}",
)
css_content = css_content.replace(
    "/* Findings Table */\n.findings-table {",
    "/* Findings Table */\n#findings-table-wrap {\n  width: 100%;\n  overflow-x: auto;\n}\n\n.findings-table {",
)
css_content = css_content.replace(
    ".findings-table {\n  width: 100%;",
    ".findings-table {\n  width: 100%;\n  min-width: 820px;",
)
css_content = css_content.replace("  .sidebar { display: none; }", "  body:not(.app-layout) .sidebar { display: none; }")
css_content = css_content.replace("  .app-main { margin-left: 0; }", "  body:not(.app-layout) .app-main { margin-left: 0; }")
with open(DEST_CSS, "w") as f:
    f.write(css_content)

with open(SRC_JS, "r") as f:
    js_content = f.read()
js_content = js_content.replace("let API_BASE = localStorage.getItem('api_base') || 'http://localhost:8888';", "let API_BASE = localStorage.getItem('api_base') || '';")
js_content = js_content.replace("const url = new URL(API_BASE);\n  $('api-url-badge').innerHTML = `<span class=\"mono\">${url.host}</span>`;", "const host = API_BASE ? new URL(API_BASE).host : window.location.host;\n  $('api-url-badge').innerHTML = `<span class=\"mono\">${host}</span>`;")
js_content = js_content.replace("    $('dot').className = 'status-dot ok';\n    $('api-status-label').textContent = 'API online';", "    if ($('dot')) $('dot').className = 'status-dot ok';\n    if ($('api-status-label')) $('api-status-label').textContent = 'API online';")
js_content = js_content.replace("    $('dot').className = 'status-dot error';\n    $('api-status-label').textContent = 'API offline';", "    if ($('dot')) $('dot').className = 'status-dot error';\n    if ($('api-status-label')) $('api-status-label').textContent = 'API offline';")
js_content = js_content.replace("const contexts = await apiFetch(`/compliance/contexts?device_id=${deviceId}`);", "const contexts = await apiFetch('/compliance/eligible-contexts');")
js_content = js_content.replace("  if (!url) return;\n  API_BASE = url;", "  API_BASE = url;")
js_content = js_content.replace("  localStorage.setItem('api_base', url);", "  if (url) {\n    localStorage.setItem('api_base', url);\n  } else {\n    localStorage.removeItem('api_base');\n  }")
js_content = js_content.replace("let API_KEY  = localStorage.getItem('api_key')  || '';", "let API_KEY  = localStorage.getItem('api_key')  || '';\n\nif (API_BASE === '/compliance/guided' || (window.location.protocol === 'https:' && API_BASE.startsWith('http://'))) {\n  API_BASE = '';\n  localStorage.removeItem('api_base');\n}")
with open(DEST_JS, "w") as f:
    f.write(js_content)

# 2. Build HTML
with open(SRC_HTML, "r") as f:
    html_lines = f.readlines()

# Extract from settings modal down to detail modal
start_idx = 0
end_idx = 0
header_start = 0
header_end = 0

for i, line in enumerate(html_lines):
    if "<!-- Header -->" in line:
        header_start = i
    if "<!-- API Settings Modal -->" in line:
        header_end = i
        start_idx = i
    if "<!-- ===== DETAIL MODAL ===== -->" in line:
        pass # we will include it
    if "<script" in line:
        end_idx = i
        break

header_content = "".join(html_lines[header_start:header_end]).replace('class="app-header"', 'class="wizard-app-header" style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 24px;"').replace("localhost", "131.108.136.133")
wizard_content = "".join(html_lines[start_idx:end_idx])
wizard_content = wizard_content.replace("</div><!-- /app-main -->", "")
wizard_content = wizard_content.replace('placeholder="http://localhost:8888" value="http://localhost:8888"', 'placeholder="Mesma origem do painel" value=""')

template_content = f"""{{% extends "base.html" %}}

{{% block title %}}Análise de Compliance Guiada{{% endblock %}}

{{% block content %}}
<link rel="stylesheet" href="{{{{ url_for('static', path='compliance_guided.css') }}}}">

{header_content}
{wizard_content}

<script src="{{{{ url_for('static', path='compliance_guided.js') }}}}"></script>
{{% endblock %}}
"""

with open(DEST_HTML, "w") as f:
    f.write(template_content)

print("Successfully built production template.")
