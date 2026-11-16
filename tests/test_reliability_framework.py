"""
Unit & Integration Tests for Reliability, Correlation, Order-Robustness, and RL Framework
TalkHier BTP - Proposed Framework Verification Suite
"""

import unittest
import numpy as np
import random

from multiagent.evidence_schema import EvaluatorEvidence, parse_evaluator_to_evidence
from multiagent.reliability import (
    PlattScaler,
    IsotonicCalibrator,
    compute_ece,
    compute_brier_score,
    EvaluatorReliabilityManager,
)
from multiagent.correlation import (
    compute_pairwise_correlation,
    apply_redundancy_discount,
    EvaluatorCorrelationTracker,
)
from multiagent.robust_aggregator import OrderRobustAggregator
from multiagent.rl_env import RefinementState, MultiAgentRefinementEnv
from multiagent.policy import FixedThresholdPolicy, LinUCBPolicy, LightweightDQNPolicy
from stress_tests import PermutationStressTest, WrongMajorityStressTest


class TestReliabilityFramework(unittest.TestCase):

    def test_1_evidence_schema_immutability_and_hashing(self):
        ev1 = parse_evaluator_to_evidence("Truth Table", 9.0, "VALID", "Valid inference", suggested_choice=0)
        ev2 = parse_evaluator_to_evidence("Truth Table", 9.0, "VALID", "Valid inference", suggested_choice=0)
        # Hashing and equality
        self.assertEqual(ev1.canonical_hash(), ev2.canonical_hash())
        self.assertEqual(ev1.verdict, "ACCEPT")

        # Frozen dataclass prevents mutation
        with self.assertRaises(Exception):
            ev1.raw_score = 10.0

    def test_2_platt_scaling_and_calibration_metrics(self):
        scaler = PlattScaler()
        # Train on synthetic data: low score -> 0, high score -> 1
        z = [1.0, 2.0, 3.0, 4.0, 7.0, 8.0, 9.0, 10.0]
        y = [0, 0, 0, 0, 1, 1, 1, 1]
        scaler.fit(z, y, epochs=200, lr=0.1)

        p_low = scaler.predict_proba(2.0)
        p_high = scaler.predict_proba(9.0)
        self.assertLess(p_low, 0.5)
        self.assertGreater(p_high, 0.5)

        # Calibration metrics
        ece, mce = compute_ece(y, [scaler.predict_proba(zi) for zi in z], n_bins=4)
        brier = compute_brier_score(y, [scaler.predict_proba(zi) for zi in z])
        self.assertGreaterEqual(ece, 0.0)
        self.assertLessEqual(ece, 1.0)
        self.assertGreaterEqual(brier, 0.0)

    def test_3_isotonic_regression_monotonicity(self):
        iso = IsotonicCalibrator()
        z = [1.0, 3.0, 5.0, 8.0, 10.0]
        y = [0, 0, 1, 1, 1]
        iso.fit(z, y)
        probs = [iso.predict_proba(zi) for zi in z]
        # Verify non-decreasing monotonicity
        for i in range(len(probs) - 1):
            self.assertLessEqual(probs[i], probs[i + 1])

    def test_4_pairwise_correlation_and_redundancy_discount(self):
        # 3 evaluators: E1 and E2 make identical errors (high correlation)
        # E3 makes independent errors
        error_matrix = np.array([
            [1, 1, 0],
            [1, 1, 0],
            [0, 0, 1],
            [0, 0, 0],
            [1, 1, 1],
        ])
        Sigma = compute_pairwise_correlation(error_matrix)
        self.assertEqual(Sigma.shape, (3, 3))
        # Correlation between E1 and E2 should be positive and high
        self.assertGreater(Sigma[0, 1], 0.7)

        # Redundancy discounting: E1 and E2 should have lower weights than independent E3
        r_scores = [0.8, 0.8, 0.8]
        disc_weights = apply_redundancy_discount(r_scores, Sigma, gamma=1.0)
        # E1 and E2 get discounted due to mutual redundancy
        self.assertLess(disc_weights[0], disc_weights[2])
        self.assertLess(disc_weights[1], disc_weights[2])

    def test_5_order_robust_zero_permutation_flip_rate(self):
        aggregator = OrderRobustAggregator()
        ev_list = [
            parse_evaluator_to_evidence("Truth Table", 2.0, "VALID", "Falsified", suggested_choice=3),
            parse_evaluator_to_evidence("Counterexample", 9.0, "VALID", "Verified counterexample", suggested_choice=3),
            parse_evaluator_to_evidence("Predicate Logic", 5.0, "VALID", "Uncertain", suggested_choice=0),
            parse_evaluator_to_evidence("Logical Argument", 3.0, "VALID", "Invalid argument", suggested_choice=3),
            parse_evaluator_to_evidence("Formal Logic", 6.0, "VALID", "Inconclusive", suggested_choice=0),
        ]

        stress = PermutationStressTest(n_permutations=30, seed=123)
        res = stress.run_on_evidence_set(ev_list, a0_choice=0, aggregator=aggregator)

        # Order-robust aggregator MUST achieve exactly 0% flip rate across permutations
        self.assertEqual(res["robust_flips"], 0)
        self.assertEqual(res["robust_flip_rate"], 0.0)

    def test_6_wrong_majority_resilience(self):
        stress = WrongMajorityStressTest(rho_correlated=0.85)
        res = stress.evaluate_resilience(ground_truth=3, a0_choice=0, use_calibration=True, use_correlation_discount=True)

        # Raw headcount fails because 3 wrong evaluators outvote 1 correct evaluator
        self.assertFalse(res["raw_headcount_correct"])
        self.assertEqual(res["raw_headcount_winner"], 2)

        # Calibrated + redundancy-discounted framework discounts co-hallucinating majority and wins
        self.assertTrue(res["discounted_correct"])
        self.assertEqual(res["discounted_winner"], 3)

    def test_7_rl_env_reward_and_linucb_policy(self):
        env = MultiAgentRefinementEnv()
        # Test reward components
        r_correct = env.compute_reward(final_correct=True, a0_correct=False, answer_changed=True, cumulative_tokens=1000)
        r_harmful = env.compute_reward(final_correct=False, a0_correct=True, answer_changed=True, cumulative_tokens=1000)
        self.assertGreater(r_correct, 0.0)
        self.assertLess(r_harmful, -1.0)  # Heavy penalty for harmful revision

        # LinUCB Policy test
        policy = LinUCBPolicy(state_dim=7, n_actions=4, alpha=0.5)
        s = RefinementState(mean_reliability=0.8, disagreement_index=0.2, aggregate_score=8.5)
        a = policy.select_action(s)
        self.assertIn(a, [0, 1, 2, 3])

        # Train policy on state: reward action 0 (ACCEPT)
        for _ in range(50):
            policy.update(s, action=0, reward=1.5)
        # Policy should strongly prefer action 0 for this state
        a_after = policy.select_action(s)
        self.assertEqual(a_after, 0)


if __name__ == "__main__":
    unittest.main()

