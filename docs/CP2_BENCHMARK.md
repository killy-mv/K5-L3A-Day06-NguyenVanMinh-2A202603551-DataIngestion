# CP2 - Question benchmark and verified source evidence

**Status:** CP2 benchmark constructed, split frozen, and static source validation passing. No embedding, retrieval scores or human scoring has yet been run.

## Content selection

The benchmark uses a single primary document, *Think Python 2e*, chapters 1-4 (35 qualifying pages). Questions mix definitions, rephrasings, examples and conditional / exception scenarios across topics in all four chapters. Each gold evidence quote was extracted from the matching PDF physical page and verified against extracted text after NFKC + whitespace normalization; required contextual meaning was checked while drafting the answer. Full gold and split are stored under `benchmark/`.

- Dev (15): Q01-Q15. Used to select and compare A/B/C.
- Test (5): Q16-Q20. Held out until the strategy choice is fixed.
- Filters: Q01, Q07, Q12, Q14 (dev); Q18, Q20 (test). Only `chapter` filter is used, from the chapter scope in the question. No gold source/page is passed into a filter.
- Source identifiers: `gold_source_id=thinkpython2_pdf`, `gold_page` is 1-based **PDF physical page**, `gold_printed_page` is the book-printed page number.

## Freeze and audit

The corpus hash and canonical JSON benchmark hash are recorded in `benchmark/split_lock.json`. `scripts/validate_benchmark.py` checks against actual source PDF contents, page manifest, fixed split, and filter values. Do not regenerate the benchmark or adjust test after examining retrieval output. Original builder intentionally refuses overwriting.

Selection criteria frozen **before viewing test**: highest Evidence Hit@3 on 15 dev questions; ties resolve by dev Hit@1, then coherence, then ingestion resource use. Report all three configurations on dev and test separately after selection is locked.

## Risks and limitations

- Just 5 test questions: high variance, no generalization claim.
- Single book, single author, English language: narrow scope.
- Some PDF glyphs extract imperfectly, especially punctuation and kerning; check evidence visually in disputes.
- Gold evidence verified against PDF text is **not** proof of retrieval performance or manual grounding scores. CP5 will perform those checks.
