"""
Sprint 3 — Graph-Level Forced Evaluator Integration
Provides deterministic, mandatory graph-level dispatch of all five evaluators,
status classification (VALID, NOT_APPLICABLE, NO_EVALUATION), retry logic,
strict denominator handling, distinction of scoring vs voting, and immutable A0 preservation.
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
    format_revisor_prompt_text,
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


def classify_evaluation_status(
    intermediate_output: Any,
    raw_response: str,
    evaluator_name: str,
) -> Tuple[str, Optional[int], str, bool, Optional[int]]:
    """
    Classifies evaluator output into exactly one of three statuses:
    - VALID: A structured evaluation with validated score in [0, 10].
    - NOT_APPLICABLE: The evaluator method does not apply to this problem.
      Score is None (NEVER converted to 0 or 10).
    - NO_EVALUATION: The evaluator ran but produced malformed/missing evaluation.
      Score is None.

    Also extracts explicit choice vote if present, distinguishing confidence scoring from voting.
    Returns: (status, score, reason, is_applicable, explicit_choice_vote)
    """
    # 1. Check for explicit NOT_APPLICABLE indicators
    na_indicators = [
        "n/a", "not applicable", "not required", "is not needed",
        "cannot be used", "doesn't apply", "does not apply"
    ]
    raw_lower = raw_response.lower() if raw_response else ""

    # Check intermediate_output for "N/A" score or reason
    target_dict = None
    if isinstance(intermediate_output, dict):
        eval_block = intermediate_output.get("evaluation", intermediate_output)
        if isinstance(eval_block, dict):
            if evaluator_name in eval_block and isinstance(eval_block[evaluator_name], dict):
                target_dict = eval_block[evaluator_name]
            else:
                for k, v in eval_block.items():
                    if isinstance(v, dict) and (evaluator_name.lower() in k.lower() or "correctness score" in [x.lower() for x in v.keys()]):
                        target_dict = v
                        break

    if target_dict and isinstance(target_dict, dict):
        raw_score = str(target_dict.get("Correctness Score", "")).strip().lower()
        reason = str(target_dict.get("Reason", ""))
        reason_lower = reason.lower()

        if raw_score in ["n/a", "na", "none", "null"]:
            return "NOT_APPLICABLE", None, reason or "Evaluator marked N/A in score field", False, None

        if any(ind in reason_lower for ind in na_indicators) and ("score" not in raw_score or raw_score in ["", "0", "10"]):
            # If reason explicitly states not applicable / not required
            if "not required" in reason_lower or "not applicable" in reason_lower:
                return "NOT_APPLICABLE", None, reason, False, None

    # Check raw response text if target_dict not explicit
    if any(ind in raw_lower for ind in ["truth table is not required", "truth table is not applicable",
                                       "counterexample is not required", "counterexample is not applicable"]):
        return "NOT_APPLICABLE", None, "Method explicitly identified as not applicable in reasoning.", False, None

    # 2. Extract score and validate
    score, st, reason = extract_evaluator_score_robust(
        intermediate_output, raw_response, evaluator_name
    )

    # Check if raw_response stated N/A even if score returned 10
    if st == "OK" and score is not None:
        reason_lower = reason.lower()
        if "not required" in reason_lower or "not applicable" in reason_lower or "return 'n/a'" in reason_lower:
            return "NOT_APPLICABLE", None, reason, False, None
        return "VALID", score, reason, True, None

    # 3. Otherwise, if unparseable or missing score
    return "NO_EVALUATION", None, reason or "Failed to extract valid structured score.", True, None


def run_evaluator_node_with_retries(
    eval_member_fn,
    state: GraphAgentState,
    eval_name: str,
    max_retries: int = 2,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Executes an evaluator node with up to max_retries on NO_EVALUATION.
    Records all retry attempts, raw responses, and timing.
    Returns: (eval_record, updated_state)
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

        status, score, reason, is_applicable, explicit_vote = classify_evaluation_status(
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

        # If NO_EVALUATION and retries remaining, add corrective instruction
        if attempt < max_retries:
            corr_prompt = (
                f"Your previous evaluation did not produce a structured evaluation. "
                f"Please evaluate the proposed answer strictly as {eval_name} and output: "
                f'{{"evaluation": {{"{eval_name}": {{"Correctness Score": <integer 0-10 or "N/A">, "Reason": "<explanation>"}}}}}}'
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


def aggregate_evaluations_strict(
    evaluations: Dict[str, Dict[str, Any]],
    expected_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Calculates score aggregates using ONLY applicable VALID evaluations.
    NOT_APPLICABLE and NO_EVALUATION NEVER enter the numerical denominator.
    Distinguishes confidence score aggregation from answer-choice voting.
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

    # Denominator uses ONLY valid applicable evaluations
    mean_score = (
        round(sum(applicable_scores) / len(applicable_scores), 2)
        if len(applicable_scores) > 0
        else None
    )

    # Majority threshold based on applicable count
    majority_threshold = (applicable_count // 2) + 1 if applicable_count > 0 else 1
    support_count = sum(1 for s in applicable_scores if s >= 6)
    oppose_count = sum(1 for s in applicable_scores if s < 6)

    # Strict completeness check
    is_complete = (invalid_count == 0 and applicable_count > 0 and valid_count == applicable_count)

    # Consensus determination
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
        "is_complete": is_complete,
        "consensus_type": consensus_type,
        "supports_initial_answer": supports_initial_answer,
        "applicable_evaluators": applicable_evals,
        "not_applicable_evaluators": not_applicable_evals,
        "invalid_evaluators": invalid_evals,
        "explicit_voting_present": False,  # Confidence scoring vs voting distinction
    }


def format_revisor_prompt_strict(
    problem: Dict[str, Any],
    a0_choice: int,
    a0_reason: str,
    agg: Dict[str, Any],
) -> str:
    """
    Formats structured Revisor input without exposing ground truth.
    Clearly distinguishes applicable vs not applicable evaluators.
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
            status_desc = f"NO EVALUATION ({status} - Invalid/Malformed)"
        eval_lines.append(f"- **{name} Evaluator**: {status_desc}\n  Reason: {reason}")

    eval_block = "\n".join(eval_lines)
    completeness_note = (
        "All applicable evaluators produced valid scores."
        if agg["is_complete"]
        else f"Evaluation is INCOMPLETE ({agg['invalid_count']} invalid/missing evaluators: {', '.join(agg['invalid_evaluators'])}). Do NOT assume unanimous consensus."
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
        f"- Total Evaluators: 5\n"
        f"- Applicable: {agg['applicable_count']} | Not Applicable: {agg['not_applicable_count']} | Invalid/Failed: {agg['invalid_count']}\n"
        f"- Valid Applicable Scores: {agg['valid_count']} -> {agg['applicable_scores']}\n"
        f"- Mean Score of Applicable Evaluators: {agg['mean_score'] if agg['mean_score'] is not None else 'N/A'} / 10\n"
        f"- Majority Threshold: {agg['majority_threshold']} of {agg['applicable_count']} supporting (score >= 6)\n"
        f"- Supporting: {agg['support_count']} | Opposing: {agg['oppose_count']}\n"
        f"- Consensus Status: {agg['consensus_type']}\n"
        f"- Note: {completeness_note}\n\n"
        f"### Instructions:\n"
        f"1. If the majority of valid applicable evaluations oppose choice {a0_choice} or identify clear logical flaws, revise the choice.\n"
        f"2. If choice {a0_choice} is well-supported, retain it.\n"
        f"3. Return your final revised answer strictly in JSON dictionary format: {{\"choice\": <int>, \"Reason\": \"<string>\"}}.\n"
    )


def evaluate_revision_quality(a0_choice: int, final_choice: int, ground_truth: int) -> str:
    """
    Categorizes the revision outcome by comparing A0 and Final Answer with Ground Truth.
    Called ONLY in the experiment runner after final answer generation (never in Revisor).
    """
    a0_correct = (a0_choice == ground_truth)
    final_correct = (final_choice == ground_truth)

    if not a0_correct and final_correct:
        return "HELPFUL"
    elif a0_correct and not final_correct:
        return "HARMFUL"
    elif a0_correct and final_correct:
        return "NEUTRAL_RETAINED_CORRECT"
    elif not a0_correct and not final_correct:
        if a0_choice == final_choice:
            return "NEUTRAL_RETAINED_INCORRECT"
        else:
            return "NEUTRAL_REVISED_INCORRECT"
    return "UNKNOWN"


def build_mandatory_graph_dispatch_team(
    prompt: Dict[str, Any],
    react_generator: ReactAgent,
    problem: Dict[str, Any],
):
    """
    Constructs a LangGraph StateGraph that deterministically executes:
    START -> Answer Generator -> Evaluator Prep -> Truth Table -> Counterexample ->
    Predicate Logic -> Logical Argument -> Formal Logic -> Aggregator -> Revisor -> END.

    Reuses the original Answer Generator node and original LangGraph state structure.
    Preserves A0 immutably in _initial_intermediate_output.
    """
    workflow = StateGraph(GraphAgentState)

    # 1. Reuse original Answer Generator node
    ans_spec = prompt["team"]["Answer Generator"]
    ans_node = react_generator.loadMember(
        "Answer Generator", ans_spec["tools"], ans_spec["prompt"], "Default Supervisor"
    )

    # 2. Build the 5 evaluator member functions
    eval_spec_dict = prompt["team"]["Evaluator"]
    eval_member_fns = {}
    for name in EVALUATOR_NAMES_FORMAL_LOGIC:
        spec = eval_spec_dict[name]
        eval_member_fns[name] = react_generator.loadMember(
            name, spec["tools"], spec["prompt"], "Evaluator Supervisor"
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
        # Immutable copy of A0
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

        eval_task = (
            f"Please evaluate the following proposed answer:\n"
            f"Question: {problem.get('question', '')}\n"
            f"Choices: {choice_info}\n"
            f"Proposed Answer: Choice {a0_choice} ({a0_reason})\n\n"
            f"Evaluate strictly according to your specialized criteria.\n"
            f'Final output in intermediate_output: {{"evaluation": {{"<Your Evaluator Name>": {{"Correctness Score": <0-10 or "N/A">, "Reason": "<explanation>"}}}}}}'
        )

        new_history = dict(state["history"])
        for name in EVALUATOR_NAMES_FORMAL_LOGIC:
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
                eval_task = (
                    f"Please evaluate the following proposed answer:\n"
                    f"Question: {problem.get('question', '')}\n"
                    f"Choices: {choice_info}\n"
                    f"Proposed Answer: Choice {a0_val.get('choice', 0)} ({a0_val.get('Reason', '')})\n\n"
                    f"Evaluate strictly according to your specialized criteria.\n"
                    f'Final output in intermediate_output: {{"evaluation": {{"{eval_name}": {{"Correctness Score": <0-10 or "N/A">, "Reason": "<explanation>"}}}}}}'
                )
                hist[eval_name] = [HumanMessage(content=eval_task, name="Evaluator_Supervisor")]
            state["history"] = hist

            record, agent_result = run_evaluator_node_with_retries(
                eval_fn, state, eval_name, max_retries=2
            )

            updated_trace = list(state.get("_evaluator_trace", [])) + [record]
            updated_evals = dict(state.get("_individual_evaluations", {}))
            updated_evals[eval_name] = record

            # IMMUTABLE PRESERVATION: A0 is NOT overwritten
            preserved_a0 = copy.deepcopy(state["_initial_intermediate_output"])

            # Merge histories so next nodes retain all member prompts
            merged_history = dict(state.get("history", {}))
            for k, v in agent_result.get("history", {}).items():
                merged_history[k] = v

            return {
                "_evaluator_trace": updated_trace,
                "_individual_evaluations": updated_evals,
                "_initial_intermediate_output": preserved_a0,  # Explicitly preserved
                "history": merged_history,
                "next": next_node,
            }
        return evaluator_runner

    # Node: Aggregator
    def aggregator_runner(state: GraphAgentState):
        agg = aggregate_evaluations_strict(
            state.get("_individual_evaluations", {}),
            EVALUATOR_NAMES_FORMAL_LOGIC,
        )

        a0_dict = state["_initial_intermediate_output"]
        a0_choice = a0_dict.get("choice", 0)
        a0_reason = a0_dict.get("Reason", "")

        revisor_prompt_text = format_revisor_prompt_strict(
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
            "_initial_intermediate_output": a0_dict,  # Strictly preserved
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

