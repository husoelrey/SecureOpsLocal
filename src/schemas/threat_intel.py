import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ThreatIntelBase(BaseModel):
    ip_address: str = Field(..., description="IPv4 or IPv6 indicator address")
    threat_type: str = Field(..., description="Type of threat (e.g. KNOWN_APT, TOR_NODE, BRUTE_FORCER)")
    severity: str = Field(default="medium", description="Severity level: low, medium, high, critical")
    description: Optional[str] = Field(default=None, description="Contextual description of the threat indicator")
    source: Optional[str] = Field(default=None, description="Origin feed source (e.g. STIX, MISP, local_csv)")


class ThreatIntelCreate(ThreatIntelBase):
    pass


class ThreatIntelRead(ThreatIntelBase):
    id: int
    created_at: datetime.datetime
    model_config = ConfigDict(from_attributes=True)


class ThreatIntelMatch(BaseModel):
    ip_address: str
    threat_type: str
    severity: str
    description: Optional[str] = None
    source: Optional[str] = None
