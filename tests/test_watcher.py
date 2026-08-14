import datetime
from pathlib import Path

from src.cli.main import app
from src.parser.ssh import SSHAuthLogParser
from src.schemas.parsed_log_line import ParsedLogLineCreate
from src.watcher.engine import LogWatcherEngine
from src.watcher.window import SlidingWindowEventTracker, is_security_failure_event
from typer.testing import CliRunner

runner = CliRunner()


def test_is_security_failure_event():
    now = datetime.datetime.now(datetime.timezone.utc)

    # Success event
    ev_success = ParsedLogLineCreate(
        timestamp=now,
        source_ip="1.1.1.1",
        user="admin",
        event_type="successful_login",
        raw_content="accepted",
        is_parsed=True,
    )
    assert not is_security_failure_event(ev_success)

    # Failure events
    for f_type in ("failed_login", "invalid_user", "sqli_attempt", "xss_attempt", "path_traversal", "windows_event_4625"):
        ev_fail = ParsedLogLineCreate(
            timestamp=now,
            source_ip="1.1.1.1",
            user="admin",
            event_type=f_type,
            raw_content="failed",
            is_parsed=True,
        )
        assert is_security_failure_event(ev_fail)

    # Unparsed event
    ev_unparsed = ParsedLogLineCreate(
        timestamp=now,
        event_type="unparsed",
        raw_content="garbage",
        is_parsed=False,
    )
    assert not is_security_failure_event(ev_unparsed)


def test_sliding_window_tracker_threshold_breach():
    tracker = SlidingWindowEventTracker(threshold=3, window_seconds=60)
    now = datetime.datetime.now(datetime.timezone.utc)

    ev = ParsedLogLineCreate(
        timestamp=now,
        source_ip="10.0.0.1",
        user="root",
        event_type="failed_login",
        raw_content="Failed password",
        is_parsed=True,
    )

    # Event 1
    assert tracker.add_event(ev, now=now) is False
    assert tracker.current_count == 1

    # Event 2
    assert tracker.add_event(ev, now=now + datetime.timedelta(seconds=10)) is False
    assert tracker.current_count == 2

    # Event 3 (threshold reached!)
    assert tracker.add_event(ev, now=now + datetime.timedelta(seconds=20)) is True
    assert tracker.current_count == 3
    assert len(tracker.get_window_events()) == 3

    # Reset
    tracker.reset()
    assert tracker.current_count == 0
    assert len(tracker.get_window_events()) == 0


def test_sliding_window_pruning():
    tracker = SlidingWindowEventTracker(threshold=3, window_seconds=30)
    t0 = datetime.datetime(2026, 8, 14, 12, 0, 0, tzinfo=datetime.timezone.utc)

    ev = ParsedLogLineCreate(
        timestamp=t0,
        source_ip="10.0.0.1",
        user="root",
        event_type="failed_login",
        raw_content="Failed password",
        is_parsed=True,
    )

    # Event 1 at t0
    tracker.add_event(ev, now=t0)
    assert tracker.current_count == 1

    # Event 2 at t0 + 10s
    t1 = t0 + datetime.timedelta(seconds=10)
    tracker.add_event(ev, now=t1)
    assert tracker.current_count == 2

    # Event 3 at t0 + 45s (Event 1 at t0 should have expired because 45s > 30s window)
    t2 = t0 + datetime.timedelta(seconds=45)
    breached = tracker.add_event(ev, now=t2)
    assert breached is False
    # Only event 2 (at 10s -> age 35s... wait, 45 - 10 = 35s which is > 30s as well!)
    # So both event 1 and event 2 expired, leaving only event 3
    assert tracker.current_count == 1


def test_log_watcher_engine_appends_and_breach(tmp_path: Path):
    log_file = tmp_path / "auth_test.log"
    log_file.write_text("", encoding="utf-8")

    breaches = []

    def on_breach(events):
        breaches.append(events)

    tracker = SlidingWindowEventTracker(threshold=2, window_seconds=60)
    parser = SSHAuthLogParser()
    engine = LogWatcherEngine(
        file_path=log_file,
        parser=parser,
        tracker=tracker,
        on_breach=on_breach,
        current_year=2026,
        start_from_beginning=True,
    )

    # Append 1 failure line
    with open(log_file, "a", encoding="utf-8") as f:
        f.write("Aug 14 12:00:01 server sshd[100]: Failed password for invalid user admin from 1.2.3.4 port 1234 ssh2\n")

    events = engine.process_new_events()
    assert len(events) == 1
    assert len(breaches) == 0

    # Append 2nd failure line -> should trigger breach!
    with open(log_file, "a", encoding="utf-8") as f:
        f.write("Aug 14 12:00:02 server sshd[101]: Failed password for invalid user admin from 1.2.3.4 port 1235 ssh2\n")

    events2 = engine.process_new_events()
    assert len(events2) == 1
    assert len(breaches) == 1
    assert len(breaches[0]) == 2


def test_cli_watch_help():
    result = runner.invoke(app, ["watch", "--help"])
    assert result.exit_code == 0
    assert "Continuously tail a security log file" in result.output
    assert "--threshold" in result.output
    assert "--log-type" in result.output
    assert "--window-seconds" in result.output
