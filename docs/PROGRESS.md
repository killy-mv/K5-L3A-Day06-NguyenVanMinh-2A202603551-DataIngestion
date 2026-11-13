# Day 06 - Submission progress

- [x] CP1: Corpus downloaded; valid page IDs, permission, hashes and metadata recorded in `data/manifest.json`.
- [x] CP1: PostgreSQL + pgvector container healthy; dependency environment checked.
- [x] CP2: 20 gold questions with source evidence and a 15 dev / 5 test split.
- [x] CP2: 6 metadata filter cases with 2 in test; immutable split/corpus hashes.
- [x] CP2: Benchmark validator passing; preliminary individual report drafted.
- [x] CP3: PDF ingestion, text normalization, two chunking algorithms and error logs; 9 unit tests pass, reproducible JSONL outputs.
- [ ] CP4: Real embedding model, vector store indexing, A/B/C retrieval and resource measurement.
- [ ] CP5: Top-3 traces, dev/test retrieval measures, coherence / metadata / grounding human audits.
- [ ] CP6: Actual experiment log, final comparisons, failure cases, conclusions, instructions, and submission link.

No test-set retrieval was run during CP1/CP2. Do not change the held-out split based on subsequent scores.
