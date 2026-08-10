# SecureOps Local — Implementation Roadmap

Use PLAN.md as the executable checklist. Complete phases in order and do not bypass a
failing gate.

Current verified transition: P0 is complete and P1 is in progress. Runtime health,
Foundry daemon readiness, and runtime-supported external model storage are verified.
The Foundation-Sec GGUF has been successfully acquired, verified, and imported into Ollama.
The next bounded task is to pull Qwen3.5 9B Q4_K_M.

## P0 — Repository governance and project context

Exit criteria:

- Context documents are internally consistent.
- PLAN.md, CURRENT_STATUS.md, and DECISION_LOG.md agree.
- Legacy model and scope assumptions are removed.
- Environment inventory is current.
- Git ignore policy protects models, caches, databases, secrets, and raw logs.

## P1 — Local runtime and model profiles

Exit criteria:

- Docker, Ollama, and Foundry runtime health is verified.
- External model storage configuration is verified.
- Foundation-Sec GGUF hash and license metadata are recorded.
- Foundation-Sec is imported into Ollama.
- Qwen3.5 9B Q4_K_M is available.
- A compatible Foundry model is resolved from the device catalog.
- All three profiles pass the same structured-output smoke case.
- Reasoning separation and non-retention are proven.
- Docker-to-host connectivity and cached offline inference are tested.

Current P1 evidence: all exit criteria have been met. P1 gate is complete.

## P2 — Deterministic SSH analysis core

Exit criteria:

- Python project and tooling are bootstrapped.
- Strict domain schemas exist.
- Upload handling is safe and bounded.
- SSHAuthLogParser supports required formats.
- Deterministic aggregates and time-window patterns are tested.
- Malformed input and timestamp limitations are covered.
- No LLM is required for parser correctness.

## P3 — Local knowledge base and RAG

Exit criteria:

- Authoritative source manifest and license decisions exist.
- PDF, Markdown, and text ingestion is safe.
- Chunks preserve source and section/page metadata.
- TF-IDF retrieval finds expected topics.
- Context packing enforces source diversity.
- Citation IDs resolve to retrieved chunks.
- Document prompt-injection tests pass.

## P4 — Provider-independent incident analysis

Exit criteria:

- LocalLLMProvider is implemented.
- Ollama and Foundry adapters return normalized results.
- Prompt and ModelAssessment schema are versioned.
- One controlled repair path is tested.
- IncidentReport assembly keeps parser truth immutable.
- Reasoning, raw prompts, and raw responses are not stored.
- One complete cited incident analysis succeeds.

## P5 — API, persistence, and job orchestration

Exit criteria:

- SQLite schema and migrations exist.
- Bounded job runner handles restart and backpressure.
- Health, model, knowledge, incident, and benchmark endpoints exist.
- Application logging is structured and privacy-safe.
- Raw security logs are absent from the database.

## P6 — Deployment-profile benchmark and default selection

Exit criteria:

- At least ten synthetic cases are version-controlled.
- Every profile receives the same frozen evidence package.
- Deterministic scorers and manual rubric are implemented.
- Cold and warm metrics are recorded sequentially.
- Failures and unavailable metrics remain visible.
- The default profile is selected using documented quality gates.
- Benchmark results and reproducibility manifest are published.

## P7 — Offline and GitHub readiness

Exit criteria:

- Cached end-to-end operation succeeds without network access.
- CI passes with fake providers and no model downloads.
- README, architecture, quickstart, troubleshooting, licenses, synthetic examples,
  benchmark results, and limitations are complete.
- The MVP acceptance checklist passes.
- main remains in a working and reviewable state.

## Scope-reduction order

If scope must be reduced, defer in this order:

1. Embedding retrieval
2. Separate frontend
3. Additional model variants beyond the three candidates
4. PDF report export
5. Additional log parsers
6. Advanced GPU telemetry

Never remove safe upload handling, deterministic parsing, authoritative local RAG,
strict output validation, both runtime providers, the benchmark case set, or offline
verification.
