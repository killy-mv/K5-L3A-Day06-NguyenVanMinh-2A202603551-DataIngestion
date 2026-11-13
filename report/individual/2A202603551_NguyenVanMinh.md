# Bao cao ca nhan - Day 06 Data Ingestion Engineering

- Hoc vien: Nguyen Van Minh
- MSSV: 2A202603551
- Lop: L3A
- Status: CP1-CP6 technical work complete; learner review and final submission pending.

## 1. Du lieu va pipeline

- Chu de: Python fundamentals; Allen B. Downey, *Think Python* 2nd edition v2.4.1, chapters 1-4.
- Nguon: https://greenteapress.com/thinkpython2/thinkpython2.pdf
- Quyen su dung: CC BY-NC 3.0, noncommercial educational use with attribution; see `docs/CP1_SETUP.md`.
- Corpus: 244 physical PDF pages in original file; 38 pages in selected chapters 1-4 (PDF 23-60), of which 35 qualify as useful >=500-character pages (68,585 characters). Pages 38, 50, 60 excluded due to insufficient content. Full page metadata / hash: `data/manifest.json`.
- Python environment: Python 3.14, pypdf 6.21.4, psycopg 3.3.8, Windows Docker Desktop. PostgreSQL 16.16 and pgvector 0.8.7 tested at localhost:55433 using starter `check_setup.py`.
- Metadata planned per chunk: `document_id`, `source`, `page`, and trusted `chapter` to filter among four different chapters. PDF pages must remain traceable.
- Known issues: some extracted special characters are imperfect. No OCR is necessary for the selected text-based corpus.
- Embedding model/provider/dimension/cost: CP4 complete; see section 6 for model, 384 dimensions, zero API charges, and measured timings.

## 2. Cau hinh va benchmark

- A: fixed-size 500 chars with 50 overlap; 170 actual chunks and 170 vector rows; no filter.
- B: paragraph/section-aware 650-char max; 160 actual chunks and 160 vector rows; no filter.
- C: identical chunks and index embedding as B, but `chapter` metadata filter applied only when provided in question; no filter otherwise.
- Benchmark: 20 questions: dev Q01-Q15 (15), test Q16-Q20 (5). Six filter questions (4 dev + 2 test). Every question stores expected answer, exact normalized source evidence, physical PDF page, source ID; files `benchmark/questions.json` and `benchmark/split_lock.json`.
- Pre-test selection policy: maximize dev Evidence Hit@3, then Hit@1, then coherence and resource use. This policy was recorded before any retrieval benchmark.
- Validation: `scripts/validate_benchmark.py` passed exact page evidence, immutable hashes, split and filter rules. **This is not a retrieval score.**

## 3. CP5 - Measured benchmark and five-dimension audit

Selection order: 15 Dev questions (45 searches), then frozen strategy B, then 5 held-out Test questions (15 searches). No Test tuning. Strict scoring requires complete gold evidence in one chunk with matching document ID and physical PDF page.

| Strategy | Dev Hit@1 | Dev Evidence Hit@3 | Test Hit@1 | Test Evidence Hit@3 |
|---|---:|---:|---:|---:|
| A | 4/15 | 9/15 | 0/5 | 2/5 |
| B | 9/15 | 12/15 | 2/5 | 4/5 |
| C | 9/15 | 12/15 | 2/5 | 4/5 |

| Strategy | Coherence (10 chunks, 0-2) | Metadata correct (5 Test x Top3) | Filter compliance | Grounding (5 Test, 0-2) |
|---|---:|---:|---:|---:|
| A | 10/20 (1.0/2) | 15/15 | N/A (no filter) | 7/10 (1.4/2) |
| B | 13/20 (1.3/2) | 15/15 | N/A (no filter) | 9/10 (1.8/2) |
| C | 13/20 (1.3/2) | 15/15 | 6/6 | 9/10 (1.8/2) |

- Selected B on Dev: B/C tied at Evidence Hit@3=12/15 and Hit@1=9/15; identical B/C chunk coherence=1.3/2; B requires no optional filter complexity. Pre-Test selection recorded in `starter/results/cp5_dev_selection.json`.
- Metadata correctness is cross-checked against the original manifest for all retrieved test chunks; Chapter 3/4 filtering in C is independently checked for the two filtered Test questions. A/B filter compliance is not applicable, not a failure.
- Strict failure examples: Q17 A retrieves the right area but splits the three-error-type sentence across chunks; B/C retrieve full evidence. Q20 B/C spread precondition/postcondition responsibilities across separate chunks and thus fail strict whole-quote matching despite partial useful evidence. Source excerpts and full Top3 traces are saved, not inferred from model scores.
- Grounding and coherence labels are **AI-assisted qualitative readings of actual chunk text**, with source IDs, quotes and rationale, not independently human-verified. Learner should review/confirm before claiming a human audit. Grounding evaluates evidence sufficiency, not generated answers.
- Strategy cost comparison: A=170 physical chunks / 76,930 chunk chars; B=160 / 69,744; C reuses B and introduces only retrieval-time chapter filtering. All embeddings are from the same local 384-d model (zero API charges, excluding local CPU/electricity). Cold and warm-cache time measurements must not be conflated. Timing details are in `cp3_statistics.json` and `cp4_run.log`.
- Caveats: 5 Test questions, single textbook, some malformed PDF glyphs; exact-single-chunk matching is deliberately conservative. No broadly generalizable superiority claimed.
- CP5 reproducibility/report evidence: `docs/CP5_EVALUATION.md`, `starter/results/cp5_summary.json`, `cp5_dev_traces.jsonl`, `cp5_test_traces.jsonl`, `cp5_dev_selection.json`, `cp5_coherence_dev.json`, `cp5_metadata_audit.csv`, `cp5_grounding_audit.csv`, `cp5_failure_cases.json`, and `artifacts/experiment_log.csv`.

## 4. AI assistance and verification

AI-assisted drafting and Python scripting were used. Gold evidence is programmatically checked against source PDF pages. CP5 retrieval metrics are measured from saved top-3 traces; coherence/grounding scores are AI-assisted close-reading annotations, clearly disclosed and awaiting independent learner verification.

## 5. CP3 - Ingestion and chunking execution (completed)

- Implemented `starter/src/ingestion.py`, `starter/src/chunking.py` and runnable `starter/src/cp3.py`. Each PDF physical page retains source, document ID, printed/physical page mapping, page ID, and reliable `chapter` for later filtering.
- Layout-mode pypdf extraction; NFKC text normalization; preserved line/paragraph boundaries and no speculative correction of malformed PDF glyphs. The original corpus hash is checked against the frozen manifest. Recorded diagnostics for three short, CP1-excluded pages (38, 50, 60); selected pages extracted successfully.
- Strategy A: fixed-size 500 characters with 50 overlap, 170 chunks, 76,930 total chunk characters, mean 452.53 chars.
- Strategy B: paragraph/heading-aware 650-char maximum, 160 chunks, 69,744 total chunk characters, mean 435.90 chars. C reuses B chunks identically and will apply only retrieval-time chapter filter.
- First execution: 0.728 s text extraction, 0.001 s A chunking, 0.001 s B chunking, 0.737 s total (timings are environment-dependent). Database ingestion/embedding time not measured yet.
- Artifacts: `starter/results/cp3_chunks_A_fixed.jsonl`, `cp3_chunks_B_paragraph.jsonl`, `cp3_page_audit.jsonl`, `cp3_diagnostics.jsonl`, `cp3_statistics.json`, `cp3_run.log`.
- Verification: 9 automated unit tests pass (`starter/tests/test_cp3.py`), two consecutive JSONL builds have matching SHA256, and every chunk has valid page, source and chapter metadata. Full instructions/limitations: `docs/CP3_INGESTION.md`.
- Limitation: fixed windows may cut mid-sentence; paragraph chunks may be very short at section boundaries. This is not yet a coherence or evidence-retrieval score; leave all CP5 manual metrics unfilled.

## 6. CP4 - Real vector storage and smoke retrieval (completed)

- Real embedding: local Sentence Transformers 6.3.0, `sentence-transformers/all-MiniLM-L6-v2` pinned at revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, PyTorch 2.15.0+cpu; model output 384 dimensions, normalized document/query vectors, max sequence length 256 tokens. No paid API used; nominal API charge USD 0, local computation resources excluded.
- Vector store: Docker PostgreSQL 16.16 + pgvector 0.8.7; native vector column, JSONB metadata, source/page/chapter columns, exact cosine similarity, parameterized `chapter` filter.
- A: 170 physical indexed chunks. B: 160 physical indexed chunks. C: reuse B's identical 160 vectors with optional chapter metadata filter during retrieval, no redundant re-embedding. Model/corpus kept constant.
- Initial successful CP4 run recorded 160 B embeddings in 3.184 seconds; A embedding reused its cache from an initial interrupted attempt. Actual database upsert times were 0.109 s for A and 0.090 s for B in that run. Subsequent idempotent rerun reused both caches and preserved row counts without duplicate records or obsolete IDs. Do not present warm-cache times as fresh model generation.
- Smoke test: 2 deliberately non-benchmark prompts x A/B/C, 6 top-3 results. Filtered strategy C returned Chapter 4 matches only, and unfiltered B/C rankings were identical. Query traces with scores and text previews saved under `starter/results/cp4_smoke_traces.json`.
- Automated checks: 12/12 tests passed; locked CP2 benchmark validator also passed. No gold dev/test questions were used for CP4 smoke checks; no Hit@1 or Evidence Hit@3 is claimed yet.
- Recorded evidence: `docs/CP4_VECTOR_STORAGE.md`, `starter/results/cp4_statistics.json`, `cp4_smoke_traces.json`, `cp4_run.log`, `cp4_rerun.log`, `cp4_tests.log`. Embedding cache is local and Git-ignored, but reproducible.


## 7. CP6 - Analysis, conclusion and reproducibility

### Comparison and selection

Dev evidence retrieval improved from 9/15 (A) to 12/15 (B and C); on held-out Test, from 2/5 (A) to 4/5 (B/C). Dev Hit@1 was 4/15 for A against 9/15 for B/C; Test Hit@1 was 0/5 against 2/5. Results came from real 384-dimensional embeddings stored persistently in pgvector, with the same questions, model, and corpus across strategies. Scores strictly require the entire gold quote inside one chunk at the correct physical PDF page and document ID. These scores are not generated-answer accuracy.

For **A vs B**, structure-aware chunking (max 650 characters) preserves evidence better in this sample than fixed windows (500 characters with 50 overlap). For example, Q17 asks for the three kinds of program errors. A returns related chunks but cuts the complete gold statement across windows; B retrieves the statement as rank 1 on physical PDF page 35. B has 160 chunks and 69,744 stored characters; A has 170 chunks and 76,930 stored characters including overlap. This comparison varies chunk size and boundary method as a *single combined chunking strategy change*; it does not isolate size from structure individually.

For **B vs C**, paragraph chunks, embedding model and physical vector index are identical; only the retrieval-time `chapter` filter differs for explicitly scoped questions. C passed 6/6 filter checks across two Test questions, while A and B intentionally had no filter (N/A). However, B and C produced identical strict Hit@1 and Hit@3 scores in the current small benchmark. B was preselected using the frozen Dev selection rule (tie on Hit@3, Hit@1 and coherence, then simpler resources), *before* viewing Test. C remains preferable when strict chapter scoping is essential, even without a measured hit gain.

Q20 is a documented difficult case: B/C retrieve fragments about pre- and postconditions but not the entire gold quote in one chunk, so the strict metric counts failure, while AI-assisted grounding analysis rates partial support. This emphasizes a difference between strict exact-quote retrieval and useful multi-chunk evidence.

### Resource use and limitations

The CP3 original extraction took about 0.728 seconds. CP4 first successful B embedding took 3.184 seconds; A used the cache from an interrupted prior attempt. CP6 independently repeated *real CPU embedding forward passes* (two warmed trials per strategy, in ABBA order): A was 5.6267 and 4.8885 seconds, mean **5.2576 seconds**; B was 4.5036 and 4.6078 seconds, mean **4.5557 seconds**. Model initialization took 13.5631 seconds and is excluded from those means, as are database/installation times. C adds no physical embedding storage or CPU pass beyond B. API cost was **USD 0**, excluding local machine/electricity/storage. These small timing samples do not support broad performance claims.

Limitations: single book and 35 content pages, only five held-out Test questions, some PDF font extraction artifacts, strict evidence matching that rejects alternative or split evidence, and AI-assisted coherence/grounding scores that have **not** been independently human-validated. Future work: larger independent benchmark, source-diverse corpora, multi-chunk and paraphrased-evidence assessment, better glyph cleanup and OCR for scanned PDFs, and attention to the embedding model's 256-token limit. Do not tune the already-seen Test then claim it is held out.

### Final audit and AI disclosure

Full source and immutable traces remain at `starter/results/cp5_*`. CP6 resource evidence: `starter/results/cp6_resource_measurement.json`; final artifact integrity/secret-pattern audit: `scripts/final_audit.py` and `starter/results/cp6_submission_audit.json`. Reproduction and completion checklist: `README.md`, `SUBMISSION.md`, and `docs/CP6_FINAL_REVIEW.md`. ChatGPT assisted source review, code generation, benchmark authoring, chunk coherence and grounding assessment, and document drafting. Automated retrieval and metadata checks ran on the local machine; qualitative scores are transparent AI-assisted judgments requiring the student's confirmation if independent manual audit is requested. Repository publication does not prove submission to the instructor.
