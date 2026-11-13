# Bao cao ca nhan - Day 06 Data Ingestion Engineering

- Hoc vien: Nguyen Van Minh
- MSSV: 2A202603551
- Lop: L3A
- Status: CP1 through CP4 complete; CP5-CP6 pending. This document will be updated as experiments are actually run.

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

## 3. Ket qua retrieval (pending CP5; CP4 storage measured separately)

| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunk count | Time | Cost |
|---|---|---|---|---|---|---|
| A | dev/test | Pending | Pending | Pending | Pending | Pending |
| B | dev/test | Pending | Pending | Pending | Pending | Pending |
| C | dev/test | Pending | Pending | Pending | Pending | Pending |

| Strategy | Coherence mean /2 (n) | Metadata correct (n/N) | Filter compliance | Grounding 0/1/2 counts, mean /2 |
|---|---|---|---|---|
| A | Pending | Pending | Pending | Pending |
| B | Pending | Pending | Pending | Pending |
| C | Pending | Pending | Pending | Pending |

- Trace path and human audit labels: Pending CP5.
- Data strategy analysis, failure case examples, limitations and conclusion: Pending actual experiments.

## 4. AI assistance and verification

AI-assisted drafting and Python scripting were used. Gold evidence is programmatically checked against source PDF pages. Manual review of retrieved evidence will be recorded in CP5. No retrieval or human audit metrics are claimed yet.

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
