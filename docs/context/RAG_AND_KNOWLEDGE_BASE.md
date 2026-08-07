# SecureOps Local — RAG and Knowledge Base

## 1. Definition

Retrieval-Augmented Generation does not train or fine-tune the language model. The application splits documents into traceable chunks, searches for chunks relevant to a case, places a bounded selection into the prompt, and asks an existing local model to use that context. Model weights do not change. Creating TF-IDF features or embeddings is also not model training.

## 2. Role in the product

The parser establishes facts such as repeated failures from one source, attempts against multiple accounts, or activity involving a privileged account. Retrieval then finds guidance about authentication monitoring, credential-access patterns, triage, evidence preservation, and SSH hardening. The model combines parser truth with the supplied guidance to produce interpretation and defensive recommendations.

RAG does not eliminate hallucinations. Missing or irrelevant retrieval produces weak context, and a citation identifier alone does not prove that the cited text supports a claim.

## 3. Initial source set

The first knowledge base contains five to ten focused sources, prioritizing:

1. NIST SP 800-61 Rev. 3
2. Current CISA incident-response guidance
3. MITRE ATT&CK T1110 and related defensive guidance
4. OWASP logging guidance
5. Microsoft security or SSH-monitoring documentation
6. Authoritative OpenSSH monitoring and hardening material
7. Evidence-preservation or log-management guidance when needed

Quality, relevance, provenance, and redistribution rights matter more than collection size.

## 4. Source manifest

Each source records:

- source_id
- title
- publisher
- canonical_url
- document_version
- publication_date
- retrieved_at
- license_id and license_url
- redistribution_status
- required_attribution
- sha256
- repository_path or download_instructions
- notes

Redistribution status is allowed, allowed_with_attribution, link_only, unknown, or prohibited. Sources marked unknown or prohibited are not committed to the repository.

## 5. Ingestion pipeline

### Accept

Validate the PDF, Markdown, or text allowlist, streamed size, MIME type, content, encoding, hash, and duplicate status.

### Extract

Preserve headings and page references. Image-only or unextractable PDFs return a controlled error because OCR is outside the MVP.

### Clean

Reduce repeated headers and footers, normalize excessive whitespace, handle page breaks and hyphenation conservatively, preserve headings, and never rewrite source meaning.

### Chunk

Initial configurable targets are 300 to 500 words with 50 to 80 words of overlap. Prefer heading and section boundaries, join very short headings to their following content, and split oversized sections deterministically.

### Persist and index

Store source metadata, chunk order, heading path, page or section references, content hashes, length estimates, and index version. Build the TF-IDF baseline from the controlled chunk store.

## 6. TF-IDF baseline

TF-IDF is the MVP retriever because it is deterministic, explainable, lightweight, completely local, easy to package, and appropriate for a small focused corpus. Its primary limitation is weaker semantic matching across synonyms and paraphrases.

Mitigations include structured security terms generated from parser findings, a small reviewed synonym map, query-expansion tests, and an optional embedding experiment after the baseline passes its gates.

## 7. Retrieval queries

A query is a privacy-minimized representation of the case, not a copy of the raw log. Useful concepts include:

- SSH authentication failures
- Repeated password attempts
- Invalid-user login
- Privileged-account monitoring
- Successful login after failures
- Incident triage
- Evidence and log preservation
- Credential-access investigation

Concrete IP addresses and account names are excluded unless a test demonstrates retrieval value.

## 8. Ranking and context packing

Initial search settings:

- top_k between four and six
- A configurable minimum relevance threshold
- A cap on excessive chunks from one source
- Preference for source and heading diversity
- A fixed context-token budget

Each context item contains a stable chunk ID, source title, section or page, content, and retrieval score. The score ranks retrieval relevance and is not a correctness probability.

## 9. Citation design

The model may cite only chunk identifiers included in its evidence package. Validation confirms:

- The identifier is in the retrieved set.
- The document and chunk exist in SQLite.
- Source metadata matches the chunk.
- The cited topic is plausibly related to the supported interpretation or recommendation.

Response citations contain document_id, chunk_id, source_title, section_or_page, and a short excerpt. Long copyrighted passages are not copied into reports.

## 10. Optional embeddings

An embedding retriever may be considered only after:

1. TF-IDF works end to end.
2. The embedding model has an acceptable license and provenance.
3. It runs offline on the target device.
4. Memory and packaging costs are acceptable.
5. Retrieval evaluation shows a measurable benefit.

Vectors may be stored in SQLite with model version, dimension, data type, and normalization metadata and searched through NumPy cosine similarity. The MVP does not require a vector database.

## 11. Retrieval evaluation

Each retrieval fixture records a query ID, parser facts, expected source topics, relevant chunks or acceptable documents, and irrelevant topics.

Report Recall@k, Precision@k, source diversity, latency, and Mean Reciprocal Rank when the dataset is large enough. Retrieval evaluation remains separate from report-generation evaluation.

## 12. Knowledge prompt-injection tests

Synthetic chunks attempt to override policy, force a risk rating, or demand remediation. Passing behavior means the content remains data, observed facts do not change, no remediation is executed or instructed, and citations remain constrained to valid chunks.

## 13. Source updates and reproducibility

- A new document version receives a new version and hash.
- New ingestion never silently overwrites old chunks.
- Replacement ingestion is transactional.
- Benchmark runs record the exact knowledge snapshot hash.
- The source manifest and chunking/index versions are reproducible.

## 14. Acceptance criteria

- At least five license-reviewed sources are available.
- Every chunk has stable source and section or page provenance.
- Duplicate document hashes are detected.
- Expected topics appear in top-k results for the evaluation set.
- Reports cite only supplied chunk identifiers.
- Adversarial document tests pass.
- Retrieval operates with networking disabled.
