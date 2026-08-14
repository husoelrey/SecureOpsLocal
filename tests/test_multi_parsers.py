import json
from pathlib import Path

import pytest
from src.cli.analyze import get_parser_for_log_type
from src.parser.aggregator import aggregate_logs
from src.parser.aws import AWSCloudTrailParser
from src.parser.nginx import NginxAccessParser
from src.parser.ssh import SSHAuthLogParser
from src.parser.windows import WindowsEventLogParser

# ============================================================================
# WindowsEventLogParser Tests
# ============================================================================


def test_windows_parser_json_4625_failed_login():
    parser = WindowsEventLogParser()
    line = json.dumps(
        {
            "EventID": 4625,
            "TimeCreated": "2026-08-14T10:15:30Z",
            "TargetUserName": "Administrator",
            "IpAddress": "192.168.1.55",
            "IpPort": 51234,
        }
    )
    res = parser.parse_line(line, 2026)
    assert res.is_parsed is True
    assert res.event_type == "failed_login"
    assert res.user == "Administrator"
    assert res.source_ip == "192.168.1.55"
    assert res.port == 51234
    assert res.timestamp.year == 2026
    assert res.timestamp.hour == 10


def test_windows_parser_json_4624_successful_login():
    parser = WindowsEventLogParser()
    line = json.dumps(
        {
            "EventID": 4624,
            "TimeCreated": "2026-08-14T10:16:00Z",
            "TargetUserName": "alice",
            "IpAddress": "10.0.0.99",
            "IpPort": 49152,
        }
    )
    res = parser.parse_line(line, 2026)
    assert res.is_parsed is True
    assert res.event_type == "successful_login"
    assert res.user == "alice"
    assert res.source_ip == "10.0.0.99"


def test_windows_parser_nested_evtx_json():
    parser = WindowsEventLogParser()
    data = {
        "Event": {
            "System": {
                "EventID": 4625,
                "TimeCreated": {"@SystemTime": "2026-08-14T11:00:00.000Z"},
            },
            "EventData": {
                "TargetUserName": "bob_admin",
                "IpAddress": "172.16.0.42",
                "IpPort": "54321",
            },
        }
    }
    res = parser.parse_line(json.dumps(data), 2026)
    assert res.is_parsed is True
    assert res.event_type == "failed_login"
    assert res.user == "bob_admin"
    assert res.source_ip == "172.16.0.42"
    assert res.port == 54321


def test_windows_parser_structured_text():
    parser = WindowsEventLogParser()
    line = (
        "2026-08-14 12:00:00 Microsoft-Windows-Security-Auditing: "
        "EventID: 4625, Account Name: admin, Source Network Address: 192.168.1.200, Source Port: 44100"
    )
    res = parser.parse_line(line, 2026)
    assert res.is_parsed is True
    assert res.event_type == "failed_login"
    assert res.user == "admin"
    assert res.source_ip == "192.168.1.200"
    assert res.port == 44100


def test_windows_parser_parse_file_json_array(tmp_path: Path):
    parser = WindowsEventLogParser()
    events = [
        {"EventID": 4625, "TargetUserName": "user1", "IpAddress": "1.1.1.1"},
        {"EventID": 4624, "TargetUserName": "user1", "IpAddress": "1.1.1.1"},
    ]
    file_path = tmp_path / "win_events.json"
    file_path.write_text(json.dumps(events), encoding="utf-8")

    parsed = list(parser.parse_file(str(file_path), 2026))
    assert len(parsed) == 2
    assert parsed[0].event_type == "failed_login"
    assert parsed[1].event_type == "successful_login"

    analysis = aggregate_logs(parsed)
    assert analysis.total_lines == 2
    assert len(analysis.ip_aggregations) == 1
    assert analysis.ip_aggregations[0].failed_attempts == 1
    assert analysis.ip_aggregations[0].successful_attempts == 1


def test_windows_parser_unparsed_line():
    parser = WindowsEventLogParser()
    res = parser.parse_line("Some random non-windows text line", 2026)
    assert res.is_parsed is False
    assert res.event_type == "unparsed_windows"


# ============================================================================
# NginxAccessParser Tests
# ============================================================================


def test_nginx_parser_combined_format_standard():
    parser = NginxAccessParser()
    line = '192.168.1.10 - alice [14/Aug/2026:12:00:00 +0000] "GET /dashboard HTTP/1.1" 200 4523 "-" "Mozilla/5.0"'
    res = parser.parse_line(line, 2026)
    assert res.is_parsed is True
    assert res.event_type == "successful_request"
    assert res.source_ip == "192.168.1.10"
    assert res.user == "alice"


def test_nginx_parser_sqli_detection():
    parser = NginxAccessParser()
    line = '10.0.0.15 - - [14/Aug/2026:12:05:00 +0000] "GET /products.php?id=1%27%20UNION%20SELECT%20null,username,password%20FROM%20users-- HTTP/1.1" 200 1024 "-" "sqlmap/1.5"'
    res = parser.parse_line(line, 2026)
    assert res.is_parsed is True
    assert res.event_type == "sqli_attempt"
    assert res.source_ip == "10.0.0.15"


def test_nginx_parser_xss_detection():
    parser = NginxAccessParser()
    line = '10.0.0.20 - - [14/Aug/2026:12:10:00 +0000] "GET /search?q=%3Cscript%3Ealert(document.cookie)%3C/script%3E HTTP/1.1" 200 512 "-" "Mozilla/5.0"'
    res = parser.parse_line(line, 2026)
    assert res.is_parsed is True
    assert res.event_type == "xss_attempt"
    assert res.source_ip == "10.0.0.20"


def test_nginx_parser_path_traversal_detection():
    parser = NginxAccessParser()
    line = '10.0.0.25 - - [14/Aug/2026:12:15:00 +0000] "GET /download?file=../../../../etc/passwd HTTP/1.1" 404 150 "-" "curl/7.68.0"'
    res = parser.parse_line(line, 2026)
    assert res.is_parsed is True
    assert res.event_type == "path_traversal"
    assert res.source_ip == "10.0.0.25"


def test_nginx_parser_auth_failure_401():
    parser = NginxAccessParser()
    line = '192.168.1.50 - baduser [14/Aug/2026:12:20:00 +0000] "POST /api/login HTTP/1.1" 401 80 "-" "Mozilla/5.0"'
    res = parser.parse_line(line, 2026)
    assert res.is_parsed is True
    assert res.event_type == "failed_login"
    assert res.source_ip == "192.168.1.50"
    assert res.user == "baduser"


def test_nginx_parser_json_format():
    parser = NginxAccessParser()
    data = {
        "remote_addr": "198.51.100.33",
        "remote_user": "john",
        "time_local": "14/Aug/2026:12:30:00 +0000",
        "request": "GET /api/users?search=%27%20OR%201=1-- HTTP/1.1",
        "status": 200,
    }
    res = parser.parse_line(json.dumps(data), 2026)
    assert res.is_parsed is True
    assert res.event_type == "sqli_attempt"
    assert res.source_ip == "198.51.100.33"
    assert res.user == "john"


def test_nginx_parser_unparsed():
    parser = NginxAccessParser()
    res = parser.parse_line("invalid nginx line content without pattern", 2026)
    assert res.is_parsed is False
    assert res.event_type == "unparsed_nginx"


# ============================================================================
# AWSCloudTrailParser Tests
# ============================================================================


def test_aws_parser_console_login_failure():
    parser = AWSCloudTrailParser()
    event = {
        "eventVersion": "1.08",
        "userIdentity": {
            "type": "IAMUser",
            "principalId": "AIDA12345EXAMPLE",
            "arn": "arn:aws:iam::123456789012:user/secadmin",
            "userName": "secadmin",
        },
        "eventTime": "2026-08-14T14:00:00Z",
        "eventSource": "signin.amazonaws.com",
        "eventName": "ConsoleLogin",
        "sourceIPAddress": "203.0.113.88",
        "errorMessage": "Failed authentication",
        "responseElements": {"ConsoleLogin": "Failure"},
    }
    res = parser.parse_line(json.dumps(event), 2026)
    assert res.is_parsed is True
    assert res.event_type == "failed_login"
    assert res.user == "secadmin"
    assert res.source_ip == "203.0.113.88"
    assert res.timestamp.hour == 14


def test_aws_parser_console_login_success():
    parser = AWSCloudTrailParser()
    event = {
        "userIdentity": {"userName": "validuser"},
        "eventTime": "2026-08-14T14:05:00Z",
        "eventName": "ConsoleLogin",
        "sourceIPAddress": "203.0.113.88",
        "responseElements": {"ConsoleLogin": "Success"},
    }
    res = parser.parse_line(json.dumps(event), 2026)
    assert res.is_parsed is True
    assert res.event_type == "successful_login"
    assert res.user == "validuser"
    assert res.source_ip == "203.0.113.88"


def test_aws_parser_records_wrapper(tmp_path: Path):
    parser = AWSCloudTrailParser()
    cloudtrail_doc = {
        "Records": [
            {
                "eventName": "ConsoleLogin",
                "eventTime": "2026-08-14T15:00:00Z",
                "sourceIPAddress": "198.51.100.99",
                "userIdentity": {"userName": "root"},
                "responseElements": {"ConsoleLogin": "Failure"},
            },
            {
                "eventName": "ConsoleLogin",
                "eventTime": "2026-08-14T15:01:00Z",
                "sourceIPAddress": "198.51.100.99",
                "userIdentity": {"userName": "root"},
                "responseElements": {"ConsoleLogin": "Failure"},
            },
        ]
    }
    file_path = tmp_path / "cloudtrail.json"
    file_path.write_text(json.dumps(cloudtrail_doc), encoding="utf-8")

    parsed = list(parser.parse_file(str(file_path), 2026))
    assert len(parsed) == 2
    assert all(p.event_type == "failed_login" for p in parsed)

    analysis = aggregate_logs(parsed)
    assert analysis.total_lines == 2
    assert analysis.ip_aggregations[0].failed_attempts == 2


def test_aws_parser_non_login_event():
    parser = AWSCloudTrailParser()
    event = {
        "eventName": "DescribeInstances",
        "eventTime": "2026-08-14T15:10:00Z",
        "sourceIPAddress": "10.0.0.1",
        "userIdentity": {"userName": "dev"},
    }
    res = parser.parse_line(json.dumps(event), 2026)
    assert res.is_parsed is True
    assert res.event_type == "aws_describeinstances"


def test_aws_parser_unparsed():
    parser = AWSCloudTrailParser()
    res = parser.parse_line("Random non-cloudtrail plain string", 2026)
    assert res.is_parsed is False
    assert res.event_type == "unparsed_cloudtrail"


# ============================================================================
# Factory & Multi-Source CLI Integration Tests
# ============================================================================


def test_get_parser_for_log_type():
    assert isinstance(get_parser_for_log_type("ssh"), SSHAuthLogParser)
    assert isinstance(get_parser_for_log_type("windows"), WindowsEventLogParser)
    assert isinstance(get_parser_for_log_type("nginx"), NginxAccessParser)
    assert isinstance(get_parser_for_log_type("aws"), AWSCloudTrailParser)

    with pytest.raises(ValueError, match="Unsupported log type"):
        get_parser_for_log_type("unsupported_source")
