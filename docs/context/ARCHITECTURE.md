# SecureOps Local — Architecture

## 1. Architectural goals

- Keep sensitive data on the local device.
- Separate deterministic facts from model interpretation.
- Keep business logic independent of Foundry Local and Ollama.
- Prefer small, testable modules over distributed-system complexity.
- Support offline operation after artifacts are prepared.
- Preserve a reliable native fallback when container networking is unsuitable.

The selected style is a modular monolith with local inference runtimes hosted on Windows.

## 2. System context

The user submits data to a FastAPI application. The application validates files, parses SSH events, retrieves local document chunks, invokes one local model provider, validates the result, and stores safe metadata in SQLite.

Foundry Local and Ollama run on the Windows host. FastAPI, SQLite, and deterministic application components normally run in Docker. WSL 2 may generate synthetic Linux fixtures and provide development helpers. No cloud model or cloud vector store is part of the core architecture.

## 3. Deployment topology

Preferred path:

- Windows host: Foundry Local, Ollama, hardware acceleration, and external model caches
- Docker container: FastAPI, parser, retrieval, persistence, and benchmark orchestration
- Docker volume: SQLite and controlled application data
- WSL 2: synthetic fixture generation and Linux-focused checks
- Container-to-runtime connection: host.docker.internal with configured local ports

Fallback order:

1. FastAPI on native Windows
2. FastAPI in WSL while reaching Windows-hosted runtimes
3. Docker only for packaging and deterministic tests

Foundry Local must not be forced into a container when doing so harms reliability or hardware acceleration.

## 4. Repository layout

Planned top-level packages under src/secureops_local:

- api: application construction, routes, dependencies, middleware, and error mapping
- core: configuration, logging, shared errors, and primitive types
- domain: incidents, knowledge, models, and benchmark contracts
- parsers: parser interface, registry, SSH parser, and aggregation
- security: upload validation, limits, cleanup, and redaction
- ingestion: document readers, cleaning, chunking, and indexing
- retrieval: common retriever contract, TF-IDF baseline, and optional embeddings
- llm: provider contract, Foundry and Ollama adapters, prompts, validation, and registry
- services: incident orchestration, jobs, and model catalog
- benchmark: cases, runner, metrics, and deterministic scoring
- db: SQLAlchemy models, sessions, migrations, and repositories

Dependencies point inward toward domain contracts. Pure parsers, scorers, and validators must not depend on FastAPI.

## 5. Analysis sequence

1. The API streams and validates the upload while calculating its SHA-256.
2. It creates a pending incident and submits a bounded job.
3. SSHAuthLogParser returns normalized events and deterministic findings.
4. Retrieval returns a stable top-k chunk package.
5. The selected LocalLLMProvider receives versioned instructions, parser facts, and retrieved evidence.
6. The provider returns content and safe runtime metrics.
7. Strict validation checks JSON shape, field constraints, parser consistency, and citation existence.
8. One controlled repair attempt is allowed for invalid output.
9. A valid report is persisted as completed; a second failure becomes invalid_model_output.
10. Temporary upload data is removed on every completion and error path.

## 6. Core contracts

### Parser

The parser contract provides capability detection, streaming parsing, aggregation, and retrieval-query construction. ParseResult carries parser identity, normalized events, deterministic findings, statistics, warnings, limitations, and unparsed-line information.

### Retriever

The retriever contract supports indexing, top-k search, filters, and health reporting. RetrievedChunk carries stable document and chunk identifiers plus provenance metadata.

### LocalLLMProvider

The common provider supports health checks, model discovery, profile resolution, standard generation, streaming generation, and optional lifecycle operations when a runtime exposes them.

GenerationResult contains provider, runtime, resolved model, quantization, execution provider, content, finish reason, token counts, time to first token, total duration, and safe provider metadata.

### Repositories

Repository interfaces isolate application services from SQLAlchemy details for documents, incidents, model runs, and benchmarks.

## 7. API behavior

GET /health reports API, database, and provider status independently. The application may be degraded when one provider is unavailable; database failure prevents readiness.

GET /models returns safe profile metadata only. It must not expose host cache paths.

POST /v1/knowledge/ingest accepts reviewed source metadata and a bounded PDF, Markdown, or text file.

POST /v1/incidents/analyze accepts a bounded SSH log and a configured profile identifier. It returns 202 Accepted for a queued job, 429 when capacity is exhausted, and 422 when the format is unsupported.

Incident status values are pending, running, completed, failed, interrupted, and invalid_model_output.

## 8. Job runner

The MVP uses a bounded in-process queue:

- Initial concurrency is one.
- Each provider allows at most one active inference unless measurement proves a safe alternative.
- Job state is stored in SQLite.
- Jobs left running after process termination become interrupted at startup.
- Graceful shutdown stops admission before completing or interrupting active work.
- Queue capacity and timeouts are configurable.

An external broker is not introduced for the MVP.

## 9. Persistence

SQLite is the source of truth for controlled application metadata. Foreign keys are enabled, WAL mode and a busy timeout are configured, and transaction boundaries are explicit.

Documents store provenance, version, license, redistribution status, and hashes. Chunks store stable ordinals, headings, page references, content hashes, and text. Incidents store state, input hash and size, parser metadata, valid report data, and safe errors. Model and benchmark records store complete profile configuration, versions, metrics, and validation results.

Raw logs are not stored by default.

## 10. Parser design

Parsing has two stages:

1. Convert each supported line into a normalized authentication event.
2. Aggregate events into statistics and deterministic findings.

Normalized fields include event type, timestamp and confidence, host, process, account, source address and port, authentication method, success state, privilege indicator, invalid-user indicator, and a safe source reference.

Regex parsing and security-pattern aggregation remain separate so each can be tested independently.

## 11. Retrieval design

SQLite stores document and chunk truth. The initial TF-IDF index may be rebuilt from trusted database content at startup or first use because the knowledge base is deliberately small.

Untrusted serialized object formats are not loaded. If index persistence becomes necessary, use a documented safe format with hashes. Optional embeddings store model identity, dimension, data type, and normalization metadata and use NumPy cosine similarity without introducing a vector database.

## 12. Prompt and validation design

Prompt sections distinguish:

1. System policy
2. Output contract
3. Trusted parser facts
4. Untrusted retrieved documents
5. Minimal untrusted log evidence
6. The assessment task

Document and log content is always data, never instruction. The model receives no tool access. Hidden reasoning traces are not requested, exposed, logged, or persisted.

Validation rejects unexpected fields, malformed citations, unsupported observed findings, and contradictions with parser output.

## 13. Model profiles

Model names and generation settings are configuration, not scattered constants. A resolved profile records:

- Profile identifier
- Provider and runtime version
- Model alias, resolved identifier, and digest when available
- Quantization and execution provider
- Temperature, top-p, seed, output limit, and context limit
- Timeout and lifecycle settings
- Prompt and schema versions

Model weights and caches live outside the repository.

## 14. Error model

Domain errors are mapped to controlled API responses:

- upload_too_large
- unsupported_media_type
- unsafe_or_invalid_file
- unsupported_log_format
- parse_failed
- knowledge_base_empty
- retrieval_failed
- provider_unavailable
- model_not_available
- inference_timeout
- invalid_model_output
- queue_full
- job_interrupted

Runtime error bodies are treated as untrusted and are not returned verbatim.

## 15. Offline design

An offline manifest records the application commit, Python version, locked wheels and hashes, image digest or native package, runtime versions, resolved model identifiers and digests, knowledge-source hashes and licenses, migration head, and prompt/schema versions.

Offline mode contains no network fallback. Missing artifacts produce a clear preflight error.

## 16. Architecture quality gates

- Provider contracts can be tested with fake implementations.
- Parser and scorer tests require no inference runtime.
- Both providers receive the same normalized evidence package.
- API tests do not download real models.
- Database-independent unit tests cover pure domain logic.
- Offline checks are explicit and separately marked.
