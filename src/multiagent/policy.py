"""
Policy Controllers for RL Meta-Controller
TalkHier BTP - Proposed Middleware Contribution 3 (Part B)

Implements:
1. FixedThresholdPolicy (TalkHier Baseline: rigid cutoff M >= threshold)
2. LinUCBPolicy (Contextual Multi-Armed Bandit with exploration bonus)
3. QLearningPolicy (Lightweight Tabular / Feature-based Q-learning)
"""

import os
import sys
from typing import Dict, Any, List, Optional, Tuple, Sequence
import numpy as np

_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from multiagent.rl_env import RefinementState, ACTION_NAMES, ACTION_IDS


class BasePolicy:
    """Base policy interface for supervisory refinement actions."""

    def select_action(self, state: RefinementState) -> int:
        raise NotImplementedError

    def update(self, state: RefinementState, action: int, reward: float):
        pass


class FixedThresholdPolicy(BasePolicy):
    """
    TalkHier Baseline policy:
    If aggregate score >= threshold -> ACCEPT (0)
    Else -> REVISE (1)
    """

    def __init__(self, accept_threshold: float = 7.0, revise_threshold: float = 4.0):
        self.accept_threshold = accept_threshold
        self.revise_threshold = revise_threshold

    def select_action(self, state: RefinementState) -> int:
        if state.aggregate_score >= self.accept_threshold:
            return 0  # ACCEPT
        elif state.aggregate_score <= self.revise_threshold:
            return 1  # REVISE
        else:
            return 2  # VERIFY_MORE (if uncertain)


class LinUCBPolicy(BasePolicy):
    """
    LinUCB Contextual Bandit:
    For each action a in {0, 1, 2, 3}, maintains:
      A_a = D_a^T D_a + I_d
      b_a = D_a^T r_a
      theta_a = A_a^{-1} b_a
    Action selection:
      a* = argmax_a [ theta_a^T s + alpha * sqrt(s^T A_a^{-1} s) ]
    """

    def __init__(self, state_dim: int = 7, n_actions: int = 4, alpha: float = 0.8):
        self.state_dim = state_dim
        self.n_actions = n_actions
        self.alpha = float(alpha)

        # Ridge regression statistics for each action
        self.A = [np.eye(state_dim) for _ in range(n_actions)]
        self.b = [np.zeros(state_dim) for _ in range(n_actions)]
        self.A_inv = [np.eye(state_dim) for _ in range(n_actions)]

    def select_action(self, state: RefinementState) -> int:
        s = state.to_vector()
        p = np.zeros(self.n_actions)

        for a in range(self.n_actions):
            theta_a = self.A_inv[a] @ self.b[a]
            mean_est = float(theta_a @ s)
            conf_bound = self.alpha * float(np.sqrt(np.maximum(1e-8, s.T @ self.A_inv[a] @ s)))
            p[a] = mean_est + conf_bound

        return int(np.argmax(p))

    def update(self, state: RefinementState, action: int, reward: float):
        s = state.to_vector()
        a = int(action)
        if 0 <= a < self.n_actions:
            self.A[a] += np.outer(s, s)
            self.b[a] += reward * s
            # Recompute pseudo-inverse
            self.A_inv[a] = np.linalg.pinv(self.A[a])


class LightweightDQNPolicy(BasePolicy):
    """
    Linear function approximation Q-Learning / lightweight DQN controller:
    Q(s, a) = w_a^T s
    Updated via semi-gradient TD error:
      delta = r + gamma * max_a' Q(s', a') - Q(s, a)
      w_a <- w_a + lr * delta * s
    """

    def __init__(self, state_dim: int = 7, n_actions: int = 4, lr: float = 0.05, gamma: float = 0.95, epsilon: float = 0.1):
        self.state_dim = state_dim
        self.n_actions = n_actions
        self.lr = lr
        self.gamma = gamma
        self.epsilon = epsilon
        # Weight vectors for each action
        self.weights = np.zeros((n_actions, state_dim))
        # Initial priors: bias ACCEPT for high scores and REVISE for low scores
        self.weights[0, 4] = 1.0   # Action 0 (ACCEPT) positively weighted on score
        self.weights[1, 4] = -1.0  # Action 1 (REVISE) negatively weighted on score

    def q_values(self, s: np.ndarray) -> np.ndarray:
        return self.weights @ s

    def select_action(self, state: RefinementState) -> int:
        s = state.to_vector()
        if np.random.rand() < self.epsilon:
            return int(np.random.randint(self.n_actions))
        q = self.q_values(s)
        return int(np.argmax(q))

    def update(self, state: RefinementState, action: int, reward: float, next_state: Optional[RefinementState] = None, done: bool = True):
        s = state.to_vector()
        a = int(action)
        current_q = float(self.weights[a] @ s)

        if done or next_state is None:
            target = reward
        else:
            s_next = next_state.to_vector()
            target = reward + self.gamma * float(np.max(self.q_values(s_next)))

        td_error = target - current_q
        self.weights[a] += self.lr * td_error * s

