from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class Provenance(BaseModel):
    source: str
    source_url: str | None = None
    observation_date: date
    retrieved_at: datetime
    data_mode: str
    is_stale: bool


class DashletErrorDetail(BaseModel):
    error_code: str
    message: str


class DashletErrorResponse(BaseModel):
    detail: DashletErrorDetail
