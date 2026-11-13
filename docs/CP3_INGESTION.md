# CP3 - PDF ingestion and chunking (verified)

## Scope and execution

- Corpus remains frozen from CP1: 35 qualifying pages of *Think Python 2e*, PDF physical pages within 23-60. Do not alter CP2 gold or split.
- Entry point (from the `starter/` directory): `.venv/Scripts/python.exe -m src.cp3` on Windows / Git Bash. Dependencies in `starter/requirements.txt`.
- Automated tests (from `starter/`): `.venv/Scripts/python.exe -m unittest discover -s tests -v`.
- No need for the database yet; real embeddings and pgvector ingest will be implemented in CP4. `src.run` remains an unfinished full-pipeline entry point.

## Ingestion decisions

1. Validate original PDF's SHA256 against `data/manifest.json`, require exactly the 35 selected pages and reject unexpected changes.
2. Read PDF with pypdf layout-mode extraction, tracking one-based physical PDF page number and associated printed page; Unicode NFKC normalization, normalized whitespace, preserved line/blank-line boundaries. Deliberately avoid lossy guesses about PDF line-end hyphenation and broken font glyphs.
3. Each `DocumentPage` retains `document_id`, source URL, PDF page number, chapter, page ID and source-text SHA256. Filter field `chapter` is grounded in the CP1 manifest.
4. Capture structured diagnostics for empty pages, replacement glyphs, extraction failures and previously excluded CP1 pages. OCR is not applied to the text-based corpus. Extracted font glyphs may still be imperfect; CP2 evidence needs source verification.

## Controlled chunk strategies

- A: fixed 500-character windows, overlap 50 characters; trailing partial windows included; never merge across physical PDF pages.
- B: paragraph-aware / section-heading-aware: split at blank lines, group within max 650 characters, split oversize paragraphs on sentence or word boundary as available, without deliberate overlap; never merge across physical pages.
- C will reuse **the exact same B chunks/embeddings**; only the retrieval-time `chapter` filter changes. Do not index a third distinct chunk corpus unless necessary for backend bookkeeping.
- Each `Chunk` retains source URL, `document_id`, page number, page ID, `chapter`, chunk index, length, and a deterministic hash-based stable chunk ID. Rebuilding unchanged source with unchanged settings reproduces the same IDs and JSONL files.

## Actual measured execution

See `starter/results/cp3_statistics.json` for the definitive machine-generated numbers and times. Initial execution reported:

| Measure | Strategy A | Strategy B |
|---|---:|---:|
| Chunk count | 170 | 160 |
| Max length | 500 | 650 |
| Mean length | 452.53 | 435.90 |
| Median length | 500 | 506 |
| Short chunks under 100 chars | 5 | 13 |
| Total stored chunk chars | 76,930 | 69,744 |

Initial CP3 timings: PDF extraction ~0.728 s, fixed chunking ~0.001 s, paragraph chunking ~0.001 s, entire execution ~0.737 s; times vary by run/hardware. Content was recovered from 35 pages, 8 / 7 / 11 / 9 pages per chapter.

A includes deliberate overlap and therefore more duplicated characters. B has some short fragments, including headers and residual paragraphs; assess coherence and grounding with the same precommitted evaluation sample in CP5 instead of assuming B is superior.

## Generated hand-in evidence

- `starter/results/cp3_chunks_A_fixed.jsonl`: all 170 complete A chunks, including text and metadata.
- `starter/results/cp3_chunks_B_paragraph.jsonl`: all 160 complete B chunks, including text and metadata; C reuses B.
- `starter/results/cp3_page_audit.jsonl`: page-level chapter, sizes, issue counts and counts of A/B chunks.
- `starter/results/cp3_diagnostics.jsonl`: three short CP1-excluded pages; no failed extraction for selected pages. A separate test proves an actual empty PDF page generates an `EMPTY_PAGE` diagnostic.
- `starter/results/cp3_statistics.json`: summary, effective parameters, versions and per-stage timings.
- `starter/results/cp3_run.log`: captured original stdout from the most recent run.
- `starter/tests/test_cp3.py`: nine automated tests for input validation, normalization, reproducibility, chunk boundaries, metadata separation, PDF page integrity and empty-page logging.

## Limits

This is a data-preparation milestone, not a retrieval or quality benchmark. No embedding model, query top-3, Hit@1/3, coherence, metadata audit, or grounding ratings have been measured. They must remain pending. Runtime comparison above excludes network embedding and DB ingestion, which will be measured separately.
