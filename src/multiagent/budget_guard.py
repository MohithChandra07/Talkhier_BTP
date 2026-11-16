"""
Budget Guard Module (Playbook Section 6, Page 10)
TalkHier BTP - Proposed Framework Safety & Termination

Enforces hard computational boundaries:
- Maximum refinement rounds (T_max)
- Maximum token budget per instance
- Maximum latency threshold
- Maximum extra verifications
"""

import time
from typing import Dict, Any, Optional, Tuple


class BudgetGuard:
    """
    Guarantees hard-stop termination to prevent infinite loops, token exhaustion,
    and timeout failures.
    """

    def __init__(
        self,
        max_rounds: int = 2,
        max_tokens_per_instance: int = 15000,
        max_latency_seconds: float = 600.0,
        max_extra_verifications: int = 1,
    ):
        self.max_rounds = max_rounds
        self.max_tokens = max_tokens_per_instance
        self.max_latency = max_latency_seconds
        self.max_extra = max_extra_verifications

        self.current_round = 0
        self.current_tokens = 0
        self.extra_verifications_used = 0
        self.start_time = time.time()

    def record_usage(self, tokens: int, round_increment: int = 0, is_extra_verification: bool = False):
        self.current_tokens += tokens
        self.current_round += round_increment
        if is_extra_verification:
            self.extra_verifications_used += 1

    def should_terminate(self) -> Tuple[bool, str]:
        """Checks if any budget threshold has been violated."""
        if self.current_round >= self.max_rounds:
            return True, f"MAX_ROUNDS_REACHED ({self.current_round}/{self.max_rounds})"
        if self.current_tokens >= self.max_tokens:
            return True, f"TOKEN_BUDGET_EXCEEDED ({self.current_tokens}/{self.max_tokens})"
        elapsed = time.time() - self.start_time
        if elapsed >= self.max_latency:
            return True, f"LATENCY_LIMIT_EXCEEDED ({elapsed:.1f}s/{self.max_latency}s)"
        return False, "OK"

    def can_verify_more(self) -> bool:
        """Determines if additional verification calls are permitted."""
        term, _ = self.should_terminate()
        if term:
            return False
        return self.extra_verifications_used < self.max_extra
