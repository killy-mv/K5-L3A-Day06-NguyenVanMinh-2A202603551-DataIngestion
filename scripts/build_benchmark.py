"""Construct the CP2 gold benchmark from real, exact PDF evidence.

Run only before retrieval evaluation. The existing benchmark is never overwritten.
"""
from __future__ import annotations
import hashlib
import json
import logging
import re
import unicodedata
from pathlib import Path
from pypdf import PdfReader
logging.getLogger('pypdf').setLevel(logging.ERROR)
ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/'benchmark/questions.json'
LOCK=ROOT/'benchmark/split_lock.json'

# (id, split, type, PDF page, question, expected answer, evidence start, evidence end, chapter filter)
SEEDS=[
('Q01','dev','direct',23,'According to Chapter 1, what is a program?',
 'A sequence of instructions specifying how to perform a computation.',
 'Aprogramis a sequence of instructions','perform a computation.','chapter_1'),
('Q02','dev','paraphrase',24,'What environment does the author recommend for beginners to start running Python?',
 'Run Python in a web browser first, to avoid learning system administration and programming simultaneously.',
 'To avoid that problem, I recommend','in a browser.',None),
('Q03','dev','direct',25,'Which Python operator performs exponentiation rather than bitwise XOR?',
 '** is exponentiation; ^ is bitwise XOR.',
 'Finally, the operator**performs exponentiation','a number to a power:',None),
('Q04','dev','direct',26,'In the book, what are the types of the example values 2 and 42.0?',
 '2 is an integer and 42.0 is a floating-point number.',
 'These values belong to differenttypes:','strung together.',None),
('Q05','dev','paraphrase',27,'What two aspects are governed by formal-language syntax rules?',
 'Rules govern tokens (legal basic elements) and the structure/combination of tokens.',
 'Syntax rules come in two flavors','tokensand structure.',None),
('Q06','dev','direct',31,'How does Chapter 2 define a variable?',
 'A variable is a name that refers to a value.',
 'A variable is a name','refers to a value.',None),
('Q07','dev','conditional',32,'In Chapter 2, why is class not permitted as a variable name?',
 'class is a reserved Python keyword; keywords are used by the interpreter and cannot be variable names.',
 'It turns out thatclassis one of Python','variable names.','chapter_2'),
('Q08','dev','conditional',33,'Why does a bare expression produce no visible output in Python script mode, and what should be used instead?',
 'A bare expression is evaluated without displaying its result; use print to display it.',
 'In script mode an expression, all by itself','need aprintstatement',None),
('Q09','dev','direct',34,'What is string concatenation using the + operator?',
 'It joins strings end-to-end.',
 'The+operator performsstring concatenation','end-to-end.',None),
('Q10','dev','paraphrase',35,'Should a useful code comment prioritize explaining what the code does or why it does it?',
 'It is more useful to explain why, especially for non-obvious behavior.',
 'Comments are most useful when','explainwhy.',None),
('Q11','dev','conditional',39,'Does int() round floating-point inputs or truncate their fractional part?',
 'It truncates/removes the fractional part rather than rounding.',
 'intcan convert floating-point values to integers','fraction part:',None),
('Q12','dev','direct',40,'In Chapter 3, how are functions in a module accessed using dot notation?',
 'Use the module name and the function name separated by a dot.',
 'To access one of the functions','calleddot notation.','chapter_3'),
('Q13','dev','conditional',42,'Does defining a function immediately run its body or print output?',
 'No. Defining creates a function object; the statements in its body run only when called, and a definition produces no output.',
 'This program contains two function definitions:','generates no output.',None),
('Q14','dev','direct',52,'In Chapter 4, what Turtle methods move backward and turn left or right?',
 'bk moves backward, lt turns left, and rt turns right. Turn arguments are angles in degrees.',
 'Other methods you can call on a Turtle arebk','angle in degrees.','chapter_4'),
('Q15','dev','paraphrase',54,'Why does adding a length parameter to square() count as generalization?',
 'The parameter replaces a fixed square size and allows the function to draw squares of any size.',
 'Adding a parameter to a function is calledgeneralization','any size.',None),
('Q16','test','direct',28,'What is the distinction between a programming bug and debugging?',
 'A bug is a programming error; debugging is the process of tracking such errors down.',
 'Programmers make mistakes.','calleddebugging.',None),
('Q17','test','direct',35,'Which three kinds of program errors are distinguished in Chapter 2?',
 'Syntax errors, runtime errors, and semantic errors.',
 'Three kinds of errors can occur in a program:','semantic errors.',None),
('Q18','test','conditional',46,'According to Chapter 3, what value is assigned when you store the result of a void function?',
 'The special value None, even though the function may have other effects like printing.',
 'Void functions might display something','calledNone.','chapter_3'),
('Q19','test','paraphrase',57,'What does refactoring change and why is it performed?',
 'It rearranges program code to improve interfaces and facilitate code reuse.',
 'This process','calledrefactoring.',None),
('Q20','test','conditional',58,'In Chapter 4, who is responsible when a documented precondition is violated versus when postconditions fail despite valid preconditions?',
 'The caller is responsible for violated preconditions; the function is responsible if preconditions hold but postconditions fail.',
 'Preconditions are the responsibility of the caller.','the bug is in the function.','chapter_4'),
]

def norm(s:str)->str:
    return ' '.join(unicodedata.normalize('NFKC',s).split())

def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')

def main():
    if TARGET.exists() or LOCK.exists():
        raise SystemExit('Benchmark is frozen; refusing to overwrite existing questions/split_lock.')
    manifest=json.loads((ROOT/'data/manifest.json').read_text(encoding='utf-8'))
    permitted={p['pdf_page']:p for p in manifest['pages']}
    reader=PdfReader(str(ROOT/manifest['local_path']))
    questions=[]
    for qid,split,kind,page,question,answer,a,b,chapter_filter in SEEDS:
        if page not in permitted: raise AssertionError(f'{qid}: invalid page {page}')
        text=norm(reader.pages[page-1].extract_text() or '')
        a=norm(a);b=norm(b)
        start=text.find(a)
        if start<0: raise AssertionError(f'{qid}: start anchor not found: {a!r}')
        stop=text.find(b,start+len(a))
        if stop<0: raise AssertionError(f'{qid}: end anchor not found: {b!r}')
        quote=text[start:stop+len(b)]
        if not 35<=len(quote)<=450: raise AssertionError(f'{qid}: unsuitable evidence length: {len(quote)}')
        questions.append({'id':qid,'split':split,'question_type':kind,'question':question,
         'expected_answer':answer,'gold_source_id':manifest['source_id'],
         'gold_page':page,'gold_printed_page':permitted[page]['printed_page'],
         'gold_page_id':permitted[page]['page_id'],'evidence_quote':quote,
         'filter':{'chapter':chapter_filter} if chapter_filter else None,
         'filter_origin':'explicit chapter scope in question' if chapter_filter else None,
         'evidence_verification':'Exact normalized substring of source PDF page; manually checked for answer support'})
    if len(questions)!=20 or sum(q['split']=='dev' for q in questions)!=15 or sum(q['split']=='test' for q in questions)!=5:
        raise AssertionError('Bad split')
    TARGET.parent.mkdir(parents=True,exist_ok=True)
    TARGET.write_text(json.dumps(questions,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lock={'status':'locked-before-retrieval','date':'2026-11-13',
       'corpus_sha256':manifest['sha256'],
       'questions_canonical_sha256':hashlib.sha256(canonical(questions)).hexdigest(),
       'dev_ids':[q['id'] for q in questions if q['split']=='dev'],
       'test_ids':[q['id'] for q in questions if q['split']=='test'],
       'selection_rule':'Select on dev only: maximize Evidence Hit@3, then Hit@1, coherence, and resource use. Evaluate test after freezing selection.',
       'notes':'No retrieval metrics were inspected when this benchmark was created.'}
    LOCK.write_text(json.dumps(lock,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('CREATED',len(questions),'questions, dev/test',len(lock['dev_ids']),len(lock['test_ids']))
    print('Filter count:',sum(bool(q['filter']) for q in questions))
    for q in questions: print(q['id'],q['split'],'pdf',q['gold_page'],'quote_len',len(q['evidence_quote']))
if __name__=='__main__': main()
