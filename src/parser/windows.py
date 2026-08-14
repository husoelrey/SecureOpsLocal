import datetime
import json
import re
from typing import Any, Dict, Iterator

from src.parser.base import LogParser
from src.schemas.parsed_log_line import ParsedLogLineCreate

# ISO timestamp pattern
ISO_TS_RE = re.compile(
    r"(?P<iso_ts>\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)"
)

# Text regex patterns for Windows Event logs
WIN_EVENT_ID_RE = re.compile(
    r"(?:Event\s*ID|EventID|Event)[\s:=]+(?P<event_id>\d+)", re.IGNORECASE
)
WIN_ACCOUNT_RE = re.compile(
    r"(?:Account\s*Name|TargetUserName|Target\s*User\s*Name|User\s*Name|User)[\s:=]+['\"]?(?P<user>[^\s,;'\"]+)",
    re.IGNORECASE,
)
WIN_IP_RE = re.compile(
    r"(?:Source\s*Network\s*Address|Source\s*IP|IpAddress|ClientAddress|Client\s*IP|IP)[\s:=]+['\"]?(?P<ip>[0-9a-fA-F:\.]+)['\"]?",
    re.IGNORECASE,
)
WIN_PORT_RE = re.compile(
    r"(?:Source\s*Port|IpPort|Port)[\s:=]+['\"]?(?P<port>\d+)['\"]?",
    re.IGNORECASE,
)


class WindowsEventLogParser(LogParser):
    """
    Deterministic parser for Windows Security Event Logs (Focus on Event IDs 4624 and 4625).
    Supports JSON lines, nested Windows EVTX JSON exports, and structured text formats.
    """

    def _parse_timestamp(self, ts_raw: Any, current_year: int) -> datetime.datetime:
        if not ts_raw:
            return datetime.datetime.now(datetime.timezone.utc)

        if isinstance(ts_raw, datetime.datetime):
            if ts_raw.tzinfo is None:
                return ts_raw.replace(tzinfo=datetime.timezone.utc)
            return ts_raw

        ts_str = str(ts_raw).strip()
        # Try ISO format
        m = ISO_TS_RE.search(ts_str)
        if m:
            clean_ts = m.group("iso_ts").replace(" ", "T")
            try:
                dt = datetime.datetime.fromisoformat(clean_ts)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=datetime.timezone.utc)
                return dt
            except ValueError:
                pass

        # Try common Windows date formats
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%Y %I:%M:%S %p",
            "%d/%b/%Y:%H:%M:%S",
        ):
            try:
                dt = datetime.datetime.strptime(ts_str, fmt)
                return dt.replace(tzinfo=datetime.timezone.utc)
            except ValueError:
                pass

        return datetime.datetime.now(datetime.timezone.utc)

    def _parse_json_dict(
        self, data: Dict[str, Any], raw_line: str, current_year: int
    ) -> ParsedLogLineCreate:
        # Check for nested Windows XML/EVTX JSON structure: Event -> System / EventData
        system_data = (
            data.get("System", {}) if isinstance(data.get("System"), dict) else {}
        )
        event_data = (
            data.get("EventData", {}) if isinstance(data.get("EventData"), dict) else {}
        )

        # 1. Extract Event ID
        event_id = None
        if "EventID" in data:
            event_id = data["EventID"]
        elif "EventId" in data:
            event_id = data["EventId"]
        elif "event_id" in data:
            event_id = data["event_id"]
        elif "EventID" in system_data:
            event_id = system_data["EventID"]

        if isinstance(event_id, dict):
            # Handle XML conversion like {"#text": "4625"}
            event_id = event_id.get("#text") or event_id.get("Value")

        try:
            event_id_int = int(str(event_id).strip()) if event_id is not None else None
        except (ValueError, TypeError):
            event_id_int = None

        # 2. Extract Timestamp
        time_created = (
            data.get("TimeCreated")
            or data.get("time_created")
            or data.get("Timestamp")
            or data.get("timestamp")
            or system_data.get("TimeCreated", {}).get("@SystemTime")
            or system_data.get("TimeCreated")
        )
        timestamp = self._parse_timestamp(time_created, current_year)

        # 3. Extract User / Account Name
        user = (
            event_data.get("TargetUserName")
            or event_data.get("TargetUser")
            or event_data.get("AccountName")
            or event_data.get("SubjectUserName")
            or data.get("TargetUserName")
            or data.get("AccountName")
            or data.get("user")
            or data.get("User")
            or data.get("Account Name")
        )
        if isinstance(user, dict):
            user = user.get("#text") or user.get("Value")
        if user and str(user).strip() in ("-", "", "SYSTEM", "ANONYMOUS LOGON"):
            # If target user is system or blank, check SubjectUserName
            alt_user = event_data.get("SubjectUserName") or data.get("SubjectUserName")
            if alt_user and str(alt_user).strip() not in ("-", ""):
                user = alt_user

        user_str = (
            str(user).strip() if user and str(user).strip() not in ("-", "") else None
        )

        # 4. Extract Source IP
        ip = (
            event_data.get("IpAddress")
            or event_data.get("IPAddress")
            or event_data.get("SourceNetworkAddress")
            or event_data.get("ClientAddress")
            or data.get("IpAddress")
            or data.get("SourceAddress")
            or data.get("ip")
            or data.get("Source IP")
            or data.get("Source Network Address")
        )
        if isinstance(ip, dict):
            ip = ip.get("#text") or ip.get("Value")
        ip_str = str(ip).strip() if ip and str(ip).strip() not in ("-", "") else None

        # 5. Extract Port
        port_raw = (
            event_data.get("IpPort")
            or event_data.get("SourcePort")
            or data.get("IpPort")
            or data.get("port")
            or data.get("Port")
        )
        if isinstance(port_raw, dict):
            port_raw = port_raw.get("#text") or port_raw.get("Value")
        try:
            port = (
                int(str(port_raw).strip())
                if port_raw and str(port_raw).strip() != "-"
                else None
            )
        except (ValueError, TypeError):
            port = None

        # Determine Event Type
        if event_id_int == 4624:
            event_type = "successful_login"
            is_parsed = True
        elif event_id_int == 4625:
            event_type = "failed_login"
            is_parsed = True
        elif event_id_int is not None:
            event_type = f"windows_event_{event_id_int}"
            is_parsed = True
        else:
            event_type = "unparsed_windows"
            is_parsed = bool(user_str or ip_str)

        return ParsedLogLineCreate(
            timestamp=timestamp,
            source_ip=ip_str,
            user=user_str,
            event_type=event_type,
            port=port,
            raw_content=raw_line,
            is_parsed=is_parsed,
        )

    def parse_line(self, line: str, current_year: int) -> ParsedLogLineCreate:
        line_clean = line.strip()
        if not line_clean:
            return ParsedLogLineCreate(
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                event_type="empty_line",
                raw_content=line,
                is_parsed=False,
            )

        # 1. Try parsing as JSON
        if (line_clean.startswith("{") and line_clean.endswith("}")) or (
            line_clean.startswith("[") and line_clean.endswith("]")
        ):
            try:
                data = json.loads(line_clean)
                if isinstance(data, dict):
                    # Unwrap {"Event": {...}} if present
                    if "Event" in data and isinstance(data["Event"], dict):
                        return self._parse_json_dict(data["Event"], line, current_year)
                    return self._parse_json_dict(data, line, current_year)
            except Exception:
                pass

        # 2. Try parsing as Structured Text / Syslog Windows Format
        m_id = WIN_EVENT_ID_RE.search(line_clean)
        m_user = WIN_ACCOUNT_RE.search(line_clean)
        m_ip = WIN_IP_RE.search(line_clean)
        m_port = WIN_PORT_RE.search(line_clean)

        timestamp = self._parse_timestamp(line_clean, current_year)

        if m_id:
            event_id = int(m_id.group("event_id"))
            user = m_user.group("user") if m_user else None
            ip = m_ip.group("ip") if m_ip else None
            port = int(m_port.group("port")) if m_port else None

            # Ignore placeholder or non-routable '-'
            if user in ("-", "ANONYMOUS LOGON", "SYSTEM"):
                user = None
            if ip in ("-", "127.0.0.1", "::1") and not ip:
                ip = None

            if event_id == 4624:
                event_type = "successful_login"
            elif event_id == 4625:
                event_type = "failed_login"
            else:
                event_type = f"windows_event_{event_id}"

            return ParsedLogLineCreate(
                timestamp=timestamp,
                source_ip=ip,
                user=user,
                event_type=event_type,
                port=port,
                raw_content=line,
                is_parsed=True,
            )

        return ParsedLogLineCreate(
            timestamp=timestamp,
            event_type="unparsed_windows",
            raw_content=line,
            is_parsed=False,
        )

    def parse_file(
        self, file_path: str, current_year: int
    ) -> Iterator[ParsedLogLineCreate]:
        """Parse Windows event log file (supports JSON arrays, JSONL, and text)."""
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read().strip()

        if content.startswith("[") and content.endswith("]"):
            try:
                events = json.loads(content)
                if isinstance(events, list):
                    for item in events:
                        if isinstance(item, dict):
                            raw_item = json.dumps(item)
                            if "Event" in item and isinstance(item["Event"], dict):
                                yield self._parse_json_dict(
                                    item["Event"], raw_item, current_year
                                )
                            else:
                                yield self._parse_json_dict(
                                    item, raw_item, current_year
                                )
                    return
            except Exception:
                pass

        # Fallback to line by line
        for line in content.splitlines():
            if line.strip():
                yield self.parse_line(line.strip(), current_year)
