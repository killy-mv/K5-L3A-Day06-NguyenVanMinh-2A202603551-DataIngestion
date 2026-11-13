"""CP5 staged benchmark: DEV -> FROZEN SELECTION -> TEST, never tune on TEST."""
from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
from .embeddings import DEFAULT_MODEL, MyEmbedder
from .evaluation import evaluate_query, summarize
from .store import PgVectorStore

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / 'starter/results'
QUESTIONS = ROOT / 'benchmark/questions.json'
LOCK = ROOT / 'benchmark/split_lock.json'
FROZEN = RESULTS / 'cp5_dev_selection.json'


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',',':')).encode('utf-8')


def validate_frozen_inputs() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from hashlib import sha256
    corpus = read_json(ROOT / 'data/manifest.json')
    lock = read_json(LOCK)
    questions = read_json(QUESTIONS)
    assert sha256(canonical(questions)).hexdigest() == lock['questions_canonical_sha256'], 'Benchmark lock invalid'
    assert sha(ROOT / corpus['local_path']) == lock['corpus_sha256'] == corpus['sha256'], 'Corpus modified'
    assert [q['id'] for q in questions if q['split']=='dev'] == lock['dev_ids'], 'Dev IDs modified'
    assert [q['id'] for q in questions if q['split']=='test'] == lock['test_ids'], 'Test IDs modified'
    return questions, lock


def store_and_model() -> tuple[PgVectorStore, MyEmbedder]:
    load_dotenv(ROOT / 'starter/.env')
    url = os.getenv('DATABASE_URL')
    if not url:
        raise RuntimeError('DATABASE_URL is not configured')
    model = MyEmbedder(os.getenv('EMBEDDING_MODEL') or DEFAULT_MODEL)
    store = PgVectorStore(url, model.dimensions, model.model_name+'@'+str(model.revision))
    store.create_schema()
    assert store.counts() == {'A':170, 'B':160}, 'Run CP4 to restore the expected indexes'
    return store, model


def run_split(split: str) -> None:
    if split not in ('dev', 'test'):
        raise ValueError('Unknown split')
    if (RESULTS / f'cp5_{split}_traces.jsonl').exists():
        raise RuntimeError(f'{split} traces already exist. Refusing accidental overwrite of locked benchmark run.')
    all_questions, lock = validate_frozen_inputs()
    if split == 'test':
        if not FROZEN.is_file():
            raise RuntimeError('Test locked: freeze and document Dev strategy selection first')
        selected = read_json(FROZEN)
        if (selected['corpus_sha256'] != lock['corpus_sha256']
                or selected['questions_canonical_sha256'] != lock['questions_canonical_sha256']
                or selected['dev_traces_sha256'] != sha(RESULTS / 'cp5_dev_traces.jsonl')):
            raise RuntimeError('Frozen selection no longer matches dev/corpus/benchmark')
    questions = [q for q in all_questions if q['split']==split]
    assert len(questions) == (15 if split == 'dev' else 5)
    store, model = store_and_model()
    traces = []
    # Embed question once; same vector across A, B, C. Do not inject answers or gold pages.
    for question in questions:
        vector = model.embed_query(question['question'])
        for strategy in ('A','B','C'):
            query_filter = question.get('filter') if strategy=='C' else None
            started=time.perf_counter()
            hits=store.search(strategy,vector,top_k=3,filters=query_filter)
            elapsed=time.perf_counter()-started
            record=evaluate_query(question,hits)
            record.update({'strategy':strategy,'applied_filter':query_filter,
                           'query_seconds':round(elapsed,6),'embedding_model':model.model_name,
                           'model_revision':model.revision})
            traces.append(record)
    counts = summarize(traces)
    # B/C are intentionally identical when no question-specific filter exists.
    by_case = {(t['id'],t['strategy']):t for t in traces}
    for q in questions:
        if not q['filter']:
            ids_b=[h['chunk_id'] for h in by_case[(q['id'],'B')]['top3']]
            ids_c=[h['chunk_id'] for h in by_case[(q['id'],'C')]['top3']]
            if ids_b != ids_c:
                raise RuntimeError(f'Unexpected difference between unfiltered B/C: {q["id"]}')
    RESULTS.mkdir(parents=True, exist_ok=True)
    output=RESULTS / f'cp5_{split}_traces.jsonl'
    output.write_text(''.join(json.dumps(t,ensure_ascii=False)+'\n' for t in traces),encoding='utf-8')
    metrics={ 'stage': f'CP5_{split}', 'created_at_utc': datetime.now(timezone.utc).isoformat(),
              'questions': len(questions), 'retrievals': len(traces), 'top_k':3,
              'corpus_sha256':lock['corpus_sha256'],
              'questions_canonical_sha256':lock['questions_canonical_sha256'],
              'model':model.model_name, 'revision':model.revision, 'dimensions':model.dimensions,
              'metric_definition':'Strict single-chunk full normalized evidence + matching gold source/page',
              'metrics':counts, 'test_used_to_tune':False}
    (RESULTS / f'cp5_{split}_metrics.json').write_text(json.dumps(metrics,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(metrics,indent=2), flush=True)


def freeze_selection() -> None:
    questions,lock=validate_frozen_inputs()
    if FROZEN.exists():
        raise RuntimeError('Dev selection already frozen, refusing overwrite')
    if (RESULTS / 'cp5_test_traces.jsonl').exists():
        raise RuntimeError('Test results already exist: cannot claim an independent pre-test freeze now')
    dev=RESULTS / 'cp5_dev_traces.jsonl'
    if not dev.is_file():
        raise RuntimeError('Run Dev benchmark first')
    metrics=read_json(RESULTS/'cp5_dev_metrics.json')['metrics']
    if any(metrics[s]['dev']['questions']!=15 for s in ('A','B','C')):
        raise RuntimeError('Dev result incomplete')
    order=sorted(('A','B','C'),key=lambda s:(-metrics[s]['dev']['hit3_n'], -metrics[s]['dev']['hit1_n']))
    best=metrics[order[0]]['dev']; tied=[s for s in order if (metrics[s]['dev']['hit3_n'],metrics[s]['dev']['hit1_n'])==(best['hit3_n'],best['hit1_n'])]
    if len(tied)>1:
        # Must honor the precommitted coherence tie-break before any test usage.
        coherence=RESULTS/'cp5_coherence_dev.json'
        if not coherence.is_file():
            raise RuntimeError(f'Dev retrieval tie {tied}: review 10 fixed source positions and document coherence in {coherence} BEFORE freezing/test')
        reviews=read_json(coherence)
        if any(s not in reviews for s in tied):
            raise RuntimeError('Missing required pre-test coherence review')
        tied.sort(key=lambda s:(-reviews[s]['mean'], {'A':170,'B':160,'C':160}[s],s))
        selected=tied[0]
        tie_note='Dev hit3 and hit1 tie resolved with pre-test coherence / chunk resource tie-break.'
    else:
        selected=order[0]
        tie_note='Unique best using precommitted Dev Hit@3, then Hit@1.'
    frozen={ 'frozen_at_utc':datetime.now(timezone.utc).isoformat(),
             'selected_strategy':selected, 'selection_rationale':tie_note,
             'dev_metrics':metrics, 'candidate_order':order,
             'selection_rule':lock['selection_rule'],
             'dev_traces_sha256':sha(dev),
             'corpus_sha256':lock['corpus_sha256'],
             'questions_canonical_sha256':lock['questions_canonical_sha256'],
             'test_seen_before_freeze':False }
    FROZEN.write_text(json.dumps(frozen,indent=2)+'\n',encoding='utf-8')
    print('FROZEN DEV SELECTION:',selected,'|',tie_note)


def main_for_stage(stage: str) -> None:
    if stage=='dev':run_split('dev')
    elif stage=='freeze':freeze_selection()
    elif stage=='test':run_split('test')
    else:raise ValueError(f'Unsupported CP5 stage: {stage}')

if __name__=='__main__':
    import sys
    if len(sys.argv)!=2:raise SystemExit('Usage: cp5 dev/freeze/test')
    main_for_stage(sys.argv[1])
