import datetime
import re
from typing import Tuple

from src.parser.base import LogParser
from src.schemas.parsed_log_line import ParsedLogLineCreate

# Syslog datetime e.g. "Aug 10 14:12:05" or "2026-08-10T14:12:05.123456+00:00"
SYSLOG_TS_RE = re.compile(r"^(?P<syslog_ts>[A-Z][a-z]{2}\s+\d+\s+\d{2}:\d{2}:\d{2})")

# ISO8601 (Journald/systemd often output this when exported)
ISO_TS_RE = re.compile(
    r"^(?P<iso_ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)"
)

# SSHd prefix
SSHD_PREFIX_RE = re.compile(r"sshd(?:\[\d+\])?:\s+(.*)")

# SSH auth patterns
# Accepted password for user from 192.168.1.1 port 1234 ssh2
# Failed password for invalid user root from 192.168.1.1 port 1234 ssh2
# Invalid user admin from 192.168.1.1 port 1234
# Connection closed by 192.168.1.1 port 1234
# Disconnected from 192.168.1.1 port 1234
# Accepted publickey for user from 192.168.1.1 port 1234 ssh2
AUTH_PATTERNS = [
    (
        re.compile(
            r"Accepted (?P<auth_method>password|publickey) for (?P<user>\S+) from (?P<ip>\S+) port (?P<port>\d+)"
        ),
        "successful_login",
    ),  # noqa: E501
    (
        re.compile(
            r"Failed (?P<auth_method>password|publickey) for invalid user (?P<user>\S+) from (?P<ip>\S+) port (?P<port>\d+)"
        ),
        "failed_login_invalid_user",
    ),  # noqa: E501
    (
        re.compile(
            r"Failed (?P<auth_method>password|publickey) for (?P<user>\S+) from (?P<ip>\S+) port (?P<port>\d+)"
        ),
        "failed_login",
    ),  # noqa: E501
    (
        re.compile(r"Invalid user (?P<user>\S+) from (?P<ip>\S+) port (?P<port>\d+)"),
        "invalid_user",
    ),  # noqa: E501
    (
        re.compile(
            r"Connection closed by (?:(?:authenticating|invalid) user (?P<user>\S+) )?(?P<ip>\S+) port (?P<port>\d+)"
        ),
        "connection_closed",
    ),  # noqa: E501
    (
        re.compile(
            r"Disconnected from (?:(?:authenticating|invalid) user (?P<user>\S+) )?(?P<ip>\S+) port (?P<port>\d+)"
        ),
        "disconnected",
    ),  # noqa: E501
]


class SSHAuthLogParser(LogParser):
    def _parse_timestamp(
        self, line: str, current_year: int
    ) -> Tuple[datetime.datetime, str]:
        # Try ISO first
        m = ISO_TS_RE.search(line)
        if m:
            ts_str = m.group("iso_ts")
            # For isoformat in python 3.12, we can just use fromisoformat
            try:
                dt = datetime.datetime.fromisoformat(ts_str)
            except ValueError:
                dt = datetime.datetime.now(datetime.timezone.utc)
            return dt, line[m.end() :].lstrip()

        m = SYSLOG_TS_RE.search(line)
        if m:
            ts_str = m.group("syslog_ts")
            try:
                # syslog doesn't have year
                dt = datetime.datetime.strptime(ts_str, "%b %d %H:%M:%S")
                dt = dt.replace(year=current_year, tzinfo=datetime.timezone.utc)
            except ValueError:
                dt = datetime.datetime.now(datetime.timezone.utc)
            return dt, line[m.end() :].lstrip()

        return datetime.datetime.now(datetime.timezone.utc), line

    def parse_line(self, line: str, current_year: int) -> ParsedLogLineCreate:
        timestamp, remainder = self._parse_timestamp(line, current_year)

        # Remove hostname if present before sshd:
        # Nov  1 12:00:00 myhost sshd[123]: ...
        # If the remainder starts with something else, we search for sshd
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
