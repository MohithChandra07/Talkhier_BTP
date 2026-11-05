#!/usr/bin/env python3
"""
Sprint 2 Experiment D: Forced Evaluator Dispatch vs Existing Supervisor Workflow
TalkHier BTP

Compares:
Condition A: Existing hierarchical evaluator supervisor workflow.
Condition B: Explicit controlled five-evaluator dispatch workflow.

Measures:
- Evaluator invocation count (whether all 5 actually ran)
- Score distribution and validity (never defaulting missing to 10)
- Accuracy (pre-revision vs final)
- Revision decisions and behaviors
- Detailed execution traces
"""

import os
import sys
import time
import json
import csv
import argparse
from typing import Dict, Any, List
from datasets import load_dataset
from langchain_core.messages import HumanMessage

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from experiments import loadConfig
from multiagent.llm import LLM
import multiagent.agent_team as agent_team
import prompts.mmlu as MMLUPrompt
from multiagent.evaluator_dispatch import (
    run_controlled_evaluator_pipeline,
    extract_evaluator_score,
    EVALUATOR_NAMES_FORMAL_LOGIC,
)


def run_condition_a(problem_id: int, problem: Dict[str, Any], config: Dict[str, Any], domain: str = "formal_logic") -> Dict[str, Any]:
    """
    Runs Condition A: Existing TalkHier hierarchical workflow.
    Tracks whether individual evaluators were actually executed or short-circuited.
    """
    print(f"\n{'='*70}")
    print(f"[Condition A: Existing Supervisor] Running Problem {problem_id}...")
    print(f"Question: {problem['question'][:100]}...")
    print(f"Ground Truth: {problem['answer']}")
    print(f"{'='*70}\n", flush=True)

    t0 = time.time()
    prompts = MMLUPrompt.getPrompts(domain, problem)
    react_generator = agent_team.ReactAgent(
        intermediate_output_desc=prompts["intermediate_output_desc"],
        config=config,
        llm=LLM(config).llm,
    )
    team = agent_team.buildTeam(
        prompts["team"],
        react_generator,
        prompts["intermediate_output_desc"],
        prompts["int_out_format"],
    )

    team_output = None
    last_err = None
    for attempt in range(3):
        try:
            team_output = team(
                state={
                    "history": {
                        "Default Supervisor": [HumanMessage(content=prompts["team"]["prompt"])],
                        "all": [HumanMessage(content=prompts["team"]["prompt"])],
                    },
                    "intermediate_output": {},
                },
                config={"recursion_limit": int(config["LLM"]["max_attempts"])},
            )
            break
        except Exception as e:
            last_err = e
            print(f"Condition A attempt {attempt+1}/3 failed: {e}", flush=True)

    elapsed = round(time.time() - t0, 2)
    if team_output is None:
        raise RuntimeError(f"Condition A failed completely for problem {problem_id}: {last_err}")

    raw_result = team_output[0] if isinstance(team_output, list) else team_output
    initial_io = team_output[1] if isinstance(team_output, list) else {}

    executed_agents = raw_result.get("_executed_agents", [])
    revision_history = raw_result.get("_revision_history", [])

    final_io = raw_result.get("intermediate_output", {})
    if not isinstance(final_io, dict):
        final_io = {}

    final_choice = final_io.get("choice", final_io.get("answer", {}).get("choice", -1))
    a0_choice = initial_io.get("choice", initial_io.get("answer", {}).get("choice", -1)) if isinstance(initial_io, dict) else -1

    # Check which evaluators actually executed
    invoked_evaluators = [name for name in EVALUATOR_NAMES_FORMAL_LOGIC if name in executed_agents]
    all_five_invoked = (len(invoked_evaluators) == len(EVALUATOR_NAMES_FORMAL_LOGIC))

    # Check scores in intermediate_output
    individual_scores = {}
    valid_scores_count = 0
    scores_list = []
    for name in EVALUATOR_NAMES_FORMAL_LOGIC:
        score, status, _ = extract_evaluator_score(final_io, name)
        individual_scores[name] = score
        if status == "OK" and score is not None:
            valid_scores_count += 1
            scores_list.append(score)

    mean_score = round(sum(scores_list) / len(scores_list), 2) if scores_list else None
    gt = problem["answer"]
    revisor_decision = "REVISED" if (final_choice != a0_choice and a0_choice != -1) else "RETAINED"

    print(f"Condition A Problem {problem_id} finished in {elapsed}s:")
    print(f"  A0: {a0_choice} | Final: {final_choice} | GT: {gt}")
    print(f"  Evaluators Invoked: {len(invoked_evaluators)}/5 ({invoked_evaluators})")
    print(f"  Supervisor Short-Circuited: {not all_five_invoked}")
    print(f"  Valid Scores in Output: {valid_scores_count}/5 -> {individual_scores}")

    return {
        "problem_id": problem_id,
        "condition": "Condition_A_Existing",
        "ground_truth": gt,
        "a0_choice": a0_choice,
        "final_choice": final_choice,
        "a0_correct": (a0_choice == gt),
        "final_correct": (final_choice == gt),
        "answer_changed": (final_choice != a0_choice and a0_choice != -1),
        "all_five_evaluators_invoked": all_five_invoked,
        "evaluators_invoked_count": len(invoked_evaluators),
        "invoked_evaluators_list": invoked_evaluators,
        "executed_agents_trace": executed_agents,
        "valid_scores_count": valid_scores_count,
        "individual_scores": individual_scores,
        "mean_score": mean_score,
        "revisor_decision": revisor_decision,
        "runtime_s": elapsed,
        "raw_final_output": final_io,
        "revision_history": revision_history,
    }


def run_condition_b(problem_id: int, problem: Dict[str, Any], config: Dict[str, Any], domain: str = "formal_logic") -> Dict[str, Any]:
    """
    Runs Condition B: Explicit Controlled Five-Evaluator Dispatch.
    Guarantees every evaluator runs, captures raw outputs, and validates scores.
    """
    print(f"\n{'='*70}")
    print(f"[Condition B: Controlled Dispatch] Running Problem {problem_id}...")
    print(f"Question: {problem['question'][:100]}...")
    print(f"Ground Truth: {problem['answer']}")
    print(f"{'='*70}\n", flush=True)

    problem_with_id = dict(problem)
    problem_with_id["id"] = problem_id

    outcome = run_controlled_evaluator_pipeline(problem_with_id, config, domain=domain)
    outcome["condition"] = "Condition_B_Controlled"
    outcome["problem_id"] = problem_id

    print(f"Condition B Problem {problem_id} finished in {outcome['runtime_s']}s:")
    print(f"  A0: {outcome['a0_choice']} | Final: {outcome['final_choice']} | GT: {outcome['ground_truth']}")
    print(f"  Evaluators Invoked: {outcome['evaluators_invoked_count']}/5")
    print(f"  Valid Scores: {outcome['valid_scores_count']}/5 -> {outcome['individual_scores']}")
    print(f"  Consensus: {outcome['consensus_type']} (Mean: {outcome['mean_score']})")
    print(f"  Revisor Decision: {outcome['revisor_decision']} (Parse Failed: {outcome['parse_failed']})")

    return outcome


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_cfg = os.path.join(base_dir, "config", "config.ini")
    default_lcfg = os.path.join(base_dir, "config", "config_llm.ini")

    parser = argparse.ArgumentParser(description="Sprint 2 Experiment D: Forced Evaluator Dispatch")
    parser.add_argument("--config", default=default_cfg)
    parser.add_argument("--llm-config", default=default_lcfg)
    parser.add_argument("--problems", nargs="+", type=int, default=[0, 1, 2, 3, 4],
                        help="Problem IDs to evaluate (default: 0 1 2 3 4)")
    parser.add_argument("--out-dir", default=os.path.join(base_dir, "results", "experiment_d"))
    parser.add_argument("--skip-condition-a", action="store_true", default=False)
    parser.add_argument("--skip-condition-b", action="store_true", default=False)
    args = parser.parse_args()

    config = loadConfig(args.config, args.llm_config)
    os.makedirs(args.out_dir, exist_ok=True)
    traces_dir = os.path.join(args.out_dir, "traces")
    os.makedirs(traces_dir, exist_ok=True)

    dataset = load_dataset("cais/mmlu", "formal_logic")["test"]

    summary_csv = os.path.join(args.out_dir, "experiment_d_summary.csv")
    comparison_csv = os.path.join(args.out_dir, "experiment_d_comparison.csv")

    summary_rows = []
    if os.path.exists(summary_csv):
        with open(summary_csv, "r") as f:
            reader = csv.DictReader(f)
            summary_rows = list(reader)

    comparison_rows = []
    if os.path.exists(comparison_csv):
        with open(comparison_csv, "r") as f:
            reader = csv.DictReader(f)
            comparison_rows = list(reader)

    print(f"\nStarting Experiment D on problems: {args.problems}")
    print(f"Results will be written to: {args.out_dir}\n")

    for pid in args.problems:
        prob = dataset[pid]
        res_a = None
        res_b = None

        if not args.skip_condition_a:
            res_a = run_condition_a(pid, prob, config)
            # Save raw trace A
            trace_path_a = os.path.join(traces_dir, f"problem_{pid}_condition_a.json")
            with open(trace_path_a, "w") as f:
                json.dump(res_a, f, indent=2, default=str)
            summary_rows.append({
                "problem_id": pid,
                "condition": "Condition_A_Existing",
                "ground_truth": res_a["ground_truth"],
                "a0_choice": res_a["a0_choice"],
                "final_choice": res_a["final_choice"],
                "a0_correct": res_a["a0_correct"],
                "final_correct": res_a["final_correct"],
                "answer_changed": res_a["answer_changed"],
                "all_five_evaluators_invoked": res_a["all_five_evaluators_invoked"],
                "evaluators_invoked_count": res_a["evaluators_invoked_count"],
                "valid_scores_count": res_a["valid_scores_count"],
                "mean_score": res_a["mean_score"],
                "revisor_decision": res_a["revisor_decision"],
                "runtime_s": res_a["runtime_s"],
                "tt_score": res_a["individual_scores"].get("Truth Table"),
                "ce_score": res_a["individual_scores"].get("Counterexample"),
                "pl_score": res_a["individual_scores"].get("Predicate Logic"),
                "la_score": res_a["individual_scores"].get("Logical Argument"),
                "fl_score": res_a["individual_scores"].get("Formal Logic"),
            })

        if not args.skip_condition_b:
            res_b = run_condition_b(pid, prob, config)
            # Save raw trace B
            trace_path_b = os.path.join(traces_dir, f"problem_{pid}_condition_b.json")
            with open(trace_path_b, "w") as f:
                json.dump(res_b, f, indent=2, default=str)
            summary_rows.append({
                "problem_id": pid,
                "condition": "Condition_B_Controlled",
                "ground_truth": res_b["ground_truth"],
                "a0_choice": res_b["a0_choice"],
                "final_choice": res_b["final_choice"],
                "a0_correct": res_b["a0_correct"],
                "final_correct": res_b["final_correct"],
                "answer_changed": res_b["answer_changed"],
                "all_five_evaluators_invoked": res_b["all_five_evaluators_invoked"],
                "evaluators_invoked_count": res_b["evaluators_invoked_count"],
                "valid_scores_count": res_b["valid_scores_count"],
                "mean_score": res_b["mean_score"],
                "revisor_decision": res_b["revisor_decision"],
                "runtime_s": res_b["runtime_s"],
                "tt_score": res_b["individual_scores"].get("Truth Table"),
                "ce_score": res_b["individual_scores"].get("Counterexample"),
                "pl_score": res_b["individual_scores"].get("Predicate Logic"),
                "la_score": res_b["individual_scores"].get("Logical Argument"),
                "fl_score": res_b["individual_scores"].get("Formal Logic"),
            })

        if res_a and res_b:
            comparison_rows.append({
                "problem_id": pid,
                "ground_truth": prob["answer"],
                "cond_a_a0": res_a["a0_choice"],
                "cond_a_final": res_a["final_choice"],
                "cond_a_correct": res_a["final_correct"],
                "cond_a_eval_invoked": res_a["evaluators_invoked_count"],
                "cond_a_mean_score": res_a["mean_score"],
                "cond_a_runtime": res_a["runtime_s"],
                "cond_b_a0": res_b["a0_choice"],
                "cond_b_final": res_b["final_choice"],
                "cond_b_correct": res_b["final_correct"],
                "cond_b_eval_invoked": res_b["evaluators_invoked_count"],
                "cond_b_mean_score": res_b["mean_score"],
                "cond_b_runtime": res_b["runtime_s"],
                "agreement_final": (res_a["final_choice"] == res_b["final_choice"]),
            })

        # Save summary CSV after each problem to prevent data loss
        summary_csv = os.path.join(args.out_dir, "experiment_d_summary.csv")
        if summary_rows:
            with open(summary_csv, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
                writer.writeheader()
                writer.writerows(summary_rows)

        comparison_csv = os.path.join(args.out_dir, "experiment_d_comparison.csv")
        if comparison_rows:
            with open(comparison_csv, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(comparison_rows[0].keys()))
                writer.writeheader()
                writer.writerows(comparison_rows)

    print(f"\n{'='*70}")
    print("Experiment D execution completed successfully!")
    print(f"Summary CSV:    {os.path.join(args.out_dir, 'experiment_d_summary.csv')}")
    print(f"Comparison CSV: {os.path.join(args.out_dir, 'experiment_d_comparison.csv')}")
    print(f"Traces Dir:     {traces_dir}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()

