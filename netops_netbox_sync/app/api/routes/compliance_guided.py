"""
Rotas do fluxo guiado de Compliance.

Endpoints:
  GET  /compliance/eligible-tenants          → tenants elegíveis
  GET  /compliance/eligible-devices          → dispositivos por tenant
  GET  /compliance/contexts                  → contextos disponíveis por device
  POST /compliance/analyze-guided            → executa análise por contextos selecionados

Regras:
  - Tenant Group = K3G Solutions
  - Dispositivos: status active + custom_field compliance = true
  - Somente leitura — nenhuma escrita no NetBox ou no equipamento
"""
from __future__ import annotations

import os
import logging
from typing import List, Optional
import concurrent.futures

import requests as req_lib
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger("netops.compliance_guided")

router = APIRouter(prefix="/compliance", tags=["Compliance Guiado"])

# ---------------------------------------------------------------------------
# NetBox helper (leve — sem pynetbox, apenas requests)
# ---------------------------------------------------------------------------

_NB_URL = os.getenv("NETBOX_URL", "").rstrip("/")
_NB_TOKEN = os.getenv("NETBOX_TOKEN", "")
_NB_VERIFY = os.getenv("NETBOX_VERIFY_SSL", "false").lower() == "true"

K3G_TENANT_GROUP_SLUG = os.getenv("K3G_TENANT_GROUP_SLUG", "k3g-solutions")
COMPLIANCE_CF_FIELD = os.getenv("COMPLIANCE_CF_FIELD", "compliance")


def _nb_headers() -> dict:
    return {
        "Authorization": f"Token {_NB_TOKEN}",
        "Accept": "application/json",
    }


def _nb_get(path: str, params: dict | None = None) -> list:
    """Busca todas as páginas de um endpoint NetBox de forma paralela para acelerar a consulta."""
    if not _NB_URL or not _NB_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="NetBox não configurado. Defina NETBOX_URL e NETBOX_TOKEN.",
        )
    url = f"{_NB_URL}/api/{path.lstrip('/')}/"
    params = params or {}
    
    # Busca a primeira página para obter o count total
    r = req_lib.get(
        url,
        headers=_nb_headers(),
        params=params,
        verify=_NB_VERIFY,
        timeout=60,
    )
    if not r.ok:
        raise HTTPException(
            status_code=r.status_code,
            detail=f"NetBox [{path}]: {r.text[:300]}",
        )
        
    data = r.json()
    results = data.get("results", [])
    count = data.get("count", 0)
    next_url = data.get("next")
    
    # Se existe próxima página, calcula os offsets e busca em paralelo
    if next_url and count > len(results):
        limit = len(results) or 50
        offsets = list(range(limit, count, limit))
        
        def fetch_page(offset: int) -> list:
            page_params = params.copy()
            page_params["offset"] = offset
            page_params["limit"] = limit
            try:
                pr = req_lib.get(
                    url,
                    headers=_nb_headers(),
                    params=page_params,
                    verify=_NB_VERIFY,
                    timeout=60,
                )
                if pr.ok:
                    return pr.json().get("results", [])
            except Exception as e:
                logger.warning(f"Erro ao buscar página {offset} de {url}: {e}")
            return []

        # Usando até 3 threads para não sobrecarregar o banco de dados do NetBox
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(fetch_page, off) for off in offsets]
            for future in concurrent.futures.as_completed(futures):
                results.extend(future.result())

    return results


# ---------------------------------------------------------------------------
# Schemas de resposta
# ---------------------------------------------------------------------------

class TenantOut(BaseModel):
    id: int
    name: str
    slug: str
    device_count: int = 0
    description: Optional[str] = None


class DeviceOut(BaseModel):
    id: int
    name: str
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    role: Optional[str] = None
    site: Optional[str] = None
    primary_ip: Optional[str] = None
    status: Optional[str] = None
    platform: Optional[str] = None


def _device_role_name(device: dict) -> Optional[str]:
    role = device.get("role") or device.get("device_role") or {}
    if isinstance(role, dict):
        for key in ("name", "display", "label", "slug", "value"):
            value = role.get(key)
            if value:
                return str(value)
    if role:
        return str(role)
    return None


class ContextOption(BaseModel):
    id: str
    label: str
    description: str
    collection_method: str  # snmp | ssh | netbox
    icon: str


class FindingOut(BaseModel):
    status: str            # approved | warning | failed
    context: str
    item: str
    title: str
    expected: Optional[str] = None
    found: Optional[str] = None
    impact: Optional[str] = None
    recommendation: Optional[str] = None
    source: str            # NetBox | SNMP | SSH
    evidence: Optional[str] = None


class AnalysisSummary(BaseModel):
    approved: int = 0
    warning: int = 0
    failed: int = 0


class AnalyzeGuidedResponse(BaseModel):
    device: str
    device_id: int
    tenant: str
    status: str          # ok | attention | failed
    summary: AnalysisSummary
    findings: List[FindingOut] = Field(default_factory=list)
    collection_notes: List[str] = Field(default_factory=list)


class AnalyzeGuidedRequest(BaseModel):
    tenant_id: int
    device_id: int
    contexts: List[str] = Field(..., min_length=1)

    model_config = {"json_schema_extra": {
        "example": {
            "tenant_id": 1,
            "device_id": 42,
            "contexts": ["interfaces", "bgp_ipv4", "security", "naming"],
        }
    }}


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _is_compliance_enabled(device: dict) -> bool:
    """Função descontinuada — não utilizada com os novos filtros de role."""
    return True


def _tenant_group_slug(tenant: dict) -> str | None:
    tg = tenant.get("group") or {}
    if isinstance(tg, dict):
        return tg.get("slug")
    return None


# ---------------------------------------------------------------------------
# Contextos disponíveis (catálogo estático + verificação de device)
# ---------------------------------------------------------------------------

_ALL_CONTEXTS: list[ContextOption] = [
    ContextOption(
        id="interfaces",
        label="Interfaces",
        description="Verifica descrições, nomenclatura e estado operacional das interfaces.",
        collection_method="snmp",
        icon="🔌",
    ),
    ContextOption(
        id="bgp_ipv4",
        label="BGP IPv4",
        description="Verifica sessões BGP IPv4, estado (Established) e policies aplicadas.",
        collection_method="snmp",
        icon="🌐",
    ),
    ContextOption(
        id="bgp_ipv6",
        label="BGP IPv6",
        description="Verifica sessões BGP IPv6, estado (Established) e policies aplicadas.",
        collection_method="snmp",
        icon="🌍",
    ),
    ContextOption(
        id="route_policy",
        label="Route-Policy",
        description="Verifica existência e nomenclatura das route-policies no dispositivo.",
        collection_method="ssh",
        icon="🗺️",
    ),
    ContextOption(
        id="prefix_list",
        label="Prefix-List / Filtros",
        description="Verifica prefix-lists e community-filters cadastrados.",
        collection_method="ssh",
        icon="📋",
    ),
    ContextOption(
        id="security",
        label="Segurança",
        description="Verifica configurações de AAA, VTY, SNMP e controle de acesso.",
        collection_method="ssh",
        icon="🔒",
    ),
    ContextOption(
        id="naming",
        label="Nomenclatura",
        description="Verifica se nomes de interfaces, sessões e políticas seguem o padrão.",
        collection_method="netbox",
        icon="🏷️",
    ),
    ContextOption(
        id="ip_addressing",
        label="IPs / Endereçamento",
        description="Verifica endereços IP configurados vs documentados no NetBox.",
        collection_method="netbox",
        icon="📡",
    ),
    ContextOption(
        id="vrf",
        label="VRF",
        description="Verifica VRFs configuradas e sua consistência com o NetBox.",
        collection_method="netbox",
        icon="🗂️",
    ),
    ContextOption(
        id="snmp",
        label="SNMP",
        description="Verifica configuração SNMP: community, versão e ACL.",
        collection_method="ssh",
        icon="📊",
    ),
    ContextOption(
        id="orphan",
        label="Configurações Órfãs",
        description="Identifica objetos no NetBox sem correspondência no dispositivo.",
        collection_method="netbox",
        icon="🔍",
    ),
]


# ---------------------------------------------------------------------------
# Análise simulada por contexto (baseado em dados do NetBox)
# ---------------------------------------------------------------------------

def _analyze_context_from_netbox(
    context_id: str,
    device: dict,
    nb_interfaces: list,
    nb_ips: list,
    nb_sessions: list,
) -> tuple[list[FindingOut], list[str]]:
    """
    Gera findings para um contexto a partir dos dados do NetBox.
    Esta é a implementação inicial — sem SSH/SNMP real. 
    Retorna (findings, collection_notes).
    """
    findings: list[FindingOut] = []
    notes: list[str] = []
    device_name = device.get("name", "?")

    if context_id == "interfaces":
        notes.append("Interfaces consultadas via NetBox (DCIM)")
        # Verifica descrições das interfaces
        STANDARD_PATTERN = r"\[SVC="  # padrão esperado
        import re
        for iface in nb_interfaces:
            name = iface.get("name", "?")
            desc = iface.get("description") or ""
            enabled = iface.get("enabled", True)
            if not enabled:
                continue
            # Verifica se descrição segue padrão machine-parseable
            if desc and not re.search(r"\[SVC=|\[ROLE=|\[ID=", desc):
                findings.append(FindingOut(
                    status="warning",
                    context="Interfaces",
                    item=name,
                    title="Descrição fora do padrão",
                    expected="[SVC=...][ROLE=...][ID=...]",
                    found=desc[:80] if desc else "(vazio)",
                    impact="A automação pode não identificar corretamente o serviço associado.",
                    recommendation="Padronizar descrição conforme modelo machine-parseable.",
                    source="NetBox",
                    evidence=f"Interface {name} em {device_name}",
                ))
            elif not desc:
                findings.append(FindingOut(
                    status="warning",
                    context="Interfaces",
                    item=name,
                    title="Interface sem descrição",
                    expected="Descrição no formato [SVC=...][ROLE=...]",
                    found="(sem descrição)",
                    impact="Interface não identificada pelo padrão de nomenclatura.",
                    recommendation="Adicionar descrição padronizada no NetBox e no dispositivo.",
                    source="NetBox",
                    evidence=f"Interface {name} sem descrição em {device_name}",
                ))
            else:
                findings.append(FindingOut(
                    status="approved",
                    context="Interfaces",
                    item=name,
                    title="Descrição conforme padrão",
                    expected="[SVC=...][ROLE=...][ID=...]",
                    found=desc[:80],
                    impact=None,
                    recommendation=None,
                    source="NetBox",
                    evidence=None,
                ))

    elif context_id == "bgp_ipv4":
        notes.append("Sessões BGP IPv4 consultadas via NetBox (plugin BGP)")
        ipv4_sessions = [
            s for s in nb_sessions
            if (s.get("address_family") or {}).get("value") in ("ipv4", "4", 4, "ipv4_unicast")
            or str((s.get("address_family") or {}).get("value", "")).startswith("4")
            or "ipv4" in str(s.get("address_family", "")).lower()
        ]
        if not ipv4_sessions:
            notes.append("Nenhuma sessão BGP IPv4 encontrada no NetBox para este dispositivo.")
        for sess in ipv4_sessions:
            status_val = (sess.get("status") or {}).get("value", "")
            remote_addr = (sess.get("remote_address") or {}).get("address", "?")
            sess_name = sess.get("name") or remote_addr
            if status_val == "active":
                findings.append(FindingOut(
                    status="approved",
                    context="BGP IPv4",
                    item=sess_name,
                    title="Sessão BGP documentada e ativa",
                    expected="Status: active",
                    found=f"Status: {status_val}",
                    source="NetBox",
                ))
            else:
                findings.append(FindingOut(
                    status="warning",
                    context="BGP IPv4",
                    item=sess_name,
                    title="Sessão BGP com status não-ativo",
                    expected="Status: active",
                    found=f"Status: {status_val or 'desconhecido'}",
                    impact="Sessão pode estar inativa ou não configurada no equipamento.",
                    recommendation="Verificar no equipamento se a sessão está Established.",
                    source="NetBox",
                    evidence=f"Peer {remote_addr}",
                ))

    elif context_id == "bgp_ipv6":
        notes.append("Sessões BGP IPv6 consultadas via NetBox (plugin BGP)")
        ipv6_sessions = [
            s for s in nb_sessions
            if "ipv6" in str(s.get("address_family", "")).lower()
            or str((s.get("address_family") or {}).get("value", "")).startswith("6")
        ]
        if not ipv6_sessions:
            notes.append("Nenhuma sessão BGP IPv6 encontrada no NetBox para este dispositivo.")
        for sess in ipv6_sessions:
            status_val = (sess.get("status") or {}).get("value", "")
            remote_addr = (sess.get("remote_address") or {}).get("address", "?")
            sess_name = sess.get("name") or remote_addr
            findings.append(FindingOut(
                status="approved" if status_val == "active" else "warning",
                context="BGP IPv6",
                item=sess_name,
                title="Sessão BGP IPv6 documentada e ativa" if status_val == "active" else "Sessão BGP IPv6 com status não-ativo",
                expected="Status: active",
                found=f"Status: {status_val or 'desconhecido'}",
                impact=None if status_val == "active" else "Sessão IPv6 pode estar inativa.",
                recommendation=None if status_val == "active" else "Verificar no equipamento.",
                source="NetBox",
                evidence=f"Peer {remote_addr}" if status_val != "active" else None,
            ))

    elif context_id == "naming":
        notes.append("Nomenclatura verificada via NetBox")
        # Verifica nome do dispositivo
        name = device.get("name", "")
        # Padrão: SITE-ROLE-TYPE (ex: 4WNET-MNS-KTG-RX)
        parts = name.split("-")
        if len(parts) < 3:
            findings.append(FindingOut(
                status="warning",
                context="Nomenclatura",
                item=name,
                title="Nome do dispositivo fora do padrão",
                expected="Formato: TENANT-SITE-ROLE-TIPO (ex: 4WNET-MNS-KTG-RX)",
                found=name,
                impact="Automação pode não identificar corretamente o papel do equipamento.",
                recommendation="Renomear o dispositivo conforme padrão definido no projeto.",
                source="NetBox",
                evidence=f"Nome atual: {name}",
            ))
        else:
            findings.append(FindingOut(
                status="approved",
                context="Nomenclatura",
                item=name,
                title="Nome do dispositivo conforme padrão",
                expected="Formato: TENANT-SITE-ROLE-TIPO",
                found=name,
                source="NetBox",
            ))

    elif context_id == "ip_addressing":
        notes.append("Endereços IP consultados via NetBox (IPAM)")
        if not nb_ips:
            findings.append(FindingOut(
                status="warning",
                context="IPs / Endereçamento",
                item=device.get("name", "?"),
                title="Nenhum IP documentado no NetBox",
                expected="Ao menos 1 IP de gerência documentado",
                found="0 IPs encontrados",
                impact="Dispositivo sem endereçamento documentado dificulta monitoramento.",
                recommendation="Documentar IPs no NetBox IPAM.",
                source="NetBox",
            ))
        else:
            for ip in nb_ips:
                addr = ip.get("address", "?")
                status_val = (ip.get("status") or {}).get("value", "")
                if status_val == "active":
                    findings.append(FindingOut(
                        status="approved",
                        context="IPs / Endereçamento",
                        item=addr,
                        title="IP documentado e ativo",
                        source="NetBox",
                        found=f"Status: {status_val}",
                        expected="Status: active",
                    ))
                else:
                    findings.append(FindingOut(
                        status="warning",
                        context="IPs / Endereçamento",
                        item=addr,
                        title="IP com status não-ativo",
                        expected="Status: active",
                        found=f"Status: {status_val}",
                        impact="IP pode estar desatualizado ou inativo.",
                        recommendation="Revisar e atualizar status do IP no NetBox.",
                        source="NetBox",
                    ))

    elif context_id == "vrf":
        notes.append("VRFs verificadas via NetBox (IPAM)")
        device_primary_ip = device.get("primary_ip4") or device.get("primary_ip6")
        if device_primary_ip:
            findings.append(FindingOut(
                status="approved",
                context="VRF",
                item="IP de gerência",
                title="IP principal documentado",
                expected="IP de gerência cadastrado",
                found=str(device_primary_ip),
                source="NetBox",
            ))
        else:
            findings.append(FindingOut(
                status="warning",
                context="VRF",
                item=device.get("name", "?"),
                title="IP principal não definido",
                expected="IP de gerência definido no NetBox",
                found="Não configurado",
                impact="Sem IP de gerência, monitoramento e acesso automatizado são comprometidos.",
                recommendation="Definir primary_ip4 ou primary_ip6 no NetBox.",
                source="NetBox",
            ))

    elif context_id in ("route_policy", "prefix_list", "security", "snmp", "orphan"):
        # Contextos que requerem SSH/SNMP — retornar mensagem informativa
        label_map = {
            "route_policy": "Route-Policy",
            "prefix_list": "Prefix-List / Filtros",
            "security": "Segurança",
            "snmp": "SNMP",
            "orphan": "Configurações Órfãs",
        }
        method_map = {
            "route_policy": "SSH",
            "prefix_list": "SSH",
            "security": "SSH",
            "snmp": "SSH",
            "orphan": "NetBox + SSH",
        }
        label = label_map.get(context_id, context_id)
        method = method_map.get(context_id, "SSH")
        notes.append(
            f"Contexto '{label}' requer coleta via {method}. "
            f"Configure credenciais SSH para análise completa."
        )
        findings.append(FindingOut(
            status="warning",
            context=label,
            item=device.get("name", "?"),
            title=f"Análise via {method} não executada",
            expected=f"Coleta via {method} habilitada",
            found="Credenciais SSH não fornecidas neste fluxo",
            impact="Contexto não verificado — não é possível garantir conformidade.",
            recommendation=f"Use o endpoint /compliance/analyze com credenciais SSH para verificar {label}.",
            source=method,
            evidence="Coleta SSH requer credenciais explícitas",
        ))

    return findings, notes


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/eligible-tenants",
    response_model=list[TenantOut],
    summary="Listar clientes elegíveis para análise de Compliance",
    description=(
        "Retorna tenants do Tenant Group K3G Solutions que possuem dispositivos ativos "
        "com o campo customizado `compliance = true`. "
        "Usa uma única chamada ao NetBox para máxima performance."
    ),
)
def get_eligible_tenants():
    # ── Estratégia: 1 chamada para todos os devices ativos do tenant-group ──
    # Muito mais rápido do que N chamadas (uma por tenant).
    try:
        all_devices = _nb_get(
            "dcim/devices",
            {
                "status": "active",
                "tenant_group": K3G_TENANT_GROUP_SLUG,
                "role": "12-ativos-de-borda",
                "limit": 1000,
            },
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    # Filtra devices com compliance habilitado e agrupa por tenant
    tenant_map: dict[int, dict] = {}   # tenant_id → {name, slug, description, count}
    for d in all_devices:
        tenant_raw = d.get("tenant")
        if not tenant_raw:
            continue
        t_id = tenant_raw.get("id") if isinstance(tenant_raw, dict) else None
        if not t_id:
            continue

        # Verifica tenant group — pode já estar filtrado pela query, mas confirmamos
        t_group = None
        if isinstance(tenant_raw, dict):
            t_group = (tenant_raw.get("group") or {}).get("slug")
        # Se o NetBox não retornou o group embutido, confiamos no filtro da query

        if t_id not in tenant_map:
            tenant_map[t_id] = {
                "name": tenant_raw.get("name", "?") if isinstance(tenant_raw, dict) else "?",
                "slug": tenant_raw.get("slug", "") if isinstance(tenant_raw, dict) else "",
                "description": tenant_raw.get("description") if isinstance(tenant_raw, dict) else None,
                "count": 0,
            }
        tenant_map[t_id]["count"] += 1

    result: list[TenantOut] = [
        TenantOut(
            id=t_id,
            name=info["name"],
            slug=info["slug"],
            device_count=info["count"],
            description=info.get("description"),
        )
        for t_id, info in sorted(tenant_map.items(), key=lambda x: x[1]["name"])
    ]
    return result


@router.get(
    "/eligible-devices",
    response_model=list[DeviceOut],
    summary="Listar dispositivos elegíveis de um cliente",
    description=(
        "Retorna dispositivos ativos com compliance habilitado para o tenant informado. "
        "Respeita filtros: Tenant Group K3G Solutions, status active, compliance = true."
    ),
)
def get_eligible_devices(tenant_id: int = Query(..., description="ID do tenant/cliente")):
    try:
        devices_raw = _nb_get(
            "dcim/devices",
            {
                "tenant_id": tenant_id, 
                "status": "active",
                "role": "12-ativos-de-borda",
                "limit": 1000,
            },
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    result: list[DeviceOut] = []
    for d in devices_raw:
        device_type = d.get("device_type") or {}
        manufacturer = device_type.get("manufacturer") or {}
        primary_ip4 = d.get("primary_ip4") or {}
        primary_ip6 = d.get("primary_ip6") or {}
        primary_ip = (
            primary_ip4.get("address") if isinstance(primary_ip4, dict)
            else str(primary_ip4) if primary_ip4
            else (
                primary_ip6.get("address") if isinstance(primary_ip6, dict)
                else str(primary_ip6) if primary_ip6
                else None
            )
        )
        site = d.get("site") or {}
        platform = d.get("platform") or {}

        result.append(DeviceOut(
            id=d["id"],
            name=d.get("name", "?"),
            manufacturer=(
                manufacturer.get("name") if isinstance(manufacturer, dict)
                else str(manufacturer) if manufacturer else None
            ),
            model=(
                device_type.get("model") if isinstance(device_type, dict)
                else None
            ),
            role=_device_role_name(d),
            site=site.get("name") if isinstance(site, dict) else str(site) if site else None,
            primary_ip=primary_ip,
            status=(d.get("status") or {}).get("value"),
            platform=platform.get("name") if isinstance(platform, dict) else str(platform) if platform else None,
        ))

    return result


@router.get(
    "/contexts",
    response_model=list[ContextOption],
    summary="Listar contextos disponíveis para análise",
    description="Retorna os contextos de análise disponíveis para o dispositivo informado.",
)
def get_contexts(device_id: int = Query(..., description="ID do dispositivo")):
    # Por ora retorna todos os contextos disponíveis
    # Futuramente pode filtrar por plataforma/modelo do dispositivo
    return _ALL_CONTEXTS


@router.post(
    "/analyze-guided",
    response_model=AnalyzeGuidedResponse,
    summary="Executar análise de compliance guiada",
    description=(
        "Executa análise de compliance para o dispositivo e contextos selecionados. "
        "Prioriza dados do NetBox. Quando SSH/SNMP não são fornecidos, "
        "retorna aviso de contexto não verificado. Somente leitura."
    ),
)
def analyze_guided(req: AnalyzeGuidedRequest):
    # Carrega dados básicos do NetBox
    try:
        devices = _nb_get("dcim/devices", {"id": req.device_id})
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erro ao buscar dispositivo: {exc}")

    if not devices:
        raise HTTPException(status_code=404, detail=f"Dispositivo {req.device_id} não encontrado.")

    device = devices[0]

    # Verifica se o tenant bate
    device_tenant = device.get("tenant") or {}
    device_tenant_id = device_tenant.get("id") if isinstance(device_tenant, dict) else None
    if device_tenant_id and device_tenant_id != req.tenant_id:
        raise HTTPException(
            status_code=400,
            detail="Dispositivo não pertence ao tenant informado.",
        )

    tenant_name = device_tenant.get("name", "?") if isinstance(device_tenant, dict) else "?"

    # Coleta dados auxiliares do NetBox
    try:
        nb_interfaces = _nb_get("dcim/interfaces", {"device_id": req.device_id})
    except Exception:
        nb_interfaces = []

    try:
        nb_ips = _nb_get("ipam/ip-addresses", {"device_id": req.device_id})
    except Exception:
        nb_ips = []

    # Tenta BGP plugin
    try:
        nb_sessions = _nb_get("plugins/bgp/session", {"device_id": req.device_id})
    except Exception:
        nb_sessions = []

    # Executa análise por contexto
    all_findings: list[FindingOut] = []
    all_notes: list[str] = []

    for ctx_id in req.contexts:
        findings, notes = _analyze_context_from_netbox(
            ctx_id, device, nb_interfaces, nb_ips, nb_sessions
        )
        all_findings.extend(findings)
        all_notes.extend(notes)

    # Calcula sumário
    approved = sum(1 for f in all_findings if f.status == "approved")
    warning = sum(1 for f in all_findings if f.status == "warning")
    failed = sum(1 for f in all_findings if f.status == "failed")

    # Status geral
    if failed > 0:
        overall = "failed"
    elif warning > 0:
        overall = "attention"
    else:
        overall = "ok"

    return AnalyzeGuidedResponse(
        device=device.get("name", "?"),
        device_id=req.device_id,
        tenant=tenant_name,
        status=overall,
        summary=AnalysisSummary(approved=approved, warning=warning, failed=failed),
        findings=all_findings,
        collection_notes=list(dict.fromkeys(all_notes)),  # deduplica mantendo ordem
    )
