"""PDF extraction and normalization with physical-page provenance (CP3)."""
from __future__ import annotations

import hashlib
import json
import logging
import re
import unicodedata
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from .models import DocumentPage

logger = logging.getLogger(__name__)


def normalize_text(text: str) -> str:
    """NFKC Unicode and spacing cleanup; retain blank lines and code line breaks.

    Do not silently dehyphenate or repair malformed PDF glyphs: this could change
    exact-source evidence. Retain all non-whitespace characters for provenance.
    """
    if not isinstance(text, str):
        raise TypeError('text must be a string')
    text = unicodedata.normalize('NFKC', text).replace('\r\n', '\n').replace('\r', '\n')
    text = text.replace('\x00', '').replace('\u00ad', '')
    lines: list[str] = []
    for line in text.split('\n'):
        # Keep a small, meaningful code indentation; compress PDF layout spaces.
        leading = len(line) - len(line.lstrip(' \t'))
        indentation = ' ' * min(leading, 8) if leading and line.strip() else ''
        body = re.sub(r'[ \t]+', ' ', line.strip())
        lines.append(indentation + body if body else '')
    result = '\n'.join(lines).strip()
    return re.sub(r'\n{3,}', '\n\n', result)


def load_pdf(
    path: Path,
    document_id: str,
    source: str,
    *,
    selected_pages: set[int] | None = None,
    metadata_by_page: dict[int, dict[str, Any]] | None = None,
    diagnostics: list[dict[str, Any]] | None = None,
) -> list[DocumentPage]:
    """Extract numbered PDF pages using layout-aware text extraction.

    `page` is one-based physical PDF index, never the printed book page.
    Selected page ranges are validated strictly, not silently truncated.
    Error diagnostics can be collected by the caller for audit artifacts.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    if not document_id.strip() or not source.strip():
        raise ValueError('document_id and source must be non-empty')
    reader = PdfReader(str(path))
    if reader.is_encrypted:
        raise ValueError(f'Encrypted PDF is unsupported: {path}')
    count = len(reader.pages)
    pages = sorted(selected_pages) if selected_pages is not None else range(1, count + 1)
    if not pages or any(p < 1 or p > count for p in pages):
        raise ValueError(f'Selected physical PDF pages must be within 1..{count}')
    result: list[DocumentPage] = []
    for page_no in pages:
        try:
            raw = reader.pages[page_no - 1].extract_text(extraction_mode='layout') or ''
        except Exception as exc:
            if diagnostics is not None:
                diagnostics.append({'severity': 'error', 'pdf_page': page_no,
                                    'code': 'PDF_EXTRACTION_FAILED', 'details': str(exc)})
            raise RuntimeError(f'Failed to extract physical PDF page {page_no}') from exc
        clean = normalize_text(raw)
        if not clean:
            if diagnostics is not None:
                diagnostics.append({'severity': 'warning', 'pdf_page': page_no,
                                    'code': 'EMPTY_PAGE', 'details': 'No extractable text; OCR may be required'})
            continue
        bad_glyphs = clean.count('\ufffd')
        if bad_glyphs and diagnostics is not None:
            diagnostics.append({'severity': 'warning', 'pdf_page': page_no,
                                'code': 'REPLACEMENT_GLYPHS', 'count': bad_glyphs,
                                'details': 'Verify evidence visually; cannot recover original font mapping with text cleanup'})
        metadata = dict((metadata_by_page or {}).get(page_no, {}))
        metadata.setdefault('page_id', f'{document_id}_p{page_no:03}')
        metadata['normalized_char_count'] = len(clean)
        metadata['text_sha256'] = hashlib.sha256(clean.encode('utf-8')).hexdigest()
        result.append(DocumentPage(document_id=document_id, source=source, page=page_no,
                                   text=clean, metadata=metadata))
    return result


def load_corpus(manifest_path: Path, *, diagnostics: list[dict[str, Any]] | None = None) -> list[DocumentPage]:
    """Load precisely the qualifying CP1 pages and verify integrity before use."""
    manifest_path = Path(manifest_path).resolve()
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    root = manifest_path.parent.parent
    pdf = root / manifest['local_path']
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    if digest != manifest['sha256']:
        raise ValueError('Corpus PDF SHA256 changed from the frozen CP1 manifest')
    page_map = {p['pdf_page']: p for p in manifest['pages']}
    if len(page_map) != len(manifest['pages']) or len(page_map) != manifest['content_page_count']:
        raise ValueError('Manifest contains duplicate or mismatched source page IDs')
    result = load_pdf(pdf, manifest['source_id'], manifest['source_path_or_url'],
                      selected_pages=set(page_map), metadata_by_page=page_map,
                      diagnostics=diagnostics)
    if len(result) != len(page_map):
        raise ValueError(f'Expected {len(page_map)} non-empty pages, extracted {len(result)}')
    for page in result:
        original = page_map[page.page]
        for key in ('page_id', 'chapter', 'printed_page'):
            if page.metadata.get(key) != original.get(key):
                raise ValueError(f'Incorrect {key} on physical PDF page {page.page}')
        if len(' '.join(page.text.split())) < manifest['min_chars_per_content_page']:
            raise ValueError(f'Page {page.page} no longer qualifies as useful content')
    for item in manifest.get('excluded_in_selected_range', []):
        if diagnostics is not None:
            diagnostics.append({'severity': 'info', 'pdf_page': item['pdf_page'],
                                'code': 'EXCLUDED_BY_CP1', 'char_count': item['char_count'],
                                'details': item['reason']})
    return result
