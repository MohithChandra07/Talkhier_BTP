#!/usr/bin/env python3
"""
Sprint 4.3 Unified Benchmark & Ablation Study Runner
TalkHier BTP: Comprehensive Evaluation, Ablation Study & Error Analysis

Conditions:
1. sprint3_opt: Sprint 3 Optimized pure-LLM baseline
2. sprint4_full: Full Sprint 4 (Verifier + Evaluator Evidence + Revisor Override)
3. sprint4_ablation_a: Ablation A (Verifier + Revisor Override, NO Evaluator Evidence)
4. sprint4_ablation_b: Ablation B (Verifier + Evaluator Evidence, NO Revisor Override)

Target Domain (27 questions): Propositional deductive arguments (slash notation)
Control Domain (8 questions): Stratified non-propositional logic (predicates, quantifiers, NL)
Total: 35 benchmark problems

Outputs saved to results/experiment_sprint4_3/
"""

import os
import sys
import time
import json
import csv
import copy
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
from multiagent.graph_dispatch_opt import build_optimized_graph_dispatch_team
from multiagent.graph_dispatch_sprint4 import build_sprint4_graph_dispatch_team

TARGET_PROBLEM_IDS = [
    3, 6, 13, 14, 20, 23, 29, 31, 35, 36, 44, 48, 49,
    67, 69, 73, 81, 87, 90, 95, 97, 101, 104, 108, 121, 122, 123
]

CONTROL_PROBLEM_IDS = [0, 1, 2, 4, 5, 7, 9, 10]

ALL_BENCHMARK_IDS = sorted(list(set(TARGET_PROBLEM_IDS + CONTROL_PROBLEM_IDS)))

VALID_CONDITIONS = [
    "sprint3_opt",
    "sprint4_full",
    "sprint4_ablation_a",
    "sprint4_ablation_b",
]


def run_pipeline(
    condition: str,
    problem_id: int,
    problem: Dict[str, Any],
    config: Dict[str, Any],
    domain: str = "formal_logic",
) -> Dict[str, Any]:
    """
    Executes a single problem under the specified condition.
    """
    is_target = (problem_id in TARGET_PROBLEM_IDS)
    domain_type = "TARGET_PROPOSITIONAL" if is_target else "CONTROL_NON_PROPOSITIONAL"

    print(f"\n{'='*80}")
    print(f"[{condition.upper()}] Problem {problem_id:3d} ({domain_type})")
    print(f"Question: {problem['question'][:120]}...")
    print(f"Ground Truth: {problem['answer']} ({problem['choices'][problem['answer']]!r})")
    print(f"{'='*80}\n", flush=True)

    t0 = time.time()
    prompts = MMLUPrompt.getPrompts(domain, problem)
    react_generator = agent_team.ReactAgent(
        intermediate_output_desc=prompts["intermediate_output_desc"],
        config=config,
        llm=LLM(config).llm,
    )

    # Dispatch to appropriate graph builder
    if condition == "sprint3_opt":
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
    elif condition == "sprint4_full":
        graph = build_sprint4_graph_dispatch_team(
            prompts, react_generator, problem,
            inject_evaluator_evidence=True,
            enable_revisor_override=True,
        )
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
    elif condition == "sprint4_ablation_a":
        # Verifier enabled, Evaluator evidence DISABLED, Revisor override ENABLED
        graph = build_sprint4_graph_dispatch_team(
            prompts, react_generator, problem,
            inject_evaluator_evidence=False,
            enable_revisor_override=True,
        )
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
    elif condition == "sprint4_ablation_b":
        # Verifier enabled, Evaluator evidence ENABLED, Revisor override DISABLED
        graph = build_sprint4_graph_dispatch_team(
            prompts, react_generator, problem,
            inject_evaluator_evidence=True,
            enable_revisor_override=False,
        )
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
    else:
        raise ValueError(f"Unknown condition: {condition}")

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
        "domain_type": domain_type,
        "is_target": is_target,
        "condition": condition,
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


def write_summary_csv(csv_path: str, rows: List[Dict[str, Any]]):
    fieldnames = [
        "problem_id", "domain_type", "condition", "ground_truth",
        "a0_choice", "final_choice", "a0_correct", "final_correct",
        "answer_changed", "deterministic_status", "has_authoritative_proof",
        "proven_choice_index", "deterministic_override", "revisor_decision",
        "revision_quality", "evaluators_invoked_count", "applicable_count",
        "valid_scores_count", "not_applicable_count", "mean_score",
        "total_evaluator_retries", "runtime_s"
    ]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_cfg = os.path.join(base_dir, "config", "config.ini")
    default_lcfg = os.path.join(base_dir, "config", "config_llm.ini")
    default_out = os.path.join(base_dir, "results", "experiment_sprint4_3")

    parser = argparse.ArgumentParser(description="Sprint 4.3 Unified Benchmark & Ablation Study")
    parser.add_argument("--config", default=default_cfg)
    parser.add_argument("--llm-config", default=default_lcfg)
    parser.add_argument("--condition", choices=VALID_CONDITIONS + ["all"], default="sprint4_full")
    parser.add_argument("--problems", nargs="+", type=int, default=ALL_BENCHMARK_IDS)
    parser.add_argument("--out-dir", default=default_out)
    parser.add_argument("--resume", action="store_true", help="Skip problems with existing traces")
    args = parser.parse_args()

    config = loadConfig(args.config, args.llm_config)
    os.makedirs(args.out_dir, exist_ok=True)
    dataset = load_dataset("cais/mmlu", "formal_logic")["test"]

    conditions_to_run = VALID_CONDITIONS if args.condition == "all" else [args.condition]

    print(f"\n================================================================================")
    print(f"TalkHier Sprint 4.3 Unified Evaluation & Ablation Study")
    print(f"Conditions: {conditions_to_run}")
    print(f"Problems ({len(args.problems)}): {args.problems}")
    print(f"Output Directory: {args.out_dir}")
    print(f"Resume Mode: {args.resume}")
    print(f"================================================================================\n", flush=True)

    for cond in conditions_to_run:
        cond_traces_dir = os.path.join(args.out_dir, "raw_traces", cond)
        os.makedirs(cond_traces_dir, exist_ok=True)
        cond_summary_csv = os.path.join(args.out_dir, f"{cond}_summary.csv")

        results_list = []

        print(f"\n>>> Running Condition: {cond} <<<\n")
        for pid in args.problems:
            trace_path = os.path.join(cond_traces_dir, f"problem_{pid}.json")
            if args.resume and os.path.exists(trace_path):
                print(f"Skipping Problem {pid} (Trace already exists at {trace_path})")
                with open(trace_path, "r") as f:
                    res = json.load(f)
                results_list.append(res)
                continue

            prob = dataset[pid]
            res = run_pipeline(cond, pid, prob, config)
            results_list.append(res)

            # Save raw trace immediately
            with open(trace_path, "w") as f:
                json.dump(res, f, indent=2, default=str)

            # Write updated CSV summary incrementally
            write_summary_csv(cond_summary_csv, results_list)

            print(f">>> Problem {pid} Done:")
            print(f"    GT: {res['ground_truth']} | A0: {res['a0_choice']} ({res['a0_correct']}) -> Final: {res['final_choice']} ({res['final_correct']})")
            print(f"    Revision Quality: {res['revision_quality']} | Override: {res['deterministic_override']}")
            print(f"    Deterministic: {res['deterministic_status']} (Proof: {res['has_authoritative_proof']}, Proven Choice: {res['proven_choice_index']})")
            print(f"    Runtime: {res['runtime_s']}s")
            print(f"{'-'*60}\n", flush=True)

        # Print Condition Summary
        total = len(results_list)
        correct = sum(1 for r in results_list if r["final_correct"])
        a0_correct = sum(1 for r in results_list if r["a0_correct"])
        helpful = sum(1 for r in results_list if r.get("revision_quality") == "HELPFUL")
        harmful = sum(1 for r in results_list if r.get("revision_quality") == "HARMFUL")
        neutral = sum(1 for r in results_list if (r.get("revision_quality") or "").startswith("NEUTRAL"))
        overrides = sum(1 for r in results_list if r.get("deterministic_override"))
        total_time = sum(r.get("runtime_s", 0) for r in results_list)

        target_results = [r for r in results_list if r["is_target"]]
        control_results = [r for r in results_list if not r["is_target"]]

        target_correct = sum(1 for r in target_results if r["final_correct"])
        control_correct = sum(1 for r in control_results if r["final_correct"])

        print(f"\n================================================================================")
        print(f"SUMMARY FOR CONDITION: {cond}")
        print(f"Total Problems: {total}")
        print(f"Overall Accuracy: {correct}/{total} ({correct/total*100:.1f}%) [A0: {a0_correct}/{total} ({a0_correct/total*100:.1f}%)]")
        if target_results:
            print(f"Target Domain Accuracy: {target_correct}/{len(target_results)} ({target_correct/len(target_results)*100:.1f}%)")
        if control_results:
            print(f"Control Domain Accuracy: {control_correct}/{len(control_results)} ({control_correct/len(control_results)*100:.1f}%)")
        print(f"Revisions: Helpful={helpful}, Harmful={harmful}, Neutral={neutral}")
        print(f"Deterministic Overrides: {overrides}")
        print(f"Total Runtime: {total_time:.1f}s (Avg {total_time/total:.1f}s/prob)")
        print(f"Summary CSV: {cond_summary_csv}")
        print(f"================================================================================\n")


if __name__ == "__main__":
    main()

