"""Reproducible read-only Day 06 pre-submission audit (no Dev/Test rerun)."""
from __future__ import annotations
import csv
import hashlib
import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'starter/results'
checks=[]

def check(name,condition,detail=''):
    checks.append({'check':name,'passed':bool(condition),'details':detail})

def read(path):return json.loads((ROOT/path).read_text(encoding='utf8'))
def h(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()

def audit():
    manifest=read('data/manifest.json'); gold=read('benchmark/questions.json'); lock=read('benchmark/split_lock.json')
    summary=read('starter/results/cp5_summary.json'); selected=read('starter/results/cp5_dev_selection.json')
    def count_csv(path):
        with (ROOT/path).open(encoding='utf8',newline='') as f:return list(csv.DictReader(f))
    check('Corpus >=30 qualifying pages',len(manifest['pages'])>=30)
    check('PDF hash unchanged',h(manifest['local_path'])==manifest['sha256'])
    check('Source permission documented',bool(manifest.get('license_evidence_url') and manifest.get('license_or_permission')))
    check('Gold count/split',len(gold)==20 and sum(q['split']=='dev' for q in gold)==15 and sum(q['split']=='test' for q in gold)==5)
    canonical=json.dumps(gold,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
    check('Gold SHA256 unchanged',hashlib.sha256(canonical).hexdigest()==lock['questions_canonical_sha256'])
    check('Filters (>=3, >=1 test)',sum(bool(q.get('filter')) for q in gold)>=3 and any(q['filter'] and q['split']=='test' for q in gold))
    for name,n in [('A',170),('B',160)]:
        p=R/('cp3_chunks_A_fixed.jsonl' if name=='A' else 'cp3_chunks_B_paragraph.jsonl')
        rows=[json.loads(x) for x in p.read_text(encoding='utf8').splitlines()]
        check(f'Strategy {name} chunk count',len(rows)==n)
        check(f'Strategy {name} valid metadata',all(x['document_id']==manifest['source_id'] and x['metadata'].get('chapter') and x['page'] for x in rows))
    cp4=read('starter/results/cp4_statistics.json')
    check('Real 384-d model and database count',cp4['dimensions']==384 and cp4['stored_counts']=={'A':170,'B':160})
    for split,num in [('dev',45),('test',15)]:
        traces=[json.loads(x) for x in (R/f'cp5_{split}_traces.jsonl').read_text(encoding='utf8').splitlines()]
        check(f'{split} traces',len(traces)==num and all(len(x['top3'])==3 for x in traces))
        check(f'{split} full text provenance',all(all(x['text'] and x['metadata'].get('page_id') for x in t['top3']) for t in traces))
    check('Pre-test selection immutable Dev hash', selected['dev_traces_sha256']==h('starter/results/cp5_dev_traces.jsonl'))
    check('Selected B (Dev only)',selected['selected_strategy']=='B' and selected['test_seen_before_freeze'] is False)
    check('Summary 60 queries',summary['retrieval_runs']==60)
    check('Manual-coherence audit entries (AI assisted)',all(summary['coherence_ai_review'][s]['n']==10 for s in 'ABC'))
    check('Grounding 5 test x 3 strategies (AI assisted)',len(count_csv('starter/results/cp5_grounding_audit.csv'))==15)
    check('Metadata 5 test x top3 x 3 strategies',len(count_csv('starter/results/cp5_metadata_audit.csv'))==45)
    check('Experiment log A/B/C', [x['strategy'] for x in count_csv('artifacts/experiment_log.csv')]==list('ABC'))
    check('Individual report and CP docs exist',all((ROOT/p).is_file() for p in (
       'report/individual/2A202603551_NguyenVanMinh.md','docs/CP1_SETUP.md','docs/CP2_BENCHMARK.md',
       'docs/CP3_INGESTION.md','docs/CP4_VECTOR_STORAGE.md','docs/CP5_EVALUATION.md')))
    check('Resource measurement recorded', (R/'cp6_resource_measurement.json').is_file())
    tracked=subprocess.run(['git','ls-files','-z'],cwd=ROOT,capture_output=True,check=True).stdout.split(b'\0')
    tracked_paths=[p.decode('utf-8') for p in tracked if p]
    check('No tracked environment/key/virtualenv/cache files',not any(
      p.endswith('.env') or '/.venv/' in p or '/.cache/' in p or p.endswith('.pem') or p.endswith('.key')
      for p in tracked_paths))
    # Read-only, conservative secret scan over tracked text. Avoid emitting matching strings.
    import re
    patterns=[r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
              r'(?i)(?:OPENAI_API_KEY|GEMINI_API_KEY|OPENROUTER_API_KEY)\s*=\s*[A-Za-z0-9_-]{18,}',
              r'ghp_[A-Za-z0-9]{25,}',r'github_pat_[A-Za-z0-9_]{30,}',r'sk-proj-[A-Za-z0-9_-]{20,}']
    risky=[]
    for relative in tracked_paths:
        p=ROOT/relative
        if not p.is_file() or p.stat().st_size>3_000_000 or p.suffix.lower() in {'.pdf','.png','.jpg','.jpeg','.svg','.woff','.ico'}:continue
        try:content=p.read_text(encoding='utf-8')
        except UnicodeDecodeError:continue
        if any(re.search(pt,content) for pt in patterns):risky.append(relative)
    check('No common API tokens in committed text',not risky,','.join(risky))
    return {'audit_type':'Day06 final pre-submission artifact check',
       'automated_checks':len(checks),'passed':sum(x['passed'] for x in checks),
       'failed':sum(not x['passed'] for x in checks), 'checks':checks,
       'manual_gate_remaining':['Student independently confirm AI-assisted coherence/grounding ratings',
          'Push final CP6 changes and submit repository link to instructor',
          'Check school/course data redistribution policy and GitHub sharing appropriateness']}

if __name__=='__main__':
    outcome=audit();out=R/'cp6_submission_audit.json'
    out.write_text(json.dumps(outcome,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for c in outcome['checks']:print(('PASS' if c['passed'] else 'FAIL'),c['check'],c['details'])
    print('SUMMARY',outcome['passed'],'/',outcome['automated_checks'])
    if outcome['failed']:raise SystemExit(1)
