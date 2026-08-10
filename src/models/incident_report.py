import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class IncidentReport(Base):
    __tablename__ = "incident_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    status: Mapped[str] = mapped_column(String, index=True)
    model_profile: Mapped[str] = mapped_column(String)
    summary: Mapped[str] = mapped_column(Text)
    risk_level: Mapped[str] = mapped_column(String)
    recommendations: Mapped[str] = mapped_column(Text)
    raw_model_response: Mapped[str] = mapped_column(Text)
