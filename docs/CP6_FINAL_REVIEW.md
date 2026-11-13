# CP6: Final review and submission handoff

Date: 2026-11-13. Status: All CP1-CP6 technical artifacts prepared and reviewed; independent learner confirmation of qualitative labels and actual course submission remain open.

## Reproducibility

- Corpus: Allen B. Downey, *Think Python*, edition 2, CC BY-NC 3.0 (attribution and noncommercial restrictions apply), source and permission recorded in `data/manifest.json` and `docs/CP1_SETUP.md`.
- Source: 35 qualifying content pages from chapters 1-4, SHA256-verified PDF; metadata document_id, source, physical page and chapter.
- Runtime: Python 3.14 on Windows, Docker Desktop with PostgreSQL 16 + pgvector 0.8.7, Sentence Transformers `all-MiniLM-L6-v2` at pinned revision, 384-d CPU embeddings.
- A fixed 500 characters with overlap 50: 170 chunks. B paragraph/heading max 650: 160 chunks. C reuses B's vectors and adds optional chapter filtering at retrieval time.
- Dev Q01-Q15 was queried first, B chosen and frozen, then Test Q16-Q20. Selection lock at `starter/results/cp5_dev_selection.json`; full traces in `cp5_dev_traces.jsonl` and `cp5_test_traces.jsonl`.

## Results

| Strategy | Dev Hit@1 | Dev Evidence Hit@3 | Test Hit@1 | Test Evidence Hit@3 |
|---|---:|---:|---:|---:|
| A | 4/15 | 9/15 | 0/5 | 2/5 |
| B | 9/15 | 12/15 | 2/5 | 4/5 |
| C | 9/15 | 12/15 | 2/5 | 4/5 |

- Strict scorer: a hit requires matching source, physical PDF page, and full normalized gold evidence in one chunk. A semantically equivalent paraphrase or evidence split across chunks is not credited.
- Coherence (AI-assisted, 10 fixed source positions): A 1.0/2, B/C 1.3/2. Metadata verified against manifest: 15/15 returned test chunks per strategy, all correct. C scoped-test filter compliance: 6/6; A/B filter not applicable. Grounding (AI-assisted, 5 test questions each): A 1.4/2, B/C 1.8/2.
- All sample text, chunk identifiers and annotation explanations are in `starter/results/cp5_coherence_dev.json`, `cp5_metadata_audit.csv`, `cp5_grounding_audit.csv`. Qualitative labels are **AI-assisted, not independently human-verified**; leave the manual review checkbox pending until learner confirms.
- A to B: chunking changes boundaries and size together, which improves full-quote retrieval here. Q17 retrieves the whole three-errors sentence on B but splits it on A. B to C: only an optional retrieval-time filter changes, with identical embeddings and chunking. No additional correct evidence hits here. Q20 fails strict whole-quote matching on B/C because evidence is distributed across chunks even though some relevant parts are retrieved.

## Time and resource estimates

- Original CP3 PDF extraction ~0.728s; each chunker ~0.001s. CP4 initial successful B embedding ~3.184s; initial A vectors had been cached from interrupted run. Database A/B upsert ~0.109s/0.090s in that run. Do not equate warm cache cost with full fresh embedding.
- CP6 measured two real **warmed, in-process** CPU embedding trials per strategy, ABBA order: A 5.6267s and 4.8885s (mean **5.2576s**), B 4.5036s and 4.6078s (mean **4.5557s**). C reuses B. Initial model load measured 13.5631s, excluded from these means. CPU, electricity and storage are not free, but embedding API charge was USD 0. This is not a strong performance benchmark.
- Read raw timings and measurement boundaries in `starter/results/cp6_resource_measurement.json`.

## Limitations and improvements

One English textbook, five held-out test questions, imperfect PDF glyph extraction, strict exact-evidence metric, and AI-assisted qualitative assessment limit generality. Improvements for future experiments include manually verified equivalent evidence judgments, multi-chunk coverage, diverse corpora, larger independent test sets, better OCR/glyph handling, and model token-length monitoring. Do not optimize using this already-seen Test set and then represent it as independent.

## Final audit and hand-in files

- Required hand-in: `README.md`, `STUDENT.md`, `data/`, `benchmark/`, `starter/src/`, `starter/tests/`, `starter/results/`, `artifacts/experiment_log.csv`, and `report/individual/2A202603551_NguyenVanMinh.md`.
- `scripts/final_audit.py` verifies immutable hashes, counts, trace integrity, scores, artifact presence, tracked-file ignore rules, and common secret patterns. Result in `starter/results/cp6_submission_audit.json`.
- Read `README.md` for exact setup/re-run instructions; the CP5 scripts refuse overwriting frozen runs, so archive existing CP5 artifacts and use a fresh worktree for a clean experiment rerun.
- Remaining learner steps: verify AI-assisted qualitative labels; confirm course/public repository reuse policy for CC BY-NC document and excerpts; commit/push CP6 changes; submit the repository link to the class platform. Repository HTTP 200 was checked, which does **not** prove submission to the instructor.
