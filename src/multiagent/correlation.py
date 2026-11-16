"""
Error Correlation & Redundancy Discounting Module
TalkHier BTP - Proposed Middleware Contribution 1 (Part B)

Estimates pairwise error dependence matrix Sigma = [rho_ij] across evaluators.
Applies redundancy discounting to prevent correlated evaluator co-hallucinations
from dominating the supervisory decision.
Computes information-theoretic effective independent evaluator count N_eff(w, R).
"""

from typing import Dict, Any, List, Optional, Tuple, Sequence
import numpy as np


def compute_pairwise_correlation(
    error_matrix: np.ndarray,
    regularizer: float = 1e-4
) -> np.ndarray:
    """
    Computes pairwise Pearson / phi correlation matrix Sigma = [rho_ij]
    between binary evaluator error vectors with Ledoit-Wolf shrinkage.

    Args:
        error_matrix: Shape (N_episodes, K_evaluators), where 1 = error, 0 = correct.
        regularizer: Small shrinkage constant added to diagonal for numerical stability.

    Returns:
        Sigma: Symmetric matrix of shape (K, K) with values in [-1.0, 1.0].
    """
    E = np.asarray(error_matrix, dtype=float)
    if E.ndim != 2 or E.shape[0] < 2:
        K = E.shape[1] if E.ndim == 2 else 5
        return np.eye(K)

    # Center by mean
    E_centered = E - np.mean(E, axis=0, keepdims=True)
    variances = np.mean(E_centered ** 2, axis=0)

    # Standard deviations with lower bound to avoid divide-by-zero on perfect evaluators
    stds = np.sqrt(np.maximum(variances, 1e-8))

    # Covariance matrix
    cov = (E_centered.T @ E_centered) / E.shape[0]

    # Correlation = Cov / (std_i * std_j)
    corr = cov / (stds[:, None] @ stds[None, :])
    np.fill_diagonal(corr, 1.0)
    corr = np.clip(corr, -1.0, 1.0)

    # Symmetrize
    corr = 0.5 * (corr + corr.T)
    return corr + regularizer * np.eye(corr.shape[0])


def apply_redundancy_discount(
    reliability_scores: Sequence[float],
    correlation_matrix: np.ndarray,
    gamma: float = 0.5
) -> np.ndarray:
    """
    Discounts evaluator weights when mutual error correlation rho_ij > 0:
    w_i = r_i / (1 + gamma * sum_{j != i} max(0, rho_ij) * r_j)

    When evaluators are mutually independent (rho_ij <= 0), w_i = r_i.
    When K evaluators co-hallucinate with high correlation (rho_ij -> 1),
    their collective weight scales as O(1) instead of O(K).
    """
    r = np.asarray(reliability_scores, dtype=float)
    K = len(r)
    if correlation_matrix is None or correlation_matrix.shape != (K, K):
        return r

    discounted = np.zeros(K, dtype=float)
    for i in range(K):
        redundancy_penalty = 0.0
        for j in range(K):
            if i != j:
                rho = max(0.0, float(correlation_matrix[i, j]))
                redundancy_penalty += rho * float(r[j])

        discounted[i] = r[i] / (1.0 + gamma * redundancy_penalty)

    return discounted


def compute_effective_vote_count(
    weights: Sequence[float],
    correlation_matrix: np.ndarray,
    regularizer: float = 1e-8
) -> float:
    """
    Computes effective independent evaluator count N_eff(w, R) (Dossier Page 8):
    N_eff(w, R) = (sum_i w_i)^2 / (w^T @ R @ w)

    - For independent voters (R = I): N_eff = (sum w)^2 / sum(w^2) <= K.
    - For equal weights and uniform correlation rho: N_eff = K / (1 + (K - 1) * rho).
    """
    w = np.asarray(weights, dtype=float)
    if len(w) == 0:
        return 0.0
    R = np.asarray(correlation_matrix, dtype=float)
    if R.ndim != 2 or R.shape != (len(w), len(w)):
        R = np.eye(len(w))
    sum_w = float(np.sum(w))
    denom = float(w.T @ R @ w)
    if denom <= regularizer:
        return 0.0
    return float((sum_w ** 2) / denom)


class EvaluatorCorrelationTracker:
    """
    Maintains historical evaluator error statistics and dynamically computes Sigma.
    """

    def __init__(self, evaluator_names: Sequence[str], gamma: float = 0.5):
        self.names = list(evaluator_names)
        self.name_to_idx = {name: i for i, name in enumerate(self.names)}
        self.history: List[List[int]] = []
        self.gamma = gamma
        self.current_sigma = np.eye(len(self.names))

    def record_episode_errors(self, evaluator_errors: Dict[str, bool]):
        """Records whether each evaluator made an error in this problem episode."""
        row = [1 if evaluator_errors.get(name, False) else 0 for name in self.names]
        self.history.append(row)
        if len(self.history) >= 3:
            self.current_sigma = compute_pairwise_correlation(np.array(self.history))

    def get_discounted_weights(self, reliability_map: Dict[str, float]) -> Dict[str, float]:
        """Returns redundancy-discounted weights for all evaluators."""
        r_vec = [reliability_map.get(name, 0.5) for name in self.names]
        disc_vec = apply_redundancy_discount(r_vec, self.current_sigma, gamma=self.gamma)
        return {name: float(disc_vec[i]) for i, name in enumerate(self.names)}

    def get_effective_voters(self, reliability_map: Dict[str, float]) -> float:
        """Returns N_eff under current weights and correlation matrix."""
        disc_weights = [self.get_discounted_weights(reliability_map).get(name, 1.0) for name in self.names]
        return compute_effective_vote_count(disc_weights, self.current_sigma)

    def get_max_pairwise_correlation(self) -> float:
        """Returns the maximum off-diagonal correlation currently recorded."""
        if self.current_sigma.shape[0] < 2:
            return 0.0
        sig_no_diag = self.current_sigma.copy()
        np.fill_diagonal(sig_no_diag, -1.0)
        return float(np.max(sig_no_diag))
