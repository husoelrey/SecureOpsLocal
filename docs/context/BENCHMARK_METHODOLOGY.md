# SecureOps Local — Benchmark Methodology

## 1. Objective

The benchmark measures which complete local deployment profile provides the best balance of security-report quality, structured-output reliability, latency, and memory use on the target device. It does not claim that one model family is universally superior.

## 2. Comparison unit

A deployment profile includes:

- Exact model identifier, revision, and digest when available
- Parameter class and quantization
- Runtime and version
- Execution provider or backend
- Prompt and schema versions
- Generation settings and context limit
- Hardware and driver context

Results describe measured trade-offs between these profiles on this device and dataset.

## 3. Candidate profiles

The initial benchmark includes:

1. Foundation-Sec-8B-Reasoning Q4_K_M through Ollama
2. Qwen3.5 9B Q4_K_M through Ollama
3. A device-supported Foundry Local profile selected after catalog inspection

No candidate is the default before compatibility and benchmark results are recorded. Profile names, versions, licenses, and runtime behavior must be verified from current primary sources before download or integration.

## 4. Case contract

Each version-controlled synthetic case records:

- case_id and title
- log_type and input_file
- input_sha256
- expected_findings
- forbidden_or_unsupported_claims
- expected_recommendation_categories
- expected_source_topics
- acceptable_risk_levels
- notes

## 5. Minimum case coverage

At least ten cases cover:

1. A normal successful login
2. A single failed login
3. Repeated failures from one address
4. One address targeting multiple accounts
5. Attempts involving a privileged account
6. Invalid-user attempts
7. Success after repeated failures
8. Multiple source addresses
9. IPv6 input
10. Malformed or unrelated input

Additional cases should include public-key authentication, low-and-slow activity, timestamp ambiguity, duplicate lines, prompt injection, plausible administrator automation, high-volume failures without success, and supported logging-format variants.

## 6. Fixed evidence package

Every profile receives the same:

- Synthetic input fixture
- Parser version and result
- Retrieved top-k chunk identifiers and content
- Knowledge snapshot hash
- Prompt and output-schema versions
- Compatible temperature, top-p, seed, output limit, and timeout settings

Retrieval runs once per case. The resulting evidence package is reused across profiles and repetitions.

## 7. Performance metrics

### Cold-load time

Measure from load initiation until the cached model is ready. Initial artifact-download time is an onboarding metric and is not inference performance.

### Time to first token

Measure from request start to the first content token or chunk through streaming.

### Total latency

Measure from request start through completed response receipt.

### Throughput

Preferred formula:

completion tokens divided by the duration from first token to completion.

If the provider does not report token counts, record the tokenizer or estimation method and mark the value as estimated.

### Memory

Record average and peak process working set or RSS and clearly name the measured processes. Host runtimes and the application container must not be conflated. System-memory deltas may be reported separately.

### CPU and GPU

Record utilization only when a reliable repeatable counter exists, together with the device and backend. Leave unsupported metrics unavailable rather than estimating them. Hardware TOPS is not an application-performance metric.

## 8. Deterministic quality metrics

- Expected finding recall
- Unsupported observed-finding count
- First-attempt schema compliance
- Compliance after one repair
- Citation identifier validity
- Citation coverage
- Recommendation-category completeness
- Risk-level consistency
- Detection of prohibited certainty or remediation language

Free-form interpretation is not presented as fully machine-verifiable entailment. Deterministic scoring evaluates only fields and patterns with defensible rules.

## 9. Manual rubric

Score each category from zero to two:

- Groundedness
- Whether citations support the associated claims
- Cautious and evidence-aware interpretation
- Practical defensive recommendations
- Report readability

Zero is incorrect or absent, one is partially adequate, and two is clearly adequate. Record evaluator and date. Do not use another model as the sole judge.

## 10. Repetition and consistency

- Run every case at least once per profile.
- Run three repetitions for three to five representative cases.
- Fix the seed when supported.
- Compare schema success, risk-category agreement, finding-set exact match or Jaccard similarity, and metric variance.

## 11. Cold and warm scenarios

Cold measurements begin with a cached model not resident in memory. Warm measurements use an already loaded model and declare whether a warm-up request was excluded.

Profiles run sequentially so that large models do not compete for the target device's limited memory. Runtime-specific unload behavior and residual memory are recorded.

## 12. Reasoning behavior

Reasoning or thinking settings are explicit profile configuration. Hidden reasoning text is never part of the product response, logs, persisted records, or benchmark artifacts. If one runtime exposes different reasoning controls, the difference is documented as part of the profile rather than hidden by an invalid equivalence claim.

## 13. Result reporting

For each profile report:

- Full profile metadata
- Completed, failed, and timed-out cases
- First-attempt and repaired schema rates
- Finding recall and unsupported claims
- Citation validity and coverage
- Recommendation completeness and risk consistency
- Median and P95 total latency
- Median time to first token and throughput
- Peak memory with measurement scope
- Manual-rubric averages

A single opaque composite score is not the primary result. If a secondary weighted score is added, its formula is explicit and the raw metrics remain visible.

## 14. Reproducibility manifest

Record:

- Application commit SHA
- Operating-system build
- CPU, memory, GPU, driver, and execution backend
- Runtime versions
- Model IDs, revisions, digests, and quantization
- Prompt and schema versions
- Knowledge snapshot and case-dataset versions
- Generation settings
- Benchmark timestamp
- Network state

## 15. Success criteria

The benchmark is valid when:

- At least ten cases complete or fail transparently for every required profile.
- Identical evidence packages are used.
- Deterministic scorer tests pass.
- Metric formulas and measurement scopes are documented.
- Timeouts, invalid outputs, and unavailable metrics are not hidden.
- Conclusions are framed as measured profile trade-offs.

## 16. Smoke Test Results

**Date**: 2026-08-10
**Target**: Foundation-Sec-8B-Reasoning Q4_K_M (via Ollama API)

A minimal Python script (`scripts/smoke_test.py`) was used to run an initial structured-output test against the Foundation-Sec model. 
- **Structured JSON Verification**: The model successfully emitted strict JSON without markdown formatting.
- **Reasoning Isolation**: Reasoning traces generated by the Foundation-Sec model were successfully isolated from the final JSON payload. They were kept out of the parsed structural result, satisfying the strict non-retention policy required by `AGENTS.md`.
