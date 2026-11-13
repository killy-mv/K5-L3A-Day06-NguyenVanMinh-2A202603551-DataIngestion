# CP5 - Frozen benchmark evaluation (2026-11-13)

## Protocol and integrity

- Corpus and gold question SHA256 validated against CP1/CP2 locks; all model and database parameters unchanged from CP4.
- Dev: Q01-Q15, queried first (45 queries, top-3 each). Results saved **before** strategy selection.
- Precommitted decision rule: maximize dev Evidence Hit@3, then Hit@1, then ten-position coherence, then cost/resource. B and C tied on the first two metrics; identical B/C chunks also imply identical coherence. B was chosen as the simpler implementation without the optional metadata-filter step. Selection, metrics and source hashes were frozen in `starter/results/cp5_dev_selection.json` before Test was run.
- Test: Q16-Q20, 15 queries (5 x 3 configurations) after freeze. Held-out test was not used for selection or tuning.
- All 60 query results include ranked top-3 *full text*, cosine similarity, PDF page, chapter, chunk ID, metadata, source, gold evidence and per-result strict evidence matches.
- Exact scoring: Hit@1 = first chunk is from the gold source+physical PDF page **and contains the entire normalized gold quote**. Evidence Hit@3 = any of top-3 meets that condition in one chunk. This is deliberately strict and yields false negatives when useful evidence is distributed across chunks or equivalent words differ. Matching page alone is insufficient. No semantic/human equivalence adjustments were used.

## Measured retrieval results

| Strategy | Dev Hit@1 | Dev Evidence Hit@3 | Test Hit@1 | Test Evidence Hit@3 |
|---|---:|---:|---:|---:|
| A: fixed-size 500, overlap 50 | 4/15 (26.7%) | 9/15 (60%) | 0/5 (0%) | 2/5 (40%) |
| B: paragraph max 650 | 9/15 (60%) | 12/15 (80%) | 2/5 (40%) | 4/5 (80%) |
| C: B + optional `chapter` filter | 9/15 (60%) | 12/15 (80%) | 2/5 (40%) | 4/5 (80%) |

Selection B is specific to this tiny English-book benchmark. No generalized superiority can be inferred. C's filters can change ranking on scoped queries, but no additional exact evidence hits were observed here.

## The five required dimensions

**1. Hit@1 / Evidence Hit@3:** Exact n/N and percentages by strategy and split above; detailed per-question checks in `starter/results/cp5_dev_traces.jsonl`, `cp5_test_traces.jsonl` and machine summary `cp5_summary.json`.

**2. Chunk coherence:** Ten source pages chosen for direct comparison: PDF physical pages 23, 26, 31, 34, 39, 42, 46, 51, 55, 58. For each strategy, the centered chunk by index on that page was reviewed. Rubric 0=fragment/no standalone meaning, 1=partially coherent, 2=coherent. A=10/20 (1.0/2); B=C=13/20 (1.3/2). Source text excerpts, chunk IDs, labels and per-item rationale saved to `cp5_coherence_dev.json`, created before the Test benchmark. Examples: the B chunk on page 31 is an isolated Figure 2.1 reference (0); B page 34 starts at the string-operations section and retains examples (2). **AI-assisted close reading, not independent human annotation**; manual confirmation is recommended before presenting this as human-labeled coursework.

**3. Metadata accuracy:** For the same five test questions, inspect the three returned chunks in each strategy (15 records per strategy). Verify `source`, `document_id`, physical `page`, `chapter`, `page_id` against the frozen CP1 manifest, not the gold answer. Result A 15/15, B 15/15, C 15/15. For C's two filter-scoped test questions Q18 and Q20, 6/6 returned chunks have the requested chapter. A/B intentionally have no filter; filter compliance is **N/A**, not zero. Row-level record: `cp5_metadata_audit.csv`.

**4. Grounding quality:** AI-assisted close reading of top-3 evidence for all five test questions and all strategies, scored 0=insufficient, 1=partial/scattered, 2=sufficient and clear. A 7/10 = 1.4/2 (2 rated 2, 3 rated 1); B/C 9/10 = 1.8/2 (4 rated 2, 1 rated 1). Each question/strategy has real chunk IDs, score, and rationale in `cp5_grounding_audit.csv`. **This evaluates only available evidence, not an LLM's generated answer.** These ratings are not claimed to be independent human evaluation and must be confirmed by the learner where required.

**5. Strategy impact/cost/tradeoffs:** A used 170 physical chunks / 76,930 stored chunk characters, B/C 160 / 69,744; C reuses B's vectors, adding only optional SQL filtering. All used the same 384-d local MiniLM model and pgvector exact cosine search. API embedding cost was USD 0, CPU/electricity not included. CP3 extraction initially ~0.728s, A chunking ~0.001s, B chunking ~0.001s. CP4 initial successful run encoded 160 B chunks in ~3.184s and upserted A/B in ~0.109/0.090s; A embeddings were cached following an interrupted attempt. Warm-cache reruns must **not** be compared as full fresh embedding costs. CP5 trace files include per-query SQL retrieval times; initial local data is small and retrieval timings are not general performance benchmarks. See `cp3_statistics.json`, `cp4_run.log`, `cp4_rerun.log`, and `artifacts/experiment_log.csv`.

## Failure analysis

- Q17 (three error types): A retrieves related content on pages 35/36 but none of the top three contains the *complete gold sentence* in one fixed chunk; strict Evidence Hit@3 fails. B/C each have the full sentence in their top-1 paragraph chunk and pass.
- Q18 (void functions): A retrieves relevant glossary/function chunks without the complete example from gold page 46; B/C retrieve the source example and pass at rank 1.
- Q20 (preconditions versus postconditions): even B/C split relevant responsibilities across paragraph chunks on page 58. Single-chunk full-gold-evidence scoring fails, although multiple hits can support parts of the answer; grounding audit marks partial rather than calling it absent.
- Real cases and all failures are enumerated with top-3 chunk IDs and retrieved page numbers in `cp5_failure_cases.json`.
- Metadata filter added no exact-hit gain in this small test; it guarantees scope compliance when a chapter constraint exists, but the test should not imply filtering never helps.

## Run instructions, repeatability and restrictions

From `starter/` after CP3 and CP4:

```bash
.venv/Scripts/python.exe -m src.run --stage dev
.venv/Scripts/python.exe -m src.cp5_audit
.venv/Scripts/python.exe -m src.run --stage freeze
.venv/Scripts/python.exe -m src.run --stage test
.venv/Scripts/python.exe -m src.cp5_finalize
.venv/Scripts/python.exe -m unittest discover -s tests -v
```

**The dev/test pipeline intentionally refuses to overwrite traces or pre-test selection.** For an independent clean re-run, first archive the existing artifacts into a dated experiment folder; then remove only `starter/results/cp5_*` in a fresh working copy, preserving corpus/gold locks and the precommitted selection rule. Never recompute Test-based tuning and call it independent. Rebuild `artifacts/experiment_log.csv` with `starter/.venv/Scripts/python.exe scripts/write_cp5_experiment_log.py` from repository root.

## Artifacts for submission

- `starter/src/evaluation.py`, `starter/src/cp5.py`, `starter/src/cp5_audit.py`, `starter/src/cp5_finalize.py`, `starter/src/run.py`, `starter/tests/test_cp5.py`.
- `starter/results/cp5_dev_traces.jsonl`, `cp5_test_traces.jsonl`: full 60x3 ranked hits with text, score, metadata, gold verification.
- `starter/results/cp5_dev_metrics.json`, `cp5_test_metrics.json`, `cp5_dev_selection.json`, `cp5_summary.json`.
- `starter/results/cp5_coherence_dev.json`, `cp5_metadata_audit.csv`, `cp5_grounding_audit.csv`, `cp5_failure_cases.json`, `cp5_dev_run.log`, `cp5_test_run.log`, `cp5_tests.log`.
- `artifacts/experiment_log.csv`: A/B/C measured values.

Limitations: one English book, one local model, small 5-question Test, strict exact quote scoring, AI-assisted qualitative labels. No fabricated experiments or unsupported human-review claim.
