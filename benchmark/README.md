# Day 06 - CP2 benchmark

This benchmark was authored and locked **before any retrieval experiments**. Do not edit the gold questions or the held-out test split after seeing retrieval results. If a defect is found, document it and create a new benchmark version; do not claim the old test set is independent after tuning.

## Files

- `questions.json`: 20 questions, each with ID, split, type, question, expected answer, gold source/page/page ID, normalized evidence quote, and optional input filter.
- `split_lock.json`: immutable corpus + canonical benchmark hashes, dev/test IDs and selection rule.
- `../scripts/build_benchmark.py`: original one-time seed construction; intentionally refuses to overwrite existing benchmark files.
- `../scripts/validate_benchmark.py`: read-only validation of hashes, page provenance, evidence and metadata filter.

## Counts and methodology

- Dev: Q01-Q15 (15 questions), test: Q16-Q20 (5 questions).
- Direct / paraphrase / conditional types are recorded per question.
- Six chapter-filter questions: Q01, Q07, Q12, Q14, Q18, Q20. Test filters: Q18 and Q20. Chapter metadata comes from source PDF boundaries in `data/manifest.json`.
- Filter is derived from the explicitly scoped chapter in the *question*, not from `gold_page` or an injected gold source ID. For unfiltered questions strategy C must use no filter.
- Fixed selection rule (before test): maximize dev Evidence Hit@3, break ties using dev Hit@1, then manual coherence, then resource use. Compare final dev-selected strategy on held-out test; **do not tune using test**.
- Verification checks exact evidence substring after Unicode NFKC and whitespace normalization, matching source PDF physical page. This establishes provenance, not embedding retrieval accuracy; answers were authored from their cited passages. Some PDF glyphs extract imperfectly; inspect actual PDF in case of disputed evidence.
- Question language is English to match the source corpus. All strategies must use the same question wording and gold labels.
- A qualifying hit requires a retrieved chunk matching a permitted gold source/page **and containing enough evidence for the answer**; matching just the page is not sufficient. Manual equivalence can be accepted if explicitly documented.

## Check

From repository root with CP1 Windows venv installed:

```bash
starter/.venv/Scripts/python.exe scripts/validate_benchmark.py
```

Expected: `PASS: 20 unique, source-verified questions | 15 dev / 5 test | 6 filters (2 test)`.
