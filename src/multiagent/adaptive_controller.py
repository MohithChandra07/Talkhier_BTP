"""
Adaptive Controller Module (Playbook Section 6, Page 10)
TalkHier BTP - Proposed Framework Component 3

Implements the RL-Assisted Adaptive Refinement Policy:
- Contextual Bandit (LinUCB) with Upper Confidence Bound exploration
- Deterministic Rule-Based Baselines (Fixed Cutoff, Always Revise Once, Verify on Uncertainty)
- Action Masking (Budget Guards restrict VERIFY_MORE when resource caps are hit)
"""

from typing import Dict, Any, List, Optional, Tuple, Sequence
import numpy as np

from multiagent.rl_env import RefinementState, ACTION_NAMES, ACTION_IDS
from multiagent.policy import BasePolicy, FixedThresholdPolicy, LinUCBPolicy, LightweightDQNPolicy
from multiagent.budget_guard import BudgetGuard


class AdaptiveController:
    """
    Adaptive Supervisory Meta-Controller with dynamic action selection and budget masking.
    """

    def __init__(
        self,
        mode: str = "linucb",
        state_dim: int = 7,
        n_actions: int = 4,
        alpha: float = 0.6,
        accept_threshold: float = 7.0,
        revise_threshold: float = 4.0,
    ):
        self.mode = mode.lower()
        self.state_dim = state_dim
        self.n_actions = n_actions

        if self.mode == "linucb":
            self.policy: BasePolicy = LinUCBPolicy(state_dim=state_dim, n_actions=n_actions, alpha=alpha)
        elif self.mode == "dqn":
            self.policy = LightweightDQNPolicy(state_dim=state_dim, n_actions=n_actions)
        else:  # "rule" / baseline
            self.policy = FixedThresholdPolicy(accept_threshold=accept_threshold, revise_threshold=revise_threshold)

    def select_action(
        self,
        state: RefinementState,
        budget_guard: Optional[BudgetGuard] = None
    ) -> Tuple[int, str]:
        """
        Selects refinement action with action-masking:
        - If budget permits no more extra verifications, action 2 (VERIFY_MORE) is masked.
        - If round >= max_rounds, action 1 (REVISE) is masked, forcing ACCEPT.
        """
        # 1. Base policy selection
        raw_action = self.policy.select_action(state)

        # 2. Apply Action Masking
        action = raw_action
        if budget_guard is not None:
            # Mask VERIFY_MORE if budget exhausted
            if action == 2 and not budget_guard.can_verify_more():
                # Fall back to REVISE if score is low, otherwise ACCEPT
                action = 1 if state.aggregate_score <= 5.0 else 0

            # Force ACCEPT if max rounds reached
            should_term, _ = budget_guard.should_terminate()
            if should_term and action in (1, 2):
                action = 0

        action_name = ACTION_NAMES.get(action, "ACCEPT")
        return action, action_name

    def record_feedback(self, state: RefinementState, action: int, reward: float):
        """Updates bandit/RL policy weights based on environment reward feedback."""
        self.policy.update(state, action, reward)

