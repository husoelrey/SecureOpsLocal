import datetime
import json
import re
import urllib.parse

from src.parser.base import LogParser
from src.schemas.parsed_log_line import ParsedLogLineCreate

# Nginx combined log format:
# $remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent"
# e.g.: 192.168.1.10 - admin [14/Aug/2026:12:00:00 +0000] "GET /index.php?id=1 HTTP/1.1" 200 4523 "-" "Mozilla/5.0"
NGINX_COMBINED_RE = re.compile(
    r'^(?P<ip>\S+)\s+\S+\s+(?P<user>\S+)\s+\[(?P<time>[^\]]+)\]\s+"(?P<request>[^"]*)"\s+(?P<status>\d{3})\s+(?P<bytes>\S+)(?:\s+"(?P<referer>[^"]*)"\s+"(?P<agent>[^"]*)")?'
)

# Alternative simple format e.g. 192.168.1.10 - - [14/Aug/2026:12:00:00 +0000] "GET / HTTP/1.1" 200
NGINX_SIMPLE_RE = re.compile(
    r'^(?P<ip>\S+)\s+\S+\s+(?P<user>\S+)\s+\[(?P<time>[^\]]+)\]\s+"(?P<request>[^"]*)"\s+(?P<status>\d{3})'
)

# SQL Injection patterns
SQLI_PATTERNS = [
    re.compile(r"(\b(UNION(\s+ALL)?)\s+SELECT\b)", re.IGNORECASE),
    re.compile(r"(['\"]\s*(OR|AND)\s*['\"]?\d+['\"]?\s*=\s*['\"]?\d+)", re.IGNORECASE),
    re.compile(r"(['\"]\s*(OR|AND)\s*['\"][^'\"]+['\"]\s*=\s*['\"])", re.IGNORECASE),
    re.compile(r"(\bSELECT\b.+\bFROM\b)", re.IGNORECASE),
    re.compile(
        r"(\bINSERT\s+INTO\b|\bUPDATE\s+.+\s+SET\b|\bDELETE\s+FROM\b)", re.IGNORECASE
    ),
    re.compile(
        r"(\bDROP\s+TABLE\b|\bALTER\s+TABLE\b|\bTRUNCATE\s+TABLE\b)", re.IGNORECASE
    ),
    re.compile(
        r"(\bSLEEP\s*\(\s*\d+\s*\)|\bBENCHMARK\s*\(|\bWAITFOR\s+DELAY\b)", re.IGNORECASE
    ),
    re.compile(r"(\bINFORMATION_SCHEMA\b|\bSYS\.TABLES\b|\bPG_SLEEP\b)", re.IGNORECASE),
    re.compile(r"(--|#|\/\*.*\*\/)", re.IGNORECASE),
    re.compile(r"(\bEXEC\s*\(|\bEXECUTE\s*\(|\bxp_cmdshell\b)", re.IGNORECASE),
]

# XSS patterns
XSS_PATTERNS = [
    re.compile(r"(<script\b[^>]*>.*?</script>|<script\b[^>]*>)", re.IGNORECASE),
    re.compile(r"(javascript\s*:)", re.IGNORECASE),
    re.compile(
        r"(\bon(error|load|click|mouseover|submit|focus|blur|change)\s*=)",
        re.IGNORECASE,
    ),
    re.compile(r"(<img\b[^>]*\bsrc\s*=[^>]*>)", re.IGNORECASE),
    re.compile(r"(<iframe\b[^>]*>|<svg\b[^>]*\bonload\b)", re.IGNORECASE),
    re.compile(
        r"(\balert\s*\(|\bdocument\.cookie\b|\beval\s*\(|\bprompt\s*\()", re.IGNORECASE
    ),
]

# Path Traversal patterns
PATH_TRAVERSAL_PATTERNS = [
    re.compile(r"(\.\./\.\./|\.\.\\\.\.\\|\.\./|\.\.\\)", re.IGNORECASE),
    re.compile(r"(/etc/passwd|/etc/shadow|/proc/self/environ)", re.IGNORECASE),
    re.compile(r"(c:\\windows\\system32|boot\.ini|win\.ini)", re.IGNORECASE),
]


class NginxAccessParser(LogParser):
    """
    Deterministic parser for Nginx access logs.
    Extracts Source IP, HTTP Status, User, and detects web attack payloads (SQLi, XSS, Path Traversal).
    """

    def _parse_time(self, time_str: str, current_year: int) -> datetime.datetime:
        time_str = time_str.strip()
        # Format: 14/Aug/2026:12:00:00 +0000 or 14/Aug/2026:12:00:00
        for fmt in (
            "%d/%b/%Y:%H:%M:%S %z",
            "%d/%b/%Y:%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d %H:%M:%S",
        ):
            try:
                dt = datetime.datetime.strptime(time_str, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=datetime.timezone.utc)
                return dt
            except ValueError:
                pass

        return datetime.datetime.now(datetime.timezone.utc)

    def _detect_payload_attacks(self, text: str) -> str | None:
        """Scan raw and URL-decoded strings for web attack patterns."""
        if not text:
            return None

        # Test both raw and decoded text
        candidates = [text]
        try:
            decoded = urllib.parse.unquote_plus(text)
            if decoded != text:
                candidates.append(decoded)
            # Double decode for evasion
            double_decoded = urllib.parse.unquote_plus(decoded)
            if double_decoded not in candidates:
                candidates.append(double_decoded)
        except Exception:
            pass

        for c in candidates:
            for pattern in SQLI_PATTERNS:
                if pattern.search(c):
                    return "sqli_attempt"
            for pattern in XSS_PATTERNS:
                if pattern.search(c):
                    return "xss_attempt"
            for pattern in PATH_TRAVERSAL_PATTERNS:
                if pattern.search(c):
                    return "path_traversal"

        return None

    def _classify_event(
        self, attack_type: str | None, status_code: int, request: str, user: str | None
    ) -> str:
        if attack_type:
            return attack_type

        is_auth_endpoint = any(
            kw in request.lower()
            for kw in ("login", "auth", "signin", "wp-login", "admin")
        )

        if status_code == 401:
            return (
                "failed_login" if (user or is_auth_endpoint) else "unauthorized_access"
            )
        elif status_code == 403:
            return "forbidden_access"
        elif status_code >= 500:
            return "server_error"
        elif status_code >= 400:
            return "failed_request"
        elif status_code in (200, 201, 204, 301, 302, 304):
            if is_auth_endpoint and user:
                return "successful_login"
            return "successful_request"

        return "http_request"

    def parse_line(self, line: str, current_year: int) -> ParsedLogLineCreate:
        line_clean = line.strip()
        if not line_clean:
            return ParsedLogLineCreate(
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                event_type="empty_line",
                raw_content=line,
                is_parsed=False,
            )

        # 1. Try JSON format
        if line_clean.startswith("{") and line_clean.endswith("}"):
            try:
                data = json.loads(line_clean)
                if isinstance(data, dict):
                    ip = (
                        data.get("remote_addr")
                        or data.get("client_ip")
                        or data.get("ip")
                    )
                    user = data.get("remote_user") or data.get("user")
                    time_raw = (
                        data.get("time_local")
                        or data.get("time_iso8601")
                        or data.get("timestamp")
                    )
                    request = data.get("request") or data.get("uri") or ""
                    status_raw = data.get("status") or data.get("status_code") or 200

                    timestamp = (
                        self._parse_time(str(time_raw), current_year)
                        if time_raw
                        else datetime.datetime.now(datetime.timezone.utc)
                    )
                    user_str = (
                        str(user).strip()
                        if user and str(user).strip() not in ("-", "")
                        else None
                    )
                    status_code = int(status_raw) if str(status_raw).isdigit() else 200

                    attack = self._detect_payload_attacks(request)
                    event_type = self._classify_event(
                        attack, status_code, request, user_str
                    )

                    return ParsedLogLineCreate(
                        timestamp=timestamp,
                        source_ip=str(ip).strip() if ip else None,
                        user=user_str,
                        event_type=event_type,
                        port=None,
                        raw_content=line,
                        is_parsed=True,
                    )
            except Exception:
                pass

        # 2. Try Combined / Common Log Format
        match = NGINX_COMBINED_RE.search(line_clean) or NGINX_SIMPLE_RE.search(
            line_clean
        )
        if match:
            groups = match.groupdict()
            ip = groups.get("ip")
            user_raw = groups.get("user")
            time_raw = groups.get("time")
            request = groups.get("request") or ""
            status_code = int(groups.get("status", 200))

            user_str = user_raw if user_raw and user_raw not in ("-", "") else None
            timestamp = (
                self._parse_time(time_raw, current_year)
                if time_raw
                else datetime.datetime.now(datetime.timezone.utc)
            )

            attack = self._detect_payload_attacks(request)
            event_type = self._classify_event(attack, status_code, request, user_str)

            return ParsedLogLineCreate(
                timestamp=timestamp,
                source_ip=ip,
                user=user_str,
                event_type=event_type,
                port=None,
                raw_content=line,
                is_parsed=True,
            )

        return ParsedLogLineCreate(
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            event_type="unparsed_nginx",
            raw_content=line,
            is_parsed=False,
        )
