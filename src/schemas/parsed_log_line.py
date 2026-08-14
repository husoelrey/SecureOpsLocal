import datetime

from pydantic import BaseModel, ConfigDict


class ParsedLogLineBase(BaseModel):
    timestamp: datetime.datetime
    source_ip: str | None = None
    user: str | None = None
    event_type: str
    port: int | None = None
    raw_content: str
    is_parsed: bool = True


class ParsedLogLineCreate(ParsedLogLineBase):
    pass


class ParsedLogLine(ParsedLogLineBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
