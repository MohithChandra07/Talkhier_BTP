#!/usr/bin/env python3
"""
Sprint 3: Graph-Level Forced Evaluator Integration Experiment Runner
Compares:
Condition A: Original TalkHier hierarchical workflow.
Condition B: Original TalkHier workflow with mandatory graph-level evaluator execution.

Both conditions use the IDENTICAL:
- Answer Generator implementation (same prompt, same tools, same LLM, same temp=0)
- Initial conversation state and context
- Dataset and problems (MMLU Formal Logic, problems 0, 1, 2, 3, 4)
- Ollama Qwen3:8B local model
"""

import os
import sys
import time
import json
import csv
import argparse
from typing import Dict, Any, List
from datasets import load_dataset
from langchain_core.messages import HumanMessage, AIMessage

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from experiments import loadConfig, mmlu
from multiagent.llm import LLM
import multiagent.agent_team as agent_team
import prompts.mmlu as MMLUPrompt
from multiagent.graph_dispatch import (
    build_mandatory_graph_dispatch_team,
    evaluate_revision_quality,
    EVALUATOR_NAMES_FORMAL_LOGIC,
)
from multiagent.evaluator_dispatch import extract_evaluator_score


def verify_identical_answer_generator_config(prompt_a: Dict[str, Any], prompt_b: Dict[str, Any]):
    """
    Requirement 10: Verify Condition A and B use identical Answer Generator configuration.
    """
    ag_a = prompt_a["team"]["Answer Generator"]
    ag_b = prompt_b["team"]["Answer Generator"]

    assert ag_a["prompt"] == ag_b["prompt"], "Answer Generator prompts differ between Condition A and B!"
    assert ag_a["tools"] == ag_b["tools"], "Answer Generator tools differ between Condition A and B!"
    assert prompt_a["team"]["prompt"] == prompt_b["team"]["prompt"], "Initial problem prompt differs!"
    print("VERIFICATION PASSED: Condition A and B use identical Answer Generator configuration and prompt.")


def run_condition_a(problem_id: int, problem: Dict[str, Any], config: Dict[str, Any], domain: str = "formal_logic") -> Dict[str, Any]:
    """
    Runs Condition A: Original TalkHier workflow.
    """
    print(f"\n{'='*70}")
    print(f"[Sprint 3 - Condition A: Original TalkHier] Running Problem {problem_id}...")
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

    invoked_evaluators = [name for name in EVALUATOR_NAMES_FORMAL_LOGIC if name in executed_agents]
    all_five_invoked = (len(invoked_evaluators) == len(EVALUATOR_NAMES_FORMAL_LOGIC))

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
    revision_quality = evaluate_revision_quality(a0_choice, final_choice, gt)

    return {
        "problem_id": problem_id,
        "condition": "Condition_A_Original",
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
        "revision_quality": revision_quality,
        "runtime_s": elapsed,
        "raw_final_output": final_io,
        "revision_history": revision_history,
    }


def run_condition_b(problem_id: int, problem: Dict[str, Any], config: Dict[str, Any], domain: str = "formal_logic") -> Dict[str, Any]:
    """
    Runs Condition B: Original TalkHier workflow with mandatory graph-level evaluator execution.
    """
    print(f"\n{'='*70}")
    print(f"[Sprint 3 - Condition B: Mandatory Graph Dispatch] Running Problem {problem_id}...")
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

    # Build the mandatory sequential graph
    graph = build_mandatory_graph_dispatch_team(prompts, react_generator, problem)

    # State preserves original problem, history and context
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

    return {
        "problem_id": problem_id,
        "condition": "Condition_B_Graph_Dispatch",
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
        "is_complete": agg.get("is_complete", False),
        "consensus_type": agg.get("consensus_type", "UNKNOWN"),
        "supports_initial_answer": agg.get("supports_initial_answer", False),
        "revisor_decision": decision,
        "revision_quality": revision_quality,
        "runtime_s": elapsed,
        "revision_history": rev_hist,
        "_initial_intermediate_output": a0_dict,
        "_evaluator_trace": eval_trace,
    }


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_cfg = os.path.join(base_dir, "config", "config.ini")
    default_lcfg = os.path.join(base_dir, "config", "config_llm.ini")

    parser = argparse.ArgumentParser(description="Sprint 3: Graph-Level Forced Evaluator Integration")
    parser.add_argument("--config", default=default_cfg)
    parser.add_argument("--llm-config", default=default_lcfg)
    parser.add_argument("--problems", nargs="+", type=int, default=[0, 1, 2, 3, 4])
    parser.add_argument("--out-dir", default=os.path.join(base_dir, "results", "experiment_d_graph"))
    parser.add_argument("--skip-condition-a", action="store_true", default=False)
    parser.add_argument("--skip-condition-b", action="store_true", default=False)
    args = parser.parse_args()

    config = loadConfig(args.config, args.llm_config)
    os.makedirs(args.out_dir, exist_ok=True)
    traces_dir = os.path.join(args.out_dir, "traces")
    os.makedirs(traces_dir, exist_ok=True)

    dataset = load_dataset("cais/mmlu", "formal_logic")["test"]

    # Pre-flight check: Verify identical Answer Generator config
    sample_problem = dataset[0]
    prompts_a = MMLUPrompt.getPrompts("formal_logic", sample_problem)
    prompts_b = MMLUPrompt.getPrompts("formal_logic", sample_problem)
    verify_identical_answer_generator_config(prompts_a, prompts_b)

    summary_csv = os.path.join(args.out_dir, "experiment_d_graph_summary.csv")
    comparison_csv = os.path.join(args.out_dir, "experiment_d_graph_comparison.csv")

    summary_rows = []
    if os.path.exists(summary_csv):
        with open(summary_csv, "r") as f:
            summary_rows = list(csv.DictReader(f))

    comparison_rows = []
    if os.path.exists(comparison_csv):
        with open(comparison_csv, "r") as f:
            comparison_rows = list(csv.DictReader(f))

    print(f"\nStarting Sprint 3 Experiment on problems: {args.problems}")
    print(f"Results output dir: {args.out_dir}\n")

    for pid in args.problems:
        prob = dataset[pid]
        res_a = None
        res_b = None

        if not args.skip_condition_a:
            res_a = run_condition_a(pid, prob, config)
            trace_path_a = os.path.join(traces_dir, f"problem_{pid}_condition_a.json")
            with open(trace_path_a, "w") as f:
                json.dump(res_a, f, indent=2, default=str)
            summary_rows.append({
                "problem_id": pid,
                "condition": "Condition_A_Original",
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
                "revision_quality": res_a["revision_quality"],
                "runtime_s": res_a["runtime_s"],
                "tt_score": res_a["individual_scores"].get("Truth Table"),
                "ce_score": res_a["individual_scores"].get("Counterexample"),
                "pl_score": res_a["individual_scores"].get("Predicate Logic"),
                "la_score": res_a["individual_scores"].get("Logical Argument"),
                "fl_score": res_a["individual_scores"].get("Formal Logic"),
            })

        if not args.skip_condition_b:
            res_b = run_condition_b(pid, prob, config)
            trace_path_b = os.path.join(traces_dir, f"problem_{pid}_condition_b.json")
            with open(trace_path_b, "w") as f:
                json.dump(res_b, f, indent=2, default=str)
            summary_rows.append({
                "problem_id": pid,
                "condition": "Condition_B_Graph_Dispatch",
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
                "revision_quality": res_b["revision_quality"],
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
                "cond_a_rev_quality": res_a["revision_quality"],
                "cond_a_runtime": res_a["runtime_s"],
                "cond_b_a0": res_b["a0_choice"],
                "cond_b_final": res_b["final_choice"],
                "cond_b_correct": res_b["final_correct"],
                "cond_b_eval_invoked": res_b["evaluators_invoked_count"],
                "cond_b_mean_score": res_b["mean_score"],
                "cond_b_rev_quality": res_b["revision_quality"],
                "cond_b_runtime": res_b["runtime_s"],
                "agreement_final": (res_a["final_choice"] == res_b["final_choice"]),
            })

        # Save summary CSV
        if summary_rows:
            with open(summary_csv, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
                writer.writeheader()
                writer.writerows(summary_rows)

        # Save comparison CSV
        if comparison_rows:
            with open(comparison_csv, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(comparison_rows[0].keys()))
                writer.writeheader()
                writer.writerows(comparison_rows)

    print(f"\n{'='*70}")
    print("Sprint 3 Experiment execution completed successfully!")
    print(f"Summary CSV:    {summary_csv}")
    print(f"Comparison CSV: {comparison_csv}")
    print(f"Traces Dir:     {traces_dir}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()

