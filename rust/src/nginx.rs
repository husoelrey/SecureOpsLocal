use std::fs::File;
use std::io::{BufRead, BufReader};
use std::path::Path;
use std::sync::LazyLock;

use chrono::{DateTime, Utc};
use regex::Regex;

use crate::types::ParsedLogLine;

static NGINX_COMBINED_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"^(?P<ip>\S+)\s+\S+\s+(?P<user>\S+)\s+\[(?P<time>[^\]]+)\]\s+"(?P<request>[^"]*)"\s+(?P<status>\d{3})\s+(?P<bytes>\S+)(?:\s+"(?P<referer>[^"]*)"\s+"(?P<agent>[^"]*)")?"#).unwrap()
});

static NGINX_SIMPLE_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"^(?P<ip>\S+)\s+\S+\s+(?P<user>\S+)\s+\[(?P<time>[^\]]+)\]\s+"(?P<request>[^"]*)"\s+(?P<status>\d{3})"#).unwrap()
});

static SQLI_PATTERNS: LazyLock<Vec<Regex>> = LazyLock::new(|| {
    vec![
        Regex::new(r"(?i)\b(UNION(\s+ALL)?)\s+SELECT\b").unwrap(),
        Regex::new(r#"(?i)['"]\s*(OR|AND)\s*['"]?\d+['"]?\s*=\s*['"]?\d+"#).unwrap(),
        Regex::new(r#"(?i)['"]\s*(OR|AND)\s*['"][^'"]+['"]\s*=\s*['"]"#).unwrap(),
        Regex::new(r"(?i)\bSELECT\b.+\bFROM\b").unwrap(),
        Regex::new(r"(?i)(\bINSERT\s+INTO\b|\bUPDATE\s+.+\s+SET\b|\bDELETE\s+FROM\b)").unwrap(),
        Regex::new(r"(?i)(\bDROP\s+TABLE\b|\bALTER\s+TABLE\b|\bTRUNCATE\s+TABLE\b)").unwrap(),
        Regex::new(r"(?i)(\bSLEEP\s*\(\s*\d+\s*\)|\bBENCHMARK\s*\(|\bWAITFOR\s+DELAY\b)").unwrap(),
        Regex::new(r"(?i)(\bINFORMATION_SCHEMA\b|\bSYS\.TABLES\b|\bPG_SLEEP\b)").unwrap(),
        Regex::new(r"(?i)(--|#|/\*.*\*\/)").unwrap(),
        Regex::new(r"(?i)(\bEXEC\s*\(|\bEXECUTE\s*\(|\bxp_cmdshell\b)").unwrap(),
    ]
});

static XSS_PATTERNS: LazyLock<Vec<Regex>> = LazyLock::new(|| {
    vec![
        Regex::new(r"(?i)(<script\b[^>]*>.*?</script>|<script\b[^>]*>)").unwrap(),
        Regex::new(r"(?i)(javascript\s*:)").unwrap(),
        Regex::new(r"(?i)(\bon(error|load|click|mouseover|submit|focus|blur|change)\s*=)").unwrap(),
        Regex::new(r"(?i)(<img\b[^>]*\bsrc\s*=[^>]*>)").unwrap(),
        Regex::new(r"(?i)(<iframe\b[^>]*>|<svg\b[^>]*\bonload\b)").unwrap(),
        Regex::new(r"(?i)(\balert\s*\(|\bdocument\.cookie\b|\beval\s*\(|\bprompt\s*\()").unwrap(),
    ]
});

static PATH_TRAVERSAL_PATTERNS: LazyLock<Vec<Regex>> = LazyLock::new(|| {
    vec![
        Regex::new(r"(?i)(\.\./\.\./|\.\.\\\.\.\\|\.\./|\.\.\\)").unwrap(),
        Regex::new(r"(?i)(/etc/passwd|/etc/shadow|/proc/self/environ)").unwrap(),
        Regex::new(r"(?i)(c:\\windows\\system32|boot\.ini|win\.ini)").unwrap(),
    ]
});

fn unquote_plus(input: &str) -> String {
    let mut bytes = Vec::with_capacity(input.len());
    let input_bytes = input.as_bytes();
    let mut i = 0;
    while i < input_bytes.len() {
        match input_bytes[i] {
            b'+' => {
                bytes.push(b' ');
                i += 1;
            }
            b'%' if i + 2 < input_bytes.len() => {
                if let Ok(b) = u8::from_str_radix(
                    std::str::from_utf8(&input_bytes[i + 1..i + 3]).unwrap_or(""),
                    16,
                ) {
                    bytes.push(b);
                    i += 3;
                } else {
                    bytes.push(input_bytes[i]);
                    i += 1;
                }
            }
            b => {
                bytes.push(b);
                i += 1;
            }
        }
    }
    String::from_utf8_lossy(&bytes).to_string()
}

fn parse_nginx_time(time_str: &str, _current_year: i32) -> DateTime<Utc> {
    let s = time_str.trim();
    if let Ok(dt) = DateTime::parse_from_str(s, "%d/%b/%Y:%H:%M:%S %z") {
        return dt.with_timezone(&Utc);
    }
    if let Ok(naive) = chrono::NaiveDateTime::parse_from_str(s, "%d/%b/%Y:%H:%M:%S") {
        return naive.and_utc();
    }
    if let Ok(dt) = DateTime::parse_from_rfc3339(s) {
        return dt.with_timezone(&Utc);
    }
    if let Ok(dt) = DateTime::parse_from_str(s, "%Y-%m-%dT%H:%M:%S%z") {
        return dt.with_timezone(&Utc);
    }
    if let Ok(naive) = chrono::NaiveDateTime::parse_from_str(s, "%Y-%m-%d %H:%M:%S") {
        return naive.and_utc();
    }
    Utc::now()
}

fn detect_payload_attacks(text: &str) -> Option<&'static str> {
    if text.is_empty() {
        return None;
    }

    let mut candidates = vec![text.to_string()];
    let decoded = unquote_plus(text);
    if decoded != text {
        candidates.push(decoded.clone());
    }
    let double_decoded = unquote_plus(&decoded);
    if !candidates.contains(&double_decoded) {
        candidates.push(double_decoded);
    }

    for c in &candidates {
        for pattern in SQLI_PATTERNS.iter() {
            if pattern.is_match(c) {
                return Some("sqli_attempt");
            }
        }
        for pattern in XSS_PATTERNS.iter() {
            if pattern.is_match(c) {
                return Some("xss_attempt");
            }
        }
        for pattern in PATH_TRAVERSAL_PATTERNS.iter() {
            if pattern.is_match(c) {
                return Some("path_traversal");
            }
        }
    }

    None
}

fn classify_event(
    attack_type: Option<&str>,
    status_code: u16,
    request: &str,
    user: Option<&str>,
) -> String {
    if let Some(att) = attack_type {
        return att.to_string();
    }

    let req_lower = request.to_lowercase();
    let is_auth_endpoint = ["login", "auth", "signin", "wp-login", "admin"]
        .iter()
        .any(|&kw| req_lower.contains(kw));

    if status_code == 401 {
        if user.is_some() || is_auth_endpoint {
            "failed_login".to_string()
        } else {
            "unauthorized_access".to_string()
        }
    } else if status_code == 403 {
        "forbidden_access".to_string()
    } else if status_code >= 500 {
        "server_error".to_string()
    } else if status_code >= 400 {
        "failed_request".to_string()
    } else if matches!(status_code, 200 | 201 | 204 | 301 | 302 | 304) {
        if is_auth_endpoint && user.is_some() {
            "successful_login".to_string()
        } else {
            "successful_request".to_string()
        }
    } else {
        "http_request".to_string()
    }
}

pub fn parse_nginx_line(line: &str, current_year: i32) -> ParsedLogLine {
    let line_clean = line.trim();
    if line_clean.is_empty() {
        return ParsedLogLine {
            timestamp: Utc::now(),
            source_ip: None,
            user: None,
            event_type: "empty_line".to_string(),
            port: None,
            raw_content: line.to_string(),
            is_parsed: false,
        };
    }

    // 1. Try JSON format
    if line_clean.starts_with('{') && line_clean.ends_with('}') {
        if let Ok(data) = serde_json::from_str::<serde_json::Value>(line_clean) {
            if let Some(obj) = data.as_object() {
                let ip = obj
                    .get("remote_addr")
                    .or_else(|| obj.get("client_ip"))
                    .or_else(|| obj.get("ip"))
                    .and_then(|v| v.as_str())
                    .map(|s| s.trim().to_string())
                    .filter(|s| !s.is_empty());

                let user_raw = obj
                    .get("remote_user")
                    .or_else(|| obj.get("user"))
                    .and_then(|v| v.as_str());
                let user = user_raw
                    .map(|s| s.trim().to_string())
                    .filter(|s| s != "-" && !s.is_empty());

                let time_raw = obj
                    .get("time_local")
                    .or_else(|| obj.get("time_iso8601"))
                    .or_else(|| obj.get("timestamp"))
                    .and_then(|v| v.as_str());

                let timestamp = match time_raw {
                    Some(t) => parse_nginx_time(t, current_year),
                    None => Utc::now(),
                };

                let request = obj
                    .get("request")
                    .or_else(|| obj.get("uri"))
                    .and_then(|v| v.as_str())
                    .unwrap_or("");

                let status_code = obj
                    .get("status")
                    .or_else(|| obj.get("status_code"))
                    .and_then(|v| {
                        if let Some(n) = v.as_u64() {
                            Some(n as u16)
                        } else if let Some(s) = v.as_str() {
                            s.parse::<u16>().ok()
                        } else {
                            None
                        }
                    })
                    .unwrap_or(200);

                let attack = detect_payload_attacks(request);
                let event_type = classify_event(attack, status_code, request, user.as_deref());

                return ParsedLogLine {
                    timestamp,
                    source_ip: ip,
                    user,
                    event_type,
                    port: None,
                    raw_content: line.to_string(),
                    is_parsed: true,
                };
            }
        }
    }

    // 2. Try Combined / Simple Log Format
    if let Some(caps) = NGINX_COMBINED_RE
        .captures(line_clean)
        .or_else(|| NGINX_SIMPLE_RE.captures(line_clean))
    {
        let ip = caps.name("ip").map(|m| m.as_str().to_string());
        let user_raw = caps.name("user").map(|m| m.as_str());
        let user = user_raw
            .map(|s| s.trim().to_string())
            .filter(|s| s != "-" && !s.is_empty());

        let time_raw = caps.name("time").map(|m| m.as_str());
        let timestamp = match time_raw {
            Some(t) => parse_nginx_time(t, current_year),
            None => Utc::now(),
        };

        let request = caps.name("request").map(|m| m.as_str()).unwrap_or("");
        let status_code = caps
            .name("status")
            .and_then(|m| m.as_str().parse::<u16>().ok())
            .unwrap_or(200);

        let attack = detect_payload_attacks(request);
        let event_type = classify_event(attack, status_code, request, user.as_deref());

        return ParsedLogLine {
            timestamp,
            source_ip: ip,
            user,
            event_type,
            port: None,
            raw_content: line.to_string(),
            is_parsed: true,
        };
    }

    ParsedLogLine {
        timestamp: Utc::now(),
        source_ip: None,
        user: None,
        event_type: "unparsed_nginx".to_string(),
        port: None,
        raw_content: line.to_string(),
        is_parsed: false,
    }
}

pub fn parse_nginx_file<P: AsRef<Path>>(
    file_path: P,
    current_year: i32,
) -> std::io::Result<Vec<ParsedLogLine>> {
    let file = File::open(file_path)?;
    let reader = BufReader::new(file);
    let mut results = Vec::new();

    for line_res in reader.lines() {
        let line = line_res?;
        results.push(parse_nginx_line(line.trim(), current_year));
    }

    Ok(results)
}
