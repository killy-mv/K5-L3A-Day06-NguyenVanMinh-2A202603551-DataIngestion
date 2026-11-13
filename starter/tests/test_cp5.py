"""Conservative CP5 evaluator and frozen benchmark integration tests."""
import json
import unittest
from pathlib import Path
from src.cp5 import validate_frozen_inputs, RESULTS, sha
from src.evaluation import evaluate_query, summarize

class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.q={'id':'T','split':'dev','question_type':'direct','question':'?','expected_answer':'answer',
          'gold_source_id':'doc','gold_page':7,'gold_page_id':'doc_p007','evidence_quote':'a full  evidence','filter':None}
        self.good={'chunk_id':'a','document_id':'doc','page':7,'text':'x a full\nevidence y','score':0.5}
    def test_evidence_requires_same_chunk_and_provenance(self):
        ok=evaluate_query(self.q,[self.good]);self.assertTrue(ok['hit1']);self.assertTrue(ok['evidence_hit3'])
        bad=evaluate_query(self.q,[{**self.good,'page':8}]);self.assertFalse(bad['evidence_hit3'])
        cut=evaluate_query(self.q,[{**self.good,'text':'a full'},{**self.good,'text':'evidence'}])
        self.assertFalse(cut['evidence_hit3']);self.assertEqual(cut['failure_type'],'right_page_but_missing_complete_evidence')
    def test_late_hit_and_summary(self):
        bad={**self.good,'text':'unrelated','page':3}
        entry=evaluate_query(self.q,[bad,self.good]);entry['strategy']='A'
        self.assertFalse(entry['hit1']);self.assertTrue(entry['evidence_hit3'])
        m=summarize([entry])['A']['dev'];self.assertEqual((m['hit1_n'],m['hit3_n']),(0,1))
    def test_benchmark_lock_and_selection(self):
        qs,lock=validate_frozen_inputs();self.assertEqual((len(qs),len(lock['test_ids'])),(20,5))
        selected=json.loads((RESULTS/'cp5_dev_selection.json').read_text(encoding='utf-8'))
        self.assertEqual(selected['selected_strategy'],'B')
        self.assertEqual(selected['dev_traces_sha256'],sha(RESULTS/'cp5_dev_traces.jsonl'))
    def test_trace_counts_and_filter_compliance(self):
        records=[json.loads(x) for x in (RESULTS/'cp5_test_traces.jsonl').read_text(encoding='utf-8').splitlines()]
        self.assertEqual(len(records),15)
        self.assertEqual({x['id'] for x in records},{'Q16','Q17','Q18','Q19','Q20'})
        for x in records:
            self.assertEqual(len(x['top3']),3)
            if x['applied_filter']:
                self.assertEqual(x['strategy'],'C')
                self.assertTrue(all(h['chapter']==x['applied_filter']['chapter'] for h in x['top3']))

if __name__=='__main__':unittest.main()
