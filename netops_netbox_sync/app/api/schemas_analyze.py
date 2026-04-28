from typing import Optional

from pydantic import BaseModel, Field

from app.api.schemas import DeviceParams, NetBoxParams
from app.schemas.analyze import AnalyzeResult


class AnalyzeRequest(BaseModel):
    device: DeviceParams
    device_id: Optional[int] = Field(None, description="ID do dispositivo no NetBox")
    device_name: Optional[str] = Field(None, description="Nome do dispositivo no NetBox (usado para resolver device_id automaticamente)")
    netbox: Optional[NetBoxParams] = Field(None, description="Parâmetros do NetBox")

    model_config = {"json_schema_extra": {
        "example": {
            "device": {
                "host": "172.30.0.1",
                "port": 51212,
                "username": "admin",
                "password": "secret"
            },
            "device_id": 5,
            "netbox": {
                "url": "http://172.30.0.112:8080",
                "token": "ojnVy4NsPIDIC0HCyKfejdp7UU1ugmynZ1FrstUO",
                "verify_ssl": False
            }
        }
    }}


AnalyzeResponse = AnalyzeResult
