"""CP4 real embedding + pgvector ingestion; no benchmark/test evaluation."""
from __future__ import annotations
import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from .embeddings import DEFAULT_MODEL, MyEmbedder
from .store import PgVectorStore

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / 'starter/results'
RESULTS.mkdir(parents=True, exist_ok=True)


def load_chunks(strategy: str) -> list:
    from .models import Chunk
    name = {'A':'cp3_chunks_A_fixed.jsonl','B':'cp3_chunks_B_paragraph.jsonl'}[strategy]
    chunks = []
    with (RESULTS / name).open(encoding='utf-8') as f:
        for line in f:
            row = json.loads(line)
            chunks.append(Chunk(**row))
    return chunks


def get_vectors(model: MyEmbedder, strategy: str, chunks: list, rebuild: bool = False) -> tuple[list[list[float]],bool,float]:
    cache_dir = ROOT / 'starter/.cache'
    cache_dir.mkdir(exist_ok=True)
    cache_path = cache_dir / f'embedding_{strategy}.json'
    signature = hashlib.sha256(json.dumps({
        'model':model.model_name, 'revision':model.revision,
        'chunks':[(c.chunk_id, hashlib.sha256(c.text.encode()).hexdigest()) for c in chunks]
    }, sort_keys=True).encode()).hexdigest()
    if cache_path.exists() and not rebuild:
        payload=json.loads(cache_path.read_text(encoding='utf-8'))
        if payload.get('signature') == signature and len(payload.get('vectors',[])) == len(chunks):
            return payload['vectors'],True,0.0
    start=time.perf_counter()
    vectors=model.embed_documents([c.text for c in chunks])
    duration=time.perf_counter()-start
    cache_path.write_text(json.dumps({'signature':signature,'vectors':vectors}),encoding='utf-8')
    return vectors,False,duration


def main() -> None:
    load_dotenv(ROOT/'starter/.env')
    url=os.environ.get('DATABASE_URL')
    if not url:
        raise RuntimeError('DATABASE_URL missing in starter/.env')
    model_name=os.getenv('EMBEDDING_MODEL') or DEFAULT_MODEL
    manifest=json.loads((ROOT/'data/manifest.json').read_text(encoding='utf-8'))
    from hashlib import sha256
    assert sha256((ROOT/manifest['local_path']).read_bytes()).hexdigest() == manifest['sha256']
    a=load_chunks('A'); b=load_chunks('B')
    for s,chunks,expected in [('A',a,170),('B',b,160)]:
        if len(chunks)!=expected:
            raise RuntimeError(f'{s} chunk count mismatch: rerun CP3 / validate changes')
    started=time.perf_counter()
    model=MyEmbedder(model_name)
    model_load=time.perf_counter()-started
    store=PgVectorStore(url,model.dimensions,model.model_name+'@'+str(model.revision))
    store.create_schema()
    outputs={}
    for label,chunks in [('A',a),('B',b)]:
        vectors,cached,encode_s=get_vectors(model,label,chunks)
        t0=time.perf_counter()
        state=store.upsert(label,chunks,vectors)
        outputs[label]={'chunks':len(chunks),'cached_vectors':cached,
                        'embedding_seconds':round(encode_s,3),
                        'database_upsert_seconds':round(time.perf_counter()-t0,3),
                        **state}
        print(f'{label} stored {state["stored"]} actual vectors, cache={cached}',flush=True)
    if store.counts()!={'A':len(a),'B':len(b)}:
        raise RuntimeError('Indexed row totals mismatch')
    # Deliberately synthetic smoke queries, not the 20 locked benchmark questions.
    smoke=[('What is a Python variable?',None),
           ('How do turtle graphics draw squares?',{'chapter':'chapter_4'})]
    checks=[]
    for question,filt in smoke:
        vec=model.embed_query(question)
        for strategy in ('A','B','C'):
            use_filter=filt if strategy=='C' else None
            t0=time.perf_counter()
            hits=store.search(strategy,vec,top_k=3,filters=use_filter)
            if len(hits)!=3 or any(not h['text'] or h['score'] < -1.01 or h['score'] > 1.01 for h in hits):
                raise RuntimeError(f'Invalid top-3 smoke retrieval: {strategy}')
            if use_filter and not all(h['chapter']==use_filter['chapter'] for h in hits):
                raise RuntimeError('Chapter filter was not respected')
            checks.append({'question':question,'strategy':strategy,'filter':use_filter,
                           'retrieval_seconds':round(time.perf_counter()-t0,4),
                           'top3':[{'chunk_id':h['chunk_id'],'page':h['page'],
                                    'chapter':h['chapter'],'score':round(h['score'],6),
                                    'text_preview':h['text'][:180]} for h in hits]})
    # Identical index and no filtering: B and C must have identical ranking/results.
    for i in (0,3):
        x=checks[i+1]['top3']; y=checks[i+2]['top3']
        if i==0 and [z['chunk_id'] for z in x] != [z['chunk_id'] for z in y]:
            raise RuntimeError('Unfiltered B/C mismatch')
    report={'stage':'CP4','timestamp_utc':datetime.now(timezone.utc).isoformat(),
            'embedding_provider':'local_sentence_transformers','model_name':model.model_name,
            'revision':model.revision,'dimensions':model.dimensions,
            'max_seq_length':model.max_seq_length,'device':model.device,
            'normalized_embeddings':True,'similarity':'exact cosine via pgvector <=>',
            'vector_store':'PostgreSQL + pgvector','physical_collections':['A','B'],
            'C_policy':'same physical B index; use chapter filtering when provided',
            'model_load_seconds':round(model_load,3),'strategies':outputs,
            'stored_counts':store.counts(),'smoke_cases':len(smoke),'smoke_runs':len(checks),
            'api_cost_usd':0,'note':'No frozen dev/test questions queried and no Hit@1/Hit@3 computed.'}
    (RESULTS/'cp4_statistics.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    (RESULTS/'cp4_smoke_traces.json').write_text(json.dumps(checks,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':
    logging.basicConfig(level=logging.ERROR)
    main()
