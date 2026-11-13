"""Run CP3 only: page extraction + A/B chunking; no retrieval or test tuning."""
from __future__ import annotations

import json
import logging
import statistics
import time
from collections import Counter
from pathlib import Path
from typing import Any

import pypdf

from .chunking import by_paragraph, fixed_size
from .ingestion import load_corpus
from .models import Chunk

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / 'starter/results'
MANIFEST = ROOT / 'data/manifest.json'
A_SIZE, A_OVERLAP, B_MAX_SIZE = 500, 50, 650


def _jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in records), encoding='utf-8')


def _chunk_record(chunk: Chunk) -> dict[str, Any]:
    return {'chunk_id': chunk.chunk_id, 'document_id': chunk.document_id,
            'source': chunk.source, 'page': chunk.page,
            'text': chunk.text, 'metadata': chunk.metadata}


def _summary(chunks: list[Chunk]) -> dict[str, Any]:
    lengths = [len(c.text) for c in chunks]
    return {'chunk_count': len(chunks), 'total_chunk_characters': sum(lengths),
            'min_chars': min(lengths), 'max_chars': max(lengths),
            'mean_chars': round(statistics.mean(lengths), 2),
            'median_chars': statistics.median(lengths),
            'under_100_chars': sum(x < 100 for x in lengths)}


def main() -> None:
    started = time.perf_counter()
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    diagnostics: list[dict[str, Any]] = []
    t0 = time.perf_counter()
    pages = load_corpus(MANIFEST, diagnostics=diagnostics)
    parse_s = time.perf_counter() - t0
    t1 = time.perf_counter()
    fixed = [c for p in pages for c in fixed_size(p, A_SIZE, A_OVERLAP)]
    fixed_s = time.perf_counter() - t1
    t2 = time.perf_counter()
    structured = [c for p in pages for c in by_paragraph(p, B_MAX_SIZE)]
    structured_s = time.perf_counter() - t2
    for strategy, chunks in [('A', fixed), ('B', structured)]:
        if not chunks or len({c.chunk_id for c in chunks}) != len(chunks):
            raise RuntimeError(f'{strategy}: missing or duplicate chunk IDs')
        for chunk in chunks:
            if chunk.metadata.get('chapter') not in {'chapter_1','chapter_2','chapter_3','chapter_4'}:
                raise RuntimeError(f'Missing chapter on chunk {chunk.chunk_id}')
            if not chunk.source or not chunk.page or not chunk.metadata.get('page_id'):
                raise RuntimeError(f'Missing provenance on chunk {chunk.chunk_id}')
    if max(len(c.text) for c in fixed) > A_SIZE or max(len(c.text) for c in structured) > B_MAX_SIZE:
        raise RuntimeError('Chunk size cap violated')
    RESULTS.mkdir(parents=True, exist_ok=True)
    _jsonl(RESULTS / 'cp3_chunks_A_fixed.jsonl', [_chunk_record(c) for c in fixed])
    _jsonl(RESULTS / 'cp3_chunks_B_paragraph.jsonl', [_chunk_record(c) for c in structured])
    _jsonl(RESULTS / 'cp3_diagnostics.jsonl', diagnostics)
    _jsonl(RESULTS / 'cp3_page_audit.jsonl', [
        {'document_id': p.document_id, 'source': p.source, 'pdf_page': p.page,
         'page_id': p.metadata['page_id'], 'chapter': p.metadata['chapter'],
         'printed_page': p.metadata['printed_page'],
         'normalized_char_count': len(p.text),
         'replacement_glyphs': p.text.count('\ufffd'),
         'A_chunks': sum(c.page == p.page for c in fixed),
         'B_chunks': sum(c.page == p.page for c in structured)} for p in pages])
    summary = {
        'stage': 'CP3_data_ingestion_chunking_only', 'source_id': manifest['source_id'],
        'source_sha256': manifest['sha256'], 'pdf_total_pages': manifest['pdf_total_physical_pages'],
        'selected_pages': len(pages), 'excluded_pages': [x['pdf_page'] for x in manifest['excluded_in_selected_range']],
        'normalized_characters': sum(len(p.text) for p in pages),
        'chapter_pages': dict(sorted(Counter(p.metadata['chapter'] for p in pages).items())),
        'extraction_mode': 'pypdf_layout', 'normalization': 'Unicode NFKC, whitespace; preserve line/paragraph breaks, no dehyphenation',
        'pypdf_version': pypdf.__version__,
        'A': {'method': 'fixed', 'size': A_SIZE, 'overlap': A_OVERLAP, **_summary(fixed)},
        'B': {'method': 'paragraph', 'max_size': B_MAX_SIZE, **_summary(structured)},
        'C': {'method': 'same B chunks and vectors; apply chapter filter only at retrieval time (CP4)',
              'same_as_B': True, 'chunk_count': len(structured)},
        'diagnostic_counts': dict(Counter(d['code'] for d in diagnostics)),
        'timing_seconds': {'extract': round(parse_s, 3), 'fixed_chunking': round(fixed_s, 3),
                           'paragraph_chunking': round(structured_s, 3),
                           'total': round(time.perf_counter() - started, 3)},
        'note': 'No embedding, vector search, Hit@1/3 or manually scored quality in CP3.'}
    (RESULTS / 'cp3_statistics.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    logging.getLogger('pypdf').setLevel(logging.ERROR)
    main()
