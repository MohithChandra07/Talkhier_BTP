#!/usr/bin/env python3
"""
Week 2 Experiment C: Feedback-Order Sensitivity Analysis for TalkHier BTP
Evaluates whether reversing the order of evaluator agents in the hierarchy
affects initial answers, revisions, final answers, and accuracy.

Selected Problems (3-problem pilot with documented selection criteria):
  - Problem 0: Argument conclusion identification; case where revision helped in baseline (0 -> 3, GT: 3)
  - Problem 3: Truth-table argument validity; case where revision helped in baseline (2 -> 0, GT: 0)
  - Problem 4: Propositional/predicate logic translation; case where final answer remained incorrect in baseline (0 -> 0, GT: 1)
"""

import os
import sys
import time
import csv
import json
import configparser
import argparse
from datasets import load_dataset

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from experiments import loadConfig, mmlu
import prompts.mmlu as MMLUPrompt

def run_condition(problem_id, reverse_evaluators, config, domain="formal_logic"):
    dataset = load_dataset("cais/mmlu", domain)["test"]
    problem = dataset[problem_id]
    
    order_label = "reversed" if reverse_evaluators else "original"
    print(f"\n{'='*70}")
    print(f"Running Problem {problem_id} under {order_label.upper()} evaluator order...")
    print(f"Question: {problem['question'][:80]}...")
    print(f"Ground Truth Answer: {problem['answer']}")
    print(f"{'='*70}\n", flush=True)
    
    t0 = time.time()
    prompt = MMLUPrompt.getPrompts(domain, problem, reverse_evaluators=reverse_evaluators)
    final_choice, pre_choice = mmlu(problem, prompt, config)
    elapsed = time.time() - t0
    
    correct = (final_choice == problem['answer'])
    pre_correct = (pre_choice == problem['answer'])
    
    print(f"\nProblem {problem_id} [{order_label.upper()}] finished in {elapsed:.2f}s")
    print(f"  Pre-Revision Answer: {pre_choice} (Correct: {pre_correct})")
    print(f"  Final Answer:        {final_choice} (Correct: {correct})")
    print(f"  Ground Truth:        {problem['answer']}")
    print(f"  Outcome:             {'CORRECT' if correct else 'INCORRECT'}")
    
    return {
        "problem_id": problem_id,
        "condition": order_label,
        "pre_revision": pre_choice,
        "final_answer": final_choice,
        "ground_truth": problem['answer'],
        "pre_correct": pre_correct,
        "correct": correct,
        "runtime_s": round(elapsed, 2)
    }

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_cfg = os.path.join(base_dir, "config", "config.ini")
    default_lcfg = os.path.join(base_dir, "config", "config_llm.ini")

    parser = argparse.ArgumentParser(description="Week 2 Experiment C: Feedback-Order Sensitivity")
    parser.add_argument("--config", default=default_cfg)
    parser.add_argument("--llm-config", default=default_lcfg)
    parser.add_argument("--problems", nargs="+", type=int, default=[0, 3, 4],
                        help="List of problem IDs to evaluate (default: 0 3 4)")
    default_csv = os.path.join(base_dir, "results", "formal_logic", "experiment_c_results.csv")
    parser.add_argument("--out-csv", default=default_csv)
    parser.add_argument("--run-original", action="store_true", default=False,
                        help="Also re-run original order instead of loading from verified baseline")
    args = parser.parse_args()

    config = loadConfig(args.config, args.llm_config)
    
    # Baseline verified results for reference
    baseline_lookup = {
        0: {"pre_revision": 0, "final_answer": 3, "ground_truth": 3, "correct": True, "runtime_s": 300.0},
        3: {"pre_revision": 2, "final_answer": 0, "ground_truth": 0, "correct": True, "runtime_s": 651.28},
        4: {"pre_revision": 0, "final_answer": 0, "ground_truth": 1, "correct": False, "runtime_s": 253.13},
    }
    
    all_results = []
    
    # 1. Original condition
    for pid in args.problems:
        if args.run_original or pid not in baseline_lookup:
            res = run_condition(pid, reverse_evaluators=False, config=config)
        else:
            b = baseline_lookup[pid]
            res = {
                "problem_id": pid,
                "condition": "original (baseline)",
                "pre_revision": b["pre_revision"],
                "final_answer": b["final_answer"],
                "ground_truth": b["ground_truth"],
                "pre_correct": b["pre_revision"] == b["ground_truth"],
                "correct": b["correct"],
                "runtime_s": b["runtime_s"]
            }
        all_results.append(res)

    # 2. Reversed condition
    for pid in args.problems:
        res = run_condition(pid, reverse_evaluators=True, config=config)
        all_results.append(res)
        
        # Save incrementally
        os.makedirs(os.path.dirname(args.out_csv), exist_ok=True)
        with open(args.out_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "problem_id", "condition", "pre_revision", "final_answer",
                "ground_truth", "pre_correct", "correct", "runtime_s"
            ])
            writer.writeheader()
            writer.writerows(all_results)

    # 3. Print Comparison Table
    print("\n" + "="*80)
    print("EXPERIMENT C: FEEDBACK-ORDER SENSITIVITY COMPARISON")
    print("="*80)
    print(f"{'Prob':<5} | {'Condition':<20} | {'Pre-Rev':<8} | {'Final':<6} | {'GT':<3} | {'Correct?':<8} | {'Runtime (s)':<10}")
    print("-" * 80)
    for r in all_results:
        corr_mark = "✓ PASS" if r['correct'] else "✗ FAIL"
        print(f"{r['problem_id']:<5} | {r['condition']:<20} | {r['pre_revision']:<8} | {r['final_answer']:<6} | {r['ground_truth']:<3} | {corr_mark:<8} | {r['runtime_s']:<10}")
    print("="*80)

if __name__ == "__main__":
    main()
