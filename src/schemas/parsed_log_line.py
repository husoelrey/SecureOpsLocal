import datetime

from pydantic import BaseModel


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
    id: int

    class Config:
        from_attributes = True
