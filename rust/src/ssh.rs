use std::sync::LazyLock;
use std::fs::File;
use std::io::{BufRead, BufReader};
use std::path::Path;

use chrono::{DateTime, Utc};
use regex::Regex;

use crate::types::ParsedLogLine;

static SYSLOG_TS_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^(?P<syslog_ts>[A-Z][a-z]{2}\s+\d+\s+\d{2}:\d{2}:\d{2})").unwrap()
});

static ISO_TS_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^(?P<iso_ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)").unwrap()
});

static SSHD_PREFIX_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"sshd(?:\[\d+\])?:\s+(.*)").unwrap()
});

struct AuthPattern {
    regex: Regex,
    event_type: &'static str,
}

static AUTH_PATTERNS: LazyLock<Vec<AuthPattern>> = LazyLock::new(|| {
    vec![
        AuthPattern {
            regex: Regex::new(r"Accepted (?P<auth_method>password|publickey) for (?P<user>\S+) from (?P<ip>\S+) port (?P<port>\d+)").unwrap(),
            event_type: "successful_login",
        },
        AuthPattern {
            regex: Regex::new(r"Failed (?P<auth_method>password|publickey) for invalid user (?P<user>\S+) from (?P<ip>\S+) port (?P<port>\d+)").unwrap(),
            event_type: "failed_login_invalid_user",
        },
        AuthPattern {
            regex: Regex::new(r"Failed (?P<auth_method>password|publickey) for (?P<user>\S+) from (?P<ip>\S+) port (?P<port>\d+)").unwrap(),
            event_type: "failed_login",
        },
        AuthPattern {
            regex: Regex::new(r"Invalid user (?P<user>\S+) from (?P<ip>\S+) port (?P<port>\d+)").unwrap(),
            event_type: "invalid_user",
        },
        AuthPattern {
            regex: Regex::new(r"Connection closed by (?:(?:authenticating|invalid) user (?P<user>\S+) )?(?P<ip>\S+) port (?P<port>\d+)").unwrap(),
            event_type: "connection_closed",
        },
        AuthPattern {
            regex: Regex::new(r"Disconnected from (?:(?:authenticating|invalid) user (?P<user>\S+) )?(?P<ip>\S+) port (?P<port>\d+)").unwrap(),
            event_type: "disconnected",
        },
    ]
});

fn parse_syslog_ts(ts_str: &str, current_year: i32) -> Option<DateTime<Utc>> {
    let mut parts = ts_str.split_whitespace();
    let month_str = parts.next()?;
    let day_str = parts.next()?;
    let time_str = parts.next()?;

    let month = match month_str {
        "Jan" => 1,
        "Feb" => 2,
        "Mar" => 3,
        "Apr" => 4,
        "May" => 5,
        "Jun" => 6,
        "Jul" => 7,
        "Aug" => 8,
        "Sep" => 9,
        "Oct" => 10,
        "Nov" => 11,
        "Dec" => 12,
        _ => return None,
    };
    let day: u32 = day_str.parse().ok()?;
    let mut time_parts = time_str.split(':');
    let hour: u32 = time_parts.next()?.parse().ok()?;
    let min: u32 = time_parts.next()?.parse().ok()?;
    let sec: u32 = time_parts.next()?.parse().ok()?;

    let naive_date = chrono::NaiveDate::from_ymd_opt(current_year, month, day)?;
    let naive_dt = naive_date.and_hms_opt(hour, min, sec)?;
    Some(naive_dt.and_utc())
}

fn parse_iso_ts(ts_str: &str) -> Option<DateTime<Utc>> {
    if let Ok(dt) = DateTime::parse_from_rfc3339(ts_str) {
        return Some(dt.with_timezone(&Utc));
    }
    if let Ok(naive_dt) = chrono::NaiveDateTime::parse_from_str(ts_str, "%Y-%m-%dT%H:%M:%S%.f") {
        return Some(naive_dt.and_utc());
    }
    if let Ok(naive_dt) = chrono::NaiveDateTime::parse_from_str(ts_str, "%Y-%m-%dT%H:%M:%S") {
        return Some(naive_dt.and_utc());
    }
    None
}

fn parse_timestamp<'a>(line: &'a str, current_year: i32) -> (DateTime<Utc>, &'a str) {
    if let Some(m) = ISO_TS_RE.find(line) {
        let ts_str = &line[m.start()..m.end()];
        let dt = parse_iso_ts(ts_str).unwrap_or_else(Utc::now);
        let remainder = line[m.end()..].trim_start();
        return (dt, remainder);
    }

    if let Some(m) = SYSLOG_TS_RE.find(line) {
        let ts_str = &line[m.start()..m.end()];
        let dt = parse_syslog_ts(ts_str, current_year).unwrap_or_else(Utc::now);
        let remainder = line[m.end()..].trim_start();
        return (dt, remainder);
    }

    (Utc::now(), line)
}

pub fn parse_ssh_line(line: &str, current_year: i32) -> ParsedLogLine {
    let (timestamp, remainder) = parse_timestamp(line, current_year);

    let sshd_match = match SSHD_PREFIX_RE.captures(remainder) {
        Some(caps) => caps,
        None => {
            return ParsedLogLine {
                timestamp,
                source_ip: None,
                user: None,
                event_type: "unparsed".to_string(),
                port: None,
                raw_content: line.to_string(),
                is_parsed: false,
            };
        }
    };

    let message = match sshd_match.get(1) {
        Some(m) => m.as_str(),
        None => "",
    };

    for ap in AUTH_PATTERNS.iter() {
        if let Some(caps) = ap.regex.captures(message) {
            let user = caps.name("user").map(|m| m.as_str().to_string());
            let source_ip = caps.name("ip").map(|m| m.as_str().to_string());
            let port = caps
                .name("port")
                .and_then(|m| m.as_str().parse::<u32>().ok());

            return ParsedLogLine {
                timestamp,
                source_ip,
                user,
                event_type: ap.event_type.to_string(),
                port,
                raw_content: line.to_string(),
                is_parsed: true,
            };
        }
    }

    ParsedLogLine {
        timestamp,
        source_ip: None,
        user: None,
        event_type: "unparsed_sshd".to_string(),
        port: None,
        raw_content: line.to_string(),
        is_parsed: false,
    }
}

pub fn parse_ssh_file<P: AsRef<Path>>(file_path: P, current_year: i32) -> std::io::Result<Vec<ParsedLogLine>> {
    let file = File::open(file_path)?;
    let reader = BufReader::new(file);
    let mut results = Vec::new();

    for line_res in reader.lines() {
        let line = line_res?;
        results.push(parse_ssh_line(line.trim(), current_year));
    }

    Ok(results)
}
