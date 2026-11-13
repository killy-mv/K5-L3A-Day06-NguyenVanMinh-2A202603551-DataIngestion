"""Read-only CP2 verification: corpus, lock, evidence, split and filter semantics."""
import hashlib,json,logging,sys,unicodedata
from pathlib import Path
from pypdf import PdfReader
logging.getLogger('pypdf').setLevel(logging.ERROR)
R=Path(__file__).resolve().parents[1]
def canonical(v):return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf-8')
def norm(s):return ' '.join(unicodedata.normalize('NFKC',s).split())
def validate():
    m=json.loads((R/'data/manifest.json').read_text(encoding='utf-8'))
    qs=json.loads((R/'benchmark/questions.json').read_text(encoding='utf-8'))
    lock=json.loads((R/'benchmark/split_lock.json').read_text(encoding='utf-8'))
    assert hashlib.sha256((R/m['local_path']).read_bytes()).hexdigest()==m['sha256']==lock['corpus_sha256'],'Corpus hash changed'
    assert hashlib.sha256(canonical(qs)).hexdigest()==lock['questions_canonical_sha256'],'Benchmark modified since split lock'
    assert len(qs)>=20 and len({q['id'] for q in qs})==len(qs),'Missing or duplicate IDs'
    assert [q['id'] for q in qs if q['split']=='dev']==lock['dev_ids'] and len(lock['dev_ids'])>=15,'Dev split changed'
    assert [q['id'] for q in qs if q['split']=='test']==lock['test_ids'] and len(lock['test_ids'])>=5,'Test split changed'
    assert len(qs)==len(lock['dev_ids'])+len(lock['test_ids']),'Split mismatch'
    valid_pages={p['pdf_page']:p for p in m['pages']}
    filters=[q for q in qs if q['filter']]
    assert len(filters)>=3 and any(q['split']=='test' for q in filters),'Filter coverage inadequate'
    r=PdfReader(str(R/m['local_path']))
    required=['id','split','question','expected_answer','gold_source_id','gold_page','evidence_quote','filter']
    for q in qs:
        assert all(k in q for k in required),f'{q["id"]}: missing key'
        assert q['gold_source_id']==m['source_id'],f'{q["id"]}: wrong source'
        p=q['gold_page'];assert p in valid_pages,f'{q["id"]}: invalid page'
        assert q['gold_page_id']==valid_pages[p]['page_id'],f'{q["id"]}: page ID mismatch'
        assert q['evidence_quote'] in norm(r.pages[p-1].extract_text() or ''),f'{q["id"]}: evidence not found on page'
        if q['filter']:
            assert set(q['filter'])=={'chapter'},f'{q["id"]}: unexpected filter'
            assert q['filter']['chapter']==valid_pages[p]['chapter'],f'{q["id"]}: incorrect chapter'
            assert ('chapter' in q['question'].lower()) or ('chapter' in q['filter_origin'].lower()),f'{q["id"]}: ungrounded filter'
    print(f'PASS: {len(qs)} unique, source-verified questions | {len(lock["dev_ids"])} dev / {len(lock["test_ids"])} test | {len(filters)} filters ({sum(q["split"]=="test" for q in filters)} test)')
    print('PASS: immutable corpus and benchmark hashes, exact page evidence, manifest page IDs and filter values')
if __name__=='__main__':
    try:validate()
    except (AssertionError,KeyError,ValueError,FileNotFoundError) as exc:
        print(f'FAIL: {exc}',file=sys.stderr);sys.exit(1)
