# SecureOps Local — Security and Privacy Model

## 1. Security objective

SecureOps Local processes sensitive security data and must not create a greater risk than the data it reviews. Its core objectives are local data handling, strict separation of data and executable behavior, minimal retention, deterministic evidence, cautious model interpretation, and verifiable offline artifacts.

## 2. Protected assets

- Raw SSH authentication logs
- IP addresses, account names, host names, and incident timelines
- Knowledge documents and provenance metadata
- SQLite application data
- Prompt and schema versions
- Runtime and model caches
- Benchmark fixtures, configurations, and results
- Application configuration

## 3. Trust boundaries

Trusted components:

- Version-controlled application code
- Strict domain schemas
- Tested parser and scoring rules
- Reviewed source metadata and internal identifiers

Untrusted inputs:

- Every uploaded file and filename
- MIME headers and user-supplied metadata
- Log lines and document text
- Retrieved chunks when used in a prompt
- Raw model output and runtime errors
- Model-generated citation identifiers
- Imported offline bundles

## 4. Upload controls

- Accept only log and text files for SSH analysis.
- Accept only PDF, Markdown, and text files for the knowledge base.
- Reject archives and compressed rotated logs in the MVP.
- Do not use the submitted filename as a storage path.
- Enforce byte limits while streaming, not only through Content-Length.
- Validate extension, MIME type, magic bytes, content shape, and encoding.
- Reject or safely report null bytes, excessive binary content, overlong lines, malformed encodings, and empty unsupported input.
- Use random temporary names and clean them on every success and error path.
- Never pass file content to a shell or subprocess.

Initial configurable limits are 5 MiB for SSH logs and 20 MiB for knowledge documents. These values must be tested and may be adjusted with evidence.

## 5. Prompt-injection controls

Logs and retrieved documents are explicitly delimited as untrusted data. Instructions contained in that data do not change system policy or the task. The model receives no tools, shell access, filesystem access, or network capability through the application.

Observed findings are reconstructed or verified against parser truth. Citation identifiers must resolve to the exact retrieved chunk package. Adversarial log and document fixtures must test attempted policy override.

## 6. Model-output controls

- Validate all output with strict Pydantic models that reject extra fields.
- Treat raw model output as untrusted.
- Allow at most one controlled structural-repair attempt.
- Mark a second failure as invalid_model_output.
- Reject unsupported observed findings and parser contradictions.
- Reject citations outside the supplied evidence package.
- Do not persist invalid output as a completed incident.
- Do not request, return, log, or store hidden reasoning traces.

## 7. Privacy by default

- Raw log retention is disabled.
- Store only the input hash, size, parser version, safe timestamps, structured findings, and necessary metrics.
- Prefer line hashes or short masked evidence references over complete log lines.
- Remove concrete IP addresses and account names from retrieval queries when they do not improve retrieval.
- Minimize parser facts and evidence sent to the local model.
- Use synthetic addresses, accounts, hosts, and timestamps in repository fixtures.

The user-facing local report may show values from the submitted log when required for review, but application logging and provider requests still follow minimization rules.

## 8. Logging

Application logs must not include:

- Raw security logs
- Full prompts
- Full model responses
- Secrets or tokens
- Unmasked identifiers when redaction policy applies

Structured logs may include a correlation ID, incident or benchmark ID, stage, duration, state, safe error code, input size and hash, and model-profile identifier. Exceptions must not embed uploaded content or raw runtime responses.

## 9. Persistence

- Store application data only in a controlled local volume.
- Keep working databases, journal files, and backups out of version control.
- Enable SQLite foreign keys and document local file-permission expectations.
- Make retention and backup behavior explicit and user-controlled.
- Test that raw logs never reach the database.

## 10. API and runtime exposure

- Bind the API to localhost by default.
- Disable CORS or restrict it to explicit local origins.
- Do not expose an unauthenticated MVP on a public interface.
- Apply request, queue, and execution limits.
- Return safe error messages.
- Configure provider base URLs through trusted settings, never upload content.
- Bind Foundry Local and Ollama to local interfaces where supported.
- Review runtime logging during integration to ensure prompts and inputs are not retained unexpectedly.

## 11. Container hardening

- Run as a non-root user.
- Use a minimal pinned base image.
- Prefer a read-only root filesystem with only controlled data and temporary paths writable.
- Do not mount the Docker socket.
- Do not use privileged mode.
- Drop unnecessary capabilities.
- Do not embed secrets or model caches in the image.

## 12. Supply-chain controls

- Pin application dependencies and retain hashes for offline packages.
- Run dependency and vulnerability checks appropriate to the lock format.
- Use official runtime sources.
- Record model source, revision, license, quantization source, and digest.
- Prefer publisher-controlled or independently verified model artifacts.
- Record knowledge-source URL, publisher, version, license, redistribution decision, and SHA-256.
- Verify imported offline manifests before use.

## 13. Defensive boundary

The application does not execute commands, block addresses, modify firewall rules, disable accounts, scan targets, exploit systems, test credentials, or automate offensive activity. Recommendations are limited to investigation, evidence preservation, validation, monitoring, hardening, and escalation through authorized procedures.

## 14. Cautious assessment policy

Reports distinguish observation from interpretation. They may state that a pattern is consistent with repeated password guessing and deserves review, but they must not assert compromise, attacker identity, or malicious intent without sufficient evidence. Limitations and plausible benign explanations must be visible when the input cannot resolve them.

## 15. Required security tests

- Oversized log and document
- Extension, MIME, and content mismatch
- Executable content renamed as text
- Null bytes and overlong lines
- Invalid encoding
- Path-traversal filename
- Empty and unsupported text
- PDF parsing failure
- Prompt injection in logs and documents
- Hallucinated citation identifier
- Unsupported observed finding
- Provider timeout and unavailable runtime
- Queue exhaustion and interrupted jobs
- Temporary-file cleanup after exceptions
- Verification that raw logs are absent from the database and application logs

## 16. Security acceptance criteria

- Upload-security success and failure tests pass.
- Untrusted content cannot alter observed parser facts.
- Invalid citations and output never become completed reports.
- Provider endpoints cannot be changed by request data.
- Raw logs are absent from persistence and application logging.
- No application code path can execute remediation.
- Cached offline analysis makes no external request.
