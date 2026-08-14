# SecureOps Local — Feature Roadmap (v1.0)

With the successful completion of the MVP (Phases P0 to P7), SecureOps Local has established a strictly deterministic, privacy-first, and document-grounded foundation for incident analysis.

To transition from an MVP to a comprehensive SOC and Sysadmin tool, the following major capabilities will be implemented:

## 1. Multi-Source Deterministic Parsers
The current architecture relies solely on the `SSHAuthLogParser`. We will extend the parsing engine to support additional critical security event sources:
- **Windows Event Logs:** Native `.evtx` support, focusing on Logon/Logoff events (Event IDs 4624, 4625).
- **Web Application Firewalls (WAF) & Nginx/Apache:** Parsing access logs for SQLi, XSS, and Path Traversal payloads.
- **Cloud Identity Logs:** AWS CloudTrail anomaly detection.

## 2. Daemon Mode (Continuous Watcher)
Moving beyond point-in-time CLI invocations to continuous monitoring.
- **File System Watchdog:** A background daemon that tails log files (`tail -f` equivalent) and triggers the RAG/LLM pipeline automatically when failure thresholds are met.
- **Alerting Integration:** Local desktop notifications, or simple webhook support (e.g., Slack) for immediate incident reporting without human intervention.

## 3. Semantic RAG (Vector Embeddings)
The MVP utilizes TF-IDF and Cosine Similarity for pure-Python keyword retrieval. To vastly improve document matching:
- **Local Embeddings:** Implement a lightweight local embedding model (e.g., `all-MiniLM-L6-v2`) via HuggingFace transformers.
- **Vector Database:** Integrate a dedicated local vector database like `FAISS` or `ChromaDB` for semantic search across thousands of pages of NIST/CISA literature.

## 4. Automated Export & SIEM Integration
For enterprise adoption, SecureOps Local must integrate with existing security operations centers:
- **Syslog Forwarding:** Ability to push the structured `IncidentReport` directly to centralized SIEMs (Splunk, Elastic, QRadar).
- **Ticket Generation:** Optional generation of Jira/ServiceNow compatible payloads from the AI's risk reasoning.
