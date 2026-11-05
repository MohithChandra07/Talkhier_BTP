#!/usr/bin/env python3
"""
Sprint 3 Optimization: Benchmark Runner
Runs the optimized graph-level forced evaluator integration on Problems 0–4.
Outputs to: results/experiment_d_graph_opt/

Compares:
- Condition A (Original TalkHier baseline - loaded or executed)
- Condition B Baseline (Sprint 3 unoptimized)
- Condition B Optimized (Sprint 3 optimized with specialized guidance, robust parsing, and revisor safeguards)
"""

import os
import sys
import time
import json
import csv
import argparse
from typing import Dict, Any, List, Optional
from datasets import load_dataset
from langchain_core.messages import HumanMessage, AIMessage

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from experiments import loadConfig
from multiagent.llm import LLM
import multiagent.agent_team as agent_team
import prompts.mmlu as MMLUPrompt
from multiagent.graph_dispatch import evaluate_revision_quality, EVALUATOR_NAMES_FORMAL_LOGIC
from multiagent.graph_dispatch_opt import (
    build_optimized_graph_dispatch_team,
)


def run_condition_b_opt(
    problem_id: int,
    problem: Dict[str, Any],
    config: Dict[str, Any],
    domain: str = "formal_logic",
) -> Dict[str, Any]:
    """
    Runs Condition B Optimized: Mandatory graph-level evaluator execution with
    domain-specialized reasoning, robust parsing, zero-leakage revisor safeguards.
    """
    print(f"\n{'='*75}")
    print(f"[Sprint 3 Optimization - Condition B Optimized] Running Problem {problem_id}...")
    print(f"Question: {problem['question'][:120]}...")
    print(f"Ground Truth: {problem['answer']}")
    print(f"{'='*75}\n", flush=True)

    t0 = time.time()
    prompts = MMLUPrompt.getPrompts(domain, problem)
    react_generator = agent_team.ReactAgent(
        intermediate_output_desc=prompts["intermediate_output_desc"],
        config=config,
        llm=LLM(config).llm,
    )

    # Build the optimized sequential graph
    graph = build_optimized_graph_dispatch_team(prompts, react_generator, problem)

    initial_state = {
        "history": {
            "Answer Generator": [HumanMessage(content=prompts["team"]["prompt"])],
            "Default Supervisor": [HumanMessage(content=prompts["team"]["prompt"])],
            "all": [HumanMessage(content=prompts["team"]["prompt"])],
        },
        "messages": HumanMessage(content=prompts["team"]["prompt"]),
        "background": AIMessage(content=problem["question"], name="Default Supervisor"),
        "intermediate_output": {},
        "next": "Answer Generator",
        "initial_prompt": prompts["team"]["Answer Generator"]["prompt"],
        "_initial_intermediate_output": {},
        "_evaluator_trace": [],
        "_individual_evaluations": {},
        "_evaluation_aggregation": {},
        "_revision_history": [],
    }

    final_state = graph.invoke(initial_state)
    elapsed = round(time.time() - t0, 2)

    a0_dict = final_state.get("_initial_intermediate_output", {})
    a0_choice = a0_dict.get("choice", -1)

    final_io = final_state.get("intermediate_output", {})
    final_choice = final_io.get("choice", a0_choice)

    gt = problem["answer"]
    agg = final_state.get("_evaluation_aggregation", {})
    rev_hist = final_state.get("_revision_history", [])
    last_rev = rev_hist[-1] if rev_hist else {}
    decision = last_rev.get("decision", "RETAINED")
    revision_quality = evaluate_revision_quality(a0_choice, final_choice, gt)

    eval_trace = final_state.get("_evaluator_trace", [])
    eval_names_invoked = [e["name"] for e in eval_trace if e.get("invoked")]
    total_retries = sum(e.get("retries", 0) for e in eval_trace)
    retries_detail = {e["name"]: e.get("retries", 0) for e in eval_trace}

    return {
        "problem_id": problem_id,
        "condition": "Condition_B_Graph_Dispatch_Opt",
        "ground_truth": gt,
        "a0_choice": a0_choice,
        "final_choice": final_choice,
        "a0_correct": (a0_choice == gt),
        "final_correct": (final_choice == gt),
        "answer_changed": (final_choice != a0_choice),
        "all_five_evaluators_invoked": (len(eval_names_invoked) == 5),
        "evaluators_invoked_count": len(eval_names_invoked),
        "invoked_evaluators_list": eval_names_invoked,
        "applicable_count": agg.get("applicable_count", 0),
        "valid_scores_count": agg.get("valid_count", 0),
        "not_applicable_count": agg.get("not_applicable_count", 0),
        "invalid_count": agg.get("invalid_count", 0),
        "individual_scores": agg.get("individual_scores", {}),
        "individual_statuses": agg.get("individual_statuses", {}),
        "mean_score": agg.get("mean_score"),
        "disagreement_detected": agg.get("disagreement_detected", False),
        "score_range": agg.get("score_range", 0),
        "is_complete": agg.get("is_complete", False),
        "consensus_type": agg.get("consensus_type", "UNKNOWN"),
        "supports_initial_answer": agg.get("supports_initial_answer", False),
        "revisor_decision": decision,
        "revision_quality": revision_quality,
        "total_evaluator_retries": total_retries,
        "retries_detail": retries_detail,
        "runtime_s": elapsed,
        "revision_history": rev_hist,
        "_initial_intermediate_output": a0_dict,
        "_evaluator_trace": eval_trace,
    }


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_cfg = os.path.join(base_dir, "config", "config.ini")
    default_lcfg = os.path.join(base_dir, "config", "config_llm.ini")

    parser = argparse.ArgumentParser(description="Sprint 3 Optimization Benchmark Runner")
    parser.add_argument("--config", default=default_cfg)
    parser.add_argument("--llm-config", default=default_lcfg)
    parser.add_argument("--problems", nargs="+", type=int, default=[0, 1, 2, 3, 4])
    parser.add_argument("--out-dir", default=os.path.join(base_dir, "results", "experiment_d_graph_opt"))
    parser.add_argument("--baseline-dir", default=os.path.join(base_dir, "results", "experiment_d_graph"))
    args = parser.parse_args()

    config = loadConfig(args.config, args.llm_config)
    os.makedirs(args.out_dir, exist_ok=True)
    traces_dir = os.path.join(args.out_dir, "traces")
    os.makedirs(traces_dir, exist_ok=True)

    dataset = load_dataset("cais/mmlu", "formal_logic")["test"]

    summary_csv = os.path.join(args.out_dir, "experiment_d_graph_opt_summary.csv")
    comparison_csv = os.path.join(args.out_dir, "experiment_d_graph_opt_comparison.csv")

    summary_rows = []
    comparison_rows = []

    print(f"\n================================================================================")
    print(f"Starting Sprint 3 Optimization Benchmark on problems: {args.problems}")
    print(f"Results output dir: {args.out_dir}")
    print(f"Baseline comparison dir: {args.baseline_dir}")
    print(f"================================================================================\n")

    for pid in args.problems:
        prob = dataset[pid]

        # 1. Load baseline traces for comparison
        base_trace_a = os.path.join(args.baseline_dir, "traces", f"problem_{pid}_condition_a.json")
        base_trace_b = os.path.join(args.baseline_dir, "traces", f"problem_{pid}_condition_b.json")

        res_a = None
        res_b_base = None

        if os.path.exists(base_trace_a):
            with open(base_trace_a, "r") as f:
                res_a = json.load(f)
        if os.path.exists(base_trace_b):
            with open(base_trace_b, "r") as f:
                res_b_base = json.load(f)

        # 2. Run Optimized Condition B
        res_b_opt = run_condition_b_opt(pid, prob, config)

        # Save trace
        trace_path_opt = os.path.join(traces_dir, f"problem_{pid}_condition_b_opt.json")
        with open(trace_path_opt, "w") as f:
            json.dump(res_b_opt, f, indent=2, default=str)

        print(f"\n>>> Problem {pid} Optimized Results:")
        print(f"    Ground Truth: {res_b_opt['ground_truth']}")
        print(f"    A0 Choice: {res_b_opt['a0_choice']} (Correct: {res_b_opt['a0_correct']})")
        print(f"    Final Choice: {res_b_opt['final_choice']} (Correct: {res_b_opt['final_correct']})")
        print(f"    Revisor Decision: {res_b_opt['revisor_decision']} -> Quality: {res_b_opt['revision_quality']}")
        print(f"    Evaluator Scores: {res_b_opt['individual_scores']} (Mean: {res_b_opt['mean_score']})")
        print(f"    Evaluator Retries: {res_b_opt['total_evaluator_retries']} (Detail: {res_b_opt['retries_detail']})")
        print(f"    Runtime: {res_b_opt['runtime_s']}s")
        if res_b_base:
            print(f"    Baseline Final Choice was: {res_b_base.get('final_choice')} ({res_b_base.get('revision_quality')}) in {res_b_base.get('runtime_s')}s")
        print(f"{'='*75}\n", flush=True)

        # Summary row
        summary_rows.append({
            "problem_id": pid,
            "condition": "Condition_B_Graph_Dispatch_Opt",
            "ground_truth": res_b_opt["ground_truth"],
            "a0_choice": res_b_opt["a0_choice"],
            "final_choice": res_b_opt["final_choice"],
            "a0_correct": res_b_opt["a0_correct"],
            "final_correct": res_b_opt["final_correct"],
            "evaluators_invoked_count": res_b_opt["evaluators_invoked_count"],
            "valid_scores_count": res_b_opt["valid_scores_count"],
            "not_applicable_count": res_b_opt["not_applicable_count"],
            "invalid_count": res_b_opt["invalid_count"],
            "mean_score": res_b_opt["mean_score"],
            "disagreement_detected": res_b_opt["disagreement_detected"],
            "total_retries": res_b_opt["total_evaluator_retries"],
            "revisor_decision": res_b_opt["revisor_decision"],
            "revision_quality": res_b_opt["revision_quality"],
            "runtime_s": res_b_opt["runtime_s"],
        })

        # Comparison row across Baseline A, Baseline B, and Optimized B
        comparison_rows.append({
            "problem_id": pid,
            "ground_truth": res_b_opt["ground_truth"],
            "cond_a_choice": res_a.get("final_choice") if res_a else "N/A",
            "cond_a_correct": res_a.get("final_correct") if res_a else "N/A",
            "cond_a_evals": res_a.get("evaluators_invoked_count") if res_a else "N/A",
            "cond_a_runtime_s": res_a.get("runtime_s") if res_a else "N/A",
            "cond_b_base_choice": res_b_base.get("final_choice") if res_b_base else "N/A",
            "cond_b_base_correct": res_b_base.get("final_correct") if res_b_base else "N/A",
            "cond_b_base_quality": res_b_base.get("revision_quality") if res_b_base else "N/A",
            "cond_b_base_runtime_s": res_b_base.get("runtime_s") if res_b_base else "N/A",
            "cond_b_opt_a0": res_b_opt["a0_choice"],
            "cond_b_opt_final": res_b_opt["final_choice"],
            "cond_b_opt_correct": res_b_opt["final_correct"],
            "cond_b_opt_quality": res_b_opt["revision_quality"],
            "cond_b_opt_mean_score": res_b_opt["mean_score"],
            "cond_b_opt_retries": res_b_opt["total_evaluator_retries"],
            "cond_b_opt_runtime_s": res_b_opt["runtime_s"],
        })

        # Incremental CSV write
        with open(summary_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
            writer.writeheader()
            writer.writerows(summary_rows)

        with open(comparison_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(comparison_rows[0].keys()))
            writer.writeheader()
            writer.writerows(comparison_rows)

    print("\nBenchmark completed successfully.")
    print(f"Summary CSV: {summary_csv}")
    print(f"Comparison CSV: {comparison_csv}")


if __name__ == "__main__":
    main()

