import datetime
from typing import List, Tuple

from src.schemas.parsed_log_line import ParsedLogLineCreate

FAILURE_EVENT_TYPES = {
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


def is_security_failure_event(event: ParsedLogLineCreate) -> bool:
    """Determine if a parsed event constitutes a security failure or attack attempt."""
    if not event.is_parsed:
        return False

    ev_type = (event.event_type or "").lower()
    if ev_type in FAILURE_EVENT_TYPES:
        return True
    if ev_type.startswith("failed_"):
        return True
    if any(k in ev_type for k in ("sqli", "xss", "traversal", "attack", "unauthorized")):
        return True

    return False


class SlidingWindowEventTracker:
    """
    Sliding window tracker for security events.
    Maintains a rolling window of events over `window_seconds` and triggers
    when the number of security failure events meets or exceeds `threshold`.
    """

    def __init__(self, threshold: int = 5, window_seconds: int = 60):
        if threshold <= 0:
            raise ValueError("Threshold must be a positive integer greater than 0.")
        if window_seconds <= 0:
            raise ValueError("Window seconds must be a positive integer greater than 0.")

        self.threshold = threshold
        self.window_seconds = window_seconds
        self.events: List[Tuple[datetime.datetime, ParsedLogLineCreate]] = []

    def prune(self, current_time: datetime.datetime) -> None:
        """Remove events outside the current rolling time window."""
        cutoff = current_time - datetime.timedelta(seconds=self.window_seconds)
        self.events = [(ts, ev) for ts, ev in self.events if ts >= cutoff]

    def add_event(
        self, event: ParsedLogLineCreate, now: datetime.datetime | None = None
    ) -> bool:
        """
        Record a parsed log event.
        Returns True if the failure threshold is breached within the sliding window.
        """
        current_time = now or datetime.datetime.now(datetime.timezone.utc)

        # Prune older events
        self.prune(current_time)

        # Only add failure / attack events to threshold count
        if is_security_failure_event(event):
            event_ts = event.timestamp
            if event_ts.tzinfo is None:
                event_ts = event_ts.replace(tzinfo=datetime.timezone.utc)

            # Use current_time as the arrival timestamp if log timestamp is far in the past
            arrival_ts = current_time
            self.events.append((arrival_ts, event))

        # Check threshold
        return len(self.events) >= self.threshold

    def get_window_events(self) -> List[ParsedLogLineCreate]:
        """Return the list of parsed log lines currently in the sliding window."""
        return [ev for _, ev in self.events]

    def reset(self) -> None:
        """Clear the current window state after an alert has triggered."""
        self.events.clear()

    @property
    def current_count(self) -> int:
        """Return the current number of failure events in the active window."""
        return len(self.events)
