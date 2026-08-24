import datetime
import logging
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from src.parser.base import LogParser
from src.schemas.parsed_log_line import ParsedLogLineCreate
from src.watcher.window import SlidingWindowEventTracker

logger = logging.getLogger(__name__)


class _LogFileEventHandler(FileSystemEventHandler):
    def __init__(self, target_path: Path, callback: Callable[..., Any]):
        super().__init__()
        self.target_path = target_path.resolve()
        self.callback = callback

    def on_modified(self, event: FileSystemEvent) -> None:
        src = str(event.src_path)
        if Path(src).resolve() == self.target_path:
            self.callback()


class LogWatcherEngine:
    """
    Continuous log tailer and event stream processor.
    Monitors one or more log files for appended lines, parses them deterministically,
    tracks failure frequencies across a sliding window, and invokes callbacks on breaches.
    """

    def __init__(
        self,
        file_path: Optional[Path] = None,
        parser: Optional[LogParser] = None,
        tracker: Optional[SlidingWindowEventTracker] = None,
        on_breach: Optional[Callable[[List[ParsedLogLineCreate]], None]] = None,
        current_year: Optional[int] = None,
        start_from_beginning: bool = False,
        targets: Optional[List[Tuple[Path, LogParser]]] = None,
    ):
        if tracker is None:
            raise ValueError("SlidingWindowEventTracker instance is required")
        if on_breach is None:
            raise ValueError("on_breach callback is required")

        self.tracker = tracker
        self.on_breach = on_breach
        self.current_year = (
            current_year or datetime.datetime.now(datetime.timezone.utc).year
        )
        self.start_from_beginning = start_from_beginning

        self.targets: List[Tuple[Path, LogParser]] = []
        if targets:
            self.targets.extend(targets)
        elif file_path and parser:
            self.targets.append((file_path, parser))
        else:
            raise ValueError(
                "Either 'targets' or both 'file_path' and 'parser' must be provided."
            )

        self._offsets: Dict[Path, int] = {}
        for path, _ in self.targets:
            resolved = path.resolve()
            if resolved.exists() and not start_from_beginning:
                self._offsets[resolved] = resolved.stat().st_size
            else:
                self._offsets[resolved] = 0

        self._running = False
        self._observer: Any = None

    @property
    def file_path(self) -> Path:
        """First target file path for backward compatibility."""
        return self.targets[0][0]

    @property
    def parser(self) -> LogParser:
        """First target parser for backward compatibility."""
        return self.targets[0][1]

    def read_new_lines(self) -> List[str]:
        """Read any new lines appended to the primary log file."""
        if not self.targets:
            return []
        resolved = self.targets[0][0].resolve()
        if not resolved.exists():
            return []

        try:
            current_size = resolved.stat().st_size
            offset = self._offsets.get(resolved, 0)
            if current_size < offset:
                offset = 0

            if current_size == offset:
                return []

            with open(resolved, "r", encoding="utf-8", errors="replace") as f:
                f.seek(offset)
                content = f.read()
                self._offsets[resolved] = f.tell()

            return [line for line in content.splitlines() if line.strip()]
        except Exception as e:
            logger.error(f"Error reading log file {resolved}: {e}")
            return []

    def process_new_events(self) -> List[ParsedLogLineCreate]:
        """Read and process newly appended log lines across all monitored files."""
        all_parsed: List[ParsedLogLineCreate] = []

        for path, parser in self.targets:
            resolved = path.resolve()
            if not resolved.exists():
                continue

            try:
                current_size = resolved.stat().st_size
                offset = self._offsets.get(resolved, 0)
                if current_size < offset:
                    offset = 0
                if current_size == offset:
                    continue

                with open(resolved, "r", encoding="utf-8", errors="replace") as f:
                    f.seek(offset)
                    content = f.read()
                    self._offsets[resolved] = f.tell()

                lines = [line for line in content.splitlines() if line.strip()]
                for line in lines:
                    parsed = parser.parse_line(line, self.current_year)
                    all_parsed.append(parsed)

                    breached = self.tracker.add_event(parsed)
                    if breached:
                        window_events = self.tracker.get_window_events()
                        self.on_breach(window_events)
                        self.tracker.reset()
            except Exception as e:
                logger.error(f"Error reading log file {resolved}: {e}")

        return all_parsed

    def start(self, poll_interval: float = 0.5, blocking: bool = True) -> None:
        """Start watchdog file monitoring and polling loop for all target files."""
        self._running = True
        self._observer = Observer()

        scheduled_dirs = set()
        for path, _ in self.targets:
            parent_dir = path.resolve().parent
            parent_dir.mkdir(parents=True, exist_ok=True)
            if parent_dir not in scheduled_dirs:
                handler = _LogFileEventHandler(
                    path, callback=self.process_new_events
                )
                self._observer.schedule(
                    handler, path=str(parent_dir), recursive=False
                )
                scheduled_dirs.add(parent_dir)

        self._observer.start()

        # Process any pending lines immediately
        self.process_new_events()

        if blocking:
            try:
                while self._running:
                    self.process_new_events()
                    time.sleep(poll_interval)
            except KeyboardInterrupt:
                self.stop()

    def stop(self) -> None:
        """Stop the watcher engine and watchdog observer."""
        self._running = False
        if self._observer and self._observer.is_alive():
            self._observer.stop()
            self._observer.join(timeout=2.0)
            self._observer = None
