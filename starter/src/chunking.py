"""Page-preserving, deterministic fixed and structure-aware chunking (CP3)."""
from __future__ import annotations
import hashlib
import re
from .models import Chunk, DocumentPage


def _chunk(page: DocumentPage, method: str, i: int, text: str, **extra: int | str) -> Chunk:
    if not text.strip():
        raise ValueError('Cannot generate empty chunk')
    fingerprint = hashlib.sha256(
        f'{page.document_id}|{page.page}|{method}|{i}|{text}'.encode('utf-8')
    ).hexdigest()[:20]
    return Chunk(chunk_id=f'{method}-{fingerprint}', document_id=page.document_id,
                 source=page.source, page=page.page, text=text,
                 metadata={**page.metadata, 'chunk_method': method, 'chunk_index': i,
                           'chunk_char_count': len(text), **extra})


def fixed_size(page: DocumentPage, size: int, overlap: int) -> list[Chunk]:
    """Fixed character windows, stepping size-overlap; never cross a PDF page."""
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError('Require size > 0 and 0 <= overlap < size')
    text = page.text.strip()
    if not text:
        return []
    results: list[Chunk] = []
    step = size - overlap
    for start in range(0, len(text), step):
        end = min(start + size, len(text))
        results.append(_chunk(page, 'fixed', len(results), text[start:end],
                              char_start=start, char_end=end, overlap=overlap))
        if end == len(text):
            break
    return results


def _split_oversized(paragraph: str, max_size: int) -> list[str]:
    """Split a long block at sentence/word boundary, never discard source chars."""
    segments = []
    remaining = paragraph
    while len(remaining) > max_size:
        scope = remaining[:max_size]
        # Sentence boundary: allow a little whitespace in comparison to hard cut.
        sentence = list(re.finditer(r'[.!?](?=\s|$)', scope))
        candidate = sentence[-1].end() if sentence else -1
        if candidate < max_size // 3:
            last_space = max(scope.rfind(' '), scope.rfind('\n'))
            candidate = last_space + 1 if last_space >= max_size // 3 else max_size
        segments.append(remaining[:candidate].strip())
        remaining = remaining[candidate:].lstrip()
    if remaining.strip():
        segments.append(remaining.strip())
    return segments


def _heading(paragraph: str) -> bool:
    line = paragraph.strip()
    if '\n' in line or len(line) > 115:
        return False
    return bool(re.match(r'^(?:Chapter\s+\d+|\d{1,2}\.\d{1,2}\s+.+)$', line))


def by_paragraph(page: DocumentPage, max_size: int) -> list[Chunk]:
    """Group source paragraphs with heading-aware boundaries and size limits."""
    if max_size < 20:
        raise ValueError('max_size must be at least 20 characters')
    blocks = [block.strip() for block in re.split(r'\n\s*\n', page.text) if block.strip()]
    if not blocks:
        return []
    groups: list[str] = []
    buffer = ''
    for block in blocks:
        if _heading(block) and buffer:
            groups.append(buffer)
            buffer = ''
        for piece in _split_oversized(block, max_size):
            if not buffer:
                buffer = piece
            elif len(buffer) + 2 + len(piece) <= max_size:
                buffer += '\n\n' + piece
            else:
                groups.append(buffer)
                buffer = piece
    if buffer:
        groups.append(buffer)
    return [_chunk(page, 'paragraph', i, text, max_size=max_size)
            for i, text in enumerate(groups)]
