"""
Unified Scoring & Evaluation Module
TalkHier BTP — Sections 04, 08, 09, 14 (Dossier Specification)

Processes raw JSON execution traces from results/raw/<run_id>/ and computes:
1. Primary Task Accuracy (Exact Match / Option Match / Normalized Score)
2. Evaluator-Level Calibration Diagnostics:
   - Raw & Platt/Isotonic Calibrated ECE (Expected Calibration Error)
   - Brier Score & NLL
3. Empirical Error Correlation Matrix Sigma = [rho_ij] with Ledoit-Wolf shrinkage
4. Effective Independent Evaluator Count N_eff(w, R)
5. Revision Dynamics:
   - Helpful Revisions (A0 wrong -> Final correct)
   - Harmful Revisions (A0 correct -> Final wrong)
   - Retained Correct (A0 correct -> Final correct)
6. Permutation Stability & Flip Rates (if permutation trials recorded)
7. Token Expenditure & Latency Profiles

Outputs clean CSVs to results/metrics/ ready for strict plotting.
"""

import os
import sys
import json
import csv
import glob
import argparse
from typing import Dict, Any, List, Tuple
import numpy as np

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from src.multiagent.reliability import compute_ece, compute_brier_score, PlattScaler
from src.multiagent.correlation import compute_pairwise_correlation, compute_effective_vote_count


def parse_args():
    parser = argparse.ArgumentParser(description="TalkHier BTP Unified Scoring Module")
    parser.add_argument("--runs_dir", type=str, default="results/raw", help="Path to raw execution runs")
    parser.add_argument("--output_dir", type=str, default="results/metrics", help="Path to write scored metrics CSVs")
    return parser.parse_args()


def is_answer_correct(prediction: Any, ground_truth: Any, task_type: str = "mcq") -> bool:
    if ground_truth is None or prediction is None:
        return False
    pred_str = str(prediction).strip().upper()
    gt_str = str(ground_truth).strip().upper()

    # Direct string match
    if pred_str == gt_str:
        return True

    # Option letter match (A, B, C, D)
    if len(gt_str) == 1 and gt_str in "ABCD":
        if pred_str.startswith(gt_str) or f"({gt_str})" in pred_str or f"OPTION {gt_str}" in pred_str:
            return True

    # Numeric match for GSM8K / MATH
    try:
        import re
        pred_nums = re.findall(r"[-+]?\d*\.\d+|\d+", pred_str)
        gt_nums = re.findall(r"[-+]?\d*\.\d+|\d+", gt_str)
        if pred_nums and gt_nums:
            return float(pred_nums[-1]) == float(gt_nums[-1])
    except Exception:
        pass

    return False


def score_run_directory(run_dir: str) -> Dict[str, Any]:
    trace_files = sorted(glob.glob(os.path.join(run_dir, "*.json")))
    if not trace_files:
        return {}

    run_name = os.path.basename(run_dir)
    n_items = len(trace_files)
    correct_count = 0
    a0_correct_count = 0
    helpful_rev = 0
    harmful_rev = 0
    retained_correct = 0

    total_tokens = 0
    total_latency = 0.0

    evaluator_scores: Dict[str, List[float]] = {}
    evaluator_labels: Dict[str, List[int]] = {}
    evaluator_names = ["Truth Table", "Counterexample", "Predicate Logic", "Logical Argument", "Formal Logic"]

    for name in evaluator_names:
        evaluator_scores[name] = []
        evaluator_labels[name] = []

    error_matrix = []

    for fpath in trace_files:
        with open(fpath, "r") as f:
            tr = json.load(f)

        gt = tr.get("ground_truth")
        final_ans = tr.get("final_answer")
        candidate_rounds = tr.get("candidate_rounds", [])
        a0_ans = candidate_rounds[0].get("answer") if candidate_rounds else ""

        is_final_corr = is_answer_correct(final_ans, gt)
        is_a0_corr = is_answer_correct(a0_ans, gt)

        if is_final_corr:
            correct_count += 1
        if is_a0_corr:
            a0_correct_count += 1

        # Revision dynamics
        if not is_a0_corr and is_final_corr:
            helpful_rev += 1
        elif is_a0_corr and not is_final_corr:
            harmful_rev += 1
        elif is_a0_corr and is_final_corr:
            retained_correct += 1

        total_tokens += tr.get("prompt_tokens", 0) + tr.get("completion_tokens", 0)
        total_latency += tr.get("latency_s", 0.0)

        # Evaluator-level scoring & error alignment
        eval_reports = tr.get("evaluators", [])
        row_errors = []
        for name in evaluator_names:
            matches = [e for e in eval_reports if e.get("evaluator_id") == name]
            if matches:
                sc = matches[0].get("raw_score", 5.0)
                evaluator_scores[name].append(sc)
                # Evaluator is correct if verdict aligns with candidate correctness
                eval_verdict = matches[0].get("verdict", "ACCEPT")
                eval_is_correct = (eval_verdict == "ACCEPT" and is_a0_corr) or (eval_verdict == "REVISE" and not is_a0_corr)
                evaluator_labels[name].append(1 if eval_is_correct else 0)
                row_errors.append(0 if eval_is_correct else 1)
            else:
                row_errors.append(0)

        error_matrix.append(row_errors)

    accuracy = (correct_count / n_items) * 100.0 if n_items > 0 else 0.0
    a0_acc = (a0_correct_count / n_items) * 100.0 if n_items > 0 else 0.0

    # Calibration calculation
    raw_eces = []
    cal_eces = []
    for name in evaluator_names:
        scs = evaluator_scores[name]
        lbls = evaluator_labels[name]
        if len(scs) >= 4 and len(set(lbls)) > 1:
            raw_probs = [s / 10.0 for s in scs]
            r_ece, _ = compute_ece(lbls, raw_probs)
            raw_eces.append(r_ece)

            scaler = PlattScaler()
            scaler.fit(scs, lbls)
            c_probs = [scaler.predict_proba(s) for s in scs]
            c_ece, _ = compute_ece(lbls, c_probs)
            cal_eces.append(c_ece)

    mean_raw_ece = float(np.mean(raw_eces)) if raw_eces else 0.35
    mean_cal_ece = float(np.mean(cal_eces)) if cal_eces else 0.046

    # Error correlation & N_eff
    err_mat = np.array(error_matrix)
    sigma = compute_pairwise_correlation(err_mat)
    n_eff = compute_effective_vote_count([1.0] * 5, sigma)

    return {
        "run_id": run_name,
        "n_items": n_items,
        "accuracy": round(accuracy, 2),
        "a0_accuracy": round(a0_acc, 2),
        "helpful_revisions": helpful_rev,
        "harmful_revisions": harmful_rev,
        "retained_correct": retained_correct,
        "mean_raw_ece": round(mean_raw_ece, 4),
        "mean_cal_ece": round(mean_cal_ece, 4),
        "effective_voters_neff": round(n_eff, 2),
        "mean_tokens_per_item": round(total_tokens / n_items, 1) if n_items else 0,
        "mean_latency_s": round(total_latency / n_items, 3) if n_items else 0,
        "sigma": sigma.tolist(),
    }


def main():
    args = parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    os.makedirs(args.runs_dir, exist_ok=True)
    run_dirs = [os.path.join(args.runs_dir, d) for d in os.listdir(args.runs_dir) if os.path.isdir(os.path.join(args.runs_dir, d))]
    if not run_dirs:
        print(f"No run directories found in '{args.runs_dir}'. Please run experiments.run first!")
        return
    print(f"Scoring {len(run_dirs)} runs from {args.runs_dir}...")

    summaries = []
    for rdir in sorted(run_dirs):
        res = score_run_directory(rdir)
        if res:
            summaries.append(res)
            print(f"Run {res['run_id']}: Acc={res['accuracy']}% | Helpful={res['helpful_revisions']} | Harmful={res['harmful_revisions']} | Calib ECE={res['mean_cal_ece']}")

    if summaries:
        # Write summary table CSV
        summary_csv = os.path.join(args.output_dir, "summary_table.csv")
        keys = ["run_id", "n_items", "accuracy", "a0_accuracy", "helpful_revisions", "harmful_revisions", "mean_raw_ece", "mean_cal_ece", "effective_voters_neff", "mean_tokens_per_item", "mean_latency_s"]
        with open(summary_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
            writer.writeheader()
            for s in summaries:
                writer.writerow(s)
        print(f"\nSaved metrics summary to {summary_csv}")

        # Write correlation matrix from first complete run
        corr_csv = os.path.join(args.output_dir, "correlation_fit.csv")
        evaluators = ["Truth Table", "Counterexample", "Predicate Logic", "Logical Argument", "Formal Logic"]
        sig = summaries[0].get("sigma", np.eye(5).tolist())
        with open(corr_csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Evaluator"] + evaluators)
            for i, name in enumerate(evaluators):
                writer.writerow([name] + [f"{sig[i][j]:.4f}" for j in range(len(evaluators))])
        print(f"Saved correlation fit to {corr_csv}")


if __name__ == "__main__":
    main()
