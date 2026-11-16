"""
Reliability Calibration Module for TalkHier Multi-Agent Framework
TalkHier BTP - Proposed Middleware Contribution 1

Implements parametric (Platt Scaling) and non-parametric (Isotonic Regression)
calibration to map raw self-reported evaluator scores z_i to true posterior
probabilities r_i = P(Evaluator E_i is correct | z_i).

Computes standard calibration diagnostics:
- Expected Calibration Error (ECE)
- Maximum Calibration Error (MCE)
- Brier Score
"""

import math
from typing import Dict, Any, List, Optional, Tuple, Sequence
import numpy as np


def compute_brier_score(y_true: Sequence[int], y_prob: Sequence[float]) -> float:
    """Computes mean squared error between binary outcomes and predicted probabilities."""
    y_t = np.asarray(y_true, dtype=float)
    y_p = np.asarray(y_prob, dtype=float)
    if len(y_t) == 0:
        return 0.0
    return float(np.mean((y_p - y_t) ** 2))


def compute_ece(y_true: Sequence[int], y_prob: Sequence[float], n_bins: int = 10) -> Tuple[float, float]:
    """
    Computes Expected Calibration Error (ECE) and Maximum Calibration Error (MCE).
    Bins predictions into n_bins equal intervals in [0, 1].
    """
    y_t = np.asarray(y_true, dtype=float)
    y_p = np.asarray(y_prob, dtype=float)
    N = len(y_t)
    if N == 0:
        return 0.0, 0.0

    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    mce = 0.0

    for i in range(n_bins):
        low, high = bins[i], bins[i + 1]
        mask = (y_p >= low) & (y_p <= high) if i == n_bins - 1 else (y_p >= low) & (y_p < high)
        bin_count = np.sum(mask)
        if bin_count > 0:
            bin_acc = np.mean(y_t[mask])
            bin_conf = np.mean(y_p[mask])
            diff = abs(bin_acc - bin_conf)
            ece += (bin_count / N) * diff
            mce = max(mce, diff)

    return float(ece), float(mce)


class PlattScaler:
    """
    Platt Scaling (1D Logistic Regression):
    P(y=1 | z) = 1 / (1 + exp(-(w * z + b)))
    Fitted via maximum likelihood with L2 regularization.
    """

    def __init__(self, w: float = 0.5, b: float = 0.0, l2_reg: float = 1e-4):
        self.w = float(w)
        self.b = float(b)
        self.l2_reg = float(l2_reg)
        self.fitted = False

    def fit(self, z_scores: Sequence[float], y_true: Sequence[int], epochs: int = 500, lr: float = 0.05):
        """Fits w and b using gradient descent with gradient clipping."""
        z = np.asarray(z_scores, dtype=float)
        y = np.asarray(y_true, dtype=float)
        if len(z) < 2:
            self.fitted = True
            return self

        # Normalize z to standard scale if constant variance exists
        w = 0.5
        b = 0.0

        for _ in range(epochs):
            # Forward pass: sigmoid(w * z + b)
            linear = np.clip(w * z + b, -15.0, 15.0)
            preds = 1.0 / (1.0 + np.exp(-linear))
            errors = preds - y  # gradient of NLL w.r.t linear

            # Gradients with L2 regularization on w
            grad_w = np.mean(errors * z) + self.l2_reg * w
            grad_b = np.mean(errors)

            w -= lr * np.clip(grad_w, -5.0, 5.0)
            b -= lr * np.clip(grad_b, -5.0, 5.0)

        self.w = float(w)
        self.b = float(b)
        self.fitted = True
        return self

    def predict_proba(self, z_score: float) -> float:
        """Returns calibrated probability r in (0, 1)."""
        linear = np.clip(self.w * float(z_score) + self.b, -15.0, 15.0)
        return float(1.0 / (1.0 + np.exp(-linear)))


class IsotonicCalibrator:
    """
    Non-parametric Isotonic Regression using the Pool Adjacent Violators (PAV) algorithm.
    Guarantees monotonic non-decreasing mapping from score to calibrated probability.
    """

    def __init__(self):
        self.thresholds: List[float] = []
        self.values: List[float] = []
        self.fitted = False

    def fit(self, z_scores: Sequence[float], y_true: Sequence[int]):
        """Fits isotonic regression via PAV."""
        z = np.asarray(z_scores, dtype=float)
        y = np.asarray(y_true, dtype=float)
        if len(z) == 0:
            self.fitted = True
            return self

        order = np.argsort(z)
        z_sorted = z[order]
        y_sorted = y[order]

        # Pool adjacent violators
        blocks = []  # list of [z_val, weight, sum_y]
        for zi, yi in zip(z_sorted, y_sorted):
            blocks.append([zi, 1.0, float(yi)])
            while len(blocks) >= 2:
                # Compare average y of top two blocks
                prev_avg = blocks[-2][2] / blocks[-2][1]
                curr_avg = blocks[-1][2] / blocks[-1][1]
                if prev_avg > curr_avg:
                    # Merge blocks
                    b2 = blocks.pop()
                    blocks[-1][0] = max(blocks[-1][0], b2[0])
                    blocks[-1][1] += b2[1]
                    blocks[-1][2] += b2[2]
                else:
                    break

        self.thresholds = [b[0] for b in blocks]
        self.values = [np.clip(b[2] / b[1], 0.01, 0.99) for b in blocks]
        self.fitted = True
        return self

    def predict_proba(self, z_score: float) -> float:
        """Step-function lookup for monotonic prediction."""
        if not self.thresholds:
            return 0.5
        idx = int(np.searchsorted(self.thresholds, float(z_score), side="right"))
        if idx == 0:
            return float(self.values[0])
        elif idx >= len(self.values):
            return float(self.values[-1])
        return float(self.values[idx - 1])


class EvaluatorReliabilityManager:
    """
    Manages calibrated reliability models for all 5 specialized TalkHier evaluators.
    """

    def __init__(self, method: str = "platt"):
        self.method = method
        self.calibrators: Dict[str, Any] = {}
        self.default_calibrator = PlattScaler(w=0.4, b=-2.0)  # Maps score 5 -> ~0.5

    def get_or_create(self, evaluator_id: str):
        if evaluator_id not in self.calibrators:
            if self.method == "isotonic":
                self.calibrators[evaluator_id] = IsotonicCalibrator()
            else:
                self.calibrators[evaluator_id] = PlattScaler(w=0.4, b=-2.0)
        return self.calibrators[evaluator_id]

    def fit_evaluator(self, evaluator_id: str, scores: Sequence[float], labels: Sequence[int]):
        cal = self.get_or_create(evaluator_id)
        cal.fit(scores, labels)
        return cal

    def get_calibrated_reliability(self, evaluator_id: str, raw_score: float) -> float:
        cal = self.calibrators.get(evaluator_id, self.default_calibrator)
        r = cal.predict_proba(raw_score)
        return float(np.clip(r, 0.05, 0.95))

