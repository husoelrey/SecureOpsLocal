import datetime

from pydantic import BaseModel


class IncidentReportBase(BaseModel):
    status: str
    model_profile: str
    summary: str
    risk_level: str
    recommendations: str
    raw_model_response: str


class IncidentReportCreate(IncidentReportBase):
    pass


class IncidentReport(IncidentReportBase):
    id: int
    created_at: datetime.datetime

    class Config:
        from_attributes = True
