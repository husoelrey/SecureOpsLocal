import datetime
import logging
import time
from pathlib import Path
from typing import Any, Callable, List, Optional

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
    Monitors a file for appended lines, parses them deterministically,
    tracks failure frequencies across a sliding window, and invokes callbacks on breaches.
    """

    def __init__(
        self,
        file_path: Path,
        parser: LogParser,
        tracker: SlidingWindowEventTracker,
        on_breach: Callable[[List[ParsedLogLineCreate]], None],
        current_year: Optional[int] = None,
        start_from_beginning: bool = False,
    ):
        self.file_path = file_path.resolve()
        self.parser = parser
        self.tracker = tracker
        self.on_breach = on_breach
        self.current_year = (
            current_year or datetime.datetime.now(datetime.timezone.utc).year
        )
        self._offset = 0
        self._running = False
        self._observer: Any = None

        if self.file_path.exists() and not start_from_beginning:
            # Tail mode: start at end of existing file
            self._offset = self.file_path.stat().st_size
        else:
            self._offset = 0

    def read_new_lines(self) -> List[str]:
        """Read any new lines appended to the log file since the last check."""
        if not self.file_path.exists():
            return []

        try:
            current_size = self.file_path.stat().st_size
            # Handle log rotation or truncation
            if current_size < self._offset:
                self._offset = 0

            if current_size == self._offset:
                return []

            with open(self.file_path, "r", encoding="utf-8", errors="replace") as f:
                f.seek(self._offset)
                content = f.read()
                self._offset = f.tell()

            return [line for line in content.splitlines() if line.strip()]
        except Exception as e:
            logger.error(f"Error reading log file {self.file_path}: {e}")
            return []

    def process_new_events(self) -> List[ParsedLogLineCreate]:
        """Read and process newly appended log lines through the parser and sliding window tracker."""
        lines = self.read_new_lines()
        parsed_list: List[ParsedLogLineCreate] = []

        for line in lines:
            parsed = self.parser.parse_line(line, self.current_year)
            parsed_list.append(parsed)

            breached = self.tracker.add_event(parsed)
            if breached:
                window_events = self.tracker.get_window_events()
                self.on_breach(window_events)
                self.tracker.reset()

        return parsed_list

    def start(self, poll_interval: float = 0.5, blocking: bool = True) -> None:
        """Start watchdog file monitoring and polling loop."""
        self._running = True

        # Set up watchdog observer for file system change events
        parent_dir = self.file_path.parent
        parent_dir.mkdir(parents=True, exist_ok=True)

        handler = _LogFileEventHandler(self.file_path, callback=self.process_new_events)
        self._observer = Observer()
        self._observer.schedule(handler, path=str(parent_dir), recursive=False)
        self._observer.start()

        # Process any pending lines immediately
        self.process_new_events()

        if blocking:
            try:
                while self._running:
                    # Hybrid check with poll interval to ensure reliability across all OS / network shares
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
