"""
Rota de análise read-only do dispositivo.
"""
import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from netmiko.exceptions import NetMikoAuthenticationException, NetMikoTimeoutException
from paramiko.ssh_exception import SSHException

from app.api.schemas_analyze import AnalyzeRequest
from app.reports.markdown_compliance import render_compliance_report
from app.reports.import_plan_markdown import render_import_plan
from app.schemas.analyze import AnalyzeResult
from app.schemas.import_plan import ImportPlan
from app.compliance.import_plan import build_import_plan
from app.drivers.huawei_netmiko import HuaweiNetmikoDriver
from app.workflow.analyze_device import run_analyze_device

router = APIRouter(prefix="/compliance", tags=["Compliance"])


def _do_analyze(req: AnalyzeRequest) -> AnalyzeResult:
    driver = HuaweiNetmikoDriver(
        host=req.device.host,
        username=req.device.username,
        password=req.device.password.get_secret_value(),
        port=req.device.port,
    )
    driver.open()
    try:
        result = run_analyze_device(
            driver,
            device_id=req.device_id,
            device_name=req.device_name,
            netbox=req.netbox,
        )
    finally:
        driver.close()
    return result


def _is_ssh_error(exc: Exception) -> bool:
    return isinstance(exc, (NetMikoAuthenticationException, NetMikoTimeoutException, SSHException))


@router.post(
    "/analyze",
    response_model=AnalyzeResult,
    summary="Analisar dispositivo em modo read-only",
    description=(
        "Conecta ao dispositivo via SSH, coleta dados e gera um resultado de análise "
        "sem escrever no NetBox."
    ),
)
async def analyze_device(req: AnalyzeRequest):
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, _do_analyze, req)
    except Exception as exc:
        if _is_ssh_error(exc):
            raise HTTPException(status_code=502, detail=f"Erro na conexão SSH: {exc}")
        raise

    return result


@router.post(
    "/analyze/report",
    response_class=PlainTextResponse,
    summary="Gerar relatório Markdown de compliance",
    description=(
        "Executa o fluxo de análise read-only e retorna um relatório de compliance em formato Markdown. "
        "Não escreve no NetBox nem aplica configuração."
    ),
)
async def analyze_device_report(req: AnalyzeRequest):
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, _do_analyze, req)
    except Exception as exc:
        if _is_ssh_error(exc):
            raise HTTPException(status_code=502, detail=f"Erro na conexão SSH: {exc}")
        raise

    return render_compliance_report(result)


@router.post(
    "/import-plan",
    response_model=ImportPlan,
    summary="Gerar plano de importação (read-only)",
    description=(
        "Executa o fluxo de análise e classifica divergências em ações de importação. "
        "Nenhuma escrita no NetBox ou aplicação de configuração. "
        "Apenas recomendações baseadas em regras de importação."
    ),
)
async def generate_import_plan(req: AnalyzeRequest):
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, _do_analyze, req)
    except Exception as exc:
        if _is_ssh_error(exc):
            raise HTTPException(status_code=502, detail=f"Erro na conexão SSH: {exc}")
        raise

    plan = build_import_plan(result)
    return plan


@router.post(
    "/import-plan/report",
    response_class=PlainTextResponse,
    summary="Gerar relatório de importação em Markdown (read-only)",
    description=(
        "Executa o fluxo de análise, classifica divergências e retorna um relatório em Markdown. "
        "Inclui seções de safe_create_staged, revisão obrigatória, bloqueados, ignorados e observações de segurança. "
        "Nenhuma ação é executada."
    ),
)
async def generate_import_plan_report(req: AnalyzeRequest):
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, _do_analyze, req)
    except Exception as exc:
        if _is_ssh_error(exc):
            raise HTTPException(status_code=502, detail=f"Erro na conexão SSH: {exc}")
        raise

    plan = build_import_plan(result)
    return render_import_plan(plan)
