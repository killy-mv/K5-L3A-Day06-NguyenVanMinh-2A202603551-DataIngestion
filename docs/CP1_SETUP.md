# CP1 - Data and environment setup (2026-11-13)

Status: Complete and tested locally. No embedding or benchmark execution claimed.

## Corpus and rights

- Allen B. Downey, *Think Python*, 2nd edition, v2.4.1.
- Source PDF: https://greenteapress.com/thinkpython2/thinkpython2.pdf
- License evidence: https://greenteapress.com/wp/think-python-2e/
- CC BY-NC 3.0: noncommercial reuse, attribution required. Educational lab use only.
- Local copy: `data/source/thinkpython2.pdf`. SHA256 and full source recorded in `data/manifest.json`.
- Pages: PDF physical pages 23-60 (chapters 1-4), counting only pages with at least 500 normalized extractable characters. The manifest records each included/excluded page, page IDs, character counts, printed page, and chapter.
- Grounded filter metadata: `chapter` with 4 distinct chapter labels sourced from actual PDF chapter boundaries.
- Extraction caveat: a few special glyphs extract imperfectly, so manually verify benchmark evidence against source pages.
- To rebuild: from repository root run `starter/.venv/Scripts/python.exe scripts/prepare_corpus.py` in Git Bash.

## Environment

- Windows + Docker Desktop; Python 3.14 via `py -3.14`. Windows Store `python` alias does not resolve here; use the venv executable.
- Run from `starter/`: `py -3.14 -m venv .venv`, `.venv/Scripts/python.exe -m pip install -r requirements.txt`, `cp .env.example .env`.
- Start: `docker compose -p day6_student_starter up -d --wait`.
- Check: `.venv/Scripts/python.exe scripts/check_setup.py` -> `Setup OK`.
- Verified running: PostgreSQL 16.16, pgvector 0.8.7 at 127.0.0.1:55433.
- Stop without data loss: `docker compose -p day6_student_starter stop`.

## CP2 handoff

Write 20+ evidence-verified questions with fixed 15 dev / 5 test split **before** running retrieval. Include 3+ `chapter` filter questions, including 1+ on test. Use pages present in manifest and never inject gold source IDs into search filters.
