from pathlib import Path

import pytest

try:
    import secureops_core

    _RUST_AVAILABLE = True
except ImportError:
    _RUST_AVAILABLE = False


@pytest.mark.skipif(not _RUST_AVAILABLE, reason="secureops_core extension is not installed")
def test_rust_ssh_syslog_successful_login():
    line = "Aug 10 14:12:05 server sshd[123]: Accepted password for admin from 192.168.1.100 port 55432 ssh2"
    res = secureops_core.parse_ssh_line(line, 2026)
    assert res["is_parsed"] is True
    assert res["event_type"] == "successful_login"
    assert res["user"] == "admin"
    assert res["source_ip"] == "192.168.1.100"
    assert res["port"] == 55432
    assert res["timestamp"].year == 2026
    assert res["timestamp"].month == 8
    assert res["timestamp"].day == 10


@pytest.mark.skipif(not _RUST_AVAILABLE, reason="secureops_core extension is not installed")
def test_rust_ssh_failed_login_ipv6():
    line = "Nov  1 12:00:00 server sshd[456]: Failed password for root from 2001:db8::1 port 22 ssh2"
    res = secureops_core.parse_ssh_line(line, 2026)
    assert res["is_parsed"] is True
    assert res["event_type"] == "failed_login"
    assert res["user"] == "root"
    assert res["source_ip"] == "2001:db8::1"
    assert res["port"] == 22


@pytest.mark.skipif(not _RUST_AVAILABLE, reason="secureops_core extension is not installed")
def test_rust_ssh_journald_iso8601_invalid_user():
    line = "2026-08-10T14:12:05.123456+00:00 server sshd[123]: Invalid user missing_user from 10.0.0.5 port 1234"
    res = secureops_core.parse_ssh_line(line, 2026)
    assert res["is_parsed"] is True
    assert res["event_type"] == "invalid_user"
    assert res["user"] == "missing_user"
    assert res["source_ip"] == "10.0.0.5"
    assert res["port"] == 1234
    assert res["timestamp"].year == 2026
    assert res["timestamp"].microsecond == 123456


@pytest.mark.skipif(not _RUST_AVAILABLE, reason="secureops_core extension is not installed")
def test_rust_ssh_unparsed_line():
    line = "Aug 10 14:12:05 server postfix/smtpd[123]: connect from unknown[192.168.1.5]"
    res = secureops_core.parse_ssh_line(line, 2026)
    assert res["is_parsed"] is False
    assert res["event_type"] == "unparsed"


@pytest.mark.skipif(not _RUST_AVAILABLE, reason="secureops_core extension is not installed")
def test_rust_ssh_parse_file(tmp_path: Path):
    lines = [
        "Aug 10 14:12:05 server sshd[123]: Accepted password for admin from 192.168.1.100 port 55432 ssh2\n",
        "Nov  1 12:00:00 server sshd[456]: Failed password for root from 2001:db8::1 port 22 ssh2\n",
    ]
    file_path = tmp_path / "ssh.log"
    file_path.write_text("".join(lines), encoding="utf-8")

    results = secureops_core.parse_ssh_file(str(file_path), 2026)
    assert len(results) == 2
    assert results[0]["event_type"] == "successful_login"
    assert results[1]["event_type"] == "failed_login"


@pytest.mark.skipif(not _RUST_AVAILABLE, reason="secureops_core extension is not installed")
def test_rust_nginx_combined_standard():
    line = '192.168.1.10 - alice [14/Aug/2026:12:00:00 +0000] "GET /dashboard HTTP/1.1" 200 4523 "-" "Mozilla/5.0"'
    res = secureops_core.parse_nginx_line(line, 2026)
    assert res["is_parsed"] is True
    assert res["event_type"] == "successful_request"
    assert res["source_ip"] == "192.168.1.10"
    assert res["user"] == "alice"


@pytest.mark.skipif(not _RUST_AVAILABLE, reason="secureops_core extension is not installed")
def test_rust_nginx_sqli_detection():
    line = '10.0.0.15 - - [14/Aug/2026:12:05:00 +0000] "GET /products.php?id=1%27%20UNION%20SELECT%20null,username,password%20FROM%20users-- HTTP/1.1" 200 1024 "-" "sqlmap/1.5"'
    res = secureops_core.parse_nginx_line(line, 2026)
    assert res["is_parsed"] is True
    assert res["event_type"] == "sqli_attempt"
    assert res["source_ip"] == "10.0.0.15"


@pytest.mark.skipif(not _RUST_AVAILABLE, reason="secureops_core extension is not installed")
def test_rust_nginx_xss_detection():
    line = '10.0.0.20 - - [14/Aug/2026:12:10:00 +0000] "GET /search?q=%3Cscript%3Ealert(document.cookie)%3C/script%3E HTTP/1.1" 200 512 "-" "Mozilla/5.0"'
    res = secureops_core.parse_nginx_line(line, 2026)
    assert res["is_parsed"] is True
    assert res["event_type"] == "xss_attempt"
    assert res["source_ip"] == "10.0.0.20"


@pytest.mark.skipif(not _RUST_AVAILABLE, reason="secureops_core extension is not installed")
def test_rust_nginx_path_traversal_detection():
    line = '10.0.0.25 - - [14/Aug/2026:12:15:00 +0000] "GET /download?file=../../../../etc/passwd HTTP/1.1" 404 150 "-" "curl/7.68.0"'
    res = secureops_core.parse_nginx_line(line, 2026)
    assert res["is_parsed"] is True
    assert res["event_type"] == "path_traversal"
    assert res["source_ip"] == "10.0.0.25"


@pytest.mark.skipif(not _RUST_AVAILABLE, reason="secureops_core extension is not installed")
def test_rust_nginx_parse_file(tmp_path: Path):
    lines = [
        '192.168.1.10 - alice [14/Aug/2026:12:00:00 +0000] "GET /dashboard HTTP/1.1" 200 4523 "-" "Mozilla/5.0"\n',
        '10.0.0.15 - - [14/Aug/2026:12:05:00 +0000] "GET /products.php?id=1%27%20UNION%20SELECT%20null,username,password%20FROM%20users-- HTTP/1.1" 200 1024 "-" "sqlmap/1.5"\n',
    ]
    file_path = tmp_path / "nginx.log"
    file_path.write_text("".join(lines), encoding="utf-8")

    results = secureops_core.parse_nginx_file(str(file_path), 2026)
    assert len(results) == 2
    assert results[0]["event_type"] == "successful_request"
    assert results[1]["event_type"] == "sqli_attempt"
