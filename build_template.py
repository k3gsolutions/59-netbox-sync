import os

SRC_HTML = "/home/suporte/projects/59-netbox_sync/webui/compliance.html"
SRC_CSS = "/home/suporte/projects/59-netbox_sync/webui/compliance.css"
SRC_JS = "/home/suporte/projects/59-netbox_sync/webui/compliance.js"

DEST_HTML = "/home/suporte/projects/59-netbox_sync/k3g-monitoring-iac/webui/templates/compliance_candidates.html"
DEST_CSS = "/home/suporte/projects/59-netbox_sync/k3g-monitoring-iac/webui/static/compliance_guided.css"
DEST_JS = "/home/suporte/projects/59-netbox_sync/k3g-monitoring-iac/webui/static/compliance_guided.js"

# 1. Copy CSS and JS
with open(SRC_CSS, "r") as f:
    css_content = f.read()
# Avoid css conflicts with main app
css_content = css_content.replace(".app-header {", ".wizard-app-header {")
with open(DEST_CSS, "w") as f:
    f.write(css_content)

with open(SRC_JS, "r") as f:
    js_content = f.read()
js_content = js_content.replace("localhost", "131.108.136.133")
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
