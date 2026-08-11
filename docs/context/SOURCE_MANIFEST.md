# SecureOps Local — Authoritative Source Manifest

This document records the curated knowledge-base sources that SecureOps Local will ingest for Retrieval-Augmented Generation (RAG). All sources must be verified for provenance, redistribution rights, and relevance to SSH authentication incident response.

## Sources

### 1. NIST SP 800-61 Rev. 3

- **source_id**: `nist-sp-800-61-r3`
- **title**: Computer Security Incident Handling Guide (Revision 3)
- **publisher**: National Institute of Standards and Technology (NIST)
- **canonical_url**: https://csrc.nist.gov/pubs/sp/800/61/r3/ipd
- **document_version**: Initial Public Draft (or current if final published)
- **publication_date**: 2024-04-18
- **retrieved_at**: 2024-05-01
- **license_id**: Public Domain (US Government Work)
- **license_url**: https://www.nist.gov/director/licensing
- **redistribution_status**: `allowed`
- **required_attribution**: Yes (NIST)
- **sha256**: TBD (Will be populated upon download)
- **repository_path**: `knowledge/nist-sp-800-61-r3.pdf`
- **notes**: The primary framework for incident response terminology, triage, and handling.

### 2. CISA IR Playbook

- **source_id**: `cisa-ir-playbook`
- **title**: Cybersecurity Incident & Vulnerability Response Playbooks
- **publisher**: Cybersecurity and Infrastructure Security Agency (CISA)
- **canonical_url**: https://www.cisa.gov/sites/default/files/publications/Federal_Government_Cybersecurity_Incident_and_Vulnerability_Response_Playbooks_508C.pdf
- **document_version**: November 2021
- **publication_date**: 2021-11-01
- **retrieved_at**: 2024-05-01
- **license_id**: Public Domain (US Government Work)
- **license_url**: https://www.cisa.gov/terms-of-use
- **redistribution_status**: `allowed`
- **required_attribution**: Yes (CISA)
- **sha256**: TBD
- **repository_path**: `knowledge/cisa-ir-playbook.pdf`
- **notes**: Provides operational guidance on standard incident response phases.

### 3. MITRE ATT&CK - Brute Force (T1110)

- **source_id**: `mitre-attack-t1110`
- **title**: MITRE ATT&CK Technique: Brute Force
- **publisher**: MITRE
- **canonical_url**: https://attack.mitre.org/techniques/T1110/
- **document_version**: v14.2
- **publication_date**: 2024-04-01
- **retrieved_at**: 2024-05-01
- **license_id**: Terms of Use
- **license_url**: https://attack.mitre.org/resources/terms-of-use/
- **redistribution_status**: `allowed_with_attribution`
- **required_attribution**: Yes (MITRE)
- **sha256**: TBD
- **repository_path**: `knowledge/mitre-attack-t1110.md`
- **notes**: Key threat intelligence describing password guessing and credential stuffing relevant to SSH.

### 4. OWASP Logging Cheat Sheet

- **source_id**: `owasp-logging-cheat-sheet`
- **title**: Logging Cheat Sheet
- **publisher**: OWASP Foundation
- **canonical_url**: https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
- **document_version**: Current
- **publication_date**: 2024-01-01
- **retrieved_at**: 2024-05-01
- **license_id**: CC BY-SA 3.0
- **license_url**: https://creativecommons.org/licenses/by-sa/3.0/
- **redistribution_status**: `allowed_with_attribution`
- **required_attribution**: Yes (OWASP)
- **sha256**: TBD
- **repository_path**: `knowledge/owasp-logging.md`
- **notes**: Guidance on what should and should not be logged, and how to protect logs.

### 5. SSH Security Guidelines

- **source_id**: `ssh-security-guidelines`
- **title**: OpenSSH Security and Hardening Guidelines
- **publisher**: OpenSSH / Security Community Consensus
- **canonical_url**: https://www.openssh.com/manual.html
- **document_version**: Current
- **publication_date**: 2024-01-01
- **retrieved_at**: 2024-05-01
- **license_id**: OpenSSH License
- **license_url**: https://www.openssh.com/txt/release-9.7
- **redistribution_status**: `allowed_with_attribution`
- **required_attribution**: Yes
- **sha256**: TBD
- **repository_path**: `knowledge/ssh-hardening.md`
- **notes**: Common SSH security configurations such as disabling root login, key-based auth, and MaxAuthTries.
