# SecureOps Local — Detailed Implementation Plan

## 1. Purpose

SecureOps Local is a local-first, air-gapped-ready defensive
incident-review assistant. It accepts untrusted Linux SSH authentication logs,
extracts deterministic facts, retrieves relevant local security guidance, and uses
a selected local LLM deployment profile to generate a cautious, cited assessment.

This document expands the executable checklist in [`PLAN.md`](../../PLAN.md). It is
the implementation reference when a checklist item needs architectural, security,
interface, model, benchmark, or acceptance detail.

The product is not a SIEM, IDS, antivirus product, attack tool, or automated
remediation system. It does not train or fine-tune a model.

## 2. Locked project decisions

- Raw logs, raw prompts, full raw model responses, and model reasoning traces are
  not persisted.
- Parser-derived facts and LLM interpretation are separate trust domains.
- `observed_findings` and parser statistics are created only by deterministic code.
- The LLM produces a constrained `ModelAssessment`, not the complete final report.
- The application assembles the final `IncidentReport` from parser truth, validated
  model assessment, verified citations, and safe runtime metadata.
- Foundry Local and Ollama are equal provider implementations behind a common
  contract. No business logic may depend directly on one runtime.
- Foundation-Sec, Qwen, and Foundry profiles are all eligible to become the default.
  The default is selected by project-specific benchmark evidence.
- Model quality and groundedness take precedence over latency. Latency is a final
  tie-breaker, not the primary selection criterion.
- The core product has no cloud LLM fallback.
- The MVP uses Swagger UI. A separate frontend is out of scope.

## 3. Current environment baseline

The last verified local inventory is:

- Active work branch: `feature/p0-repository-governance`
- Application code: not created
- Host operating system: Windows 11
- CPU: Intel Core Ultra 5 125H
- Memory: approximately 15.52 GB
- GPU: Intel Arc Graphics
- Host Python: 3.13.3
- Project Python target: 3.12
- Docker Desktop: installed, version 4.85.0; service health still needs verification
- Ollama: installed, version 0.32.6; service was not running at the last check
- Foundry Local CLI: installed, version 0.10.2
- External model root: exists and is empty at
  `C:\Users\husoelrey\Documents\docs\AI_models`
- Previous interrupted Ollama download: removed from the checked cache locations
- Model download completion and file integrity: not verified

Do not treat installation as successful runtime readiness. P1 closes only after each
selected profile returns a valid response and its metadata is recorded.

## 4. Target topology

The preferred deployment is:

```text
Windows host
├── Foundry Local runtime and model cache
├── Ollama runtime and model cache
└── Docker Desktop
    └── SecureOps Local container
        ├── FastAPI
        ├── deterministic parser
        ├── RAG and citation validation
        ├── bounded job runner
        └── SQLite volume
```

The application container connects to host runtimes through
`host.docker.internal`. If Foundry endpoint binding or Docker host networking is
unreliable, use native Windows FastAPI as the documented fallback. Do not move
Foundry Local into a container merely to preserve a single-container appearance.

## 5. Model and runtime profiles

### 5.1 Foundation-Sec profile

- Model source: `fdtn-ai/Foundation-Sec-8B-Reasoning-Q4_K_M-GGUF`
- Runtime: Ollama
- Quantization: Q4_K_M
- Expected GGUF size: approximately 4.92 GB
- Local alias: `foundation-sec-8b-reasoning:q4_k_m`
- Role: initial primary candidate and domain-specialized cybersecurity profile
- Source file and Ollama cache must remain outside the repository.

The model is built on Llama 3.1. The model manifest must distinguish the Meta Llama
3.1 Community License governing the base model from the Apache 2.0 license stated
for Cisco changes. The project may document installation but must not redistribute
the weights.

Foundation's chat template begins with a reasoning section. The Ollama adapter must:

1. Prefer the runtime's separate `message.thinking` and `message.content` fields.
2. Fall back to removing one complete leading `<think>...</think>` block.
3. Never return, log, or persist the reasoning trace.
4. Count reasoning duration or tokens only when the runtime exposes defensible metrics.
5. Reject malformed or unterminated reasoning output rather than guessing boundaries.

### 5.2 Qwen reference profile

- Model: `qwen3.5:9b-q4_K_M`
- Runtime: Ollama
- Quantization: Q4_K_M
- Expected package size: approximately 6.6 GB
- Role: general-purpose quality reference and fallback candidate

Qwen is retained because its official Ollama packaging, broad ecosystem, clean
Apache 2.0 metadata, and general instruction-following capability reduce integration
risk. Features unrelated to this incident-review workflow are not selection
requirements and must not be presented as project benefits.

### 5.3 Foundry Local profile

The exact Foundry model is resolved from the device catalog during P1. Select the
strongest available profile that:

- is a chat/instruct model;
- runs reliably on the target device;
- supports at least an 8,192-token application context;
- can produce parseable structured output through the available API;
- exposes enough metadata to identify its model, runtime, and execution provider;
- fits the 16 GB sequential-execution constraint.

Record the resolved model identifier instead of hiding it behind a friendly alias.

### 5.4 Initial generation configuration

Use the following normalized application settings where supported:

- context limit: `8192`
- temperature: `0`
- top-p: `0.9`
- seed: `42`
- maximum output tokens: `2048`
- timeout: `300` seconds
- keep-alive: `10` minutes

Provider-specific unsupported settings must be recorded, not silently emulated.
Profiles run sequentially and are unloaded between cold measurements.

## 6. Deterministic SSH analysis

### 6.1 Safe file acceptance

Treat every uploaded file as hostile.

- SSH logs: `.log` and `.txt`, maximum 5 MiB
- Knowledge documents: `.pdf`, `.md`, and `.txt`, maximum 20 MiB
- Enforce limits while streaming, before complete buffering.
- Validate extension, MIME/magic signature, and expected textual structure.
- Reject archives, null bytes, unsafe binary content, and unbounded line lengths.
- Use random temporary names; never use a user filename as a disk path.
- Delete temporary files on success, validation failure, parser failure, timeout,
  cancellation, and unexpected exception paths.
- Never pass file content to a shell or subprocess.

### 6.2 Parser contract and supported events

Define an extensible parser contract with `can_parse`, `parse`, `summarize`, and
`build_retrieval_query` behavior. The first implementation is `SSHAuthLogParser`.

It must support:

- IPv4 and IPv6 sources
- failed password events
- accepted password and public-key events
- invalid-user variants
- root and configured privileged-account attempts
- source port and authentication method when present
- common syslog and journald prefixes
- malformed or irrelevant lines
- duplicate lines without silently inventing deduplication semantics

Required deterministic aggregates include total events, failures, successes, unique
sources, top source, target users, privileged attempts, invalid-user attempts,
authentication methods, first and last timestamps, analysis duration, unparsed-line
count, and timestamp limitations.

Initial configurable patterns are:

- repeated authentication attempts: at least five failures from one source within
  five minutes;
- success after repeated failures: a success for the same source and user within
  fifteen minutes after at least five failures.

These flags describe patterns, not confirmed attacks. Logs without a year or timezone
must expose the assumption. Benchmark fixtures use year `2026` and timezone `UTC`.

## 7. Knowledge base and local RAG

### 7.1 Initial authoritative sources

The first knowledge snapshot targets:

1. NIST SP 800-61 Rev. 3
2. CISA Federal Government Cybersecurity Incident Response Playbook
3. MITRE ATT&CK T1110 and relevant detection/mitigation material
4. OWASP Logging Cheat Sheet
5. Microsoft OpenSSH logging guidance
6. NIST SP 800-92

Each manifest entry records publisher, canonical URL, version/date, retrieval date,
license identifier and URL, redistribution status, attribution, SHA-256, local path
or download instructions, and notes. Content with `unknown` or `prohibited`
redistribution status stays outside Git.

### 7.2 Ingestion and retrieval

- Extract text from PDF, Markdown, and plain text without executing active content.
- Reject image-only PDFs; OCR is outside the MVP.
- Preserve heading paths, page/section references, chunk order, and content hashes.
- Start with 400-word chunks and 60-word overlap.
- Use TF-IDF and cosine similarity as the deterministic baseline.
- Use `top_k=5`, initial minimum score `0.05`, and at most two chunks per source.
- Construct controlled security queries from parser statistics.
- Exclude IP addresses and usernames unless an explicitly tested retrieval reason exists.
- Treat document instructions as untrusted data, never as system instructions.

Every model citation must refer to a chunk in the exact retrieved context set and a
real database record. Citation validation must reject invented document or chunk IDs.

## 8. LLM boundary and report assembly

### 8.1 Provider contract

The shared provider boundary exposes:

- `health()`
- `list_models()`
- `resolve_model()`
- `generate()`
- `generate_stream()`

Normalized results contain provider/runtime identity, resolved model ID and digest,
quantization, execution provider, final content, finish reason, token counts, TTFT,
total duration, and safe provider metadata.

### 8.2 ModelAssessment

The LLM generates only:

- `summary`
- `possible_interpretations`
- `risk_level`
- `risk_reasoning`
- `recommended_actions`
- `citations`
- `limitations`

Use strict Pydantic v2 validation and reject additional fields. Allowed risk values
are `low`, `medium`, and `high`. The model must use cautious language, acknowledge
insufficient evidence, and limit recommendations to investigation, evidence
preservation, correlation, escalation, and defensive hardening.

If JSON parsing or schema validation fails, perform one controlled repair request.
A second failure produces `invalid_model_output`; no completed report is stored.

### 8.3 IncidentReport

The application assembles the public report from:

- incident identity and job status;
- parser-controlled `observed_findings` and statistics;
- validated model assessment;
- verified citation metadata;
- model profile and runtime information;
- defensible performance metrics.

If model text conflicts with parser truth, reject the assessment. Never allow the
model to replace counts, addresses, users, event times, or evidence references.

## 9. API and persistence

The MVP API contains:

- `GET /health`
- `GET /models`
- `POST /v1/knowledge/ingest`
- `GET /v1/knowledge/sources`
- `POST /v1/incidents/analyze`
- `GET /v1/incidents/{incident_id}`
- `POST /v1/benchmarks/run`
- `GET /v1/benchmarks/{benchmark_id}`

Incident submission accepts a multipart SSH log, `model_profile_id`, and optional
redaction mode defaulting to `masked`. It returns `202 Accepted` with a job ID.

Use a bounded in-process queue with capacity four, global inference concurrency one,
and one active inference per provider. Persist job state in SQLite. On startup, mark
leftover `running` jobs as `interrupted`.

SQLite may store file hash and size, masked parser findings, validated final reports,
citations, model metadata, and performance metrics. It must not store raw logs, raw
prompts, complete raw responses, secrets, or reasoning traces.

## 10. Benchmark and default-profile selection

### 10.1 Cases and fixed inputs

Create at least ten synthetic, version-controlled cases covering:

- one normal successful login;
- one failed login;
- repeated failures from one source;
- one source targeting multiple users;
- privileged/root attempts;
- invalid-user attempts;
- success after repeated failures;
- multiple source addresses;
- IPv6;
- malformed or non-SSH input;
- a log-line prompt-injection attempt as an additional security case.

Freeze the raw fixture hash, parser result, retrieved context, knowledge snapshot,
prompt version, schema version, generation settings, and timeout for every profile.
Retrieval runs once per case; models receive the same evidence pack.

### 10.2 Metrics

Quality metrics are first-attempt and post-repair schema success, unsupported-claim
count, citation validity and coverage, recommendation completeness, risk consistency,
cautious-language compliance, groundedness, and readability.

Performance metrics are cold load, TTFT, total duration, token rate, and defensible
RAM measurements. CPU/GPU metrics remain unavailable if the measurement scope cannot
be established. Do not present estimated GPU data or TOPS as application performance.

Run every case at least once for every profile. Run three warm repetitions for three
to five representative cases. Do not keep multiple models loaded during comparison.

### 10.3 Eligibility and winner rules

A profile is eligible to become the default only if it:

- completes every mandatory case;
- reaches 100% schema compliance after at most one repair;
- reaches 100% citation-ID validity;
- produces zero unsupported deterministic claims;
- avoids definitive attack attribution and forbidden automated-remediation language.

If multiple profiles remain eligible, select in this order:

1. groundedness;
2. citation coverage;
3. recommendation completeness;
4. risk consistency;
5. readability;
6. median latency.

Publish raw metrics rather than hiding trade-offs behind one magic score. Foundation,
Qwen, or Foundry may win. Do not announce a winner before the benchmark is complete.

## 11. Verification strategy

Required automated coverage includes:

- parser formats, aggregations, thresholds, malformed input, and time assumptions;
- upload size, extension, content, null-byte, encoding, long-line, and cleanup paths;
- retrieval relevance, source diversity, and citation validation;
- document and log prompt-injection resistance;
- provider contract behavior with deterministic fake providers;
- strict schema, one-repair, and invalid-output paths;
- reasoning trace exclusion from API responses, SQLite, and application logs;
- job queue, restart, timeout, and provider-unavailable behavior;
- end-to-end synthetic incident analysis.

CI runs Pytest, Ruff, mypy, migration checks, and secret/artifact checks. CI does not
download or run real models. Real model benchmarks and
offline tests are documented hardware-dependent workflows.

## 12. GitHub and offline readiness

The repository must provide a README, architecture diagram, quickstart,
runtime and model bootstrap instructions, license manifest, synthetic example,
benchmark results, reproducibility manifest, and explicit limitations.

Air-gapped-ready means that dependency, knowledge, and model downloads occur during
a documented online preparation step. After caches are prepared, the complete core
workflow must be demonstrated with network access disabled.

Do not commit model weights, runtime caches, operational SQLite databases, secrets,
real organizational logs, raw prompts/responses, or documents without redistribution
permission.

## 13. Definition of done for every checklist item

An item may be checked only when:

- the requested behavior is implemented;
- success and relevant failure paths are tested;
- applicable Pytest, Ruff, and mypy checks pass;
- security, privacy, and offline constraints remain intact;
- documentation and decisions are updated when affected;
- `CURRENT_STATUS.md` describes the verified state;
- the next safe, bounded task is identifiable.

## 14. Explicitly deferred work

- model training or fine-tuning
- cloud inference fallback
- automatic blocking, account actions, command execution, or exploitation
- separate web frontend
- vector database or embedding retrieval
- Nmap and Nginx parsers
- PDF report generation
