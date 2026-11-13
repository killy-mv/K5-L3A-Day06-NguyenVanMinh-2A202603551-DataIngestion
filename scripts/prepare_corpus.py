"""Validate CP1 source pages and produce a reproducible manifest."""
import hashlib, json, logging
from pathlib import Path
from pypdf import PdfReader
logging.getLogger('pypdf').setLevel(logging.ERROR)
root=Path(__file__).resolve().parents[1]
pdf=root/'data/source/thinkpython2.pdf'
chapters=[(23,'chapter_1','The way of the program'),(31,'chapter_2','Variables, expressions and statements'),(39,'chapter_3','Functions'),(51,'chapter_4','Case study: interface design')]
def main():
    reader=PdfReader(str(pdf)); included=[]; excluded=[]
    for page in range(23,61):
        raw=reader.pages[page-1].extract_text() or ''
        count=len(' '.join(raw.split()))
        chapter=next(name for first,name,_ in reversed(chapters) if page>=first)
        item={'page_id':f'thinkpython2_pdf_p{page:03}', 'pdf_page':page,'printed_page':page-22,'chapter':chapter,'char_count':count}
        if count>=500: included.append(item)
        else: excluded.append({**item,'reason':'under 500 extracted characters'})
    m={'corpus_id':'thinkpython2_chapters_1_4','source_id':'thinkpython2_pdf','title':'Think Python: How to Think Like a Computer Scientist, 2nd Edition','author':'Allen B. Downey','edition':'2nd, v2.4.1','source_path_or_url':'https://greenteapress.com/thinkpython2/thinkpython2.pdf','local_path':'data/source/thinkpython2.pdf','license_or_permission':'CC BY-NC 3.0 Unported','license_url':'https://creativecommons.org/licenses/by-nc/3.0/','license_evidence_url':'https://greenteapress.com/wp/think-python-2e/','accessed_at':'2026-11-13','sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'pdf_total_physical_pages':len(reader.pages),'selected_pdf_page_range_inclusive':[23,60],'counting_rule':'Only actual PDF physical pages 23-60 from chapters 1-4, >=500 characters after whitespace normalization. Exclude near-empty pages and all front matter.','min_chars_per_content_page':500,'content_page_count':len(included),'content_char_count':sum(x['char_count'] for x in included),'metadata_filter_field':'chapter','metadata_filter_values':[{'value':n,'title':t,'starts_pdf_page':p} for p,n,t in chapters],'pages':included,'excluded_in_selected_range':excluded,'extraction_notes':'Certain font glyphs have imperfect extraction; manually verify all CP2 evidence against the PDF.'}
    if len(included)<30: raise RuntimeError('Insufficient valid pages')
    (root/'data/manifest.json').write_text(json.dumps(m,indent=2,ensure_ascii=True)+'\n',encoding='utf-8')
    print('VALID_PAGES',len(included),'CHARS',m['content_char_count'],'EXCLUDED',[x['pdf_page'] for x in excluded])
if __name__=='__main__': main()
