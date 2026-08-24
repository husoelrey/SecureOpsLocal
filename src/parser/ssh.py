import datetime
import logging
import re
from typing import Iterator, Tuple

from src.parser.base import LogParser
from src.schemas.parsed_log_line import ParsedLogLineCreate

logger = logging.getLogger(__name__)

try:
    import secureops_core  # type: ignore[import-untyped]

    _RUST_AVAILABLE = True
except ImportError:
    _RUST_AVAILABLE = False
    logger.warning(
        "secureops_core Rust extension not available; falling back to pure Python."
    )

# Syslog datetime e.g. "Aug 10 14:12:05" or "2026-08-10T14:12:05.123456+00:00"
SYSLOG_TS_RE = re.compile(r"^(?P<syslog_ts>[A-Z][a-z]{2}\s+\d+\s+\d{2}:\d{2}:\d{2})")

# ISO8601 (Journald/systemd often output this when exported)
ISO_TS_RE = re.compile(
    r"^(?P<iso_ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)"
)

# SSHd prefix
SSHD_PREFIX_RE = re.compile(r"sshd(?:\[\d+\])?:\s+(.*)")

# SSH auth patterns
AUTH_PATTERNS = [
    (
        re.compile(
            r"Accepted (?P<auth_method>password|publickey) for (?P<user>\S+) from (?P<ip>\S+) port (?P<port>\d+)"
        ),
        "successful_login",
    ),
    (
        re.compile(
            r"Failed (?P<auth_method>password|publickey) for invalid user (?P<user>\S+) from (?P<ip>\S+) port (?P<port>\d+)"
        ),
        "failed_login_invalid_user",
    ),
    (
        re.compile(
            r"Failed (?P<auth_method>password|publickey) for (?P<user>\S+) from (?P<ip>\S+) port (?P<port>\d+)"
        ),
        "failed_login",
    ),
    (
        re.compile(r"Invalid user (?P<user>\S+) from (?P<ip>\S+) port (?P<port>\d+)"),
        "invalid_user",
    ),
    (
        re.compile(
            r"Connection closed by (?:(?:authenticating|invalid) user (?P<user>\S+) )?(?P<ip>\S+) port (?P<port>\d+)"
        ),
        "connection_closed",
    ),
    (
        re.compile(
            r"Disconnected from (?:(?:authenticating|invalid) user (?P<user>\S+) )?(?P<ip>\S+) port (?P<port>\d+)"
        ),
        "disconnected",
    ),
]


class SSHAuthLogParser(LogParser):
    def _parse_timestamp(
        self, line: str, current_year: int
    ) -> Tuple[datetime.datetime, str]:
        # Try ISO first
        m = ISO_TS_RE.search(line)
        if m:
            ts_str = m.group("iso_ts")
            try:
                dt = datetime.datetime.fromisoformat(ts_str)
            except ValueError:
                dt = datetime.datetime.now(datetime.timezone.utc)
            return dt, line[m.end() :].lstrip()

        m = SYSLOG_TS_RE.search(line)
        if m:
            ts_str = m.group("syslog_ts")
            try:
                dt = datetime.datetime.strptime(ts_str, "%b %d %H:%M:%S")
                dt = dt.replace(year=current_year, tzinfo=datetime.timezone.utc)
            except ValueError:
                dt = datetime.datetime.now(datetime.timezone.utc)
            return dt, line[m.end() :].lstrip()

        return datetime.datetime.now(datetime.timezone.utc), line

    def parse_line(self, line: str, current_year: int) -> ParsedLogLineCreate:
        if _RUST_AVAILABLE:
            raw = secureops_core.parse_ssh_line(line, current_year)
            return ParsedLogLineCreate(
                timestamp=raw["timestamp"],
                source_ip=raw.get("source_ip"),
                user=raw.get("user"),
                event_type=raw["event_type"],
                port=raw.get("port"),
                raw_content=raw["raw_content"],
                is_parsed=raw["is_parsed"],
            )

        timestamp, remainder = self._parse_timestamp(line, current_year)

        sshd_match = SSHD_PREFIX_RE.search(remainder)
        if not sshd_match:
            return ParsedLogLineCreate(
                timestamp=timestamp,
                event_type="unparsed",
                raw_content=line,
                is_parsed=False,
            )

        message = sshd_match.group(1)

        for pattern, ev_type in AUTH_PATTERNS:
            match = pattern.search(message)
            if match:
                groups = match.groupdict()
                return ParsedLogLineCreate(
                    timestamp=timestamp,
                    source_ip=groups.get("ip"),
                    user=groups.get("user"),
                    event_type=ev_type,
                    port=int(groups["port"])
                    if "port" in groups and groups["port"]
                    else None,
                    raw_content=line,
                    is_parsed=True,
                )

        return ParsedLogLineCreate(
            timestamp=timestamp,
            event_type="unparsed_sshd",
            raw_content=line,
            is_parsed=False,
        )

    def parse_file(
        self, file_path: str, current_year: int
    ) -> Iterator[ParsedLogLineCreate]:
        if _RUST_AVAILABLE:
            raw_lines = secureops_core.parse_ssh_file(file_path, current_year)
            for raw in raw_lines:
                yield ParsedLogLineCreate(
                    timestamp=raw["timestamp"],
                    source_ip=raw.get("source_ip"),
                    user=raw.get("user"),
                    event_type=raw["event_type"],
                    port=raw.get("port"),
                    raw_content=raw["raw_content"],
                    is_parsed=raw["is_parsed"],
                )
        else:
            yield from super().parse_file(file_path, current_year)
