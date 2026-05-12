#!/bin/bash
# Start k3g Compliance Web UI on port 8890

cd /data/home-moved/Projects/_legacy_lowercase_projects/59-netbox_sync

# Kill any existing process on 8890
lsof -ti:8890 | xargs kill -9 2>/dev/null || true

# Load env vars
set -a
source k3g-monitoring-iac/.env.webui.local
set +a

# Start app with env vars
nohup python3 -m uvicorn k3g-monitoring-iac.webui.app:app --host 127.0.0.1 --port 8890 > /tmp/webui.log 2>&1 &

sleep 2
echo "Web UI started on http://127.0.0.1:8890"
echo "Logs: /tmp/webui.log"
echo "Env: NETBOX_URL=$NETBOX_URL"
