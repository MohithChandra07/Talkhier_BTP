"""
Order-Robust Set Aggregation Module
TalkHier BTP - Proposed Middleware Contribution 2

Implements order-invariant evidence aggregation G({F_1 ... F_k}).
Sorts feedback into a canonical sequence and performs permutation-invariant
weighted voting, mathematically guaranteeing a 0% Permutation Flip Rate.
"""

from typing import Dict, Any, List, Optional, Tuple, Sequence
import numpy as np

from multiagent.evidence_schema import EvaluatorEvidence


class OrderRobustAggregator:
    """
    Permutation-invariant evidence aggregator.
    Regardless of the order in which evaluators return critiques or are fed
    into the prompt, this aggregator produces strictly identical outputs.
    """

    def __init__(self, accept_threshold: float = 7.0, revise_threshold: float = 4.0):
        self.accept_threshold = accept_threshold
        self.revise_threshold = revise_threshold

    def canonicalize_evidence_set(self, evidence_list: Sequence[EvaluatorEvidence]) -> List[EvaluatorEvidence]:
        """
        Sorts evidence records by canonical key (evaluator_id, criterion).
        Ensures identical presentation independent of upstream collection order.
        """
        return sorted(evidence_list, key=lambda e: (e.evaluator_id, e.criterion))

    def aggregate(
        self,
        evidence_list: Sequence[EvaluatorEvidence],
        a0_choice: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Computes permutation-invariant aggregation over an evidence set.

        Returns:
            Dict containing:
            - consensus_verdict: 'ACCEPT', 'REVISE', or 'UNCERTAIN'
            - recommended_choice: Int choice index or a0_choice
            - aggregate_score: Calibrated weighted mean score in [0.0, 10.0]
            - mean_reliability: Average calibrated reliability r_i
            - variance_reliability: Variance of reliability across evaluators
            - disagreement_index: Disagreement metric among evaluators in [0.0, 1.0]
            - choice_votes: Weighted vote distribution over multiple choices
            - canonical_evidence: Deterministically sorted evidence list
            - permutation_hash: Hash of the canonical set
        """
        if not evidence_list:
            return {
                "consensus_verdict": "ACCEPT",
                "recommended_choice": a0_choice,
                "aggregate_score": 10.0,
                "mean_reliability": 0.5,
                "variance_reliability": 0.0,
                "disagreement_index": 0.0,
                "choice_votes": {},
                "canonical_evidence": [],
                "permutation_hash": "empty",
            }

        # 1. Canonical sorting ensures order invariance
        canonical_ev = self.canonicalize_evidence_set(evidence_list)

        # 2. Filter applicable evaluators
        applicable = [e for e in canonical_ev if e.verdict != "NOT_APPLICABLE"]
        if not applicable:
            # All N/A -> retain A0
            return {
                "consensus_verdict": "ACCEPT",
                "recommended_choice": a0_choice,
                "aggregate_score": 10.0,
                "mean_reliability": 0.5,
                "variance_reliability": 0.0,
                "disagreement_index": 0.0,
                "choice_votes": {},
                "canonical_evidence": canonical_ev,
                "permutation_hash": canonical_ev[0].canonical_hash(),
            }

        # 3. Weighted score calculation using discounted reliability weights
        weights = np.array([max(0.01, e.discounted_weight) for e in applicable], dtype=float)
        scores = np.array([e.raw_score for e in applicable], dtype=float)
        reliabilities = np.array([e.calibrated_reliability for e in applicable], dtype=float)

        weight_sum = np.sum(weights)
        norm_weights = weights / weight_sum if weight_sum > 0 else np.ones_like(weights) / len(weights)

        weighted_mean_score = float(np.sum(norm_weights * scores))
        mean_r = float(np.mean(reliabilities))
        var_r = float(np.var(reliabilities))

        # 4. Disagreement index (entropy/variance of scores)
        score_std = float(np.std(scores))
        disagreement_index = float(np.clip(score_std / 5.0, 0.0, 1.0))

        # 5. Choice-level weighted voting
        choice_votes: Dict[int, float] = {}
        for e in applicable:
            target_choice = e.suggested_choice if e.suggested_choice is not None else a0_choice
            if target_choice is not None:
                vote_weight = e.discounted_weight * (1.0 if e.verdict != "REVISE" else 1.5)
                choice_votes[target_choice] = choice_votes.get(target_choice, 0.0) + vote_weight

        # 6. Consensus decision
        if weighted_mean_score >= self.accept_threshold:
            verdict = "ACCEPT"
            rec_choice = a0_choice
        elif weighted_mean_score <= self.revise_threshold:
            verdict = "REVISE"
            # Pick highest voted choice
            if choice_votes:
                rec_choice = max(choice_votes.items(), key=lambda kv: kv[1])[0]
            else:
                rec_choice = a0_choice
        else:
            verdict = "UNCERTAIN"
            rec_choice = a0_choice

        # Permutation set hash
        import hashlib
        combined_hashes = "_".join(e.canonical_hash() for e in canonical_ev)
        perm_hash = hashlib.md5(combined_hashes.encode("utf-8")).hexdigest()

        return {
            "consensus_verdict": verdict,
            "recommended_choice": rec_choice,
            "aggregate_score": weighted_mean_score,
            "mean_reliability": mean_r,
            "variance_reliability": var_r,
            "disagreement_index": disagreement_index,
            "choice_votes": choice_votes,
            "canonical_evidence": canonical_ev,
            "permutation_hash": perm_hash,
        }

