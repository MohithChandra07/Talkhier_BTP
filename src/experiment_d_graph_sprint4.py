#!/usr/bin/env python3
"""
Sprint 4 Benchmark Runner: Deterministic Evidence-Guided Multi-Agent Graph Integration
Evaluates Problems 0–4 using the Sprint 4 pipeline.
Outputs to: results/experiment_d_graph_sprint4/

Compares across all 4 conditions under identical LLM and problem configs:
- Condition A: Original TalkHier
- Condition B Baseline: Sprint 3 Unoptimized Graph
- Condition B Optimized: Sprint 3 Optimized Graph
- Condition B Sprint 4: Deterministic Evidence-Guided Graph
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
from multiagent.graph_dispatch_sprint4 import (
    build_sprint4_graph_dispatch_team,
)


def run_condition_b_sprint4(
    problem_id: int,
    problem: Dict[str, Any],
    config: Dict[str, Any],
    domain: str = "formal_logic",
) -> Dict[str, Any]:
    """
    Runs Condition B Sprint 4: Graph dispatch with deterministic verification node,
    evidence injection, and authoritative deterministic override.
    """
    print(f"\n{'='*75}")
    print(f"[Sprint 4 - Deterministic Evidence-Guided Graph] Running Problem {problem_id}...")
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

    # Build the Sprint 4 sequential graph
    graph = build_sprint4_graph_dispatch_team(prompts, react_generator, problem)

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
        "_deterministic_evidence": {},
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
    det = final_state.get("_deterministic_evidence", {})
    rev_hist = final_state.get("_revision_history", [])
    last_rev = rev_hist[-1] if rev_hist else {}
    decision = last_rev.get("decision", "RETAINED")
    det_override = last_rev.get("deterministic_override", False)
    revision_quality = evaluate_revision_quality(a0_choice, final_choice, gt)

    eval_trace = final_state.get("_evaluator_trace", [])
    eval_names_invoked = [e["name"] for e in eval_trace if e.get("invoked")]
    total_retries = sum(e.get("retries", 0) for e in eval_trace)
    retries_detail = {e["name"]: e.get("retries", 0) for e in eval_trace}

    return {
        "problem_id": problem_id,
        "condition": "Condition_B_Sprint4_Deterministic",
        "ground_truth": gt,
        "a0_choice": a0_choice,
        "final_choice": final_choice,
        "a0_correct": (a0_choice == gt),
        "final_correct": (final_choice == gt),
        "answer_changed": (final_choice != a0_choice),
        "all_five_evaluators_invoked": (len(eval_names_invoked) == 5),
        "evaluators_invoked_count": len(eval_names_invoked),
        "invoked_evaluators_list": eval_names_invoked,
        "deterministic_status": det.get("status", "NOT_APPLICABLE"),
        "has_authoritative_proof": det.get("has_authoritative_proof", False),
        "proven_choice_index": det.get("proven_choice_index"),
        "deterministic_override": det_override,
        "deterministic_evidence": det,
        "applicable_count": agg.get("applicable_count", 0),
        "valid_scores_count": agg.get("valid_count", 0),
        "not_applicable_count": agg.get("not_applicable_count", 0),
        "invalid_count": agg.get("invalid_count", 0),
        "individual_scores": agg.get("individual_scores", {}),
        "individual_statuses": agg.get("individual_statuses", {}),
        "mean_score": agg.get("mean_score"),
        "consensus_type": agg.get("consensus_type", "UNKNOWN"),
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

    parser = argparse.ArgumentParser(description="Sprint 4 Benchmark Runner")
    parser.add_argument("--config", default=default_cfg)
    parser.add_argument("--llm-config", default=default_lcfg)
    parser.add_argument("--problems", nargs="+", type=int, default=[0, 1, 2, 3, 4])
    parser.add_argument("--out-dir", default=os.path.join(base_dir, "results", "experiment_d_graph_sprint4"))
    parser.add_argument("--sprint3-base-dir", default=os.path.join(base_dir, "results", "experiment_d_graph"))
    parser.add_argument("--sprint3-opt-dir", default=os.path.join(base_dir, "results", "experiment_d_graph_opt"))
    args = parser.parse_args()

    config = loadConfig(args.config, args.llm_config)
    os.makedirs(args.out_dir, exist_ok=True)
    traces_dir = os.path.join(args.out_dir, "traces")
    os.makedirs(traces_dir, exist_ok=True)

    dataset = load_dataset("cais/mmlu", "formal_logic")["test"]

    summary_csv = os.path.join(args.out_dir, "experiment_d_graph_sprint4_summary.csv")
    comparison_csv = os.path.join(args.out_dir, "experiment_d_graph_sprint4_comparison.csv")

    summary_rows = []
    comparison_rows = []

    print(f"\n================================================================================")
    print(f"Starting Sprint 4 Benchmark on problems: {args.problems}")
    print(f"Results output dir: {args.out_dir}")
    print(f"Baseline comparison dir: {args.sprint3_base_dir}")
    print(f"Sprint 3 Opt comparison dir: {args.sprint3_opt_dir}")
    print(f"================================================================================\n")

    for pid in args.problems:
        prob = dataset[pid]

        # 1. Load prior traces for 4-way comparison
        base_trace_a = os.path.join(args.sprint3_base_dir, "traces", f"problem_{pid}_condition_a.json")
        base_trace_b = os.path.join(args.sprint3_base_dir, "traces", f"problem_{pid}_condition_b.json")
        opt_trace_b = os.path.join(args.sprint3_opt_dir, "traces", f"problem_{pid}_condition_b_opt.json")

        res_a = None
        res_b_base = None
        res_b_opt = None

        if os.path.exists(base_trace_a):
            with open(base_trace_a, "r") as f:
                res_a = json.load(f)
        if os.path.exists(base_trace_b):
            with open(base_trace_b, "r") as f:
                res_b_base = json.load(f)
        if os.path.exists(opt_trace_b):
            with open(opt_trace_b, "r") as f:
                res_b_opt = json.load(f)

        # 2. Run Sprint 4
        res_s4 = run_condition_b_sprint4(pid, prob, config)

        # Save trace
        trace_path_s4 = os.path.join(traces_dir, f"problem_{pid}_condition_b_sprint4.json")
        with open(trace_path_s4, "w") as f:
            json.dump(res_s4, f, indent=2, default=str)

        print(f"\n>>> Problem {pid} Sprint 4 Results:")
        print(f"    Ground Truth: {res_s4['ground_truth']}")
        print(f"    A0 Choice: {res_s4['a0_choice']} (Correct: {res_s4['a0_correct']})")
        print(f"    Final Choice: {res_s4['final_choice']} (Correct: {res_s4['final_correct']})")
        print(f"    Deterministic Status: {res_s4['deterministic_status']} | Has Proof: {res_s4['has_authoritative_proof']} | Proven Choice: {res_s4['proven_choice_index']}")
        print(f"    Deterministic Override: {res_s4['deterministic_override']}")
        print(f"    Revisor Decision: {res_s4['revisor_decision']} -> Quality: {res_s4['revision_quality']}")
        print(f"    Evaluator Scores: {res_s4['individual_scores']} (Mean: {res_s4['mean_score']})")
        print(f"    Evaluator Retries: {res_s4['total_evaluator_retries']}")
        print(f"    Runtime: {res_s4['runtime_s']}s")
        if res_b_opt:
            print(f"    Sprint 3 Opt Choice: {res_b_opt.get('final_choice')} ({res_b_opt.get('revision_quality')}) in {res_b_opt.get('runtime_s')}s")
        print(f"{'='*75}\n", flush=True)

        summary_rows.append({
            "problem_id": pid,
            "condition": "Condition_B_Sprint4_Deterministic",
            "ground_truth": res_s4["ground_truth"],
            "a0_choice": res_s4["a0_choice"],
            "final_choice": res_s4["final_choice"],
            "a0_correct": res_s4["a0_correct"],
            "final_correct": res_s4["final_correct"],
            "deterministic_status": res_s4["deterministic_status"],
            "has_authoritative_proof": res_s4["has_authoritative_proof"],
            "proven_choice_index": res_s4["proven_choice_index"],
            "deterministic_override": res_s4["deterministic_override"],
            "evaluators_invoked_count": res_s4["evaluators_invoked_count"],
            "mean_score": res_s4["mean_score"],
            "total_retries": res_s4["total_evaluator_retries"],
            "revisor_decision": res_s4["revisor_decision"],
            "revision_quality": res_s4["revision_quality"],
            "runtime_s": res_s4["runtime_s"],
        })

        comparison_rows.append({
            "problem_id": pid,
            "ground_truth": res_s4["ground_truth"],
            "cond_a_final": res_a.get("final_choice") if res_a else "N/A",
            "cond_a_correct": res_a.get("final_correct") if res_a else "N/A",
            "s3_base_final": res_b_base.get("final_choice") if res_b_base else "N/A",
            "s3_base_correct": res_b_base.get("final_correct") if res_b_base else "N/A",
            "s3_base_quality": res_b_base.get("revision_quality") if res_b_base else "N/A",
            "s3_opt_final": res_b_opt.get("final_choice") if res_b_opt else "N/A",
            "s3_opt_correct": res_b_opt.get("final_correct") if res_b_opt else "N/A",
            "s3_opt_quality": res_b_opt.get("revision_quality") if res_b_opt else "N/A",
            "s3_opt_runtime_s": res_b_opt.get("runtime_s") if res_b_opt else "N/A",
            "s4_a0": res_s4["a0_choice"],
            "s4_final": res_s4["final_choice"],
            "s4_correct": res_s4["final_correct"],
            "s4_det_status": res_s4["deterministic_status"],
            "s4_has_proof": res_s4["has_authoritative_proof"],
            "s4_override": res_s4["deterministic_override"],
            "s4_quality": res_s4["revision_quality"],
            "s4_runtime_s": res_s4["runtime_s"],
        })

        # Incremental write
        with open(summary_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
            writer.writeheader()
            writer.writerows(summary_rows)

        with open(comparison_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(comparison_rows[0].keys()))
            writer.writeheader()
            writer.writerows(comparison_rows)

    print("\nSprint 4 Benchmark completed successfully.")
    print(f"Summary CSV: {summary_csv}")
    print(f"Comparison CSV: {comparison_csv}")


if __name__ == "__main__":
    main()

