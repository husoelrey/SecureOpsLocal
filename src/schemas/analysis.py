import datetime
from typing import Any

from pydantic import BaseModel, Field


class IPAggregation(BaseModel):
    ip: str
    failed_attempts: int
    successful_attempts: int
    first_seen: datetime.datetime
    last_seen: datetime.datetime
    users_attempted: list[str]
    intel_flags: list[str] = []


class LogAnalysis(BaseModel):
    total_lines: int
    unparsed_lines: int
    start_time: datetime.datetime | None
    end_time: datetime.datetime | None
    ip_aggregations: list[IPAggregation]
    limitations: list[str]
    multi_source_timeline: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
