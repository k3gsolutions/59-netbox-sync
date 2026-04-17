"""
Rotas de consulta direta ao NetBox (sem acessar o dispositivo).
Permite checar o estado atual dos objetos já sincronizados.
"""
import requests as req_lib
from fastapi import APIRouter, HTTPException
from typing import Optional

from app.api.schemas import NetBoxQueryRequest, NetBoxParams

router = APIRouter(prefix="/netbox", tags=["NetBox"])


# ─────────────────────────────────────────────────────────────────────────────
# Cliente NetBox mínimo (sem pynetbox — para manter leveza nos handlers)
# ─────────────────────────────────────────────────────────────────────────────

def _headers(token: str) -> dict:
    return {
        "Authorization": f"Token {token}",
        "Accept": "application/json",
    }


def _get_all(base_url: str, token: str, path: str,
             params: dict, verify: bool) -> list:
    """Busca todas as páginas de um endpoint NetBox e retorna lista consolidada."""
    url = f"{base_url.rstrip('/')}/api/{path}/"
    results = []
    while url:
        r = req_lib.get(url, headers=_headers(token),
                        params=params, verify=verify, timeout=15)
        if not r.ok:
            raise HTTPException(
                status_code=r.status_code,
                detail=f"NetBox [{path}]: {r.text[:200]}"
            )
        data = r.json()
        results.extend(data.get("results", []))
        url = data.get("next")       # próxima página (None quando acabar)
        params = {}                  # next já traz os params na URL
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Rotas
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/sessions",
    summary="Consultar sessões BGP no NetBox",
    description=(
        "Retorna as sessões BGP registradas no plugin `netbox-bgp`. "
        "Use `device_id` para filtrar por dispositivo."
    ),
)
async def query_sessions(body: NetBoxQueryRequest):
    nb = body.netbox
    params = {}
    if body.device_id:
        params["device_id"] = body.device_id
    try:
        sessions = _get_all(nb.url, nb.token, "plugins/bgp/session", params, nb.verify_ssl)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {
        "total": len(sessions),
        "sessions": [
            {
                "id":             s.get("id"),
                "name":           s.get("name"),
                "status":         s.get("status", {}).get("value"),
                "local_address":  s.get("local_address", {}).get("address") if s.get("local_address") else None,
                "remote_address": s.get("remote_address", {}).get("address") if s.get("remote_address") else None,
                "local_as":       s.get("local_as", {}).get("asn") if s.get("local_as") else None,
                "remote_as":      s.get("remote_as", {}).get("asn") if s.get("remote_as") else None,
                "description":    s.get("description"),
                "import_policies": [p.get("name") for p in (s.get("import_policies") or [])],
                "export_policies": [p.get("name") for p in (s.get("export_policies") or [])],
            }
            for s in sessions
        ],
    }


@router.post(
    "/interfaces",
    summary="Consultar interfaces no NetBox",
    description="Retorna as interfaces DCIM registradas para um dispositivo.",
)
async def query_interfaces(body: NetBoxQueryRequest):
    nb = body.netbox
    params = {}
    if body.device_id:
        params["device_id"] = body.device_id
    try:
        ifaces = _get_all(nb.url, nb.token, "dcim/interfaces", params, nb.verify_ssl)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {
        "total": len(ifaces),
        "interfaces": [
            {
                "id":          i.get("id"),
                "name":        i.get("name"),
                "type":        i.get("type", {}).get("value"),
                "enabled":     i.get("enabled"),
                "description": i.get("description"),
                "lag":         i.get("lag", {}).get("name") if i.get("lag") else None,
                "ip_addresses": [],  # preenchido abaixo
            }
            for i in ifaces
        ],
    }


@router.post(
    "/ip-addresses",
    summary="Consultar IPs no NetBox",
    description="Retorna endereços IP associados a um dispositivo.",
)
async def query_ips(body: NetBoxQueryRequest):
    nb = body.netbox
    params = {}
    if body.device_id:
        params["device_id"] = body.device_id
    try:
        ips = _get_all(nb.url, nb.token, "ipam/ip-addresses", params, nb.verify_ssl)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {
        "total": len(ips),
        "ip_addresses": [
            {
                "id":        ip.get("id"),
                "address":   ip.get("address"),
                "status":    ip.get("status", {}).get("value"),
                "interface": (
                    ip.get("assigned_object", {}).get("name")
                    if ip.get("assigned_object") else None
                ),
            }
            for ip in ips
        ],
    }


@router.post(
    "/routing-policies",
    summary="Consultar routing policies no NetBox",
    description="Retorna as route-policies registradas no plugin `netbox-bgp`.",
)
async def query_routing_policies(body: NetBoxQueryRequest):
    nb = body.netbox
    try:
        policies = _get_all(nb.url, nb.token, "plugins/bgp/routing-policy", {}, nb.verify_ssl)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {
        "total": len(policies),
        "routing_policies": [
            {"id": p.get("id"), "name": p.get("name"), "description": p.get("description")}
            for p in policies
        ],
    }


@router.post(
    "/prefix-lists",
    summary="Consultar prefix-lists no NetBox",
    description="Retorna as prefix-lists registradas no plugin `netbox-bgp`.",
)
async def query_prefix_lists(body: NetBoxQueryRequest):
    nb = body.netbox
    try:
        pls = _get_all(nb.url, nb.token, "plugins/bgp/prefix-list", {}, nb.verify_ssl)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {
        "total": len(pls),
        "prefix_lists": [
            {"id": pl.get("id"), "name": pl.get("name"), "family": pl.get("family", {}).get("value")}
            for pl in pls
        ],
    }


@router.post(
    "/vrfs",
    summary="Consultar VRFs no NetBox",
    description="Retorna as VRFs registradas no NetBox IPAM.",
)
async def query_vrfs(body: NetBoxQueryRequest):
    nb = body.netbox
    try:
        vrfs = _get_all(nb.url, nb.token, "ipam/vrfs", {}, nb.verify_ssl)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {
        "total": len(vrfs),
        "vrfs": [
            {"id": v.get("id"), "name": v.get("name"), "rd": v.get("rd")}
            for v in vrfs
        ],
    }
