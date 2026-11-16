"""
Reliability Estimator Module (Playbook Section 6, Page 10)
TalkHier BTP - Proposed Framework Component 1

Provides calibrated stance correctness estimation r_{i,t} = P(E_i is correct | z_i, H_t)
and uncertainty estimation u_{i,t}.
Supports:
- Platt Scaling (Parametric 1D Logistic Sigmoid)
- Isotonic Regression (Non-parametric Pool Adjacent Violators)
- Expected Calibration Error (ECE), Maximum Calibration Error (MCE), Brier Score
"""

from typing import Dict, Any, List, Optional, Tuple, Sequence
import numpy as np

from multiagent.reliability import (
    PlattScaler,
    IsotonicCalibrator,
    compute_ece,
    compute_brier_score,
    EvaluatorReliabilityManager,
)


class ReliabilityEstimator:
    """
    Unified interface for estimating evaluator reliability and uncertainty.
    Estimates r_i in [0.0, 1.0] and u_i = 4 * r_i * (1 - r_i) in [0.0, 1.0].
    """

    def __init__(self, method: str = "platt", regularizer: float = 1e-4):
        self.method = method.lower()
        self.regularizer = regularizer
        self.manager = EvaluatorReliabilityManager(method=self.method)
        self.fitted_evaluators = set()

    def fit_evaluator(self, evaluator_id: str, scores: Sequence[float], correctness_labels: Sequence[int]):
        """Fits calibration curves on training split only (zero test set leakage)."""
        cal = self.manager.fit_evaluator(evaluator_id, scores, correctness_labels)
        self.fitted_evaluators.add(evaluator_id)
        return cal

    def estimate_reliability_and_uncertainty(
        self, evaluator_id: str, raw_score: float
    ) -> Tuple[float, float]:
        """
        Returns:
            r_i: Calibrated reliability probability in [0.05, 0.95]
            u_i: Normalized epistemic uncertainty in [0.0, 1.0]
        """
        r_i = self.manager.get_calibrated_reliability(evaluator_id, float(raw_score))
        # Epistemic variance / normalized entropy proxy: 4 * r * (1 - r) peaks at r = 0.5 (max uncertainty 1.0)
        u_i = float(np.clip(4.0 * r_i * (1.0 - r_i), 0.0, 1.0))
        return float(r_i), float(u_i)

    def evaluate_calibration(
        self, evaluator_id: str, scores: Sequence[float], labels: Sequence[int]
    ) -> Dict[str, float]:
        """Computes ECE, MCE, and Brier score before and after calibration."""
        if not scores or not labels:
            return {"raw_ece": 0.0, "calibrated_ece": 0.0, "raw_brier": 0.0, "calibrated_brier": 0.0}

        raw_probs = [float(s) / 10.0 for s in scores]
        cal_probs = [self.estimate_reliability_and_uncertainty(evaluator_id, s)[0] for s in scores]

        raw_ece, raw_mce = compute_ece(labels, raw_probs)
        cal_ece, cal_mce = compute_ece(labels, cal_probs)

        raw_brier = compute_brier_score(labels, raw_probs)
        cal_brier = compute_brier_score(labels, cal_probs)

        return {
            "raw_ece": round(raw_ece, 4),
            "calibrated_ece": round(cal_ece, 4),
            "ece_reduction_pct": round(max(0.0, (raw_ece - cal_ece) / max(1e-4, raw_ece) * 100.0), 2),
            "raw_mce": round(raw_mce, 4),
            "calibrated_mce": round(cal_mce, 4),
            "raw_brier": round(raw_brier, 4),
            "calibrated_brier": round(cal_brier, 4),
        }

