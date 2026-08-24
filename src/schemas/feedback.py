import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class FeedbackBase(BaseModel):
    incident_id: str = Field(..., description="The identifier of the incident report")
    is_false_positive: bool = Field(default=True, description="Whether the incident was flagged as a false positive")
    admin_notes: str = Field(..., description="Administrator reasoning and context")
    source_ip: Optional[str] = Field(default=None, description="Associated source IP address")
    target_user: Optional[str] = Field(default=None, description="Associated target user account")


class FeedbackCreate(FeedbackBase):
    pass


class FeedbackRead(FeedbackBase):
    id: int
    created_at: datetime.datetime
    model_config = ConfigDict(from_attributes=True)
