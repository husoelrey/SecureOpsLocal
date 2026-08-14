from src.parser.aggregator import aggregate_logs
from src.parser.aws import AWSCloudTrailParser
from src.parser.base import LogParser
from src.parser.nginx import NginxAccessParser
from src.parser.ssh import SSHAuthLogParser
from src.parser.windows import WindowsEventLogParser

__all__ = [
    "LogParser",
    "SSHAuthLogParser",
    "WindowsEventLogParser",
    "NginxAccessParser",
    "AWSCloudTrailParser",
    "aggregate_logs",
]
