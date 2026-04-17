"""
Rota de sincronização: coleta dados do dispositivo e envia ao NetBox.
"""
import asyncio
from fastapi import APIRouter, HTTPException

from app.api.schemas import SyncRequest, SyncResponse
from app.drivers.huawei_netmiko import HuaweiNetmikoDriver
from app.workflow.sync_device import run_update

router = APIRouter(prefix="/sync", tags=["Sincronização"])


def _do_sync(req: SyncRequest) -> dict:
    """Executa coleta SSH + sync NetBox (bloqueante — roda em thread pool)."""
    driver = HuaweiNetmikoDriver(
        host=req.device.host,
        username=req.device.username,
        password=req.device.password,
        port=req.device.port,
    )
    driver.open()
    try:
        result = run_update(
            driver=driver,
            nb_url=req.netbox.url,
            nb_token=req.netbox.token,
            device_id=req.device_id,
            verify_ssl=req.netbox.verify_ssl,
        )
    finally:
        driver.close()
    return result


@router.post(
    "",
    response_model=SyncResponse,
    summary="Sincronizar dispositivo com o NetBox",
    description=(
        "Conecta ao dispositivo via SSH, coleta todos os dados e sincroniza com o NetBox:\n\n"
        "1. **Interfaces** (com tipos e membros LACP)\n"
        "2. **IPs** vinculados às interfaces\n"
        "3. **VRFs** e VLANs\n"
        "4. **Sessões BGP** de todas as address-families e VRFs (via plugin `netbox-bgp`)\n"
        "5. **Route-policies**, **prefix-lists** e **filtros AS-path**\n\n"
        "Retorna um changelog detalhado de todas as criações e atualizações."
    ),
)
async def sync_device(req: SyncRequest):
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, _do_sync, req)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=f"Erro de sincronização: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erro na conexão SSH: {exc}")

    return SyncResponse(
        inventory_summary=result["inventory_summary"],
        bgp_changelog=result["bgp_changelog"],
    )
