# CP4 - Real embeddings and vector retrieval (verified)

## Run and re-run

From repo root, Docker Desktop must be running. The `starter/` directory contains `.env` (ignored by Git) with `DATABASE_URL` pointing at local pgvector. Run:

```bash
cd starter
.venv/Scripts/python.exe -m pip install -r requirements.txt
docker compose -p day6_student_starter up -d --wait
.venv/Scripts/python.exe scripts/check_setup.py
.venv/Scripts/python.exe -m src.cp3
.venv/Scripts/python.exe -m src.cp4
.venv/Scripts/python.exe -m unittest discover -s tests -v
```

Python was executed on Windows 3.14 with a local virtual environment. The `python` Microsoft Store alias was not used. A local pre-cached Hugging Face model was used. The first-time download may require Internet connectivity; none of the PDF contents were sent to an embedding API.

## Model details

- Embedding backend: local `sentence-transformers` 6.3.0, PyTorch 2.15.0+cpu.
- Model: `sentence-transformers/all-MiniLM-L6-v2` pinned to Hugging Face commit `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.
- 384-dimensional output; mean-pooling model loaded by SentenceTransformer. 256-token model maximum sequence length; excess input tokens may be truncated by the tokenizer. This is a limitation of the model and requires caution when interpreting missing evidence.
- All documents and queries are encoded with the same model / `encode()` recipe, CPU-only, normalized to unit vectors; no random / TF-IDF fallback.
- Embedding API charges: 0 USD (local CPU; electricity and hardware excluded).

## Vector database design

- Backend: PostgreSQL 16.16 with pgvector 0.8.7 using Docker Desktop, host `127.0.0.1:55433`.
- Table `day6_embeddings`: `strategy`, `chunk_id` (composite primary key), `model_name`, `document_id`, `source`, physical PDF `page`, `chapter`, full `content`, JSONB `metadata`, `embedding` (native pgvector).
- Table `day6_embedding_config`: model and vector dimensionality guard, rejecting incompatible model changes in an existing index.
- Physical datasets: A=170 fixed chunks and B=160 paragraph chunks. C is a logical retrieval strategy: **same physical B embeddings**, with a parameterized SQL `chapter` filter only when requested. C has 160 logical chunks, not a separately embedded third dataset.
- Metric: cosine distance via pgvector `<=>` and reported score `1 - distance`. Exact search (sequential scan), **no approximate ANN index**. SQL parameterization is used for metadata values and query vectors.
- Upsert is deterministic and idempotent by `(strategy,chunk_id)`. On rerun, update matching chunks and remove stale chunk IDs within that strategy. Validation rejects vector dimension mismatch, NaN/infinity, zero vectors, absent source metadata and duplicate chunk IDs. Model/dimension changes are rejected rather than silently mixed.
- A and B indexes use the same 384-d model and database; the model is loaded once per run.

## Actual checks

- Both physical indexes successfully populated with 170 + 160 **real embeddings** and remained queryable after process exit/reconnection.
- Two *smoke-only* queries were executed against A, B and C, yielding six runs of ranked top-3 matches with text previews, similarity scores, page metadata and filter context.
- C obeyed the Chapter 4 filter when provided; for an unfiltered query, B and C returned identical ordered chunk IDs.
- A second execution had both embedding caches hit, `obsolete_removed = 0` and indexed row counts unchanged at A=170/B=160.
- The 12 automated tests (9 CP3 + 3 CP4) passed against the live database, including real CPU embedding generation and filter/negative cases.
- The locked CP2 benchmark revalidated without changes. **None of the 20 frozen dev/test questions was used in CP4 smoke queries.** Evidence metrics and human audit remain CP5 work.

## Artifacts

- `starter/results/cp4_statistics.json`: most recent run, exact model configuration, row counts, timing, costs and smoke status.
- `starter/results/cp4_smoke_traces.json`: all six smoke retrievals (top-3 IDs, scores, pages, brief text previews).
- `starter/results/cp4_run.log`: first successful CP4 execution output (copied from initial run below if preserved) or most recent captured run.
- `starter/results/cp4_rerun.log`: repeat execution, proving index idempotency and cache reuse.
- `starter/results/cp4_tests.log`: successful integration and unit tests.
- `starter/.cache/`: optional local embedding cache, ignored by Git; immutable signature includes model revision, chunk IDs and text hashes. This directory can be removed to rebuild all vectors.

## Known limits and future tasks

- Timing values on a warm cache do **not** measure fresh model embedding cost. The initial successful run had A cached after an interrupted run, but B embedded 160 chunks in ~3.184 seconds. Reproduce fresh measurement by deleting local cache and rerunning if needed. No cross-hardware extrapolation.
- The two smoke prompts are not a benchmark and their results do not establish Hit@1/Hit@3, coherence, or grounding.
- The full `python -m src.run` entry point and `src/evaluation.py` remain pending CP5. Run `src.cp4` for CP4 only.
- If changing embedding model or dimensions, reset/recreate the dedicated day6 tables only after preserving evidence; do not delete the PostgreSQL volume casually.
