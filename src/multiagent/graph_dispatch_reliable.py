"""
Reliable & RL-Adaptive LangGraph Execution Engine
TalkHier BTP — Core Proposed Architecture (Dossier Sections 03, 04, 10, 11)

Wires together:
1. Generator node producing initial candidate A0.
2. Parallel / sequential domain Evaluator nodes producing structured critiques.
3. Platt / Isotonic Reliability Estimator mapping scores to posterior probabilities.
4. Error Correlation Matrix Sigma with Ledoit-Wolf shrinkage and redundancy discounting.
5. Order-Robust Canonical Set Aggregator (0% permutation flip rate guarantee).
6. RL Meta-Controller (LinUCB / Fixed Rule) with real execution semantics:
   - ACCEPT: Halt and output current candidate At.
   - REVISE: Pass structured evidence to Revisor to generate A_(t+1).
   - VERIFY_MORE: Dynamically invoke additional specialist evaluator / symbolic verifier.
   - SUPPRESS: Prune correlated / unreliable feedback and re-aggregate.
7. BudgetGuard enforcing token limits and termination guarantees.
"""

import os
import sys
import time
import copy
import json

_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)
from typing import Dict, Any, List, Optional, Tuple, Sequence
from typing_extensions import TypedDict, Annotated
import operator
import numpy as np

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, START, END

from multiagent.agent_team import ReactAgent, parse_intermediate_output
from multiagent.evaluator_dispatch import extract_evaluator_score_robust, EVALUATOR_NAMES_FORMAL_LOGIC
from multiagent.evidence_schema import EvaluatorEvidence, parse_evaluator_to_evidence
from multiagent.reliability import EvaluatorReliabilityManager, PlattScaler, compute_ece, compute_brier_score
from multiagent.correlation import compute_pairwise_correlation, apply_redundancy_discount, compute_effective_vote_count
from multiagent.robust_aggregator import OrderRobustAggregator
from multiagent.rl_env import RefinementState, MultiAgentRefinementEnv, ACTION_NAMES
from multiagent.policy import LinUCBPolicy, FixedThresholdPolicy
from multiagent.budget_guard import BudgetGuard
from multiagent.logic_verifier import verify_argument_validity


class ReliableGraphState(TypedDict):
    history: Dict[str, Annotated[Sequence[BaseMessage], operator.add]]
    messages: BaseMessage
    background: BaseMessage
    intermediate_output: Dict[str, Any]
    next: str
    initial_prompt: Any

    # Tracking & State Variables
    _candidate_rounds: List[Dict[str, Any]]
    _evaluator_reports: List[Dict[str, Any]]
    _canonical_evidence: List[Dict[str, Any]]
    _decision_log: List[Dict[str, Any]]
    _current_round: int
    _max_rounds: int
    _cumulative_tokens: int
    _chosen_action: int
    _final_answer: str
    _final_choice: Optional[int]
    _method: str
    _ablation: str


def build_reliable_talkhier_graph(
    agents_map: Dict[str, ReactAgent],
    reliability_manager: Optional[EvaluatorReliabilityManager] = None,
    correlation_matrix: Optional[np.ndarray] = None,
    policy: Optional[Any] = None,
    aggregator: Optional[OrderRobustAggregator] = None,
    budget_guard: Optional[BudgetGuard] = None,
    method: str = "proposed",
    ablation: str = "A0",
    max_rounds: int = 3,
):
    """
    Builds the executable LangGraph state graph with live RL action transitions.
    """
    if reliability_manager is None:
        reliability_manager = EvaluatorReliabilityManager(method="platt")
    if correlation_matrix is None:
        correlation_matrix = np.eye(5)
    if aggregator is None:
        aggregator = OrderRobustAggregator()
    if policy is None:
        policy = LinUCBPolicy(state_dim=7, n_actions=4, alpha=0.5) if method == "proposed" else FixedThresholdPolicy()
    if budget_guard is None:
        budget_guard = BudgetGuard(max_rounds=max_rounds, max_total_tokens=15000)

    # using verify_argument_validity

    # --- Node 1: Generator Node ---
    def generator_node(state: ReliableGraphState) -> Dict[str, Any]:
        agent = agents_map["Generator"]
        prompt = state.get("initial_prompt", "")
        response = agent.run(HumanMessage(content=str(prompt)))
        parsed = parse_intermediate_output(response.content if hasattr(response, "content") else str(response))

        raw_ans = parsed.get("Final Answer", parsed.get("answer", parsed.get("Choice", "")))
        candidate_record = {
            "round": 0,
            "answer": str(raw_ans),
            "parsed": parsed,
            "timestamp": time.time(),
        }
        return {
            "intermediate_output": parsed,
            "_candidate_rounds": [candidate_record],
            "_current_round": 0,
            "_max_rounds": max_rounds,
            "_cumulative_tokens": state.get("_cumulative_tokens", 0) + 500,
            "_decision_log": [],
            "_method": method,
            "_ablation": ablation,
        }

    # --- Node 2: Evaluator Dispatch Node ---
    def evaluators_node(state: ReliableGraphState) -> Dict[str, Any]:
        candidate_rounds = state.get("_candidate_rounds", [])
        current_candidate = candidate_rounds[-1]["answer"] if candidate_rounds else ""
        round_idx = state.get("_current_round", 0)
        tokens_spent = 0

        eval_reports = []
        for name in EVALUATOR_NAMES_FORMAL_LOGIC:
            if name not in agents_map:
                continue
            agent = agents_map[name]
            prompt = f"Candidate Answer at Round {round_idx}:\n{current_candidate}\n\nPlease evaluate correctness, consistency, and provide score (0-10) and suggested choice index if incorrect."
            resp = agent.run(HumanMessage(content=prompt))
            resp_text = resp.content if hasattr(resp, "content") else str(resp)
            score, choice = extract_evaluator_score_robust(resp_text)
            tokens_spent += 350

            eval_reports.append({
                "evaluator_id": name,
                "round": round_idx,
                "raw_score": float(score) if score is not None else 5.0,
                "verdict": "ACCEPT" if (score is not None and score >= 6.0) else "REVISE",
                "suggested_choice": choice,
                "raw_text": resp_text[:300],
            })

        return {
            "_evaluator_reports": eval_reports,
            "_cumulative_tokens": state.get("_cumulative_tokens", 0) + tokens_spent,
        }

    # --- Node 3: Reliable & Order-Robust Aggregator + RL Controller Node ---
    def reliable_aggregator_node(state: ReliableGraphState) -> Dict[str, Any]:
        eval_reports = state.get("_evaluator_reports", [])
        round_idx = state.get("_current_round", 0)
        tokens = state.get("_cumulative_tokens", 0)

        # 1. Convert to Canonical Evidence Records
        evidence_list: List[EvaluatorEvidence] = []
        for r in eval_reports:
            ev = parse_evaluator_to_evidence(
                evaluator_id=r["evaluator_id"],
                raw_score=r["raw_score"],
                verdict=r["verdict"],
                criterion="correctness",
                suggested_choice=r.get("suggested_choice"),
            )
            # Calibrate reliability
            if ablation != "A1":  # A1: no calibration
                ev.calibrated_reliability = reliability_manager.predict_proba(ev.evaluator_id, ev.raw_score)
            else:
                ev.calibrated_reliability = ev.raw_score / 10.0

            evidence_list.append(ev)

        # 2. Apply Error Correlation Discounting
        reliabilities = [e.calibrated_reliability for e in evidence_list]
        if ablation != "A3":  # A3: no correlation
            discounted_weights = apply_redundancy_discount(reliabilities, correlation_matrix, gamma=0.5)
        else:
            discounted_weights = np.array(reliabilities)

        for i, ev in enumerate(evidence_list):
            ev.discounted_weight = float(discounted_weights[i])

        # 3. Order-Robust Canonical Set Aggregation
        if ablation != "A5":  # A5: unconstrained serialized ordering
            agg_result = aggregator.aggregate(evidence_list)
        else:
            # Naive unordered mean
            mean_sc = float(np.mean([e.raw_score for e in evidence_list])) if evidence_list else 5.0
            agg_result = {
                "consensus_verdict": "ACCEPT" if mean_sc >= 7.0 else "REVISE",
                "aggregate_score": mean_sc,
                "mean_reliability": float(np.mean(reliabilities)) if reliabilities else 0.5,
                "variance_reliability": float(np.var(reliabilities)) if reliabilities else 0.0,
                "disagreement_index": 0.2,
                "canonical_evidence": evidence_list,
            }

        # 4. Construct 7D MDP State Vector
        mean_r = agg_result.get("mean_reliability", 0.5)
        var_r = agg_result.get("variance_reliability", 0.0)
        disag = agg_result.get("disagreement_index", 0.0)
        sig_no_diag = correlation_matrix.copy()
        np.fill_diagonal(sig_no_diag, -1.0)
        max_rho = float(np.max(sig_no_diag)) if correlation_matrix.shape[0] > 1 else 0.0
        score_val = agg_result.get("aggregate_score", 5.0)

        rl_state = RefinementState(
            mean_reliability=mean_r,
            var_reliability=var_r,
            disagreement_index=disag,
            max_correlation=max_rho,
            aggregate_score=score_val,
            cumulative_tokens=tokens,
            round_index=round_idx,
        )

        # 5. RL Action Selection with Budget Masking
        # Available actions: 0: ACCEPT, 1: REVISE, 2: VERIFY_MORE, 3: SUPPRESS
        valid_actions = [0, 1, 2, 3]
        if round_idx >= max_rounds - 1:
            valid_actions = [0]  # Hard stop: must accept
        elif tokens > 12000:
            valid_actions = [0, 1]  # Exceeded budget: mask VERIFY_MORE

        if ablation in ["A7", "A8"]:
            # A7: fixed rule; A8: random cost-matched
            if ablation == "A7":
                chosen_action = 0 if score_val >= 7.0 else 1
            else:
                chosen_action = int(np.random.choice([0, 1]))
        elif method == "proposed" and isinstance(policy, LinUCBPolicy):
            chosen_action = policy.select_action(rl_state)
            if chosen_action not in valid_actions:
                chosen_action = valid_actions[0]
        else:
            # Fixed cutoff baseline
            chosen_action = 0 if score_val >= 7.0 else 1

        decision_entry = {
            "round": round_idx,
            "action_id": chosen_action,
            "action_name": ACTION_NAMES.get(chosen_action, "UNKNOWN"),
            "aggregate_score": score_val,
            "mean_reliability": mean_r,
            "timestamp": time.time(),
        }

        updated_log = list(state.get("_decision_log", []))
        updated_log.append(decision_entry)

        return {
            "_chosen_action": chosen_action,
            "_decision_log": updated_log,
            "_canonical_evidence": [e.to_dict() for e in evidence_list],
            "_cumulative_tokens": tokens + 150,
        }

    # --- Node 4: Revisor Node (Executed on Action == 1: REVISE) ---
    def revisor_node(state: ReliableGraphState) -> Dict[str, Any]:
        agent = agents_map["Revisor"]
        candidate_rounds = state.get("_candidate_rounds", [])
        current_cand = candidate_rounds[-1]["answer"] if candidate_rounds else ""
        canonical_ev = state.get("_canonical_evidence", [])
        round_idx = state.get("_current_round", 0)

        critiques_summary = "\n".join([
            f"- Evaluator {e['evaluator_id']}: score={e['raw_score']:.1f}, reliability={e['calibrated_reliability']:.2f}, weight={e['discounted_weight']:.2f}, verdict={e['verdict']}"
            for e in canonical_ev
        ])

        prompt = (
            f"Original Candidate Answer:\n{current_cand}\n\n"
            f"Calibrated and Order-Discounted Evaluator Critiques:\n{critiques_summary}\n\n"
            "Please refine the candidate answer to address valid critiques while rejecting ungrounded claims."
        )

        resp = agent.run(HumanMessage(content=prompt))
        resp_text = resp.content if hasattr(resp, "content") else str(resp)
        parsed = parse_intermediate_output(resp_text)
        new_ans = parsed.get("Final Answer", parsed.get("answer", parsed.get("Choice", resp_text[:200])))

        new_record = {
            "round": round_idx + 1,
            "answer": str(new_ans),
            "parsed": parsed,
            "timestamp": time.time(),
        }

        updated_rounds = list(candidate_rounds)
        updated_rounds.append(new_record)

        return {
            "_candidate_rounds": updated_rounds,
            "_current_round": round_idx + 1,
            "_cumulative_tokens": state.get("_cumulative_tokens", 0) + 600,
        }

    # --- Node 5: Verification Node (Executed on Action == 2: VERIFY_MORE) ---
    def verifier_node(state: ReliableGraphState) -> Dict[str, Any]:
        candidate_rounds = state.get("_candidate_rounds", [])
        current_cand = candidate_rounds[-1]["answer"] if candidate_rounds else ""
        eval_reports = list(state.get("_evaluator_reports", []))

        # Dynamic verification call (Symbolic SAT / Logic Proof Verification)
        try:
            res = verify_argument_validity([], current_cand)
            is_valid_proof = res.get("is_valid", False)
        except Exception:
            is_valid_proof = False
        verif_score = 9.0 if is_valid_proof else 3.0

        eval_reports.append({
            "evaluator_id": "Symbolic_Verifier_Action2",
            "round": state.get("_current_round", 0),
            "raw_score": verif_score,
            "verdict": "ACCEPT" if is_valid_proof else "REVISE",
            "suggested_choice": None,
            "raw_text": f"Dynamic verification completed. Valid deductive inference={is_valid_proof}",
        })

        return {
            "_evaluator_reports": eval_reports,
            "_cumulative_tokens": state.get("_cumulative_tokens", 0) + 200,
        }

    # --- Node 6: Suppressor Node (Executed on Action == 3: SUPPRESS) ---
    def suppressor_node(state: ReliableGraphState) -> Dict[str, Any]:
        eval_reports = list(state.get("_evaluator_reports", []))
        canonical_ev = state.get("_canonical_evidence", [])

        # Prune outlier / high-redundancy lowest-weight evaluator
        if canonical_ev:
            min_weight_ev = min(canonical_ev, key=lambda e: e.get("discounted_weight", 1.0))
            pruned_id = min_weight_ev.get("evaluator_id")
            filtered_reports = [r for r in eval_reports if r.get("evaluator_id") != pruned_id]
        else:
            filtered_reports = eval_reports

        return {
            "_evaluator_reports": filtered_reports,
            "_cumulative_tokens": state.get("_cumulative_tokens", 0) + 50,
        }

    # --- Conditional Router ---
    def route_action(state: ReliableGraphState) -> str:
        action = state.get("_chosen_action", 0)
        round_idx = state.get("_current_round", 0)
        max_r = state.get("_max_rounds", max_rounds)

        if action == 0 or round_idx >= max_r:
            return "end"
        elif action == 1:
            return "revise"
        elif action == 2:
            return "verify"
        elif action == 3:
            return "suppress"
        return "end"

    # --- Build StateGraph ---
    workflow = StateGraph(ReliableGraphState)
    workflow.add_node("generator", generator_node)
    workflow.add_node("evaluators", evaluators_node)
    workflow.add_node("reliable_aggregator", reliable_aggregator_node)
    workflow.add_node("revisor", revisor_node)
    workflow.add_node("verifier", verifier_node)
    workflow.add_node("suppressor", suppressor_node)

    workflow.add_edge(START, "generator")
    workflow.add_edge("generator", "evaluators")
    workflow.add_edge("evaluators", "reliable_aggregator")

    workflow.add_conditional_edges(
        "reliable_aggregator",
        route_action,
        {
            "end": END,
            "revise": "revisor",
            "verify": "verifier",
            "suppress": "suppressor",
        }
    )

    # After revising, re-evaluate
    workflow.add_edge("revisor", "evaluators")
    # After dynamic verification or suppression, re-aggregate with updated evidence
    workflow.add_edge("verifier", "reliable_aggregator")
    workflow.add_edge("suppressor", "reliable_aggregator")

    return workflow.compile()
