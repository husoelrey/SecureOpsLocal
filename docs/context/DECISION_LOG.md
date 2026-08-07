# SecureOps Local — Decision Log

Statuses: Proposed, Accepted, Superseded, Rejected.

## D-001 — Decision-support product boundary

- Status: Accepted
- Decision: The product supports initial incident review; it is not a SIEM, IDS,
  attack tool, or automated remediation product.

## D-002 — Deterministic parser before LLM

- Status: Accepted
- Decision: Counts, identities, timestamps, and patterns come from deterministic code.
- Consequence: observed_findings is application-controlled.

## D-003 — No model training

- Status: Accepted
- Decision: Use existing local models with RAG; no training or fine-tuning.

## D-004 — Provider-independent multi-runtime architecture

- Status: Accepted
- Decision: Foundry Local and Ollama implement the same LocalLLMProvider contract.

## D-005 — Deployment profile is the comparison unit

- Status: Accepted
- Decision: Benchmark model, runtime, quantization, execution backend, and generation
  settings as one deployment profile.

## D-006 — Host runtimes with containerized application

- Status: Accepted, subject to P1 verification
- Decision: Run Foundry and Ollama on Windows; prefer FastAPI in Docker.
- Fallback: Run FastAPI natively on Windows.

## D-007 — Modular monolith

- Status: Accepted
- Decision: Use one FastAPI deployment unit with internal modules.

## D-008 — Bounded local job runner

- Status: Accepted
- Decision: Use an in-process queue with SQLite state and no external broker.

## D-009 — SQLite persistence stack

- Status: Accepted
- Decision: Use SQLite, SQLAlchemy 2, and Alembic.

## D-010 — TF-IDF retrieval baseline

- Status: Accepted
- Decision: Use TF-IDF and cosine similarity before considering embeddings.

## D-011 — No vector database for the MVP

- Status: Accepted
- Decision: The small knowledge collection does not justify an external vector store.

## D-012 — No raw-log persistence

- Status: Accepted
- Decision: Persist only safe hashes, metadata, masked evidence, and validated reports.

## D-013 — Strict validation with one repair

- Status: Accepted
- Decision: Reject additional fields, allow one controlled repair, then fail with
  invalid_model_output.

## D-014 — Swagger UI

- Status: Accepted
- Decision: Do not build a separate frontend for the MVP.

## D-015 — Air-gapped-ready terminology

- Status: Accepted
- Decision: Clearly separate online preparation from verified cached offline operation.

## D-016 — Ollama benchmark candidates

- Status: Accepted for P1 evaluation
- Decision: Evaluate Foundation-Sec-8B-Reasoning Q4_K_M and Qwen3.5 9B Q4_K_M.
- Consequence: Neither is the default before the benchmark.

## D-017 — Project Python version

- Status: Accepted
- Decision: Target Python 3.12 even though host Python 3.13.3 is installed.

## D-018 — Knowledge-source license audit

- Status: Accepted
- Decision: Keep content outside Git when redistribution is unknown or prohibited.

## D-019 — No definitive attack attribution

- Status: Accepted
- Decision: Reports express evidence-supported possibilities and limitations.

## D-020 — Reasoning non-retention

- Status: Accepted
- Decision: Model reasoning may run internally but is never returned, logged, or persisted.

## D-021 — Quality-first default selection

- Status: Accepted
- Decision: Foundation, Qwen, and Foundry may all win. Quality gates precede latency;
  latency is the final tie-breaker.

## D-022 — External model storage

- Status: Accepted
- Decision: Store downloads and runtime model caches outside the repository under:
  C:\Users\husoelrey\Documents\docs\AI_models
- Condition: Verify each runtime's supported cache configuration before moving or downloading models.

## D-023 — Tool-neutral Git workflow

- Status: Accepted
- Date: 2026-08-07
- Decision: Use feature/p<phase>-<feature>, fix/<topic>, docs/<topic>, and
  spike/<topic> branch names without editor or assistant branding.
- Commit policy: Create small, single-purpose commits only after relevant checks pass.
- Push policy: When the user authorizes Git publication, push every verified feature
  commit to its working branch.
- Merge policy: Keep main verified and merge only after the feature or phase exit
  criteria pass.
- Safety: Do not force-push, rewrite shared history, or stage unrelated user changes.

## D-024 — Repository artifact exclusion policy

- Status: Accepted
- Date: 2026-08-07
- Decision: Keep Python caches, virtual environments, coverage and build output,
  editor and operating-system state, secrets, environment files, operational
  databases, temporary and uploaded data, raw security logs, generated reports,
  runtime caches, downloads, archives, and model weights out of version control.
- Trackable boundary: Safe synthetic logs are allowed only in explicit synthetic
  fixture, benchmark-case, or version-controlled example paths. Benchmark case
  definitions, migrations, source manifests, documentation, and text examples remain
  trackable by default.
- Verification: Representative ignored and trackable paths must pass
  `git check-ignore` during repository-governance validation.

## New decision template

## D-XXX — Title

- Status:
- Date:
- Decision:
- Rationale:
- Alternatives:
- Consequence or fallback:
