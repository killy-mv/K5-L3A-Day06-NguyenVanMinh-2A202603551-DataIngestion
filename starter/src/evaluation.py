"""Evidence-based retrieval evaluation for the frozen Day 06 benchmark.

Conservative automated hits require BOTH gold provenance and the full normalized
source evidence inside one retrieved chunk. Semantic equivalence is NOT inferred
from the cosine score or an LLM. Any manually adjudicated equivalent requires a
separate documented reviewer decision.
"""
from __future__ import annotations

from collections import Counter
from typing import Any
import unicodedata


def normalize_for_evidence(text: str) -> str:
    return ' '.join(unicodedata.normalize('NFKC', text).split())


def evaluate_query(question: dict[str, Any], hits: list[dict[str, Any]]) -> dict[str, Any]:
    if question['split'] not in ('dev', 'test'):
        raise ValueError('Unknown question split')
    evidence = normalize_for_evidence(question['evidence_quote'])
    if not evidence:
        raise ValueError('Gold evidence cannot be empty')
    if len(hits) > 3:
        raise ValueError('Only a top-3 trace can be evaluated here')
    assessed: list[dict[str, Any]] = []
    for rank, hit in enumerate(hits, start=1):
        match_source = hit['document_id'] == question['gold_source_id']
        match_page = int(hit['page']) == int(question['gold_page'])
        match_quote = evidence in normalize_for_evidence(hit['text'])
        assessed.append({**hit, 'rank': rank, 'gold_source_match': match_source,
                         'gold_page_match': match_page,
                         'full_gold_evidence_present': match_quote,
                         'evidence_hit': match_source and match_page and match_quote})
    hit1 = bool(assessed and assessed[0]['evidence_hit'])
    hit3 = any(h['evidence_hit'] for h in assessed)
    return {
        'id': question['id'], 'split': question['split'],
        'question_type': question['question_type'], 'question': question['question'],
        'expected_answer': question['expected_answer'],
        'gold_source_id': question['gold_source_id'], 'gold_page': question['gold_page'],
        'gold_page_id': question['gold_page_id'], 'evidence_quote': question['evidence_quote'],
        'requested_filter': question.get('filter'),
        'hit1': hit1, 'evidence_hit3': hit3,
        'metric_method': 'full normalized gold evidence within same chunk and matching gold source+page',
        'top3': assessed,
        'failure_type': None if hit3 else (
            'right_page_but_missing_complete_evidence'
            if any(h['gold_source_match'] and h['gold_page_match'] for h in assessed)
            else 'wrong_page_or_source'),
    }


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    if not traces:
        raise ValueError('Cannot summarize empty traces')
    by_key = {}
    for trace in traces:
        key = (trace['strategy'], trace['split'])
        by_key.setdefault(key, []).append(trace)
    result = {}
    for (strategy, split), cases in sorted(by_key.items()):
        n = len(cases)
        result.setdefault(strategy, {})[split] = {
            'questions': n, 'hit1_n': sum(bool(q['hit1']) for q in cases),
            'hit3_n': sum(bool(q['evidence_hit3']) for q in cases),
            'hit1': round(sum(bool(q['hit1']) for q in cases) / n, 4),
            'hit3': round(sum(bool(q['evidence_hit3']) for q in cases) / n, 4),
            'failure_types': dict(Counter(q['failure_type'] for q in cases if q['failure_type'])),
        }
    return result
