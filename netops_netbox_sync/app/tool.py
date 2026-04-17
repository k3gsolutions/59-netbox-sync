#!/usr/bin/env python3
"""
netops_netbox_sync — Tool Interface (JSON in / JSON out)

Uso:
  # Via stdin
  echo '<json>' | python -m app.tool

  # Via argumento
  python -m app.tool '<json>'

  # Via arquivo
  python -m app.tool @params.json

Formato de entrada:
  {
    "device": {
      "host":     "192.168.1.1",
      "port":     22,
      "username": "admin",
      "password": "secret"
    },
    "netbox": {
      "url":        "http://netbox:8080",
      "token":      "abc...",
      "device_id":  5,           // obrigatório para action=update
      "verify_ssl": false
    },
    "action": "get" | "update"
  }

Saída get:
  {
    "status": "ok",
    "summary": { "interfaces": N, "bgp_sessions": N, ... },
    "bgp_sessions": [
      { "peer_ip": "...", "peer_as": N, "address_family": "ipv4", "vrf": null,
        "state": "Established", "peer_type": "EBGP", "description": "..." }
    ]
  }

Saída update:
  {
    "status": "ok",
    "inventory_summary": { "interfaces": N, ... },
    "bgp_changelog": {
      "totals":  { "created": N, "updated": N, "skipped": N },
      "by_type": { "BGPSession": {...}, ... },
      "detail":  [...]
    }
  }
"""
import json
import sys

from app.drivers.huawei_netmiko import HuaweiNetmikoDriver
from app.collectors.huawei_ne8000 import HuaweiNE8000Collector
from app.normalizers.netbox_mapper import build_inventory
from app.workflow.sync_device import run_update


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _ok(payload: dict) -> None:
    print(json.dumps({"status": "ok", **payload}, indent=2, ensure_ascii=False))


def _err(message: str, code: int = 1) -> None:
    print(json.dumps({"status": "error", "message": message}, indent=2, ensure_ascii=False),
          file=sys.stderr)
    sys.exit(code)


def _load_params() -> dict:
    """Lê JSON de stdin, argumento posicional ou @arquivo."""
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg.startswith("@"):
            with open(arg[1:], encoding="utf-8") as f:
                return json.load(f)
        return json.loads(arg)
    if not sys.stdin.isatty():
        return json.load(sys.stdin)
    _err("Nenhum parâmetro fornecido. Use stdin, argumento JSON ou @arquivo.json")


def _make_driver(dev: dict) -> HuaweiNetmikoDriver:
    return HuaweiNetmikoDriver(
        host=dev["host"],
        username=dev["username"],
        password=dev["password"],
        port=int(dev.get("port", 22)),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Ações
# ─────────────────────────────────────────────────────────────────────────────

def action_get(params: dict) -> None:
    """Coleta dados do dispositivo e retorna inventário estruturado."""
    dev = params["device"]
    driver = _make_driver(dev)
    driver.open()
    try:
        collector = HuaweiNE8000Collector(driver)
        raw = collector.collect_all()
        vrf_bgp = collector.collect_bgp_all_vrfs(raw.get("vrfs", ""))
        inventory = build_inventory(raw, vrf_bgp=vrf_bgp)
    finally:
        driver.close()

    sessions = [
        {
            "peer_ip":        s.peer_ip,
            "peer_as":        s.peer_as,
            "local_as":       s.local_as,
            "router_id":      s.router_id,
            "peer_type":      s.peer_type,
            "state":          s.state,
            "description":    s.description,
            "address_family": s.address_family,
            "vrf":            s.vrf,
            "import_policy":  s.import_policy,
            "export_policy":  s.export_policy,
        }
        for s in inventory.bgp_sessions
    ]

    _ok({
        "summary": {
            "interfaces":      len(inventory.interfaces),
            "ip_addresses":    len(inventory.ip_addresses),
            "vrfs":            len(inventory.vrfs),
            "vlans":           len(inventory.vlans),
            "bgp_sessions":    len(inventory.bgp_sessions),
            "route_policies":  len(inventory.route_policies),
            "prefix_lists":    len(inventory.prefix_lists),
            "as_path_filters": len(inventory.as_path_filters),
            "communities":     len(inventory.communities),
            "community_lists": len(inventory.community_lists),
        },
        "bgp_sessions": sessions,
    })


def action_update(params: dict) -> None:
    """Coleta dados do dispositivo e sincroniza com NetBox."""
    dev = params["device"]
    nb = params.get("netbox", {})

    raw_url = nb.get("url") or _err("netbox.url é obrigatório para action=update")
    nb_url = raw_url.rstrip("/")
    if nb_url.endswith("/api"):
        nb_url = nb_url[:-4]
    nb_token = nb.get("token") or _err("netbox.token é obrigatório para action=update")
    device_id = nb.get("device_id")
    if not device_id:
        _err("netbox.device_id é obrigatório para action=update")
    verify_ssl = bool(nb.get("verify_ssl", False))

    driver = _make_driver(dev)
    driver.open()
    try:
        result = run_update(driver, nb_url, nb_token, int(device_id), verify_ssl)
    finally:
        driver.close()

    _ok(result)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    try:
        params = _load_params()
    except (json.JSONDecodeError, FileNotFoundError) as exc:
        _err(f"Erro ao ler parâmetros: {exc}")

    action = params.get("action", "").lower()
    if not action:
        _err("Campo 'action' é obrigatório: 'get' ou 'update'")

    try:
        if action == "get":
            action_get(params)
        elif action == "update":
            action_update(params)
        else:
            _err(f"Ação desconhecida: '{action}'. Use 'get' ou 'update'")
    except KeyError as exc:
        _err(f"Parâmetro obrigatório ausente: {exc}")
    except Exception as exc:
        _err(f"{type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
