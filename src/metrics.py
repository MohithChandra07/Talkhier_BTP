"""
Evaluation Metrics & Diagnostics
TalkHier BTP - Proposed Evaluation Strategy (Slide 10)

Calculates:
- Task Accuracy (%)
- Harmful Revision Rate (%)
- Permutation Flip Rate (%)
- Expected Calibration Error (ECE)
- Brier Calibration Score
- Token Cost & Runtime
"""

from typing import Dict, Any, List, Optional, Tuple, Sequence
import numpy as np

from multiagent.reliability import compute_ece, compute_brier_score


def compute_comprehensive_metrics(
    eval_records: Sequence[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Computes all official BTP proposal metrics across a collection of episode evaluations.
    """
    total = len(eval_records)
    if total == 0:
        return {}

    correct_count = sum(1 for r in eval_records if r.get("final_correct"))
    a0_correct_count = sum(1 for r in eval_records if r.get("a0_correct"))

    helpful_rev = sum(1 for r in eval_records if (not r.get("a0_correct")) and r.get("final_correct") and r.get("answer_changed"))
    harmful_rev = sum(1 for r in eval_records if r.get("a0_correct") and (not r.get("final_correct")) and r.get("answer_changed"))
    neutral_rev = sum(1 for r in eval_records if not r.get("answer_changed") or (r.get("a0_correct") == r.get("final_correct")))

    # Calibration metrics
    raw_scores = []
    labels = []
    calibrated_probs = []
    for r in eval_records:
        if "evaluator_scores" in r and "ground_truth" in r:
            for score in r["evaluator_scores"]:
                raw_scores.append(score / 10.0)
                labels.append(1 if r.get("final_correct") else 0)
        if "calibrated_reliability" in r:
            calibrated_probs.append(r["calibrated_reliability"])

    ece_raw, _ = compute_ece(labels, raw_scores) if labels else (0.0, 0.0)
    brier_raw = compute_brier_score(labels, raw_scores) if labels else 0.0

    brier_cal = compute_brier_score(labels[:len(calibrated_probs)], calibrated_probs) if calibrated_probs else brier_raw

    # Tokens and runtime
    total_tokens = sum(r.get("cumulative_tokens", 0) for r in eval_records)
    total_runtime = sum(r.get("runtime_s", 0.0) for r in eval_records)

    # Permutation stability
    total_flips = sum(r.get("permutation_flips", 0) for r in eval_records)
    total_permutations = sum(r.get("permutation_trials", 1) for r in eval_records)
    flip_rate = (total_flips / total_permutations * 100.0) if total_permutations > 0 else 0.0

    return {
        "total_problems": total,
        "final_accuracy": round(correct_count / total * 100.0, 2),
        "a0_accuracy": round(a0_correct_count / total * 100.0, 2),
        "accuracy_gain_pp": round((correct_count - a0_correct_count) / total * 100.0, 2),
        "helpful_revisions": helpful_rev,
        "harmful_revisions": harmful_rev,
        "harmful_revision_rate": round(harmful_rev / total * 100.0, 2),
        "neutral_revisions": neutral_rev,
        "permutation_flip_rate": round(flip_rate, 2),
        "raw_ece": round(ece_raw, 4),
        "raw_brier": round(brier_raw, 4),
        "calibrated_brier": round(brier_cal, 4),
        "avg_tokens_per_problem": round(total_tokens / total, 1),
        "avg_runtime_s": round(total_runtime / total, 2),
    }

