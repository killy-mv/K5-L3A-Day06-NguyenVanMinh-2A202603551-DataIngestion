"""CP3 automated checks; no embedding or held-out retrieval access."""
import json
import unittest
from pathlib import Path
from src.chunking import by_paragraph, fixed_size
from src.ingestion import load_corpus, load_pdf, normalize_text
from src.models import DocumentPage
ROOT = Path(__file__).resolve().parents[2]

class TextTests(unittest.TestCase):
    def setUp(self):
        self.page = DocumentPage('doc', 'source', 2,
            'Heading\n\nThis is a small paragraph.\n\nThis is a second paragraph.',
            {'chapter': 'chapter_1', 'page_id': 'doc_p002'})

    def test_normalization(self):
        self.assertEqual(normalize_text('a  b\r\n\r\nc\t d'), 'a b\n\nc d')
        self.assertEqual(normalize_text('\uff21\u00a0B'), 'A B')

    def test_fixed_windows_reconstruct(self):
        chunks = fixed_size(self.page, 20, 4)
        self.assertEqual(chunks[0].text, self.page.text[:20])
        self.assertEqual(''.join(x.text[4:] for x in chunks[1:]), self.page.text[20:])
        self.assertEqual([x.chunk_id for x in chunks],
                         [x.chunk_id for x in fixed_size(self.page, 20, 4)])

    def test_fixed_invalid_parameters(self):
        for size, overlap in [(0, 0), (10, 10), (10, -1), (10, 11)]:
            with self.subTest(size=size, overlap=overlap), self.assertRaises(ValueError):
                fixed_size(self.page, size, overlap)

    def test_paragraph_chunking_keeps_content(self):
        chunks = by_paragraph(self.page, 38)
        self.assertTrue(all(len(x.text) <= 38 and x.page == 2 for x in chunks))
        self.assertEqual(' '.join(' '.join(x.text.split()) for x in chunks),
                         ' '.join(self.page.text.split()))
        self.assertEqual([x.chunk_id for x in chunks],
                         [x.chunk_id for x in by_paragraph(self.page, 38)])

    def test_paragraph_splits_long_unbroken_words(self):
        long_page = DocumentPage('id', 'src', 1, 'A' * 90)
        chunks = by_paragraph(long_page, 30)
        self.assertEqual(''.join(c.text for c in chunks), long_page.text)
        self.assertTrue(all(len(c.text) <= 30 for c in chunks))

    def test_metadata_isolation(self):
        chunks = fixed_size(self.page, 20, 4)
        chunks[0].metadata['chapter'] = 'changed'
        self.assertEqual(chunks[1].metadata['chapter'], 'chapter_1')
        self.assertEqual(self.page.metadata['chapter'], 'chapter_1')

    def test_manifest_integrity_and_pages(self):
        manifest = json.loads((ROOT/'data/manifest.json').read_text(encoding='utf-8'))
        events = []
        pages = load_corpus(ROOT/'data/manifest.json', diagnostics=events)
        self.assertEqual(len(pages), manifest['content_page_count'])
        self.assertEqual([p.page for p in pages], [r['pdf_page'] for r in manifest['pages']])
        self.assertEqual(set(r['code'] for r in events), {'EXCLUDED_BY_CP1'})
        self.assertTrue(all(p.metadata['chapter'] for p in pages))

    def test_empty_pdf_page_warns(self):
        events = []
        pages = load_pdf(ROOT/'data/source/thinkpython2.pdf', 'id', 'source',
                         selected_pages={2}, diagnostics=events)
        self.assertEqual(pages, [])
        self.assertEqual(events[0]['code'], 'EMPTY_PAGE')

    def test_out_of_bounds_and_missing_file(self):
        with self.assertRaises(ValueError):
            load_pdf(ROOT/'data/source/thinkpython2.pdf', 'id', 'source', selected_pages={245})
        with self.assertRaises(FileNotFoundError):
            load_pdf(ROOT/'data/source/missing.pdf', 'id', 'source')

if __name__ == '__main__': unittest.main()
