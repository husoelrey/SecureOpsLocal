import datetime
from collections import defaultdict
from typing import Any, Dict, Iterable, Set

from src.schemas.analysis import IPAggregation, LogAnalysis
from src.schemas.parsed_log_line import ParsedLogLineCreate


def aggregate_logs(lines: Iterable[ParsedLogLineCreate]) -> LogAnalysis:
    total_lines = 0
    unparsed_lines = 0
    start_time: datetime.datetime | None = None
    end_time: datetime.datetime | None = None

    # explicit typing to please mypy
    ip_stats: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {
            "failed_attempts": 0,
            "successful_attempts": 0,
            "first_seen": None,
            "last_seen": None,
            "users": set(),
        }
    )

    for line in lines:
        total_lines += 1

        if start_time is None or line.timestamp < start_time:
            start_time = line.timestamp
        if end_time is None or line.timestamp > end_time:
            end_time = line.timestamp

        if not line.is_parsed:
            unparsed_lines += 1
            continue

        if line.source_ip:
            stats = ip_stats[line.source_ip]

            if stats["first_seen"] is None or line.timestamp < stats["first_seen"]:
                stats["first_seen"] = line.timestamp
            if stats["last_seen"] is None or line.timestamp > stats["last_seen"]:
                stats["last_seen"] = line.timestamp

            if line.event_type == "successful_login":
                stats["successful_attempts"] += 1
            elif line.event_type in (
                "failed_login",
                "failed_login_invalid_user",
                "invalid_user",
            ):
                stats["failed_attempts"] += 1

            if line.user:
                users: Set[str] = stats["users"]
                users.add(line.user)

    ip_aggregations = []
    for ip, stats in ip_stats.items():
        ip_aggregations.append(
            IPAggregation(
                ip=ip,
                failed_attempts=stats["failed_attempts"],
                successful_attempts=stats["successful_attempts"],
                first_seen=stats["first_seen"],
                last_seen=stats["last_seen"],
                users_attempted=sorted(list(stats["users"])),
            )
        )

    limitations = [
        "Syslog entries lack years, so current year was assumed if ISO-8601 wasn't used.",  # noqa: E501
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
    )
