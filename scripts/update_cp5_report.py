"""Update the individual report from immutable real CP5 metrics."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=root/'report/individual/2A202603551_NguyenVanMinh.md'
s=json.loads((root/'starter/results/cp5_summary.json').read_text(encoding='utf8'))
text=p.read_text(encoding='utf8')
text=text.replace('Status: CP1 through CP4 complete; CP5-CP6 pending. This document will be updated as experiments are actually run.',
                  'Status: CP1 through CP5 complete; CP6 final submission review pending.')
a=text.index('## 3. Ket qua retrieval (pending CP5; CP4 storage measured separately)')
b=text.index('## 4. AI assistance and verification',a)
metric='## 3. CP5 - Measured benchmark and five-dimension audit\n\n'
metric+='Selection order: 15 Dev questions (45 searches), then frozen strategy B, then 5 held-out Test questions (15 searches). No Test tuning. Strict scoring requires complete gold evidence in one chunk with matching document ID and physical PDF page.\n\n'
metric+='| Strategy | Dev Hit@1 | Dev Evidence Hit@3 | Test Hit@1 | Test Evidence Hit@3 |\n|---|---:|---:|---:|---:|\n'
for key in ('A','B','C'):
    m=s['metrics'][key]
    metric+=f"| {key} | {m['dev']['hit1_n']}/15 | {m['dev']['hit3_n']}/15 | {m['test']['hit1_n']}/5 | {m['test']['hit3_n']}/5 |\n"
metric+='\n| Strategy | Coherence (10 chunks, 0-2) | Metadata correct (5 Test x Top3) | Filter compliance | Grounding (5 Test, 0-2) |\n|---|---:|---:|---:|---:|\n'
for key in ('A','B','C'):
    x=s['coherence_ai_review'][key]; y=s['metadata_audit'][key]; z=s['grounding_ai_review'][key]
    filt=f"{y['filter_compliant']}/{y['filtered_topk']}" if y['filtered_topk'] else 'N/A (no filter)'
    metric+=f"| {key} | {x['sum']}/20 ({x['mean_0_2']:.1f}/2) | {y['correct']}/{y['total']} | {filt} | {z['sum']}/10 ({z['mean_0_2']:.1f}/2) |\n"
metric+='''\n- Selected B on Dev: B/C tied at Evidence Hit@3=12/15 and Hit@1=9/15; identical B/C chunk coherence=1.3/2; B requires no optional filter complexity. Pre-Test selection recorded in `starter/results/cp5_dev_selection.json`.
- Metadata correctness is cross-checked against the original manifest for all retrieved test chunks; Chapter 3/4 filtering in C is independently checked for the two filtered Test questions. A/B filter compliance is not applicable, not a failure.
- Strict failure examples: Q17 A retrieves the right area but splits the three-error-type sentence across chunks; B/C retrieve full evidence. Q20 B/C spread precondition/postcondition responsibilities across separate chunks and thus fail strict whole-quote matching despite partial useful evidence. Source excerpts and full Top3 traces are saved, not inferred from model scores.
- Grounding and coherence labels are **AI-assisted qualitative readings of actual chunk text**, with source IDs, quotes and rationale, not independently human-verified. Learner should review/confirm before claiming a human audit. Grounding evaluates evidence sufficiency, not generated answers.
- Strategy cost comparison: A=170 physical chunks / 76,930 chunk chars; B=160 / 69,744; C reuses B and introduces only retrieval-time chapter filtering. All embeddings are from the same local 384-d model (zero API charges, excluding local CPU/electricity). Cold and warm-cache time measurements must not be conflated. Timing details are in `cp3_statistics.json` and `cp4_run.log`.
- Caveats: 5 Test questions, single textbook, some malformed PDF glyphs; exact-single-chunk matching is deliberately conservative. No broadly generalizable superiority claimed.
- CP5 reproducibility/report evidence: `docs/CP5_EVALUATION.md`, `starter/results/cp5_summary.json`, `cp5_dev_traces.jsonl`, `cp5_test_traces.jsonl`, `cp5_dev_selection.json`, `cp5_coherence_dev.json`, `cp5_metadata_audit.csv`, `cp5_grounding_audit.csv`, `cp5_failure_cases.json`, and `artifacts/experiment_log.csv`.
\n'''
text=text[:a]+metric+text[b:]
text=text.replace('Manual review of retrieved evidence will be recorded in CP5. No retrieval or human audit metrics are claimed yet.',
                  'CP5 retrieval metrics are measured from saved top-3 traces; coherence/grounding scores are AI-assisted close-reading annotations, clearly disclosed and awaiting independent learner verification.')
text += '\n## 7. CP6 handoff\n\nPending final submission audit: verify README setup from clean environment, repo URL/access, source rights, final report completeness, and links. CP5 metrics are complete and should not be retrospectively tuned on Test.\n'
p.write_text(text,encoding='utf8')
print('Updated',p)
