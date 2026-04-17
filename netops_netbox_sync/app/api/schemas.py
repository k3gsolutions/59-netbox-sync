"""
Schemas Pydantic para request e response da API FastAPI.
"""
from typing import Optional, Any
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Params de entrada (reutilizáveis entre rotas)
# ─────────────────────────────────────────────────────────────────────────────

class DeviceParams(BaseModel):
    host:     str = Field(..., description="IP ou hostname do dispositivo")
    port:     int = Field(22, description="Porta SSH")
    username: str = Field(..., description="Usuário SSH")
    password: str = Field(..., description="Senha SSH")

    model_config = {"json_schema_extra": {
        "example": {
            "host": "172.30.0.1",
            "port": 51212,
            "username": "admin",
            "password": "secret"
        }
    }}


class NetBoxParams(BaseModel):
    url:        str  = Field(..., description="URL base do NetBox (ex: http://host:8080)")
    token:      str  = Field(..., description="Token de API do NetBox")
    verify_ssl: bool = Field(False, description="Verificar certificado TLS")

    model_config = {"json_schema_extra": {
        "example": {
            "url": "http://172.30.0.112:8080",
            "token": "ojnVy4NsPIDIC0HCyKfejdp7UU1ugmynZ1FrstUO",
            "verify_ssl": False
        }
    }}


# ─────────────────────────────────────────────────────────────────────────────
# Requests
# ─────────────────────────────────────────────────────────────────────────────

class CollectRequest(BaseModel):
    """Coleta dados via SSH. Não escreve no NetBox."""
    device: DeviceParams

    model_config = {"json_schema_extra": {
        "example": {
            "device": {
                "host": "172.30.0.1",
                "port": 51212,
                "username": "admin",
                "password": "secret"
            }
        }
    }}


class SyncRequest(BaseModel):
    """Coleta dados via SSH e sincroniza com o NetBox."""
    device:    DeviceParams
    netbox:    NetBoxParams
    device_id: int = Field(..., description="ID do dispositivo no NetBox")

    model_config = {"json_schema_extra": {
        "example": {
            "device": {
                "host": "172.30.0.1",
                "port": 51212,
                "username": "admin",
                "password": "secret"
            },
            "netbox": {
                "url": "http://172.30.0.112:8080",
                "token": "ojnVy4NsPIDIC0HCyKfejdp7UU1ugmynZ1FrstUO",
                "verify_ssl": False
            },
            "device_id": 5
        }
    }}


class NetBoxQueryRequest(BaseModel):
    """Parâmetros para consultar o NetBox diretamente (sem acessar o dispositivo)."""
    netbox:    NetBoxParams
    device_id: Optional[int] = Field(None, description="Filtrar por device ID no NetBox")

    model_config = {"json_schema_extra": {
        "example": {
            "netbox": {
                "url": "http://172.30.0.112:8080",
                "token": "ojnVy4NsPIDIC0HCyKfejdp7UU1ugmynZ1FrstUO",
                "verify_ssl": False
            },
            "device_id": 5
        }
    }}


# ─────────────────────────────────────────────────────────────────────────────
# Responses
# ─────────────────────────────────────────────────────────────────────────────

class InventorySummary(BaseModel):
    interfaces:      int
    ip_addresses:    int
    vrfs:            int
    vlans:           int
    bgp_sessions:    int
    route_policies:  int
    prefix_lists:    int
    as_path_filters: int
    communities:     int
    community_lists: int


class BGPSessionOut(BaseModel):
    peer_ip:        str
    peer_as:        Optional[int]
    local_as:       Optional[int]
    router_id:      Optional[str]
    peer_type:      Optional[str]
    state:          Optional[str]
    description:    Optional[str]
    address_family: Optional[str]
    vrf:            Optional[str]
    import_policy:  Optional[str]
    export_policy:  Optional[str]


class CollectResponse(BaseModel):
    summary:      InventorySummary
    bgp_sessions: list[BGPSessionOut]


class ChangeLogTotals(BaseModel):
    created: int
    updated: int
    skipped: int


class SyncResponse(BaseModel):
    inventory_summary: InventorySummary
    bgp_changelog:     dict[str, Any]


class ErrorResponse(BaseModel):
    detail: str
