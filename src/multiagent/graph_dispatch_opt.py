"""
Sprint 3 Optimization — Graph-Level Forced Evaluator Integration
Optimized implementation of the mandatory sequential LangGraph dispatch pipeline.

Enhancements:
1. Evaluator Reliability: Specialized, evidence-based instructions for each of the 5 evaluators.
2. Structured Output: Case-insensitive score parsing, robust JSON extraction, precise evaluator key seeding (eliminates <Your Evaluator Name> placeholder).
3. Evaluator Reasoning Quality: Explicit counterexample definition (Premises=True, Conclusion=False) preventing Problem 3 fallacies.
4. Score Aggregation: Disagreement detection, strict denominator calculation (NOT_APPLICABLE & NO_EVALUATION excluded), voting vs scoring distinction.
5. Revisor Reliability: Presumption of A0 validity, counterexample fallacy rejection rule, zero ground-truth leakage, A0 immutability.
6. Runtime & Token Optimization: Reduced prompt noise, clean history merging, eliminated unnecessary retries.
7. Modular, maintainable architecture preserving the exact LangGraph topology.
"""

import time
import copy
import json
import ast
from typing import Dict, Any, List, Optional, Tuple, Sequence
from typing_extensions import TypedDict, Annotated
import operator

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, START, END

from multiagent.agent_team import (
    ReactAgent,
    extract_evaluator_score,
    parse_intermediate_output,
)
from multiagent.evaluator_dispatch import (
    extract_evaluator_score_robust,
    EVALUATOR_NAMES_FORMAL_LOGIC,
)


class GraphAgentState(TypedDict):
    history: Dict[str, Annotated[Sequence[BaseMessage], operator.add]]
    messages: BaseMessage
    background: BaseMessage
    intermediate_output: Dict[str, Any]
    next: str
    initial_prompt: Any
    _initial_intermediate_output: Dict[str, Any]
    _evaluator_trace: List[Dict[str, Any]]
    _individual_evaluations: Dict[str, Any]
    _evaluation_aggregation: Dict[str, Any]
    _revision_history: List[Dict[str, Any]]


# Specialized guidance per evaluator to ensure high reasoning fidelity
EVALUATOR_SPECIALIZED_GUIDANCE = {
    "Truth Table": (
        "Role: Truth Table Evaluator.\n"
        "- If the question asks whether an argument is valid/invalid using a truth table, recall the strict definition of deductive validity:\n"
        "  An argument is VALID if and only if there is NO truth assignment where all premises are TRUE and the conclusion is FALSE.\n"
        "  A counterexample requires: ALL PREMISES = True AND CONCLUSION = False.\n"
        "  CRITICAL: A row or choice where the conclusion is TRUE CANNOT be a counterexample!\n"
        "- If the problem is about identifying arguments or translating sentences where a truth table is NOT required, return 'N/A' as the score."
    ),
    "Counterexample": (
        "Role: Counterexample Evaluator.\n"
        "- A counterexample to an argument requires an assignment of truth values that makes ALL PREMISES TRUE and the CONCLUSION FALSE.\n"
        "  CRITICAL: If a proposed counterexample option assigns values that make the conclusion TRUE, it is logically impossible for it to be a counterexample!\n"
        "- If no counterexample is required for this question (e.g. direct sentence translation), return 'N/A' as the score."
    ),
    "Predicate Logic": (
        "Role: Predicate Logic Evaluator.\n"
        "- Check syntax and argument ordering in relations (e.g., Txy means 'x teaches y' -> 'David teaches Chris' is Tdc, NOT Tcd).\n"
        "- Check quantifiers: universal (all, every) vs existential (some, exists).\n"
        "- If the problem involves purely propositional logic without predicates or quantifiers, return 'N/A' as the score."
    ),
    "Logical Argument": (
        "Role: Logical Argument Evaluator.\n"
        "- Verify whether the identified conclusion genuinely follows from the supporting premises.\n"
        "- The conclusion is the central claim; premise indicator phrases ('Because of this...', 'Since...') indicate premises, not the bare conclusion statement itself.\n"
        "- In truth-table validity arguments, check whether the inferential step from premises to conclusion is deductively sound."
    ),
    "Formal Logic": (
        "Role: Formal Logic Evaluator.\n"
        "- Check formal logical translation and connective semantics: ~ (negation), • (conjunction), ∨ (disjunction), ⊃ (implication).\n"
        "- Verify negation scope: (~B • E) means 'not B, and E', whereas ~(B • E) means 'it is not the case that both B and E'.\n"
        "- Ensure syntactic and semantic alignment with formal logic rules."
    ),
}


def classify_evaluation_status_opt(
    intermediate_output: Any,
    raw_response: str,
    evaluator_name: str,
) -> Tuple[str, Optional[int], str, bool, Optional[int]]:
    """
    Optimized status classification:
    - Case-insensitive key extraction ('Correctness Score', 'correctness score', 'Score', 'score').
    - Handles 'evaluation' block with evaluator name, 'Evaluator', or direct dictionary.
    - Explicit NOT_APPLICABLE detection: score is None (never 0 or 10).
    - Returns: (status, score, reason, is_applicable, explicit_choice_vote)
    """
    na_indicators = [
        "n/a", "not applicable", "not required", "is not needed",
        "cannot be used", "doesn't apply", "does not apply", "no truth table is required",
        "no counterexample is required"
    ]
    raw_lower = raw_response.lower() if raw_response else ""

    # Check for direct or nested dictionary
    target_dict = None
    if isinstance(intermediate_output, dict):
        eval_block = intermediate_output.get("evaluation", intermediate_output)
        if isinstance(eval_block, dict):
            # 1. Exact or case-insensitive name match
            for k, v in eval_block.items():
                if isinstance(v, dict):
                    if k.lower() == evaluator_name.lower() or evaluator_name.lower() in k.lower() or k.lower() in evaluator_name.lower():
                        target_dict = v
                        break
            # 2. Generic 'Evaluator' key match
            if target_dict is None and "Evaluator" in eval_block and isinstance(eval_block["Evaluator"], dict):
                target_dict = eval_block["Evaluator"]
            # 3. Direct dictionary check if single evaluation
            if target_dict is None:
                for k, v in eval_block.items():
                    if isinstance(v, dict) and any(score_key in [x.lower() for x in v.keys()] for score_key in ["correctness score", "score"]):
                        target_dict = v
                        break
        elif any(score_key in [x.lower() for x in intermediate_output.keys()] for score_key in ["correctness score", "score"]):
            target_dict = intermediate_output

    if target_dict and isinstance(target_dict, dict):
        raw_score_val = None
        for sk in ["Correctness Score", "correctness score", "Score", "score"]:
            if sk in target_dict:
                raw_score_val = target_dict[sk]
                break

        reason = str(target_dict.get("Reason", target_dict.get("reason", "")))
        reason_lower = reason.lower()

        # Check explicit N/A indicators in reason
        if any(ind in reason_lower for ind in na_indicators):
            return "NOT_APPLICABLE", None, reason, False, None

        if raw_score_val is not None:
            raw_score_str = str(raw_score_val).strip().lower()
            if raw_score_str in ["n/a", "na", "none", "null"]:
                return "NOT_APPLICABLE", None, reason or "Evaluator marked N/A in score field.", False, None

            try:
                parsed_score = int(float(raw_score_val))
                if 0 <= parsed_score <= 10:
                    return "VALID", parsed_score, reason, True, None
            except (ValueError, TypeError):
                pass

    # Check raw response for explicit N/A statements
    if any(ind in raw_lower for ind in [
        "truth table is not required", "truth table is not applicable",
        "counterexample is not required", "counterexample is not applicable",
        "no counterexample is required", "no truth table is required",
        "predicate logic is not required", "predicate logic is not applicable"
    ]):
        return "NOT_APPLICABLE", None, "Method explicitly identified as not applicable in reasoning.", False, None

    # Extract score robustly
    score, st, reason = extract_evaluator_score_robust(
        intermediate_output, raw_response, evaluator_name
    )

    if st == "OK" and score is not None:
        reason_lower = reason.lower()
        if "not required" in reason_lower or "not applicable" in reason_lower or "return 'n/a'" in reason_lower:
            return "NOT_APPLICABLE", None, reason, False, None
        return "VALID", score, reason, True, None

    return "NO_EVALUATION", None, reason or "Failed to extract valid structured score.", True, None


def run_evaluator_node_optimized(
    eval_member_fn,
    state: GraphAgentState,
    eval_name: str,
    max_retries: int = 2,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Optimized evaluator execution:
    - Pre-seeds base history with exact evaluator name to eliminate formatting ambiguity.
    - Deepcopies state history per attempt so attempts do not wipe downstream keys.
    - Handles retries gracefully with targeted corrective feedback.
    """
    attempts_trace = []
    eval_record = None
    agent_result = {}
    base_history = {k: list(v) for k, v in state.get("history", {}).items()}

    for attempt in range(max_retries + 1):
        t0 = time.time()
        current_state = dict(state)
        current_state["history"] = {k: list(v) for k, v in base_history.items()}

        agent_result = eval_member_fn(current_state)
        elapsed = round(time.time() - t0, 2)

        raw_msg = agent_result.get("messages")
        raw_text = raw_msg.content if hasattr(raw_msg, "content") else str(raw_msg)
        io_out = agent_result.get("intermediate_output", {})

        status, score, reason, is_applicable, explicit_vote = classify_evaluation_status_opt(
            io_out, raw_text, eval_name
        )

        attempt_info = {
            "attempt": attempt + 1,
            "status": status,
            "score": score,
            "reason": reason,
            "is_applicable": is_applicable,
            "raw_response": raw_text,
            "intermediate_output": io_out,
            "runtime_s": elapsed,
        }
        attempts_trace.append(attempt_info)

        if status in ("VALID", "NOT_APPLICABLE"):
            eval_record = {
                "name": eval_name,
                "invoked": True,
                "status": status,
                "score": score,
                "reason": reason,
                "is_applicable": is_applicable,
                "explicit_vote": explicit_vote,
                "retries": attempt,
                "runtime_s": elapsed,
                "raw_response": raw_text,
                "intermediate_output": io_out,
                "attempts_trace": attempts_trace,
            }
            break

        if attempt < max_retries:
            corr_prompt = (
                f"Your previous output was missing the required structured JSON format. "
                f"Please evaluate strictly as '{eval_name}' and return: "
                f'{{"evaluation": {{"{eval_name}": {{"Correctness Score": <integer 0-10 or "N/A">, "Reason": "<evidence-based reasoning>"}}}}}}'
            )
            base_history[eval_name] = base_history.get(eval_name, []) + [
                HumanMessage(content=corr_prompt, name="Evaluator_Supervisor")
            ]

    if eval_record is None:
        last_attempt = attempts_trace[-1]
        eval_record = {
            "name": eval_name,
            "invoked": True,
            "status": "NO_EVALUATION",
            "score": None,
            "reason": last_attempt["reason"],
            "is_applicable": True,
            "explicit_vote": None,
            "retries": max_retries,
            "runtime_s": last_attempt["runtime_s"],
            "raw_response": last_attempt["raw_response"],
            "intermediate_output": last_attempt["intermediate_output"],
            "attempts_trace": attempts_trace,
        }

    return eval_record, agent_result


def aggregate_evaluations_optimized(
    evaluations: Dict[str, Dict[str, Any]],
    expected_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Optimized aggregation:
    - Strict denominator: ONLY valid applicable evaluations enter mean_score calculation.
    - Disagreement detection: flags sharp variance between evaluators.
    - Explicit distinction between confidence scoring of A0 and answer-choice voting.
    - Completeness flag.
    """
    if expected_names is None:
        expected_names = EVALUATOR_NAMES_FORMAL_LOGIC

    total_expected = len(expected_names)
    applicable_evals = []
    not_applicable_evals = []
    valid_evals = []
    invalid_evals = []
    applicable_scores = []
    individual_scores = {}
    individual_statuses = {}
    individual_reasons = {}

    for name in expected_names:
        e = evaluations.get(name)
        if not e or not e.get("invoked", False):
            individual_scores[name] = None
            individual_statuses[name] = "NOT_INVOKED"
            individual_reasons[name] = "Evaluator was not executed."
            invalid_evals.append(name)
            continue

        status = e.get("status", "UNKNOWN")
        score = e.get("score")
        reason = e.get("reason", "")

        individual_statuses[name] = status
        individual_reasons[name] = reason

        if status == "NOT_APPLICABLE":
            individual_scores[name] = None
            not_applicable_evals.append(name)
        elif status == "VALID" and score is not None:
            individual_scores[name] = score
            valid_evals.append(name)
            applicable_evals.append(name)
            applicable_scores.append(score)
        else:
            individual_scores[name] = None
            invalid_evals.append(name)
            applicable_evals.append(name)

    applicable_count = len(applicable_evals)
    valid_count = len(valid_evals)
    not_applicable_count = len(not_applicable_evals)
    invalid_count = len(invalid_evals)

    mean_score = (
        round(sum(applicable_scores) / len(applicable_scores), 2)
        if len(applicable_scores) > 0
        else None
    )

    majority_threshold = (applicable_count // 2) + 1 if applicable_count > 0 else 1
    support_count = sum(1 for s in applicable_scores if s >= 6)
    oppose_count = sum(1 for s in applicable_scores if s < 6)

    # Disagreement detection
    score_range = (max(applicable_scores) - min(applicable_scores)) if len(applicable_scores) >= 2 else 0
    disagreement_detected = (support_count > 0 and oppose_count > 0) or (score_range >= 5)

    is_complete = (invalid_count == 0 and applicable_count > 0 and valid_count == applicable_count)

    if not is_complete:
        consensus_type = "INCOMPLETE"
    else:
        if support_count == applicable_count:
            consensus_type = "UNANIMOUS_SUPPORT"
        elif support_count >= majority_threshold:
            consensus_type = "MAJORITY_SUPPORT"
        elif oppose_count >= majority_threshold:
            consensus_type = "MAJORITY_OPPOSE"
        else:
            consensus_type = "DIVIDED"

    supports_initial_answer = (support_count >= majority_threshold) if applicable_count > 0 else False

    return {
        "total_evaluators_expected": total_expected,
        "evaluators_invoked_count": len([e for e in evaluations.values() if e.get("invoked")]),
        "applicable_count": applicable_count,
        "valid_count": valid_count,
        "not_applicable_count": not_applicable_count,
        "invalid_count": invalid_count,
        "individual_scores": individual_scores,
        "individual_statuses": individual_statuses,
        "individual_reasons": individual_reasons,
        "applicable_scores": applicable_scores,
        "mean_score": mean_score,
        "majority_threshold": majority_threshold,
        "support_count": support_count,
        "oppose_count": oppose_count,
        "score_range": score_range,
        "disagreement_detected": disagreement_detected,
        "is_complete": is_complete,
        "consensus_type": consensus_type,
        "supports_initial_answer": supports_initial_answer,
        "applicable_evaluators": applicable_evals,
        "not_applicable_evaluators": not_applicable_evals,
        "invalid_evaluators": invalid_evals,
        "explicit_voting_present": False,
    }


def format_revisor_prompt_optimized(
    problem: Dict[str, Any],
    a0_choice: int,
    a0_reason: str,
    agg: Dict[str, Any],
) -> str:
    """
    Optimized Revisor Prompt:
    - Injects Presumption of A0 Validity.
    - Injects Counterexample Verification Rule (prevents Problem 3 fallacies).
    - Highlights Disagreement Alerts if variance is high.
    - Zero ground-truth leakage.
    """
    choices_str = ", ".join([f"{i}) {c}" for i, c in enumerate(problem.get("choices", []))])

    eval_lines = []
    for name, status in agg["individual_statuses"].items():
        score = agg["individual_scores"].get(name)
        reason = agg["individual_reasons"].get(name, "")
        if status == "VALID":
            status_desc = f"{score}/10 [VALID - Applicable]"
        elif status == "NOT_APPLICABLE":
            status_desc = "NOT APPLICABLE (Excluded from numerical score)"
        else:
            status_desc = f"NO EVALUATION ({status} - Malformed/Missing)"
        eval_lines.append(f"- **{name} Evaluator**: {status_desc}\n  Reason: {reason}")

    eval_block = "\n".join(eval_lines)

    disagreement_warning = ""
    if agg.get("disagreement_detected", False):
        disagreement_warning = (
            "\n⚠️ ALERT: Evaluator Disagreement Detected! Evaluators differ significantly on Choice "
            f"{a0_choice} (Scores: {agg['applicable_scores']}). Do NOT treat numerical consensus as proof. "
            "Scrutinize the logical evidence carefully before deciding to revise."
        )

    completeness_note = (
        "All applicable evaluators produced valid scores."
        if agg["is_complete"]
        else f"Evaluation is INCOMPLETE ({agg['invalid_count']} invalid evaluators: {', '.join(agg['invalid_evaluators'])}). Do NOT assume consensus."
    )

    return (
        f"You are the Answer Revisor. Review the problem, initial answer A0, and all individual evaluations below.\n\n"
        f"### Problem:\n{problem.get('question', '')}\n\n"
        f"### Choices:\n{choices_str}\n\n"
        f"### Proposed Initial Answer (A0):\n"
        f"- Choice: {a0_choice}\n"
        f"- Reason: {a0_reason}\n\n"
        f"### Individual Evaluator Results (5 Dispatched):\n"
        f"{eval_block}\n\n"
        f"### Aggregation Summary (Applicable Evaluations Only):\n"
        f"- Applicable: {agg['applicable_count']} | Not Applicable: {agg['not_applicable_count']} | Invalid/Failed: {agg['invalid_count']}\n"
        f"- Valid Applicable Scores: {agg['valid_count']} -> {agg['applicable_scores']}\n"
        f"- Mean Score of Applicable Evaluators: {agg['mean_score'] if agg['mean_score'] is not None else 'N/A'} / 10\n"
        f"- Consensus Status: {agg['consensus_type']} (Threshold: {agg['majority_threshold']}/{agg['applicable_count']})\n"
        f"- Note: {completeness_note}{disagreement_warning}\n\n"
        f"### Critical Revision Guidelines:\n"
        f"1. Presumption of A0 Validity: A0 was generated by directly solving the problem. Do NOT revise A0 unless an evaluator provides concrete, logically sound proof of error. If evaluations are divided or lack proof, RETAIN A0.\n"
        f"2. Counterexample Fallacy Check: An argument is invalid ONLY IF all premises are TRUE and the conclusion is FALSE. If an evaluator claims a counterexample where the conclusion is explicitly TRUE (e.g. 'Counterexample when conclusion G is True'), that evaluator has made a fundamental fallacy — IGNORE IT and retain A0.\n"
        f"3. N/A Exclusion: Evaluators marked NOT APPLICABLE provide zero evidence for or against A0.\n"
        f"4. Output format: Return strictly in JSON dictionary format: {{\"choice\": <int>, \"Reason\": \"<string>\"}}.\n"
    )


def build_optimized_graph_dispatch_team(
    prompt: Dict[str, Any],
    react_generator: ReactAgent,
    problem: Dict[str, Any],
):
    """
    Constructs an optimized LangGraph StateGraph:
    START -> Answer Generator -> Evaluator Prep -> Truth Table -> Counterexample ->
    Predicate Logic -> Logical Argument -> Formal Logic -> Aggregator -> Revisor -> END.

    Preserves exact LangGraph topology while maximizing reasoning fidelity and eliminating retries.
    """
    workflow = StateGraph(GraphAgentState)

    # 1. Reuse original Answer Generator node
    ans_spec = prompt["team"]["Answer Generator"]
    ans_node = react_generator.loadMember(
        "Answer Generator", ans_spec["tools"], ans_spec["prompt"], "Default Supervisor"
    )

    # 2. Build the 5 evaluator member functions with specialized guidance
    eval_spec_dict = prompt["team"]["Evaluator"]
    eval_member_fns = {}
    for name in EVALUATOR_NAMES_FORMAL_LOGIC:
        spec = eval_spec_dict[name]
        guidance = EVALUATOR_SPECIALIZED_GUIDANCE.get(name, "")
        enhanced_prompt = f"{spec['prompt']}\n\n### Specialized Domain Guidance:\n{guidance}"
        eval_member_fns[name] = react_generator.loadMember(
            name, spec["tools"], enhanced_prompt, "Evaluator Supervisor"
        )

    # 3. Reuse original Revisor node
    rev_spec = prompt["team"]["Revisor"]
    rev_node = react_generator.loadMember(
        "Revisor", rev_spec["tools"], rev_spec["prompt"], "Default Supervisor"
    )

    choice_info = ", ".join([f"{i}) {x}" for i, x in enumerate(problem.get("choices", []))])

    # Node: Answer Generator Runner
    def answer_generator_runner(state: GraphAgentState):
        result = ans_node(dict(state))
        raw_io = result.get("intermediate_output", {})
        parsed_io = parse_intermediate_output(raw_io, None)
        if parsed_io is None and hasattr(result.get("messages"), "content"):
            parsed_io = parse_intermediate_output(result["messages"].content, {})

        a0_choice = parsed_io.get("choice", parsed_io.get("answer", {}).get("choice", 0))
        try:
            a0_choice = int(a0_choice)
        except Exception:
            a0_choice = 0
        a0_reason = parsed_io.get("Reason", parsed_io.get("reason", parsed_io.get("answer", {}).get("Reason", "")))

        a0_dict = {"choice": a0_choice, "Reason": a0_reason}
        imm_a0 = copy.deepcopy(a0_dict)

        return {
            "intermediate_output": a0_dict,
            "_initial_intermediate_output": imm_a0,
            "messages": result.get("messages"),
            "history": result.get("history", state["history"]),
            "background": result.get("background", state["background"]),
            "_evaluator_trace": [],
            "_individual_evaluations": {},
            "_revision_history": [
                {"step": "A0", "choice": a0_choice, "reason": a0_reason, "intermediate_output": imm_a0}
            ],
        }

    # Node: Evaluator Prep
    def evaluator_prep_runner(state: GraphAgentState):
        a0_dict = state["_initial_intermediate_output"]
        a0_choice = a0_dict.get("choice", 0)
        a0_reason = a0_dict.get("Reason", "")

        new_history = dict(state["history"])
        for name in EVALUATOR_NAMES_FORMAL_LOGIC:
            guidance = EVALUATOR_SPECIALIZED_GUIDANCE.get(name, "")
            eval_task = (
                f"Please evaluate the following proposed answer strictly from your perspective as {name} Evaluator:\n"
                f"Question: {problem.get('question', '')}\n"
                f"Choices: {choice_info}\n"
                f"Proposed Answer: Choice {a0_choice} ({a0_reason})\n\n"
                f"### Domain Guidelines:\n{guidance}\n\n"
                f"Output strictly in intermediate_output: "
                f'{{"evaluation": {{"{name}": {{"Correctness Score": <integer 0-10 or "N/A">, "Reason": "<evidence-based reasoning>"}}}}}}'
            )
            new_history[name] = [HumanMessage(content=eval_task, name="Evaluator_Supervisor")]

        return {
            "history": new_history,
            "background": AIMessage(content=f"Question: {problem.get('question', '')}\nChoices: {choice_info}\nProposed Answer: Choice {a0_choice}"),
            "next": "Truth Table",
        }

    # Creator for each evaluator node
    def make_evaluator_node(eval_name: str, next_node: str):
        def evaluator_runner(state: GraphAgentState):
            eval_fn = eval_member_fns[eval_name]

            # Ensure eval_name has its task prompt in history
            hist = dict(state.get("history", {}))
            if eval_name not in hist or not hist[eval_name]:
                a0_val = state["_initial_intermediate_output"]
                guidance = EVALUATOR_SPECIALIZED_GUIDANCE.get(eval_name, "")
                eval_task = (
                    f"Please evaluate the following proposed answer strictly as {eval_name} Evaluator:\n"
                    f"Question: {problem.get('question', '')}\n"
                    f"Choices: {choice_info}\n"
                    f"Proposed Answer: Choice {a0_val.get('choice', 0)} ({a0_val.get('Reason', '')})\n\n"
                    f"### Domain Guidelines:\n{guidance}\n\n"
                    f"Output strictly in intermediate_output: "
                    f'{{"evaluation": {{"{eval_name}": {{"Correctness Score": <integer 0-10 or "N/A">, "Reason": "<evidence-based reasoning>"}}}}}}'
                )
                hist[eval_name] = [HumanMessage(content=eval_task, name="Evaluator_Supervisor")]
            state["history"] = hist

            record, agent_result = run_evaluator_node_optimized(
                eval_fn, state, eval_name, max_retries=2
            )

            updated_trace = list(state.get("_evaluator_trace", [])) + [record]
            updated_evals = dict(state.get("_individual_evaluations", {}))
            updated_evals[eval_name] = record

            # IMMUTABLE PRESERVATION: A0 is NOT overwritten
            preserved_a0 = copy.deepcopy(state["_initial_intermediate_output"])

            # Merge histories so downstream nodes retain prompts
            merged_history = dict(state.get("history", {}))
            for k, v in agent_result.get("history", {}).items():
                merged_history[k] = v

            return {
                "_evaluator_trace": updated_trace,
                "_individual_evaluations": updated_evals,
                "_initial_intermediate_output": preserved_a0,
                "history": merged_history,
                "next": next_node,
            }
        return evaluator_runner

    # Node: Aggregator
    def aggregator_runner(state: GraphAgentState):
        agg = aggregate_evaluations_optimized(
            state.get("_individual_evaluations", {}),
            EVALUATOR_NAMES_FORMAL_LOGIC,
        )

        a0_dict = state["_initial_intermediate_output"]
        a0_choice = a0_dict.get("choice", 0)
        a0_reason = a0_dict.get("Reason", "")

        revisor_prompt_text = format_revisor_prompt_optimized(
            problem, a0_choice, a0_reason, agg
        )

        revisor_io = {
            "answer": a0_dict,
            "evaluation": {
                name: {
                    "Correctness Score": agg["individual_scores"].get(name),
                    "Status": agg["individual_statuses"].get(name),
                    "Reason": agg["individual_reasons"].get(name),
                }
                for name in EVALUATOR_NAMES_FORMAL_LOGIC
            },
            "aggregation": agg,
        }

        new_history = dict(state["history"])
        new_history["Revisor"] = [HumanMessage(content=revisor_prompt_text, name="Default_Supervisor")]

        return {
            "_evaluation_aggregation": agg,
            "intermediate_output": revisor_io,
            "history": new_history,
            "next": "Revisor",
            "background": AIMessage(content=revisor_prompt_text, name="Default Supervisor"),
            "_initial_intermediate_output": copy.deepcopy(a0_dict),
        }

    # Node: Revisor Runner
    def revisor_runner(state: GraphAgentState):
        t0 = time.time()
        result = rev_node(dict(state))
        elapsed = round(time.time() - t0, 2)

        raw_msg = result.get("messages")
        raw_text = raw_msg.content if hasattr(raw_msg, "content") else str(raw_msg)
        io_out = result.get("intermediate_output", {})

        a0_dict = state["_initial_intermediate_output"]
        a0_choice = a0_dict.get("choice", 0)

        parsed = parse_intermediate_output(io_out, None)
        if parsed is None or not isinstance(parsed, dict):
            parsed = parse_intermediate_output(raw_text, None)

        parse_failed = False
        if parsed and isinstance(parsed, dict):
            new_choice = parsed.get("choice")
            if new_choice is None and "answer" in parsed and isinstance(parsed["answer"], dict):
                new_choice = parsed["answer"].get("choice")

            if new_choice is not None and isinstance(new_choice, (int, str)):
                try:
                    final_choice = int(new_choice)
                    new_reason = parsed.get("Reason", parsed.get("reason", parsed.get("answer", {}).get("Reason", "")))
                    decision = "REVISED" if final_choice != a0_choice else "RETAINED"
                except Exception:
                    parse_failed = True
                    final_choice = a0_choice
                    new_reason = f"Could not cast choice {new_choice!r} to int; retained A0."
                    decision = "PARSE_FAILURE_RETAINED_A0"
            else:
                parse_failed = True
                final_choice = a0_choice
                new_reason = "No valid choice key found in Revisor JSON; retained A0."
                decision = "PARSE_FAILURE_RETAINED_A0"
        else:
            parse_failed = True
            final_choice = a0_choice
            new_reason = "Revisor output unparseable; retained previous valid answer A0."
            decision = "PARSE_FAILURE_RETAINED_A0"

        revision_step = {
            "step": "Revisor",
            "choice": final_choice,
            "reason": new_reason,
            "decision": decision,
            "parse_failed": parse_failed,
            "raw_response": raw_text,
            "runtime_s": elapsed,
        }

        updated_history = list(state.get("_revision_history", [])) + [revision_step]

        return {
            "intermediate_output": {"choice": final_choice, "Reason": new_reason},
            "_revision_history": updated_history,
            "_initial_intermediate_output": a0_dict,
            "messages": result.get("messages"),
        }

    # Add all nodes
    workflow.add_node("Answer Generator", answer_generator_runner)
    workflow.add_node("Evaluator Prep", evaluator_prep_runner)
    workflow.add_node("Truth Table", make_evaluator_node("Truth Table", "Counterexample"))
    workflow.add_node("Counterexample", make_evaluator_node("Counterexample", "Predicate Logic"))
    workflow.add_node("Predicate Logic", make_evaluator_node("Predicate Logic", "Logical Argument"))
    workflow.add_node("Logical Argument", make_evaluator_node("Logical Argument", "Formal Logic"))
    workflow.add_node("Formal Logic", make_evaluator_node("Formal Logic", "Aggregator"))
    workflow.add_node("Aggregator", aggregator_runner)
    workflow.add_node("Revisor", revisor_runner)

    # Mandatory sequential edges
    workflow.add_edge(START, "Answer Generator")
    workflow.add_edge("Answer Generator", "Evaluator Prep")
    workflow.add_edge("Evaluator Prep", "Truth Table")
    workflow.add_edge("Truth Table", "Counterexample")
    workflow.add_edge("Counterexample", "Predicate Logic")
    workflow.add_edge("Predicate Logic", "Logical Argument")
    workflow.add_edge("Logical Argument", "Formal Logic")
    workflow.add_edge("Formal Logic", "Aggregator")
    workflow.add_edge("Aggregator", "Revisor")
    workflow.add_edge("Revisor", END)

    compiled_graph = workflow.compile(debug=False)
    return compiled_graph
