#!/usr/bin/env python3
import glob
import json

files = glob.glob('results/experiment_sprint4_3/raw_traces/sprint4_full/*.json')
target_pids = [3, 6, 13, 14, 20, 23, 29, 31, 35, 36, 44, 48, 49, 67, 69, 73, 81, 87, 90, 95, 97, 101, 104, 108, 121, 122, 123]

data = sorted([json.load(open(f)) for f in files], key=lambda x: x['problem_id'])

print('| Problem ID | Domain | Question Type | GT | A0 Choice | Final Choice | Status | Revision Quality | Deterministic Proof | Latency |')
print('| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |')

for d in data:
    pid = d['problem_id']
    is_t = pid in target_pids
    dom = 'Target' if is_t else 'Control'
    det = d.get('deterministic_evidence', {})
    det_status = det.get('status', 'N/A')
    has_proof = det.get('has_authoritative_proof', False)
    proven = det.get('proven_choice_index')
    proof_str = f'{det_status} (Choice {proven})' if has_proof else det_status
    status_icon = '✅ Correct' if d['final_correct'] else '❌ Incorrect'
    qual = d.get('revision_quality', 'N/A')
    gt = d['ground_truth']
    a0 = d['a0_choice']
    final = d['final_choice']
    time_s = d['runtime_s']

    if not is_t:
        if pid in [0, 1]: q_type = 'NL Argument (Conclusion)'
        elif pid == 7: q_type = 'NL Conditional (Antecedent)'
        elif pid == 2: q_type = 'Predicate Relation (Txy)'
        elif pid in [4, 5, 10]: q_type = 'First-Order Quantifier'
        elif pid == 9: q_type = 'Categorical Proposition'
        else: q_type = 'Non-Propositional Control'
    else:
        if pid in [49, 69, 101]: q_type = 'Propositional w/ Predicates'
        elif det_status == 'VALID': q_type = 'Propositional Deductive (Valid)'
        else: q_type = 'Propositional Deductive (Invalid)'

    print(f'| **{pid}** | {dom} | {q_type} | `{gt}` | `{a0}` | `{final}` | {status_icon} | `{qual}` | `{proof_str}` | {time_s}s |')

