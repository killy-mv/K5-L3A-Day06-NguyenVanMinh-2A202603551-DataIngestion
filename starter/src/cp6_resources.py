"""Re-measure local embedding computation only; never read Test gold or alter vector DB."""
from __future__ import annotations
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from .cp4 import load_chunks
from .embeddings import MyEmbedder, DEFAULT_MODEL

ROOT=Path(__file__).resolve().parents[2]
RESULTS=ROOT/'starter/results'

def main():
    before=time.perf_counter()
    model=MyEmbedder(DEFAULT_MODEL)
    load_seconds=time.perf_counter()-before
    a=load_chunks('A')
    b=load_chunks('B')
    chunks={'A':a,'B':b}
    trials={'A':[],'B':[]}
    # ABBA order reduces systematic model warm-up differences.
    for stage in ('A','B','B','A'):
        texts=[c.text for c in chunks[stage]]
        t0=time.perf_counter()
        vectors=model.embed_documents(texts)
        elapsed=time.perf_counter()-t0
        if len(vectors)!=len(texts) or any(len(v)!=model.dimensions for v in vectors):
            raise RuntimeError('Unexpected embedding output dimensions/count')
        trials[stage].append(round(elapsed,4))
    results={
        'timestamp_utc':datetime.now(timezone.utc).isoformat(),
        'stage':'CP6_embedding_cpu_resource_measurement',
        'model':model.model_name,'revision':model.revision,'dimensions':model.dimensions,
        'device':model.device,'model_load_seconds':round(load_seconds,4),
        'measurement':'in-process forward-pass encoding time; excludes model load, PDF parse, DB upsert, OS package install; warmed CPU and filesystem cache',
        'batch_size':32,'C_policy':'C reuses B vectors; no additional embedding computation',
        'A':{'chunks':len(a),'trials_seconds':trials['A'],'mean_seconds':round(statistics.mean(trials['A']),4)},
        'B':{'chunks':len(b),'trials_seconds':trials['B'],'mean_seconds':round(statistics.mean(trials['B']),4)},
        'api_cost_usd':0,
        'limitations':'Single machine/two non-independent trials per strategy; not cold-start estimates or statistically strong benchmark. No retrieval or Test result used for tuning.'}
    (RESULTS/'cp6_resource_measurement.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(results,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
