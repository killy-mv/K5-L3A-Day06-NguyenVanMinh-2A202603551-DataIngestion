"""Fill the required experiment log with real measured CP3/4/5 values only."""
import csv,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
get=lambda path:json.loads((R/path).read_text(encoding='utf-8'))
summary=get('starter/results/cp5_summary.json')
cp3=get('starter/results/cp3_statistics.json')
cp4=get('starter/results/cp4_statistics.json')
rows=[]
for s in ('A','B','C'):
    bench=summary['metrics'][s]
    chunk='fixed' if s=='A' else 'paragraph'
    source='A' if s=='A' else 'B'
    rows.append({'strategy':s,'chunking':chunk,'chunk_size':cp3[source].get('size',cp3[source].get('max_size')),
        'overlap':cp3[source].get('overlap',0),'metadata':'document_id, source, pdf_page, chapter, page_id',
        'filter':'chapter at retrieval only' if s=='C' else 'none',
        'vectorizer':cp4['model_name']+' (384d, local CPU)',
        'hypothesis':{'A':'Basic fixed-size baseline, risk of cutting evidence',
                     'B':'Paragraph boundaries improve standalone answerability',
                     'C':'Explicit chapter filter may improve scoped searches, identical chunks to B'}[s],
        'dev_hit1':f"{bench['dev']['hit1_n']}/{bench['dev']['questions']}",
        'dev_hit3':f"{bench['dev']['hit3_n']}/{bench['dev']['questions']}",
        'test_hit1':f"{bench['test']['hit1_n']}/{bench['test']['questions']}",
        'test_hit3':f"{bench['test']['hit3_n']}/{bench['test']['questions']}",
        'notes':f"coherence {summary['coherence_ai_review'][s]['mean_0_2']}/2; "
                f"grounding {summary['grounding_ai_review'][s]['mean_0_2']}/2 (AI-assisted); "
                f"{summary['metadata_audit'][s]['correct']}/15 metadata correct; "
                f"physical chunks {cp3[source]['chunk_count']}; "
                f"selection locked B before test"})
with (R/'artifacts/experiment_log.csv').open('w',newline='',encoding='utf-8') as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
print('Wrote 3 measured rows to artifacts/experiment_log.csv')
