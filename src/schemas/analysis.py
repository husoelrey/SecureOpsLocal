import datetime

from pydantic import BaseModel


class IPAggregation(BaseModel):
    ip: str
    failed_attempts: int
    successful_attempts: int
    first_seen: datetime.datetime
    last_seen: datetime.datetime
    users_attempted: list[str]


class LogAnalysis(BaseModel):
    total_lines: int
    unparsed_lines: int
    start_time: datetime.datetime | None
    end_time: datetime.datetime | None
    ip_aggregations: list[IPAggregation]
    limitations: list[str]
