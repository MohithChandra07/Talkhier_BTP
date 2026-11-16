"""
Error Dependence & Correlation Modeling Module (Playbook Section 6, Page 10)
TalkHier BTP - Proposed Framework Component 1 (Part B)

Estimates pairwise error dependence matrix Sigma = [rho_ij] with shrinkage regularization.
Discounts redundant evaluator weights to mitigate co-hallucination majority traps.
"""

from typing import Dict, Any, List, Optional, Tuple, Sequence
import numpy as np

from multiagent.correlation import (
    compute_pairwise_correlation,
    apply_redundancy_discount,
    EvaluatorCorrelationTracker,
)


class ErrorDependenceModel:
    """
    Manages pairwise error dependence across evaluators.
    Applies shrinkage regularization toward an identity prior:
      Sigma_shrink = (1 - lambda_s) * Sigma_sample + lambda_s * I
    """

    def __init__(self, evaluator_names: Sequence[str], shrinkage_lambda: float = 0.15, gamma: float = 0.6):
        self.evaluator_names = list(evaluator_names)
        self.K = len(self.evaluator_names)
        self.shrinkage_lambda = shrinkage_lambda
        self.gamma = gamma
        self.tracker = EvaluatorCorrelationTracker(self.evaluator_names, gamma=self.gamma)
        self.sigma = np.eye(self.K)

    def fit_from_error_history(self, error_matrix: np.ndarray):
        """
        Estimates Sigma with shrinkage regularization:
          Sigma_shrink = (1 - lambda) * Sigma + lambda * I
        """
        E = np.asarray(error_matrix, dtype=float)
        if E.shape[0] < 2:
            self.sigma = np.eye(self.K)
            return self.sigma

        raw_corr = compute_pairwise_correlation(E)
        # Apply Ledoit-Wolf-style shrinkage toward Identity
        lam = float(self.shrinkage_lambda)
        shrunk_corr = (1.0 - lam) * raw_corr + lam * np.eye(self.K)
        np.fill_diagonal(shrunk_corr, 1.0)
        self.sigma = np.clip(shrunk_corr, -1.0, 1.0)
        self.tracker.current_sigma = self.sigma
        return self.sigma

    def discount_weights(self, reliability_dict: Dict[str, float]) -> Dict[str, float]:
        """Returns redundancy-discounted weights for all evaluators."""
        r_vec = [reliability_dict.get(name, 0.5) for name in self.evaluator_names]
        disc = apply_redundancy_discount(r_vec, self.sigma, gamma=self.gamma)
        return {name: float(disc[i]) for i, name in enumerate(self.evaluator_names)}

    def compute_effective_vote_count(self, weights: Sequence[float]) -> float:
        """
        Computes effective number of independent evaluators:
        N_eff = (sum w_i)^2 / sum (w_i^2)
        """
        w = np.asarray(weights, dtype=float)
        sum_w = np.sum(w)
        sum_sq = np.sum(w ** 2)
        if sum_sq <= 0:
            return 0.0
        return float((sum_w ** 2) / sum_sq)

