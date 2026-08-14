import json
import os
from datetime import datetime, timezone, timedelta

def generate_cases():
    cases_dir = os.path.join("tests", "benchmark", "cases")
    os.makedirs(cases_dir, exist_ok=True)
    
    # Base chunks to reuse
    nist_chunk = {
        "chunk_id": "nist-800-61-r3-sec3",
        "document_id": "doc-nist-800-61",
        "source_title": "NIST SP 800-61 Rev. 3",
        "section_or_page": "Section 3.1: Incident Indicators",
        "content": "Multiple failed login attempts from an unknown IP address followed by a successful login may indicate a brute force attack resulting in compromised credentials.",
        "word_count": 25
    }
    
    cisa_chunk = {
        "chunk_id": "cisa-ssh-guidance",
        "document_id": "doc-cisa-ssh",
        "source_title": "CISA SSH Best Practices",
        "section_or_page": "Page 5",
        "content": "SSH brute forcing from automated scripts is common. Organizations should monitor for rapid successive authentication failures (e.g., >10 per minute) targeting root or administrative accounts.",
        "word_count": 26
    }
    
    mitre_chunk = {
        "chunk_id": "mitre-t1110",
        "document_id": "doc-mitre",
        "source_title": "MITRE ATT&CK T1110",
        "section_or_page": "Brute Force",
        "content": "Adversaries may use brute force techniques to gain access to accounts when passwords are unknown or when password hashes are obtained.",
        "word_count": 21
    }

    base_time = datetime(2026, 8, 12, 10, 0, 0, tzinfo=timezone.utc)
    
    cases = []
    
    # Case 1: Simple brute force
    cases.append({
        "case_id": "case-01-brute-force",
        "description": "Standard brute force attack with no success",
        "analysis": {
            "total_lines": 50,
            "unparsed_lines": 0,
            "start_time": base_time.isoformat(),
            "end_time": (base_time + timedelta(minutes=2)).isoformat(),
            "ip_aggregations": [
                {
                    "ip": "192.168.1.100",
                    "failed_attempts": 45,
                    "successful_attempts": 0,
                    "first_seen": base_time.isoformat(),
                    "last_seen": (base_time + timedelta(minutes=2)).isoformat(),
                    "users_attempted": ["root", "admin", "test"]
                }
            ],
            "limitations": []
        },
        "chunks": [nist_chunk, cisa_chunk],
        "expected_risk_level": "medium", # Attempted but no success
    })
    
    # Case 2: Brute force followed by success (Compromise)
    cases.append({
        "case_id": "case-02-compromise",
        "description": "Brute force attack followed by a successful login",
        "analysis": {
            "total_lines": 100,
            "unparsed_lines": 0,
            "start_time": base_time.isoformat(),
            "end_time": (base_time + timedelta(minutes=5)).isoformat(),
            "ip_aggregations": [
                {
                    "ip": "203.0.113.50",
                    "failed_attempts": 80,
                    "successful_attempts": 1,
                    "first_seen": base_time.isoformat(),
                    "last_seen": (base_time + timedelta(minutes=5)).isoformat(),
                    "users_attempted": ["ubuntu", "root"]
                }
            ],
            "limitations": []
        },
        "chunks": [nist_chunk, mitre_chunk],
        "expected_risk_level": "high",
    })
    
    # Case 3: Distributed brute force
    cases.append({
        "case_id": "case-03-distributed-brute",
        "description": "Distributed brute force from multiple IPs targeting one user",
        "analysis": {
            "total_lines": 300,
            "unparsed_lines": 5,
            "start_time": base_time.isoformat(),
            "end_time": (base_time + timedelta(minutes=10)).isoformat(),
            "ip_aggregations": [
                {
                    "ip": f"198.51.100.{i}",
                    "failed_attempts": 5,
                    "successful_attempts": 0,
                    "first_seen": (base_time + timedelta(minutes=i)).isoformat(),
                    "last_seen": (base_time + timedelta(minutes=i, seconds=30)).isoformat(),
                    "users_attempted": ["admin"]
                } for i in range(10)
            ],
            "limitations": ["Timezone assumed UTC due to lack of offset in log"]
        },
        "chunks": [cisa_chunk, mitre_chunk],
        "expected_risk_level": "medium",
    })

    # Case 4: Single failed login (Noise)
    cases.append({
        "case_id": "case-04-single-failure",
        "description": "A single failed login attempt, likely a typo",
        "analysis": {
            "total_lines": 1,
            "unparsed_lines": 0,
            "start_time": base_time.isoformat(),
            "end_time": base_time.isoformat(),
            "ip_aggregations": [
                {
                    "ip": "10.0.0.5",
                    "failed_attempts": 1,
                    "successful_attempts": 0,
                    "first_seen": base_time.isoformat(),
                    "last_seen": base_time.isoformat(),
                    "users_attempted": ["jsmith"]
                }
            ],
            "limitations": []
        },
        "chunks": [nist_chunk],
        "expected_risk_level": "low",
    })

    # Case 5: Normal successful login
    cases.append({
        "case_id": "case-05-normal-login",
        "description": "Normal successful login from an internal IP",
        "analysis": {
            "total_lines": 1,
            "unparsed_lines": 0,
            "start_time": base_time.isoformat(),
            "end_time": base_time.isoformat(),
            "ip_aggregations": [
                {
                    "ip": "10.0.0.50",
                    "failed_attempts": 0,
                    "successful_attempts": 1,
                    "first_seen": base_time.isoformat(),
                    "last_seen": base_time.isoformat(),
                    "users_attempted": ["jsmith"]
                }
            ],
            "limitations": []
        },
        "chunks": [nist_chunk],
        "expected_risk_level": "low",
    })
    
    # Case 6: High volume normal activity
    cases.append({
        "case_id": "case-06-high-volume-normal",
        "description": "High volume of successful logins from automated script (internal)",
        "analysis": {
            "total_lines": 1000,
            "unparsed_lines": 0,
            "start_time": base_time.isoformat(),
            "end_time": (base_time + timedelta(hours=1)).isoformat(),
            "ip_aggregations": [
                {
                    "ip": "10.0.0.100",
                    "failed_attempts": 0,
                    "successful_attempts": 500,
                    "first_seen": base_time.isoformat(),
                    "last_seen": (base_time + timedelta(hours=1)).isoformat(),
                    "users_attempted": ["service_account"]
                }
            ],
            "limitations": []
        },
        "chunks": [cisa_chunk],
        "expected_risk_level": "low",
    })

    # Case 7: Invalid users targeting root
    cases.append({
        "case_id": "case-07-invalid-users",
        "description": "Attempts using random invalid users and root",
        "analysis": {
            "total_lines": 25,
            "unparsed_lines": 2,
            "start_time": base_time.isoformat(),
            "end_time": (base_time + timedelta(minutes=1)).isoformat(),
            "ip_aggregations": [
                {
                    "ip": "203.0.113.10",
                    "failed_attempts": 20,
                    "successful_attempts": 0,
                    "first_seen": base_time.isoformat(),
                    "last_seen": (base_time + timedelta(minutes=1)).isoformat(),
                    "users_attempted": ["invalid1", "invalid2", "root"]
                }
            ],
            "limitations": []
        },
        "chunks": [cisa_chunk],
        "expected_risk_level": "medium",
    })
    
    # Case 8: Success after a long period of failures
    cases.append({
        "case_id": "case-08-slow-brute-success",
        "description": "Slow brute force resulting in success",
        "analysis": {
            "total_lines": 30,
            "unparsed_lines": 0,
            "start_time": base_time.isoformat(),
            "end_time": (base_time + timedelta(days=1)).isoformat(),
            "ip_aggregations": [
                {
                    "ip": "198.51.100.200",
                    "failed_attempts": 28,
                    "successful_attempts": 1,
                    "first_seen": base_time.isoformat(),
                    "last_seen": (base_time + timedelta(days=1)).isoformat(),
                    "users_attempted": ["user1"]
                }
            ],
            "limitations": []
        },
        "chunks": [nist_chunk, mitre_chunk],
        "expected_risk_level": "high",
    })

    # Case 9: Extreme volume unparsed lines
    cases.append({
        "case_id": "case-09-high-unparsed",
        "description": "Log file with mostly unparsed lines and one failure",
        "analysis": {
            "total_lines": 10000,
            "unparsed_lines": 9990,
            "start_time": base_time.isoformat(),
            "end_time": (base_time + timedelta(minutes=5)).isoformat(),
            "ip_aggregations": [
                {
                    "ip": "10.0.0.99",
                    "failed_attempts": 5,
                    "successful_attempts": 0,
                    "first_seen": base_time.isoformat(),
                    "last_seen": (base_time + timedelta(minutes=5)).isoformat(),
                    "users_attempted": ["admin"]
                }
            ],
            "limitations": ["Extremely high number of unparsed lines suggests log corruption or unsupported format"]
        },
        "chunks": [nist_chunk],
        "expected_risk_level": "medium",
    })

    # Case 10: Mixed IPs, some success some fail
    cases.append({
        "case_id": "case-10-mixed-activity",
        "description": "Mixed normal activity and brute force from different IPs",
        "analysis": {
            "total_lines": 200,
            "unparsed_lines": 0,
            "start_time": base_time.isoformat(),
            "end_time": (base_time + timedelta(hours=2)).isoformat(),
            "ip_aggregations": [
                {
                    "ip": "10.0.0.5",
                    "failed_attempts": 1,
                    "successful_attempts": 5,
                    "first_seen": base_time.isoformat(),
                    "last_seen": (base_time + timedelta(hours=2)).isoformat(),
                    "users_attempted": ["jsmith"]
                },
                {
                    "ip": "192.0.2.1",
                    "failed_attempts": 150,
                    "successful_attempts": 0,
                    "first_seen": (base_time + timedelta(hours=1)).isoformat(),
                    "last_seen": (base_time + timedelta(hours=1, minutes=30)).isoformat(),
                    "users_attempted": ["root", "admin"]
                }
            ],
            "limitations": []
        },
        "chunks": [nist_chunk, cisa_chunk, mitre_chunk],
        "expected_risk_level": "medium",
    })

    for case in cases:
        path = os.path.join(cases_dir, f"{case['case_id']}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(case, f, indent=2)
            
    print(f"Generated {len(cases)} benchmark cases in {cases_dir}")

if __name__ == "__main__":
    generate_cases()
