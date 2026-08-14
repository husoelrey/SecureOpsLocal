import datetime
import json
import re
from typing import Any, Dict, Iterator

from src.parser.base import LogParser
from src.schemas.parsed_log_line import ParsedLogLineCreate

# ISO timestamp pattern for CloudTrail eventTime
ISO_TS_RE = re.compile(
    r"(?P<iso_ts>\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)"
)

# Text / Syslog CloudTrail regex fallback
CLOUDTRAIL_TEXT_RE = re.compile(
    r"(?:eventName=[\"']?(?P<event_name>\w+)[\"']?|eventSource=[\"']?(?P<event_source>[^\"'\s]+)[\"']?|userName=[\"']?(?P<user>[^\"'\s]+)[\"']?|sourceIPAddress=[\"']?(?P<ip>[^\"'\s]+)[\"']?|ConsoleLogin=[\"']?(?P<console_status>\w+)[\"']?|errorMessage=[\"']?(?P<error>[^\"']+)[\"']?)",
    re.IGNORECASE,
)


class AWSCloudTrailParser(LogParser):
    """
    Deterministic parser for AWS CloudTrail security events.
    Focuses on ConsoleLogin failure/success anomalies and IAM authentication events.
    """

    def _parse_timestamp(self, ts_raw: Any, current_year: int) -> datetime.datetime:
        if not ts_raw:
            return datetime.datetime.now(datetime.timezone.utc)

        if isinstance(ts_raw, datetime.datetime):
            if ts_raw.tzinfo is None:
                return ts_raw.replace(tzinfo=datetime.timezone.utc)
            return ts_raw

        ts_str = str(ts_raw).strip()
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

        return datetime.datetime.now(datetime.timezone.utc)

    def _parse_json_dict(
        self, data: Dict[str, Any], raw_line: str, current_year: int
    ) -> ParsedLogLineCreate:
        event_name = str(data.get("eventName") or data.get("event_name") or "").strip()
        event_time = (
            data.get("eventTime") or data.get("event_time") or data.get("timestamp")
        )
        timestamp = self._parse_timestamp(event_time, current_year)

        # Extract Source IP
        source_ip = (
            data.get("sourceIPAddress")
            or data.get("source_ip_address")
            or data.get("sourceIP")
            or data.get("ip")
        )
        source_ip_str = (
            str(source_ip).strip()
            if source_ip and str(source_ip).strip() not in ("-", "AWS Internal", "null")
            else None
        )

        # Extract User / IAM Identity
        user_identity = (
            data.get("userIdentity", {})
            if isinstance(data.get("userIdentity"), dict)
            else {}
        )
        user = (
            user_identity.get("userName")
            or user_identity.get("principalId")
            or user_identity.get("arn")
            or data.get("userName")
            or data.get("user")
        )
        # If ARN e.g. arn:aws:iam::123456789012:user/alice, simplify to alice if possible
        user_str = (
            str(user).strip()
            if user and str(user).strip() not in ("-", "", "null")
            else None
        )
        if user_str and "/" in user_str and user_str.startswith("arn:aws:"):
            user_str = user_str.split("/")[-1]

        # Extract response elements & error status
        response_elements = (
            data.get("responseElements", {})
            if isinstance(data.get("responseElements"), dict)
            else {}
        )
        console_login_status = response_elements.get("ConsoleLogin") or data.get(
            "ConsoleLogin"
        )
        error_msg = data.get("errorMessage") or data.get("errorCode")

        # Classify event
        if event_name.lower() == "consolelogin":
            if str(console_login_status).lower() == "failure" or error_msg:
                event_type = "failed_login"
            elif str(console_login_status).lower() == "success" and not error_msg:
                event_type = "successful_login"
            else:
                event_type = "failed_login" if error_msg else "successful_login"
            is_parsed = True
        elif event_name:
            if error_msg:
                event_type = f"failed_aws_{event_name.lower()}"
            else:
                event_type = f"aws_{event_name.lower()}"
            is_parsed = True
        else:
            event_type = "unparsed_cloudtrail"
            is_parsed = bool(source_ip_str or user_str)

        return ParsedLogLineCreate(
            timestamp=timestamp,
            source_ip=source_ip_str,
            user=user_str,
            event_type=event_type,
            port=None,
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

        # 1. Try JSON parsing
        if line_clean.startswith("{") and line_clean.endswith("}"):
            try:
                data = json.loads(line_clean)
                if isinstance(data, dict):
                    # Handle single record or single CloudTrail wrapper
                    if (
                        "Records" in data
                        and isinstance(data["Records"], list)
                        and len(data["Records"]) == 1
                    ):
                        return self._parse_json_dict(
                            data["Records"][0], line, current_year
                        )
                    return self._parse_json_dict(data, line, current_year)
            except Exception:
                pass

        # 2. Try Regex / text fallback
        timestamp = self._parse_timestamp(line_clean, current_year)
        if "ConsoleLogin" in line_clean or "AWSCloudTrail" in line_clean:
            user_m = re.search(
                r"(?:user(?:Name)?|arn)=['\"]?([^\s,'\"]+)", line_clean, re.IGNORECASE
            )
            ip_m = re.search(
                r"(?:sourceIPAddress|ip)=['\"]?([0-9a-fA-F:\.]+)",
                line_clean,
                re.IGNORECASE,
            )
            is_fail = bool(
                re.search(
                    r"(Failure|failed|error|Unauthorized)", line_clean, re.IGNORECASE
                )
            )
            is_success = bool(
                re.search(r"(Success|accepted)", line_clean, re.IGNORECASE)
            )

            user = user_m.group(1) if user_m else None
            ip = ip_m.group(1) if ip_m else None

            if is_fail:
                event_type = "failed_login"
            elif is_success:
                event_type = "successful_login"
            else:
                event_type = "aws_consolelogin"

            return ParsedLogLineCreate(
                timestamp=timestamp,
                source_ip=ip,
                user=user,
                event_type=event_type,
                port=None,
                raw_content=line,
                is_parsed=True,
            )

        return ParsedLogLineCreate(
            timestamp=timestamp,
            event_type="unparsed_cloudtrail",
            raw_content=line,
            is_parsed=False,
        )

    def parse_file(
        self, file_path: str, current_year: int
    ) -> Iterator[ParsedLogLineCreate]:
        """Parse CloudTrail log file (supports Records wrapper array, JSON array, JSONL, and text)."""
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read().strip()

        # Handle full CloudTrail JSON format {"Records": [...]}
        if content.startswith("{") and content.endswith("}"):
            try:
                data = json.loads(content)
                if (
                    isinstance(data, dict)
                    and "Records" in data
                    and isinstance(data["Records"], list)
                ):
                    for record in data["Records"]:
                        if isinstance(record, dict):
                            raw_record = json.dumps(record)
                            yield self._parse_json_dict(
                                record, raw_record, current_year
                            )
                    return
            except Exception:
                pass

        # Handle JSON array format [{...}, {...}]
        if content.startswith("[") and content.endswith("]"):
            try:
                events = json.loads(content)
                if isinstance(events, list):
                    for item in events:
                        if isinstance(item, dict):
                            raw_item = json.dumps(item)
                            yield self._parse_json_dict(item, raw_item, current_year)
                    return
            except Exception:
                pass

        # Fallback to line by line
        for line in content.splitlines():
            if line.strip():
                yield self.parse_line(line.strip(), current_year)
