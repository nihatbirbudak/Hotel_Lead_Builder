from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class FacilityUpload(BaseModel):
    """Upload model for facility data"""
    raw_id: Optional[str] = None
    name: str
    sehir: Optional[str] = None
    ilce: Optional[str] = None
    type: Optional[str] = None
    address: Optional[str] = None

class FacilityBase(BaseModel):
    name: str
    sehir: str | None = None
    ilce: str | None = None
    type: str | None = None
    website: str | None = None
    email: str | None = None
    website_status: str
    email_status: str

class FacilityResponse(FacilityBase):
    id: str
    website_score: float

    # Aliases to keep frontend somewhat compatible if it expects city/district
    @property
    def city(self) -> str | None:
        return self.sehir

    @property
    def district(self) -> str | None:
        return self.ilce

    class Config:
        from_attributes = True

class JobLogResponse(BaseModel):
    timestamp: datetime
    level: str
    message: str

    class Config:
        from_attributes = True

class JobResponse(BaseModel):
    job_id: str
    status: str
    total: int
    done: int
    errors: int
    logs: List[JobLogResponse] = []

    class Config:
        from_attributes = True

class JobSettings(BaseModel):
    provider: str = "ddg"
    rate_limit: float = 1.0 # seconds delay
    max_concurrency: int = 1

class DiscoveryRequest(BaseModel):
    mode: str = "all" # 'all' or 'selected'
    uids: List[str] = []
    settings: JobSettings = JobSettings()

class EmailRequest(BaseModel):
    mode: str = "all" 
    uids: List[str] = []
    settings: JobSettings = JobSettings()
