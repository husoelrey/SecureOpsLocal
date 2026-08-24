import datetime
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

from src.integrations.intel_feed import lookup_ips_intel
from src.parser.base import LogParser
from src.schemas.analysis import IPAggregation, LogAnalysis
from src.schemas.parsed_log_line import ParsedLogLineCreate

SUCCESS_EVENTS = {
    "successful_login",
    "successful_request",
    "successful_console_login",
    "windows_event_4624",
}

FAILURE_EVENTS = {
    "failed_login",
    "failed_login_invalid_user",
    "invalid_user",
    "failed_request",
    "failed_console_login",
    "sqli_attempt",
    "xss_attempt",
    "path_traversal",
    "web_attack",
    "unauthorized_access",
    "forbidden_access",
    "failed_event",
    "windows_event_4625",
}

class CrossLogAggregator:
    """
    Deterministic cross-log correlation engine.
    Correlates and merges parsed log streams from multiple heterogeneous sources
    (SSH, Nginx, Windows, AWS), grouped by Source IP and sorted chronologically by Timestamp.
    """

    def __init__(
        self,
        current_year: Optional[int] = None,
        enable_threat_intel: bool = True,
    ):
        self.events: List[ParsedLogLineCreate] = []
        self.current_year = (
            current_year or datetime.datetime.now(datetime.timezone.utc).year
        )
        self.enable_threat_intel = enable_threat_intel

    def add_events(self, events: Iterable[ParsedLogLineCreate]) -> None:
        """Add parsed log line events to the correlation pool."""
        self.events.extend(events)

    def add_parsed_lines(self, lines: Iterable[ParsedLogLineCreate]) -> None:
        """Alias for add_events."""
        self.add_events(lines)

    def add_file(
        self, file_path: str | Path, parser: LogParser
    ) -> List[ParsedLogLineCreate]:
        """Parse a log file with the given parser and add all events."""
        parsed = list(
            parser.parse_file(str(file_path), current_year=self.current_year)
        )
        self.add_events(parsed)
        return parsed

    def correlate_by_ip(self) -> Dict[str, List[ParsedLogLineCreate]]:
        """
        Group events by Source IP, filtering unparsed or IP-less lines,
        and sort each IP's events chronologically by Timestamp.
        """
        grouped: Dict[str, List[ParsedLogLineCreate]] = defaultdict(list)
        for line in self.events:
            if line.is_parsed and line.source_ip:
                grouped[line.source_ip].append(line)

        for ip in grouped:
            grouped[ip].sort(key=lambda x: x.timestamp)

        return dict(grouped)

    def get_multi_source_timeline(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Build a serializable multi-source timeline grouped by Source IP and sorted by Timestamp.
        """
        ip_groups = self.correlate_by_ip()
        timeline: Dict[str, List[Dict[str, Any]]] = {}

        for ip, events in ip_groups.items():
            timeline[ip] = [
                {
                    "timestamp": ev.timestamp.isoformat(),
                    "event_type": ev.event_type,
                    "user": ev.user,
                    "port": ev.port,
                    "raw_content": ev.raw_content,
                }
                for ev in events
            ]

        return timeline

    def aggregate(self) -> LogAnalysis:
        """
        Aggregate all collected events into a unified LogAnalysis object
        with deterministic counts, per-IP statistics, and correlated timelines.
        """
        total_lines = len(self.events)
        unparsed_lines = 0
        start_time: datetime.datetime | None = None
        end_time: datetime.datetime | None = None

        ip_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "failed_attempts": 0,
                "successful_attempts": 0,
                "first_seen": None,
                "last_seen": None,
                "users": set(),
                "events": [],
            }
        )

        for line in self.events:
            if start_time is None or line.timestamp < start_time:
                start_time = line.timestamp
            if end_time is None or line.timestamp > end_time:
                end_time = line.timestamp

            if not line.is_parsed:
                unparsed_lines += 1
                continue

            if line.source_ip:
                stats = ip_stats[line.source_ip]
                stats["events"].append(line)

                if stats["first_seen"] is None or line.timestamp < stats["first_seen"]:
                    stats["first_seen"] = line.timestamp
                if stats["last_seen"] is None or line.timestamp > stats["last_seen"]:
                    stats["last_seen"] = line.timestamp

                if line.event_type in SUCCESS_EVENTS or line.event_type.startswith(
                    "successful"
                ):
                    stats["successful_attempts"] += 1
                elif (
                    line.event_type in FAILURE_EVENTS
                    or line.event_type.startswith("failed_")
                    or "attempt" in line.event_type
                    or "attack" in line.event_type
                    or "traversal" in line.event_type
                ):
                    stats["failed_attempts"] += 1

                if line.user:
                    users: Set[str] = stats["users"]
                    users.add(line.user)

        # Query local SQLite threat intelligence database for extracted IPs
        intel_matches: Dict[str, Any] = {}
        if self.enable_threat_intel and ip_stats:
            try:
                intel_matches = lookup_ips_intel(list(ip_stats.keys()))
            except Exception:
                intel_matches = {}

        ip_aggregations = []
        multi_source_timeline: Dict[str, List[Dict[str, Any]]] = {}

        for ip, stats in ip_stats.items():
            # Sort events for this IP chronologically
            sorted_events = sorted(stats["events"], key=lambda x: x.timestamp)
            multi_source_timeline[ip] = [
                {
                    "timestamp": ev.timestamp.isoformat(),
                    "event_type": ev.event_type,
                    "user": ev.user,
                    "port": ev.port,
                    "raw_content": ev.raw_content,
                }
                for ev in sorted_events
            ]

            flags: List[str] = []
            if ip in intel_matches:
                match = intel_matches[ip]
                flags.append(match.threat_type.upper())

            ip_aggregations.append(
                IPAggregation(
                    ip=ip,
                    failed_attempts=stats["failed_attempts"],
                    successful_attempts=stats["successful_attempts"],
                    first_seen=stats["first_seen"],
                    last_seen=stats["last_seen"],
                    users_attempted=sorted(list(stats["users"])),
                    intel_flags=flags,
                )
            )

        # Sort IP aggregations by failed_attempts descending, then ip
        ip_aggregations.sort(key=lambda x: (-x.failed_attempts, x.ip))

        limitations = [
            "Syslog entries lack years, so current year was assumed if ISO-8601 wasn't used.",
        ]
        if unparsed_lines > 0:
            limitations.append(f"{unparsed_lines} line(s) could not be parsed.")

        return LogAnalysis(
            total_lines=total_lines,
            unparsed_lines=unparsed_lines,
            start_time=start_time,
            end_time=end_time,
            ip_aggregations=ip_aggregations,
            limitations=limitations,
            multi_source_timeline=multi_source_timeline,
        )


def aggregate_logs(
    lines: Iterable[ParsedLogLineCreate],
    enable_threat_intel: bool = True,
) -> LogAnalysis:
    """Convenience function to aggregate an iterable of parsed log lines."""
    aggregator = CrossLogAggregator(enable_threat_intel=enable_threat_intel)
    aggregator.add_events(lines)
    return aggregator.aggregate()
