import abc
from typing import Iterator

from src.schemas.parsed_log_line import ParsedLogLineCreate


class LogParser(abc.ABC):
    @abc.abstractmethod
    def parse_line(self, line: str, current_year: int) -> ParsedLogLineCreate:
        """Parse a single log line."""
        pass

    def parse_file(
        self, file_path: str, current_year: int
    ) -> Iterator[ParsedLogLineCreate]:
        """Parse a log file line by line."""
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                yield self.parse_line(line.strip(), current_year)
