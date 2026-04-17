"""
Rotas de coleta direta do dispositivo via SSH.
Não realiza nenhuma escrita no NetBox.
"""
import asyncio
from fastapi import APIRouter, HTTPException

from app.api.schemas import CollectRequest, CollectResponse, BGPSessionOut, InventorySummary
from app.drivers.huawei_netmiko import HuaweiNetmikoDriver
from app.collectors.huawei_ne8000 import HuaweiNE8000Collector
from app.normalizers.netbox_mapper import build_inventory

router = APIRouter(prefix="/device", tags=["Dispositivo"])


def _do_collect(req: CollectRequest) -> dict:
    """Executa a coleta SSH (bloqueante — roda em thread pool)."""
    driver = HuaweiNetmikoDriver(
        host=req.device.host,
        username=req.device.username,
        password=req.device.password,
        port=req.device.port,
    )
    driver.open()
    try:
        collector = HuaweiNE8000Collector(driver)
        raw = collector.collect_all()
        vrf_bgp = collector.collect_bgp_all_vrfs(raw.get("vrfs", ""))
        inventory = build_inventory(raw, vrf_bgp=vrf_bgp)
    finally:
        driver.close()
    return inventory


@router.post(
    "/collect",
    response_model=CollectResponse,
    summary="Coletar dados do dispositivo",
    description=(
        "Conecta ao dispositivo via SSH, coleta todos os dados "
        "(interfaces, IPs, VRFs, BGP, route-policies, prefix-lists, filtros AS-path) "
        "e retorna o inventário estruturado. **Não escreve nada no NetBox.**"
    ),
)
async def collect_device(req: CollectRequest):
    loop = asyncio.get_event_loop()
    try:
        inventory = await loop.run_in_executor(None, _do_collect, req)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erro na conexão SSH: {exc}")

    sessions = [
        BGPSessionOut(
            peer_ip=s.peer_ip,
            peer_as=s.peer_as,
            local_as=s.local_as,
            router_id=s.router_id,
            peer_type=s.peer_type,
            state=s.state,
            description=s.description,
            address_family=s.address_family,
            vrf=s.vrf,
            import_policy=s.import_policy,
            export_policy=s.export_policy,
        )
        for s in inventory.bgp_sessions
    ]

    return CollectResponse(
        summary=InventorySummary(
            interfaces=len(inventory.interfaces),
            ip_addresses=len(inventory.ip_addresses),
            vrfs=len(inventory.vrfs),
            vlans=len(inventory.vlans),
            bgp_sessions=len(inventory.bgp_sessions),
            route_policies=len(inventory.route_policies),
            prefix_lists=len(inventory.prefix_lists),
            as_path_filters=len(inventory.as_path_filters),
        ),
        bgp_sessions=sessions,
    )
