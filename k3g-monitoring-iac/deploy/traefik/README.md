# Traefik Web UI Route

This directory contains the dynamic Traefik configuration for the Web UI.

## Route

- Host: `bgpsync.devops.k3gsolutions.com.br`
- Backend: `http://127.0.0.1:8890`

## Notes

- `webui/app.py` is proxy-aware through `ProxyHeadersMiddleware`.
- The config assumes Traefik can reach the Web UI on the same host.
- If Traefik runs in a container and cannot reach `127.0.0.1`, replace the upstream URL with the host-reachable address for that deployment.
- HTTP redirects to HTTPS.

## Expected Traefik setup

- `entryPoints.web`
- `entryPoints.websecure`
- file provider enabled for this dynamic config

