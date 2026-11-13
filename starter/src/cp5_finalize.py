"""CP5 audit and submission artifacts, sourced only from frozen traces.

Grounding/coherence labels are AI-assisted interpretations of real excerpts and
must not be misrepresented as independent human annotation.
"""
from __future__ import annotations
import csv
import json
from collections import Counter
from pathlib import Path
from .cp5 import RESULTS, ROOT, read_json, sha
from .evaluation import summarize

# Labels: assess the combined top-3 evidence for a response (not an LLM answer).
# 0=absent/off-topic, 1=partial or scattered evidence, 2=clear sufficient evidence.
GROUNDING={
 'Q16': {'A':(2,'Rank 2 explains both bug and debugging.'), 'B':(2,'Rank 2 gives the complete distinction.'), 'C':(2,'Same source evidence as B.')},
 'Q17': {'A':(1,'Error types are scattered across glossary / two cut windows; no concise combined explanation.'), 'B':(2,'Rank 1 explicitly lists all three error types.'), 'C':(2,'Rank 1 explicitly lists all three error types.')},
 'Q18': {'A':(1,'A glossary fragment states that void functions return None but lacks the full assignment example.'), 'B':(2,'Rank 1 states assigned result is None and includes code output.'), 'C':(2,'Rank 1 states assigned result is None and includes code output.')},
 'Q19': {'A':(2,'Rank 3 defines refactoring and explains improved interfaces/reuse.'), 'B':(2,'Rank 2 provides the complete refactoring definition.'), 'C':(2,'Rank 2 provides the complete refactoring definition.')},
 'Q20': {'A':(1,'Responsibility can be inferred across two truncated windows; low standalone clarity.'), 'B':(1,'Caller and function obligations appear in separate chunks, weakening standalone grounding.'), 'C':(1,'Same split obligations as B.')},
}

def write_json(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def write_csv(path,rows):
    with path.open('w',encoding='utf-8',newline='') as f:
        out=csv.DictWriter(f,fieldnames=list(rows[0]));out.writeheader();out.writerows(rows)

def main():
    selection=read_json(RESULTS/'cp5_dev_selection.json')
    assert selection['dev_traces_sha256']==sha(RESULTS/'cp5_dev_traces.jsonl')
    tests=[json.loads(s) for s in (RESULTS/'cp5_test_traces.jsonl').read_text(encoding='utf-8').splitlines()]
    dev=[json.loads(s) for s in (RESULTS/'cp5_dev_traces.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(tests)==15 and len(dev)==45
    assert selection['selected_strategy']=='B'
    manifest=read_json(ROOT/'data/manifest.json')
    pages={p['pdf_page']:p for p in manifest['pages']}
    grounding=[];metadata=[]
    for t in tests:
        qid=t['id'];s=t['strategy']
        score,note=GROUNDING[qid][s]
        grounding.append({'id':qid,'strategy':s,'score_0_2':score,'rationale':note,
                          'retrieved_chunk_ids':'|'.join(x['chunk_id'] for x in t['top3']),
                          'gold_page':t['gold_page'], 'exact_evidence_hit3':int(t['evidence_hit3']),
                          'reviewer':'AI-assisted excerpt review; learner confirmation recommended'})
        for hit in t['top3']:
            meta=hit['metadata']
            correct=(hit['document_id']==manifest['source_id'] and
                     hit['page'] in pages and meta.get('page_id')==pages[hit['page']]['page_id'] and
                     hit['chapter']==pages[hit['page']]['chapter'] and
                     meta.get('chapter')==pages[hit['page']]['chapter'] and
                     hit['source']==manifest['source_path_or_url'])
            fil=t['applied_filter']
            filter_pass=None if not fil else hit['chapter']==fil['chapter']
            metadata.append({'id':qid,'strategy':s,'rank':hit['rank'],
                             'chunk_id':hit['chunk_id'],'pdf_page':hit['page'],
                             'chapter':hit['chapter'],'page_source_metadata_correct':int(correct),
                             'filter_requested':(fil or {}).get('chapter',''),
                             'filter_compliance':('NA' if filter_pass is None else int(filter_pass)),
                             'check_method':'cross-check document/source/page/chapter/page_id against frozen CP1 manifest'})
    write_csv(RESULTS/'cp5_grounding_audit.csv',grounding)
    write_csv(RESULTS/'cp5_metadata_audit.csv',metadata)
    coherence=read_json(RESULTS/'cp5_coherence_dev.json')
    scores=summarize(dev+tests)
    summary={'stage':'CP5_complete','selected_before_test':selection['selected_strategy'],
      'selection_lock_path':'starter/results/cp5_dev_selection.json',
      'selection_trace_sha256':selection['dev_traces_sha256'],
      'corpus_sha256':manifest['sha256'],
      'question_count':20,'dev':15,'test':5,'retrieval_runs':60,
      'top_k':3,'metrics':scores,'coherence_ai_review':{},
      'metadata_audit':{},'grounding_ai_review':{},
      'audit_disclosure':'Coherence and grounding rated by AI-assisted close reading; not independently verified by a human.',
      'strict_metric_limitation':'Exact complete gold evidence in one chunk on gold source+page; semantic equivalence or answers assembled across chunks are not credited.',
      'test_caution':'Five questions is too small to assert a general best strategy.'}
    for s in ('A','B','C'):
        ground=[g for g in grounding if g['strategy']==s]
        meta=[m for m in metadata if m['strategy']==s]
        checks=[m for m in meta if m['filter_compliance']!='NA']
        summary['coherence_ai_review'][s]={'sum':sum(x['score_0_2'] for x in coherence[s]['sample']),
                                           'n':len(coherence[s]['sample']),'mean_0_2':coherence[s]['mean']}
        summary['metadata_audit'][s]={'correct':sum(m['page_source_metadata_correct'] for m in meta),
          'total':len(meta),'filter_compliant':sum(m['filter_compliance']==1 for m in checks),
          'filtered_topk':len(checks)}
        summary['grounding_ai_review'][s]={'sum':sum(g['score_0_2'] for g in ground),
           'n':len(ground),'mean_0_2':sum(g['score_0_2'] for g in ground)/len(ground),
           'score_counts':dict(Counter(str(g['score_0_2']) for g in ground))}
    write_json(RESULTS/'cp5_summary.json',summary)
    failures=[]
    for q in dev+tests:
        if not q['evidence_hit3']:
            failures.append({'id':q['id'],'split':q['split'],'strategy':q['strategy'],
                'gold_page':q['gold_page'],'top3_pages':[x['page'] for x in q['top3']],
                'type':q['failure_type'],'top3_chunk_ids':[x['chunk_id'] for x in q['top3']]})
    write_json(RESULTS/'cp5_failure_cases.json',failures)
    print(json.dumps({k:summary[k] for k in ('selected_before_test','metadata_audit','grounding_ai_review')},indent=2))

if __name__=='__main__':main()
