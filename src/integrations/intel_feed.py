"""Offline Threat Intelligence (STIX, MISP, CSV, JSON) Feed Ingestion and Local Lookup."""

import csv
import io
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy.orm import Session

from src.database import Base, SessionLocal, engine
from src.models.threat_intel import ThreatIntel
from src.schemas.threat_intel import ThreatIntelCreate, ThreatIntelMatch

logger = logging.getLogger(__name__)

IP_PATTERN = re.compile(
    r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
)
STIX_IPV4_PATTERN = re.compile(r"ipv4-addr:value\s*=\s*'([^']+)'", re.IGNORECASE)
STIX_IPV6_PATTERN = re.compile(r"ipv6-addr:value\s*=\s*'([^']+)'", re.IGNORECASE)


def init_threat_intel_db() -> None:
    """Ensure threat_intel table exists in the local database."""
    Base.metadata.create_all(bind=engine, tables=[ThreatIntel.__table__])


def parse_csv_feed(content: str, source_label: str = "CSV") -> List[ThreatIntelCreate]:
    """Parse local CSV threat intelligence feed."""
    entries: List[ThreatIntelCreate] = []
    reader = csv.DictReader(io.StringIO(content.strip()))

    for row in reader:
        # Normalize keys (lowercase and stripped)
        row_norm = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}

        ip = (
            row_norm.get("ip_address")
            or row_norm.get("ip")
            or row_norm.get("indicator")
            or row_norm.get("ioc")
            or row_norm.get("address")
        )
        if not ip:
            continue

        threat_type = (
            row_norm.get("threat_type")
            or row_norm.get("type")
            or row_norm.get("category")
            or row_norm.get("tag")
            or "MALICIOUS_IP"
        ).upper()

        severity = (row_norm.get("severity") or "medium").lower()
        description = row_norm.get("description") or row_norm.get("comment")
        src = row_norm.get("source") or source_label

        entries.append(
            ThreatIntelCreate(
                ip_address=ip,
                threat_type=threat_type,
                severity=severity,
                description=description,
                source=src,
            )
        )

    return entries


def parse_stix_bundle(data: Dict[str, Any], source_label: str = "STIX") -> List[ThreatIntelCreate]:
    """Parse STIX 2.1 bundle for IPv4 / IPv6 indicators."""
    entries: List[ThreatIntelCreate] = []
    objects = data.get("objects", [])

    for obj in objects:
        if obj.get("type") != "indicator":
            continue

        pattern = obj.get("pattern", "")
        # Extract IP from STIX pattern
        match = STIX_IPV4_PATTERN.search(pattern) or STIX_IPV6_PATTERN.search(pattern)
        if not match:
            continue

        ip = match.group(1)
        name = obj.get("name", "")
        indicator_types = obj.get("indicator_types", [])

        if indicator_types:
            threat_type = "_".join(
                re.sub(r"[^A-Z0-9_]+", "_", t.upper()).strip("_")
                for t in indicator_types
            )
        elif name:
            threat_type = re.sub(r"[^A-Z0-9_]+", "_", name.upper()).strip("_")
        else:
            threat_type = "KNOWN_THREAT"

        # Determine severity from confidence or labels
        confidence = obj.get("confidence", 50)
        if confidence >= 80:
            severity = "high"
        elif confidence >= 50:
            severity = "medium"
        else:
            severity = "low"

        entries.append(
            ThreatIntelCreate(
                ip_address=ip,
                threat_type=threat_type,
                severity=severity,
                description=obj.get("description") or name,
                source=source_label,
            )
        )

    return entries


def parse_misp_event(data: Dict[str, Any], source_label: str = "MISP") -> List[ThreatIntelCreate]:
    """Parse MISP JSON event for IP attributes."""
    entries: List[ThreatIntelCreate] = []
    event = data.get("Event", data)
    attributes = event.get("Attribute", [])

    for attr in attributes:
        attr_type = attr.get("type", "")
        if attr_type not in ("ip-src", "ip-dst", "ip", "domain|ip"):
            continue

        ip = attr.get("value", "").strip()
        if "|" in ip:
            ip = ip.split("|")[-1].strip()

        if not ip:
            continue

        category = attr.get("category", "MALICIOUS_IP")
        threat_type = re.sub(r"[^A-Z0-9_]+", "_", category.upper()).strip("_")

        tags = attr.get("Tag", [])
        for tag in tags:
            tag_name = tag.get("name", "")
            if "threat-type" in tag_name or "apt" in tag_name.lower():
                threat_type = re.sub(r"[^A-Z0-9_]+", "_", tag_name.upper()).strip("_")
                break

        entries.append(
            ThreatIntelCreate(
                ip_address=ip,
                threat_type=threat_type,
                severity="high" if "apt" in threat_type.lower() else "medium",
                description=attr.get("comment"),
                source=source_label,
            )
        )

    return entries


def parse_json_feed(content: str, source_label: str = "JSON") -> List[ThreatIntelCreate]:
    """Parse JSON threat feed (standard list, STIX bundle, or MISP event)."""
    data = json.loads(content)

    if isinstance(data, dict):
        if data.get("type") == "bundle":
            return parse_stix_bundle(data, source_label="STIX")
        elif "Event" in data or "Attribute" in data:
            return parse_misp_event(data, source_label="MISP")
        elif "indicators" in data and isinstance(data["indicators"], list):
            data = data["indicators"]

    entries: List[ThreatIntelCreate] = []
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            ip = (
                item.get("ip_address")
                or item.get("ip")
                or item.get("indicator")
                or item.get("ioc")
            )
            if not ip:
                continue

            threat_type = (
                item.get("threat_type")
                or item.get("type")
                or item.get("category")
                or "MALICIOUS_IP"
            ).upper()
            severity = (item.get("severity") or "medium").lower()

            entries.append(
                ThreatIntelCreate(
                    ip_address=ip,
                    threat_type=threat_type,
                    severity=severity,
                    description=item.get("description") or item.get("comment"),
                    source=item.get("source") or source_label,
                )
            )

    return entries


def parse_threat_feed_file(file_path: Path | str) -> List[ThreatIntelCreate]:
    """Inspect and parse a threat feed file from disk (CSV, JSON, STIX, MISP)."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Threat feed file not found: {path}")

    content = path.read_text(encoding="utf-8", errors="replace")
    ext = path.suffix.lower()

    if ext in (".json", ".stix", ".misp"):
        return parse_json_feed(content, source_label=path.name)
    else:
        # Default to CSV parser
        try:
            return parse_csv_feed(content, source_label=path.name)
        except Exception:
            return parse_json_feed(content, source_label=path.name)


def ingest_threat_intel_file(file_path: Path | str, db: Optional[Session] = None) -> int:
    """
    Ingest a local threat feed file and persist/update indicators in SQLite.
    Returns the number of indicators ingested or updated.
    """
    init_threat_intel_db()
    entries = parse_threat_feed_file(file_path)

    if not entries:
        return 0

    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        count = 0
        for entry in entries:
            existing = (
                db.query(ThreatIntel)
                .filter(ThreatIntel.ip_address == entry.ip_address)
                .first()
            )
            if existing:
                existing.threat_type = entry.threat_type
                existing.severity = entry.severity
                existing.description = entry.description
                existing.source = entry.source
            else:
                record = ThreatIntel(
                    ip_address=entry.ip_address,
                    threat_type=entry.threat_type,
                    severity=entry.severity,
                    description=entry.description,
                    source=entry.source,
                )
                db.add(record)
            count += 1

        db.commit()
        return count
    finally:
        if should_close:
            db.close()


def lookup_ips_intel(
    ips: Iterable[str], db: Optional[Session] = None
) -> Dict[str, ThreatIntelMatch]:
    """
    Query the local SQLite threat_intel table for a collection of IP addresses.
    Returns a dictionary mapping matching IP -> ThreatIntelMatch.
    CRITICAL: Performs ONLY local database queries. Zero external network requests.
    """
    ip_list = [ip.strip() for ip in ips if ip and ip.strip()]
    if not ip_list:
        return {}

    init_threat_intel_db()
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        records = (
            db.query(ThreatIntel)
            .filter(ThreatIntel.ip_address.in_(ip_list))
            .all()
        )
        matches: Dict[str, ThreatIntelMatch] = {}
        for r in records:
            matches[r.ip_address] = ThreatIntelMatch(
                ip_address=r.ip_address,
                threat_type=r.threat_type,
                severity=r.severity,
                description=r.description,
                source=r.source,
            )
        return matches
    except Exception as e:
        logger.warning(f"Error querying local threat_intel table: {e}")
        return {}
    finally:
        if should_close:
            db.close()


def lookup_ip_intel(ip: str, db: Optional[Session] = None) -> Optional[ThreatIntelMatch]:
    """Look up a single IP in the local threat intelligence table."""
    res = lookup_ips_intel([ip], db=db)
    return res.get(ip)
