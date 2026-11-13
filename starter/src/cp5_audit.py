"""Fixed audit sampling and transparent, reviewable qualitative annotations."""
from __future__ import annotations
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
RESULTS=ROOT/'starter/results'
PAGES=[23,26,31,34,39,42,46,51,55,58]
# AI-assisted close reading of the exact chunk texts at deterministic positions.
# Reviewer should confirm before claiming independent human review.
NOTES={
 'A':[(1,'Begins mid-word; contains a useful definition, but trails off mid-word.'),
      (1,'Connects numeric examples to language differences, but crosses a section boundary.'),
      (1,'Begins in the middle of a sentence and changes from assignments to names.'),
      (1,'Starts in the middle of a definition; coherent string examples follow.'),
      (1,'Opens mid-explanation and ends near a cut conversion example.'),
      (1,'Opens mid-quoted output, but includes a complete function code example.'),
      (1,'Contains good examples but begins mid-expression and ends mid-definition.'),
      (1,'Combines chapter setup and turtle introduction with a partial final sentence.'),
      (1,'Discusses polygon circle approximation but cuts at a line/window boundary.'),
      (1,'Begins mid-word; combines debugging notes with a glossary.')],
 'B':[(2,'Starts at the section heading and keeps the program definition with its explanation.'),
      (2,'Complete self-contained example about comma-separated integers.'),
      (0,'Isolated figure-reference sentence with no useful explanation or context.'),
      (2,'Starts at string-operations heading and preserves related examples.'),
      (2,'Complete function-call heading and detailed introduction with examples.'),
      (0,'Short tail of song output; detached from the code that generated it.'),
      (2,'Explains fruitful functions with complete use examples.'),
      (0,'Only a link to external source code with no useful standalone explanation.'),
      (2,'Section heading, complete circle function and explanation are grouped.'),
      (1,'Short but meaningful standalone postcondition/debugging statement.')],
}

def chunks(strategy):
    file=RESULTS/('cp3_chunks_A_fixed.jsonl' if strategy=='A' else 'cp3_chunks_B_paragraph.jsonl')
    return [json.loads(line) for line in file.read_text(encoding='utf-8').splitlines()]

def create_coherence():
    target=RESULTS/'cp5_coherence_dev.json'
    if target.exists():raise RuntimeError('Pre-test coherence already captured')
    records={}
    for s in ('A','B'):
        cs=chunks(s)
        items=[]
        for p,(score,note) in zip(PAGES,NOTES[s]):
            source=[c for c in cs if c['page']==p]
            picked=source[len(source)//2]
            items.append({'pdf_page':p,'chunk_id':picked['chunk_id'],
                          'chunk_index':picked['metadata']['chunk_index'],
                          'chunk_chars':len(picked['text']),
                          'chunk_sha256':hashlib.sha256(picked['text'].encode('utf-8')).hexdigest(),
                          'score_0_2':score,'rationale':note,
                          'text_excerpt':picked['text'][:320]})
        records[s]={'mean':sum(x['score_0_2'] for x in items)/len(items),
                    'count':len(items),'sample':items}
    records['C']={**records['B'],'same_chunks_as':'B','note':'C uses identical B chunks; coherence cannot differ.'}
    records['protocol']={'position_selection':'One centered-by-index chunk from each of 10 predeclared physical PDF pages: '+str(PAGES),
      'rubric':'0=fragment/lacks standalone meaning; 1=partially coherent with cuts or weak context; 2=coherent with sufficient context.',
      'review_provenance':'AI-assisted close reading of actual chunk excerpts; not claimed as independent human reviewer; learner validation recommended.',
      'created_before_test':'yes','strategy_blind':'no (A/B are visibly different)'}
    target.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('COHERENCE CREATED', {k:records[k]['mean'] for k in ('A','B','C')})

if __name__=='__main__':create_coherence()
