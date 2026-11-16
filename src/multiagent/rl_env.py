"""
Reinforcement Learning Environment for Multi-Agent Refinement MDP
TalkHier BTP - Proposed Middleware Contribution 3

Formulates the supervisory refinement step as a Markov Decision Process (MDP):
State s_t: Compact numeric vector [mean(r), var(r), disagreement, max(rho), score, tokens, round]
Actions a_t: {0: ACCEPT, 1: REVISE, 2: VERIFY_MORE, 3: SUPPRESS}
Reward R: Multi-objective function balancing task correctness, harmful revision penalty,
          token consumption, and permutation stability.
"""

from typing import Dict, Any, List, Optional, Tuple
import numpy as np


ACTION_NAMES = {
    0: "ACCEPT",
    1: "REVISE",
    2: "VERIFY_MORE",
    3: "SUPPRESS",
}
ACTION_IDS = {v: k for k, v in ACTION_NAMES.items()}


class RefinementState:
    """Represents the compact numeric state vector s_t for the RL controller."""

    def __init__(
        self,
        mean_reliability: float = 0.5,
        var_reliability: float = 0.0,
        disagreement_index: float = 0.0,
        max_correlation: float = 0.0,
        aggregate_score: float = 5.0,
        cumulative_tokens: int = 0,
        round_index: int = 1,
    ):
        self.mean_reliability = float(np.clip(mean_reliability, 0.0, 1.0))
        self.var_reliability = float(np.clip(var_reliability, 0.0, 1.0))
        self.disagreement_index = float(np.clip(disagreement_index, 0.0, 1.0))
        self.max_correlation = float(np.clip(max_correlation, -1.0, 1.0))
        self.aggregate_score = float(np.clip(aggregate_score, 0.0, 10.0))
        self.cumulative_tokens = int(cumulative_tokens)
        self.round_index = int(round_index)

    def to_vector(self) -> np.ndarray:
        """Returns normalized 7-dimensional feature vector."""
        return np.array([
            self.mean_reliability,
            self.var_reliability,
            self.disagreement_index,
            (self.max_correlation + 1.0) / 2.0,  # Map [-1, 1] -> [0, 1]
            self.aggregate_score / 10.0,         # Map [0, 10] -> [0, 1]
            min(1.0, self.cumulative_tokens / 10000.0),
            min(1.0, self.round_index / 3.0),
        ], dtype=float)


class MultiAgentRefinementEnv:
    """
    Simulation / Step Environment for evaluating and training RL meta-controllers.
    """

    def __init__(
        self,
        c_harmful: float = 2.0,      # Heavy penalty against flipping correct A0 into incorrect
        c_token: float = 0.15,       # Linear cost penalty per 10k tokens
        c_flip: float = 1.0,         # Penalty for permutation instability
        max_rounds: int = 3,
    ):
        self.c_harmful = c_harmful
        self.c_token = c_token
        self.c_flip = c_flip
        self.max_rounds = max_rounds

    def compute_reward(
        self,
        final_correct: bool,
        a0_correct: bool,
        answer_changed: bool,
        cumulative_tokens: int,
        permutation_flips: int = 0,
    ) -> float:
        """
        Multi-objective terminal reward function:
        R = +1.0 * Correct - c_harmful * HarmfulRevision - c_token * Tokens - c_flip * Flips
        """
        # Base task accuracy reward
        r = 1.0 if final_correct else -0.5

        # Harmful revision trap: A0 was correct, but revised into wrong
        is_harmful = a0_correct and (not final_correct) and answer_changed
        if is_harmful:
            r -= self.c_harmful

        # Helpful revision bonus: A0 was wrong, successfully corrected
        is_helpful = (not a0_correct) and final_correct and answer_changed
        if is_helpful:
            r += 0.5

        # Resource efficiency penalty
        norm_tokens = min(2.0, cumulative_tokens / 5000.0)
        r -= self.c_token * norm_tokens

        # Stability penalty
        if permutation_flips > 0:
            r -= self.c_flip * min(2.0, permutation_flips / 5.0)

        return float(r)

