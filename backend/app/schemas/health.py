from pydantic import BaseModel
from typing import Dict, Any
from datetime import datetime


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    services: Dict[str, Any]


class ServiceStatus(BaseModel):
    name: str
    status: str
    details: Dict[str, Any] = {}