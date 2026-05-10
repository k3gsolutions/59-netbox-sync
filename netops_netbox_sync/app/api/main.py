"""
netops_netbox_sync — API FastAPI

Iniciar:
    uvicorn app.api.main:app --host 0.0.0.0 --port 8888 --reload

Docs interativas:
    http://localhost:8888/docs      (Swagger UI)
    http://localhost:8888/redoc     (ReDoc)
"""
import os
import time
import logging
from contextlib import asynccontextmanager

import pathlib
from fastapi import FastAPI, Request, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import compliance, compliance_guided, device, netbox, sync

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("netops.api")


# ─────────────────────────────────────────────────────────────────────────────
# Autenticação por API Key (opcional)
# Configure via variável de ambiente API_KEY.
# Se não definida, autenticação é desabilitada.
# ─────────────────────────────────────────────────────────────────────────────
API_KEY = os.getenv("API_KEY", "")
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(key: str = Security(_api_key_header)):
    if not API_KEY:
        return  # autenticação desabilitada
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="API Key inválida ou ausente")


# ─────────────────────────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("netops_netbox_sync API iniciada")
    if API_KEY:
        logger.info("Autenticação por API Key habilitada")
    else:
        logger.warning("API_KEY não definida — API pública sem autenticação")
    yield
    logger.info("netops_netbox_sync API encerrada")


app = FastAPI(
    title="netops_netbox_sync API",
    description=(
        "API para coleta de dados de dispositivos Huawei NE8000 e sincronização com o NetBox.\n\n"
        "## Fluxo principal\n\n"
        "1. **`POST /device/collect`** — coleta dados do dispositivo via SSH (somente leitura)\n"
        "2. **`POST /sync`** — coleta + sincroniza com o NetBox (leitura + escrita)\n"
        "3. **`POST /netbox/*`** — consulta dados já sincronizados no NetBox (somente leitura)\n\n"
        "## Autenticação\n\n"
        "Se a variável `API_KEY` estiver definida no servidor, inclua o header `X-API-Key` em todas as requisições."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    dependencies=[Security(verify_api_key)],
)


# ─────────────────────────────────────────────────────────────────────────────
# CORS (ajuste origins conforme o ambiente)
# ─────────────────────────────────────────────────────────────────────────────
_cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Middleware de log de requisições
# ─────────────────────────────────────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    logger.info(
        "%s %s  →  %d  (%.2fs)",
        request.method, request.url.path,
        response.status_code, elapsed,
    )
    return response


# ─────────────────────────────────────────────────────────────────────────────
# Handler global de erros inesperados
# ─────────────────────────────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Erro inesperado em %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Erro interno: {type(exc).__name__}: {exc}"},
    )


# ─────────────────────────────────────────────────────────────────────────────
# Routers
# ─────────────────────────────────────────────────────────────────────────────
app.include_router(device.router)
app.include_router(netbox.router)
app.include_router(sync.router)
app.include_router(compliance.router)
app.include_router(compliance_guided.router)

# ── Static webui ──────────────────────────────────────────────────
_WEBUI_DIR = pathlib.Path(__file__).parent.parent.parent.parent / "webui"
if _WEBUI_DIR.is_dir():
    app.mount("/ui", StaticFiles(directory=str(_WEBUI_DIR), html=True), name="webui")
    logger.info("WebUI servindo em /ui  (dir: %s)", _WEBUI_DIR)


# ─────────────────────────────────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["Sistema"], summary="Health check")
async def health():
    return {"status": "ok", "version": app.version}


# ─────────────────────────────────────────────────────────────────────────────
# Entry point direto
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.api.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8888")),
        reload=os.getenv("API_RELOAD", "false").lower() == "true",
        log_level="info",
    )
