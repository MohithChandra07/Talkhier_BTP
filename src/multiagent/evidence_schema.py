"""
Evidence Schema for Reliability-Calibrated & Order-Robust Multi-Agent Framework
TalkHier BTP - Proposed Middleware Contribution 2

Defines structured, canonical evidence records extracted from evaluator feedback.
Guarantees order-invariant hashing and serialization to eliminate feedback presentation order bias.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
import hashlib
import json


@dataclass(frozen=True)
class EvaluatorEvidence:
    """
    Immutable structured evidence record for an individual evaluator's critique.
    Frozen dataclass ensures hashability and prevents in-place mutation.
    """
    evaluator_id: str                          # e.g., 'Truth Table', 'Counterexample'
    criterion: str                             # Domain focus / evaluation dimension
    raw_score: float                           # Raw score reported (typically 0.0 - 10.0)
    verdict: str                               # 'ACCEPT', 'REVISE', 'UNCERTAIN', 'NOT_APPLICABLE'
    calibrated_reliability: float = 0.5        # Calibrated probability r_i in [0.0, 1.0]
    discounted_weight: float = 1.0             # Redundancy-discounted weight w_i
    claim: str = ""                            # Concise natural-language claim or proof summary
    suggested_choice: Optional[int] = None     # Suggested multiple choice index if revision needed
    tokens_used: int = 0                       # Token footprint for cost-aware decision making
    metadata: Dict[str, Any] = field(default_factory=dict, hash=False)

    def canonical_dict(self) -> Dict[str, Any]:
        """Returns sorted, deterministic dictionary representation."""
        return {
            "evaluator_id": self.evaluator_id,
            "criterion": self.criterion,
            "raw_score": round(float(self.raw_score), 4),
            "verdict": self.verdict,
            "calibrated_reliability": round(float(self.calibrated_reliability), 4),
            "discounted_weight": round(float(self.discounted_weight), 4),
            "claim": self.claim.strip(),
            "suggested_choice": self.suggested_choice,
            "tokens_used": int(self.tokens_used),
        }

    def canonical_hash(self) -> str:
        """Computes deterministic MD5 hash of canonical representation."""
        serialized = json.dumps(self.canonical_dict(), sort_keys=True)
        return hashlib.md5(serialized.encode("utf-8")).hexdigest()


def parse_evaluator_to_evidence(
    evaluator_name: str,
    raw_score: Optional[float],
    status: str,
    reason: str = "",
    suggested_choice: Optional[int] = None,
    tokens: int = 0
) -> EvaluatorEvidence:
    """
    Converts raw evaluator dispatch output into a validated EvaluatorEvidence record.
    """
    norm_score = float(raw_score) if raw_score is not None else 5.0
    status_upper = (status or "VALID").upper()

    if status_upper == "NOT_APPLICABLE":
        verdict = "NOT_APPLICABLE"
    elif norm_score >= 7.0:
        verdict = "ACCEPT"
    elif norm_score <= 4.0:
        verdict = "REVISE"
    else:
        verdict = "UNCERTAIN"

    criterion_map = {
        "Truth Table": "semantic_truth_conditions",
        "Counterexample": "countermodel_falsification",
        "Predicate Logic": "quantifier_and_predicate_rules",
        "Logical Argument": "structural_inference_soundness",
        "Formal Logic": "formal_deductive_rules",
    }

    return EvaluatorEvidence(
        evaluator_id=evaluator_name.strip(),
        criterion=criterion_map.get(evaluator_name.strip(), "general_reasoning"),
        raw_score=norm_score,
        verdict=verdict,
        calibrated_reliability=0.5,  # Populated downstream by reliability.py
        discounted_weight=1.0,       # Populated downstream by correlation.py
        claim=reason.strip(),
        suggested_choice=suggested_choice,
        tokens_used=tokens,
    )

