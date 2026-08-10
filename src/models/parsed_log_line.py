import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class ParsedLogLine(Base):
    __tablename__ = "parsed_log_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, index=True)
    source_ip: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    user: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    event_type: Mapped[str] = mapped_column(String, index=True)
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_content: Mapped[str] = mapped_column(Text)
    is_parsed: Mapped[bool] = mapped_column(Boolean, default=True)
