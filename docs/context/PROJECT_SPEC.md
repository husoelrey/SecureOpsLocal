# SecureOps Local — Project Specification

## 1. Product definition

SecureOps Local is an air-gapped-ready incident review assistant for Linux SSH authentication logs. It keeps sensitive inputs on the local machine, derives factual findings with deterministic Python code, retrieves supporting security guidance from a local knowledge base, and asks a local language model to produce a cautious structured assessment.

The product also compares local deployment profiles across Microsoft Foundry Local and Ollama. It is a decision-support prototype, not an autonomous security control.

## 2. Problem

Authentication logs can contain IP addresses, account names, host details, authentication methods, and incident timelines. Sending this material to a cloud model may conflict with privacy requirements or organizational policy. Small teams also need a repeatable way to turn raw logs into an initial review without presenting model speculation as fact.

SecureOps Local addresses this need through a fully local analysis pipeline with explicit boundaries between deterministic evidence and model interpretation.

## 3. Target users

- Junior SOC analysts
- System administrators
- Security students
- Small technical teams performing initial incident review
- Developers evaluating local RAG and local inference runtimes

## 4. Product boundary

The product is:

- An initial incident-review assistant
- A log summarization and evidence-structuring tool
- A document-grounded decision-support prototype
- A local deployment-profile evaluation platform

The product is not:

- A SIEM, IDS, IPS, antivirus, or forensic platform
- An automated remediation or attack-prevention system
- A multi-user production SaaS
- A source of guaranteed attribution or compromise determination

## 5. Primary workflow

1. A user submits an SSH authentication log through the API.
2. Upload controls validate size, type, encoding, and content.
3. SSHAuthLogParser converts supported lines into normalized events.
4. Deterministic aggregation produces statistics, findings, warnings, and limitations.
5. The application creates a privacy-minimized retrieval query.
6. The local retriever returns a fixed top-k evidence package.
7. The selected local model profile receives parser facts and the same retrieved context.
8. The model returns a structured assessment.
9. Strict Pydantic validation and deterministic consistency checks accept or reject the output.
10. Safe metadata and a valid report are stored in SQLite. Raw logs are not retained by default.

## 6. Deterministic parser outputs

The MVP parser must calculate:

- Relevant, successful, failed, and unparsed event counts
- Unique and most active source addresses
- Targeted user accounts and privileged-account attempts
- First and last known event times
- Repeated attempts within a configurable window
- Invalid-user attempts
- Authentication methods
- Success-after-repeated-failure patterns
- Timestamp, year, timezone, and parsing limitations

Parser findings describe observable patterns and never assert an attack.

## 7. Report contract

IncidentReport contains:

- incident_id
- status
- summary
- observed_findings
- possible_interpretations
- risk_level
- risk_reasoning
- recommended_actions
- citations
- limitations
- parser_statistics
- model_information
- performance_metrics

Observed findings are generated or verified by deterministic components. Model-generated interpretation is kept in separate fields. Risk levels are low, medium, or high and must include evidence-based reasoning. Recommendations are limited to review, evidence preservation, validation, hardening, monitoring, and authorized escalation.

## 8. Runtime and model scope

The MVP supports equal provider implementations for:

- Microsoft Foundry Local, with the concrete device-supported profile selected after catalog inspection
- Ollama with Foundation-Sec-8B-Reasoning Q4_K_M as the security-specialized candidate
- Ollama with Qwen3.5 9B Q4_K_M as the general-purpose reference

All three candidates remain eligible to become the recommended deployment profile. Availability, licensing, hardware fit, runtime behavior, structured-output reliability, quality, latency, and memory usage must be measured before a default is selected.

## 9. Knowledge and retrieval scope

The first knowledge base contains five to ten reviewed sources from organizations such as NIST, CISA, MITRE ATT&CK, OWASP, Microsoft, and authoritative SSH documentation.

MVP retrieval includes:

- PDF, Markdown, and plain-text ingestion
- Heading-aware chunking with bounded overlap
- Source and chunk metadata in SQLite
- TF-IDF with cosine similarity
- Stable top-k citations

A local embedding retriever is optional and may be added only after the TF-IDF baseline is working and measured.

## 10. API scope

Planned endpoints:

- GET /health
- GET /models
- POST /v1/knowledge/ingest
- GET /v1/knowledge/sources
- POST /v1/incidents/analyze
- GET /v1/incidents/{incident_id}
- POST /v1/benchmarks/run
- GET /v1/benchmarks/{benchmark_id}

Analysis and benchmark operations use bounded application jobs. Creation endpoints return 202 Accepted; status endpoints return progress, a valid result, or a controlled error.

## 11. Persistence scope

Planned tables:

- documents
- document_chunks
- incidents
- incident_findings
- model_runs
- benchmark_runs
- benchmark_results

The database may store hashes, sizes, parser metadata, structured findings, valid reports, safe runtime metadata, and metrics. It must not store raw logs by default.

## 12. Benchmark objective

The benchmark determines which complete local deployment profile offers the best balance of report quality, structured-output reliability, latency, and memory use on the target device.

Profiles are compared with identical:

- Synthetic cases
- Parser results
- Retrieved chunk packages
- Prompt and schema versions
- Compatible generation settings
- Repetition policy

Metrics include cold-load time, time to first token, total latency, tokens per second, memory measurements with declared scope, schema compliance, expected-finding recall, unsupported claims, citation validity, groundedness, recommendation completeness, risk consistency, and repeatability.

## 13. Security and privacy requirements

- All uploads are untrusted.
- The core path has no cloud-model fallback.
- Raw logs, full prompts, and full model responses are excluded from application logs.
- Model and document content never become executable instructions.
- The model has no tools, shell, or operating-system access.
- Uploads have streamed limits, validation, timeouts, and guaranteed temporary-file cleanup.
- API and runtime endpoints bind locally by default.
- Secrets, personal data, real organizational logs, caches, and model weights are excluded from version control.

## 14. Non-functional requirements

- Reproducible dependency, model-profile, prompt, schema, and fixture versions
- Deterministic parser behavior for identical inputs
- Strict validation of model output
- Controlled job and error states
- Native Windows fallback when container-to-host runtime access is unreliable
- Structured privacy-preserving logs with correlation IDs and stage durations
- Offline execution after required artifacts have been prepared and verified

## 15. MVP acceptance criteria

1. At least one Foundry Local profile and one Ollama profile run successfully.
2. The application can reach both provider implementations.
3. Secure SSH log upload and deterministic parsing pass positive and negative tests.
4. At least five license-reviewed sources are ingested.
5. Retrieval returns relevant, traceable chunks.
6. Each provider produces a valid structured report or a controlled failure.
7. Every citation resolves to an existing source and chunk.
8. At least ten labeled synthetic cases exercise normal, suspicious, malformed, and adversarial inputs.
9. Candidate deployment profiles are compared with the same evidence packages.
10. Required quality, latency, throughput, and memory metrics are recorded or explicitly marked unavailable.
11. Unit, integration, security, lint, formatting, and type checks pass.
12. Docker deployment or the documented native fallback works.
13. A cached, network-disabled analysis completes without external requests.
14. Repository documentation enables another developer to reproduce the setup and validation.

## 16. Stretch goals

In priority order:

1. Stable IP and account pseudonymization
2. A minimal local web interface
3. MITRE ATT&CK technique mapping
4. A local embedding retrieval experiment
5. RAG-on versus RAG-off evaluation
6. Additional log parsers after the SSH MVP
7. PDF report export
8. Analysis history and retention controls
9. A signed offline-bundle manifest

## 17. Repository deliverables

- Source code and configuration
- Setup, usage, architecture, security, and offline-operation documentation
- Synthetic fixtures and benchmark cases
- Automated tests
- Reproducible benchmark configuration and results
- License and provenance metadata for redistributable knowledge sources
