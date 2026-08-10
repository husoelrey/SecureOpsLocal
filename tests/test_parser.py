from src.parser.ssh import SSHAuthLogParser


def test_syslog_successful_login_ipv4():
    parser = SSHAuthLogParser()
    line = "Aug 10 14:12:05 server sshd[123]: Accepted password for admin from 192.168.1.100 port 55432 ssh2"  # noqa: E501
    res = parser.parse_line(line, 2026)
    assert res.is_parsed is True
    assert res.event_type == "successful_login"
    assert res.user == "admin"
    assert res.source_ip == "192.168.1.100"
    assert res.port == 55432
    assert res.timestamp.year == 2026
    assert res.timestamp.month == 8
    assert res.timestamp.day == 10

def test_syslog_failed_login_ipv6():
    parser = SSHAuthLogParser()
    line = "Nov  1 12:00:00 server sshd[456]: Failed password for root from 2001:db8::1 port 22 ssh2"  # noqa: E501
    res = parser.parse_line(line, 2026)
    assert res.is_parsed is True
    assert res.event_type == "failed_login"
    assert res.user == "root"
    assert res.source_ip == "2001:db8::1"
    assert res.port == 22

def test_journald_iso8601_invalid_user():
    parser = SSHAuthLogParser()
    line = "2026-08-10T14:12:05.123456+00:00 server sshd[123]: Invalid user missing_user from 10.0.0.5 port 1234"  # noqa: E501
    res = parser.parse_line(line, 2026)
    assert res.is_parsed is True
    assert res.event_type == "invalid_user"
    assert res.user == "missing_user"
    assert res.source_ip == "10.0.0.5"
    assert res.port == 1234
    assert res.timestamp.year == 2026
    assert res.timestamp.microsecond == 123456

def test_publickey_accepted():
    parser = SSHAuthLogParser()
    line = "Aug 10 14:12:05 server sshd[123]: Accepted publickey for testuser from 10.0.0.2 port 44322 ssh2"  # noqa: E501
    res = parser.parse_line(line, 2026)
    assert res.is_parsed is True
    assert res.event_type == "successful_login"
    assert res.user == "testuser"
    assert res.source_ip == "10.0.0.2"

def test_unparsed_line():
    parser = SSHAuthLogParser()
    line = "Aug 10 14:12:05 server postfix/smtpd[123]: connect from unknown[192.168.1.5]"  # noqa: E501
    res = parser.parse_line(line, 2026)
    assert res.is_parsed is False
    assert res.event_type == "unparsed"

def test_unparsed_sshd_line():
    parser = SSHAuthLogParser()
    line = "Aug 10 14:12:05 server sshd[123]: Server listening on 0.0.0.0 port 22."
    res = parser.parse_line(line, 2026)
    assert res.is_parsed is False
    assert res.event_type == "unparsed_sshd"
