#!/usr/bin/env python3
"""
Week 2 Analysis Scripts for TalkHier BTP
Analyzes harmful revisions, evaluator agreement, and generates summary tables.
"""
import csv
import sys
import os
from collections import Counter

def load_csv(path):
    """Load baseline CSV and return list of dicts."""
    rows = []
    with open(path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip placeholder rows
            if row.get('Answer', '-') == '-':
                continue
            rows.append({
                'problem_id': int(row['Problem ID']),
                'answer': int(row['Answer']),
                'correct': int(row['Correct Answer']),
                'pre_revision': int(row['Pre-Revision']),
            })
    return rows

def analyze_revisions(rows):
    """Experiment A: Harmful Revisions Analysis."""
    print("\n" + "="*60)
    print("EXPERIMENT A: HARMFUL REVISIONS ANALYSIS")
    print("="*60)
    
    categories = {
        'correct_stayed_correct': [],     # C→C
        'incorrect_to_correct': [],       # I→C (revision helped)
        'correct_to_incorrect': [],       # C→I (revision harmed)
        'incorrect_stayed_incorrect': [], # I→I
    }
    
    for r in rows:
        pre_correct = (r['pre_revision'] == r['correct'])
        final_correct = (r['answer'] == r['correct'])
        
        if pre_correct and final_correct:
            categories['correct_stayed_correct'].append(r)
        elif not pre_correct and final_correct:
            categories['incorrect_to_correct'].append(r)
        elif pre_correct and not final_correct:
            categories['correct_to_incorrect'].append(r)
        else:
            categories['incorrect_stayed_incorrect'].append(r)
    
    total = len(rows)
    pre_accuracy = sum(1 for r in rows if r['pre_revision'] == r['correct']) / total * 100
    final_accuracy = sum(1 for r in rows if r['answer'] == r['correct']) / total * 100
    
    print(f"\nTotal problems analyzed: {total}")
    print(f"\nPre-Revision accuracy:  {pre_accuracy:.1f}% ({sum(1 for r in rows if r['pre_revision'] == r['correct'])}/{total})")
    print(f"Final accuracy:         {final_accuracy:.1f}% ({sum(1 for r in rows if r['answer'] == r['correct'])}/{total})")
    print(f"Accuracy change:        {final_accuracy - pre_accuracy:+.1f}%")
    
    print(f"\n{'Category':<35} {'Count':>5} {'Problems':<30}")
    print("-" * 70)
    for label, items in [
        ('Correct → Correct (stable)', categories['correct_stayed_correct']),
        ('Incorrect → Correct (helped)', categories['incorrect_to_correct']),
        ('Correct → Incorrect (HARMED)', categories['correct_to_incorrect']),
        ('Incorrect → Incorrect (no help)', categories['incorrect_stayed_incorrect']),
    ]:
        pids = ', '.join(str(r['problem_id']) for r in items)
        print(f"{label:<35} {len(items):>5}  {pids:<30}")
    
    print(f"\n{'Revision net effect:':<35} ", end="")
    helped = len(categories['incorrect_to_correct'])
    harmed = len(categories['correct_to_incorrect'])
    if helped > harmed:
        print(f"POSITIVE (+{helped - harmed} net correct)")
    elif harmed > helped:
        print(f"NEGATIVE (-{harmed - helped} net correct) ⚠️")
    else:
        print(f"NEUTRAL (0 net change)")
    
    # Detail table
    print(f"\n{'Prob':>4} | {'Pre-Rev':>7} | {'Final':>5} | {'GT':>2} | {'Pre OK':>6} | {'Final OK':>8} | {'Effect':<20}")
    print("-" * 70)
    for r in sorted(rows, key=lambda x: x['problem_id']):
        pre_ok = '✓' if r['pre_revision'] == r['correct'] else '✗'
        final_ok = '✓' if r['answer'] == r['correct'] else '✗'
        if r['pre_revision'] == r['answer']:
            effect = 'No change'
        elif pre_ok == '✗' and final_ok == '✓':
            effect = 'HELPED'
        elif pre_ok == '✓' and final_ok == '✗':
            effect = 'HARMED ⚠️'
        elif pre_ok == '✗' and final_ok == '✗':
            effect = 'Changed (still wrong)'
        else:
            effect = 'Maintained'
        print(f"{r['problem_id']:>4} | {r['pre_revision']:>7} | {r['answer']:>5} | {r['correct']:>2} | {pre_ok:>6} | {final_ok:>8} | {effect:<20}")
    
    return {
        'pre_accuracy': pre_accuracy,
        'final_accuracy': final_accuracy,
        'helped': helped,
        'harmed': harmed,
        'total': total,
    }


def analyze_evaluator_log(log_path):
    """Experiment B: Extract evaluator judgments from execution log."""
    print("\n" + "="*60)
    print("EXPERIMENT B: EVALUATOR AGREEMENT ANALYSIS")
    print("="*60)
    
    if not os.path.exists(log_path):
        print(f"Log file not found: {log_path}")
        return
    
    with open(log_path, 'r') as f:
        content = f.read()
    
    # Look for evaluator scores in the log
    import re
    score_pattern = re.compile(r'"Correctness Score":\s*(\d+)')
    scores = score_pattern.findall(content)
    
    print(f"\nTotal evaluator scores found in log: {len(scores)}")
    score_counts = Counter(scores)
    for score, count in sorted(score_counts.items(), key=lambda x: -int(x[0])):
        print(f"  Score {score}: {count} occurrences")
    
    # Check if all evaluators always agree (score 10)
    all_ten = sum(1 for s in scores if s == '10')
    if all_ten == len(scores) and len(scores) > 0:
        print(f"\n⚠️  ALL {len(scores)} evaluator scores are 10/10.")
        print("   This suggests evaluators may produce misleading unanimous consensus,")
        print("   even when the final answer is incorrect (as observed in Problem 4).")
    
    # Look for evaluator agent names
    eval_pattern = re.compile(r'Agent: ((?:Formal Logic|Truth Table|Predicate Logic|Logical Argument)\s*\(\d+\))')
    evaluators = eval_pattern.findall(content)
    eval_names = set(e.split(' (')[0] for e in evaluators)
    print(f"\nEvaluator agents identified: {', '.join(sorted(eval_names))}")
    
    return {
        'total_scores': len(scores),
        'score_distribution': dict(score_counts),
        'evaluator_names': sorted(eval_names),
    }


if __name__ == '__main__':
    csv_path = sys.argv[1] if len(sys.argv) > 1 else '../results/formal_logic/baseline_qwen3.csv'
    log_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    print("TalkHier BTP — Week 2 Analysis")
    print(f"CSV: {csv_path}")
    
    rows = load_csv(csv_path)
    if not rows:
        print("No completed results found in CSV. Waiting for experiment to finish.")
        sys.exit(0)
    
    revision_results = analyze_revisions(rows)
    
    if log_path:
        evaluator_results = analyze_evaluator_log(log_path)
    else:
        print("\nNo log path provided for evaluator analysis. Usage:")
        print("  python week2_analysis.py <csv_path> <log_path>")
