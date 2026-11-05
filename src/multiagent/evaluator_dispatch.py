"""
Controlled Evaluator Dispatch Module for TalkHier BTP - Sprint 2 / Experiment D.
Provides deterministic, explicit invocation of all five evaluators,
transparent evaluation aggregation, structured Revisor input, and robust error handling.
"""

import time
import json
import ast
from typing import Dict, Any, List, Optional, Tuple
from langchain_core.messages import HumanMessage, AIMessage

from multiagent.agent_team import (
    ReactAgent,
    extract_evaluator_score,
    parse_intermediate_output,
)
from multiagent.llm import LLM
import prompts.mmlu as MMLUPrompt

EVALUATOR_NAMES_FORMAL_LOGIC = [
    "Truth Table",
    "Counterexample",
    "Predicate Logic",
    "Logical Argument",
    "Formal Logic",
]


def extract_evaluator_score_robust(
    intermediate_output: Any,
    message_content: Optional[str] = None,
    evaluator_name: Optional[str] = None,
) -> Tuple[Optional[int], str, str]:
    """
    Robust score extraction that checks both intermediate_output and raw message text.
    NEVER defaults a malformed or missing score to 10.
    """
    score, status, reason = extract_evaluator_score(intermediate_output, evaluator_name)
    if status == "OK" and score is not None:
        return score, status, reason

    # If not found in structured intermediate_output, check if raw message contains JSON
    if message_content and status in ("NO_EVALUATION", "INVALID_STRUCTURE", "EVALUATOR_NOT_FOUND"):
        parsed_msg = parse_intermediate_output(message_content, None)
        if isinstance(parsed_msg, dict):
            s2, st2, r2 = extract_evaluator_score(parsed_msg, evaluator_name)
            if st2 == "OK" and s2 is not None:
                return s2, st2, r2

    return score, status, reason


class AggregatedEvaluation:
    def __init__(
        self,
        evaluators_invoked: int,
        valid_scores_count: int,
        individual_scores: Dict[str, Optional[int]],
        individual_statuses: Dict[str, str],
        individual_reasons: Dict[str, str],
        mean_score: Optional[float],
        is_complete: bool,
        support_count: int,
        oppose_count: int,
        majority_threshold: int,
        supports_initial_answer: bool,
        consensus_type: str,
        missing_or_invalid: List[str],
        individual_details: List[Dict[str, Any]],
    ):
        self.evaluators_invoked = evaluators_invoked
        self.valid_scores_count = valid_scores_count
        self.individual_scores = individual_scores
        self.individual_statuses = individual_statuses
        self.individual_reasons = individual_reasons
        self.mean_score = mean_score
        self.is_complete = is_complete
        self.support_count = support_count
        self.oppose_count = oppose_count
        self.majority_threshold = majority_threshold
        self.supports_initial_answer = supports_initial_answer
        self.consensus_type = consensus_type
        self.missing_or_invalid = missing_or_invalid
        self.individual_details = individual_details

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evaluators_invoked": self.evaluators_invoked,
            "valid_scores_count": self.valid_scores_count,
            "individual_scores": self.individual_scores,
            "individual_statuses": self.individual_statuses,
            "mean_score": self.mean_score,
            "is_complete": self.is_complete,
            "support_count": self.support_count,
            "oppose_count": self.oppose_count,
            "majority_threshold": self.majority_threshold,
            "supports_initial_answer": self.supports_initial_answer,
            "consensus_type": self.consensus_type,
            "missing_or_invalid": self.missing_or_invalid,
        }


class EvaluationAggregator:
    @staticmethod
    def aggregate(
        evaluations: List[Dict[str, Any]],
        expected_evaluators: Optional[List[str]] = None,
        support_score_threshold: int = 6,
    ) -> AggregatedEvaluation:
        """
        Transparently aggregates evaluator outputs.
        Enforces:
        - Incomplete evaluations CANNOT be treated as unanimous.
        - Missing/malformed scores never default to 10.
        - Documents majority status based on dynamic threshold (N//2 + 1).
        """
        if expected_evaluators is None:
            expected_evaluators = EVALUATOR_NAMES_FORMAL_LOGIC

        total_expected = len(expected_evaluators)
        majority_threshold = (total_expected // 2) + 1

        eval_by_name = {e.get("name"): e for e in evaluations if isinstance(e, dict)}

        evaluators_invoked = 0
        valid_scores_count = 0
        individual_scores: Dict[str, Optional[int]] = {}
        individual_statuses: Dict[str, str] = {}
        individual_reasons: Dict[str, str] = {}
        missing_or_invalid: List[str] = []
        valid_scores: List[int] = []

        for name in expected_evaluators:
            e = eval_by_name.get(name)
            if not e or not e.get("invoked", False):
                individual_scores[name] = None
                individual_statuses[name] = "NOT_INVOKED"
                individual_reasons[name] = "Evaluator was not executed."
                missing_or_invalid.append(name)
                continue

            evaluators_invoked += 1
            score = e.get("score")
            status = e.get("status", "UNKNOWN")
            reason = e.get("reason", "")
            is_valid = e.get("is_valid", False) and score is not None

            individual_scores[name] = score if is_valid else None
            individual_statuses[name] = status
            individual_reasons[name] = reason

            if is_valid:
                valid_scores_count += 1
                valid_scores.append(score)
            else:
                missing_or_invalid.append(name)

        is_complete = (evaluators_invoked == total_expected and valid_scores_count == total_expected)
        mean_score = round(sum(valid_scores) / len(valid_scores), 2) if valid_scores else None

        support_count = sum(1 for s in valid_scores if s >= support_score_threshold)
        oppose_count = sum(1 for s in valid_scores if s < support_score_threshold)

        supports_initial_answer = (support_count >= majority_threshold)

        if not is_complete:
            consensus_type = "INCOMPLETE"
        else:
            if support_count == total_expected:
                consensus_type = "UNANIMOUS_SUPPORT"
            elif support_count >= majority_threshold:
                consensus_type = "MAJORITY_SUPPORT"
            elif oppose_count >= majority_threshold:
                consensus_type = "MAJORITY_OPPOSE"
            else:
                consensus_type = "DIVIDED"

        return AggregatedEvaluation(
            evaluators_invoked=evaluators_invoked,
            valid_scores_count=valid_scores_count,
            individual_scores=individual_scores,
            individual_statuses=individual_statuses,
            individual_reasons=individual_reasons,
            mean_score=mean_score,
            is_complete=is_complete,
            support_count=support_count,
            oppose_count=oppose_count,
            majority_threshold=majority_threshold,
            supports_initial_answer=supports_initial_answer,
            consensus_type=consensus_type,
            missing_or_invalid=missing_or_invalid,
            individual_details=evaluations,
        )


def format_revisor_prompt_text(
    problem: Dict[str, Any],
    a0_choice: int,
    a0_reason: str,
    aggregated_eval: AggregatedEvaluation,
) -> str:
    """
    Constructs structured, unambiguous evaluation feedback for the Revisor.
    Clearly marks invalid/missing evaluators so the Revisor does not assume unanimous agreement.
    """
    choices_str = ", ".join([f"{i}) {c}" for i, c in enumerate(problem.get("choices", []))])

    eval_lines = []
    for name, score in aggregated_eval.individual_scores.items():
        status = aggregated_eval.individual_statuses.get(name, "UNKNOWN")
        reason = aggregated_eval.individual_reasons.get(name, "")
        if score is not None:
            score_str = f"{score}/10 [VALID]"
        else:
            score_str = f"INVALID ({status})"
        eval_lines.append(f"- **{name} Evaluator**: {score_str}\n  Reason: {reason}")

    eval_block = "\n".join(eval_lines)

    completeness_note = (
        "ALL 5 evaluators produced valid scores."
        if aggregated_eval.is_complete
        else f"WARNING: Evaluation is INCOMPLETE ({len(aggregated_eval.missing_or_invalid)} evaluator(s) missing or invalid: {', '.join(aggregated_eval.missing_or_invalid)}). Do NOT assume unanimous consensus."
    )

    prompt_text = (
        f"You are the Answer Revisor. Review the problem, initial answer A0, and all individual evaluations below.\n\n"
        f"### Problem:\n{problem.get('question', '')}\n\n"
        f"### Choices:\n{choices_str}\n\n"
        f"### Proposed Initial Answer (A0):\n"
        f"- Choice: {a0_choice}\n"
        f"- Reason: {a0_reason}\n\n"
        f"### Individual Evaluator Results (5 Evaluators Dispatched):\n"
        f"{eval_block}\n\n"
        f"### Evaluation Aggregation Summary:\n"
        f"- Total Evaluators Invoked: {aggregated_eval.evaluators_invoked}/5\n"
        f"- Valid Scores: {aggregated_eval.valid_scores_count}/5\n"
        f"- Mean Valid Score: {aggregated_eval.mean_score if aggregated_eval.mean_score is not None else 'N/A'}\n"
        f"- Majority Threshold: {aggregated_eval.majority_threshold} of 5 supporting (score >= 6)\n"
        f"- Supporting Evaluators: {aggregated_eval.support_count}\n"
        f"- Opposing Evaluators: {aggregated_eval.oppose_count}\n"
        f"- Consensus Status: {aggregated_eval.consensus_type}\n"
        f"- Notes: {completeness_note}\n\n"
        f"### Instructions:\n"
        f"1. If the majority of valid evaluations oppose choice {a0_choice} or identify clear logical errors, revise the choice.\n"
        f"2. If choice {a0_choice} is well-supported, retain it.\n"
        f"3. Return your final revised answer strictly in JSON dictionary format: {{\"choice\": <int>, \"Reason\": \"<string>\"}}.\n"
    )
    return prompt_text


class ControlledEvaluatorDispatcher:
    def __init__(self, config: Dict[str, Any], react_generator: Optional[ReactAgent] = None):
        self.config = config
        self.react_generator = react_generator or ReactAgent(
            config=config, llm=LLM(config).llm
        )

    def dispatch_all(
        self,
        problem: Dict[str, Any],
        a0_choice: int,
        a0_reason: str,
        prompts: Dict[str, Any],
        expected_evaluators: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Explicitly executes all five evaluators sequentially.
        Captures raw responses, extracted scores, tool calls, and runtimes.
        Never defaults missing scores to 10.
        """
        if expected_evaluators is None:
            expected_evaluators = EVALUATOR_NAMES_FORMAL_LOGIC

        eval_team_info = prompts["team"]["Evaluator"]
        results = []

        choice_info = ", ".join(
            [f"{i}) {x}" for i, x in enumerate(problem["choices"])]
        )

        for eval_name in expected_evaluators:
            t0 = time.time()
            if eval_name not in eval_team_info:
                results.append({
                    "name": eval_name,
                    "invoked": False,
                    "score": None,
                    "status": "NOT_CONFIGURED",
                    "reason": f"Evaluator {eval_name} not found in prompts config.",
                    "is_valid": False,
                    "raw_response": "",
                    "intermediate_output": {},
                    "runtime_s": 0.0,
                })
                continue

            eval_spec = eval_team_info[eval_name]
            tools = eval_spec.get("tools", [4])
            prompt_str = eval_spec.get("prompt", "")

            try:
                member_fn = self.react_generator.loadMember(
                    eval_name, tools, prompt_str, "Evaluator Supervisor"
                )

                task_content = (
                    f"Please evaluate the following proposed answer:\n"
                    f"Question: {problem['question']}\n"
                    f"Choices: {choice_info}\n"
                    f"Proposed Answer: Choice {a0_choice} ({a0_reason})\n\n"
                    f"Evaluate strictly according to your specialized criteria as {eval_name} Evaluator.\n"
                    f"Output your assessment and include in intermediate_output: "
                    f'{{"answer": {{"choice": {a0_choice}, "Reason": "{a0_reason}"}}, "evaluation": {{"{eval_name}": {{"Correctness Score": <score_0_to_10>, "Reason": "<reason>"}}}}}}'
                )

                state = {
                    "history": {
                        eval_name: [HumanMessage(content=task_content, name="Evaluator_Supervisor")],
                        "Evaluator Supervisor": [HumanMessage(content=task_content, name="Evaluator_Supervisor")],
                        "all": [HumanMessage(content=task_content, name="Evaluator_Supervisor")],
                    },
                    "initial_prompt": prompt_str,
                    "background": AIMessage(
                        content=f"Question: {problem['question']}\nChoices: {choice_info}\nProposed Answer: Choice {a0_choice}",
                        name="Evaluator Supervisor",
                    ),
                    "intermediate_output": {"choice": a0_choice, "Reason": a0_reason},
                    "next": eval_name,
                    "messages": [],
                }

                agent_result = member_fn(state)
                elapsed = time.time() - t0

                raw_msg = agent_result.get("messages")
                raw_response = raw_msg.content if hasattr(raw_msg, "content") else str(raw_msg)
                io_out = agent_result.get("intermediate_output", {})

                score, status, reason = extract_evaluator_score_robust(
                    io_out, raw_response, eval_name
                )
                is_valid = (status == "OK" and score is not None and (0 <= score <= 10))

                results.append({
                    "name": eval_name,
                    "invoked": True,
                    "score": score if is_valid else None,
                    "status": status,
                    "reason": reason,
                    "is_valid": is_valid,
                    "raw_response": raw_response,
                    "intermediate_output": io_out,
                    "runtime_s": round(elapsed, 2),
                })
            except Exception as e:
                elapsed = time.time() - t0
                results.append({
                    "name": eval_name,
                    "invoked": False,
                    "score": None,
                    "status": "EXECUTION_EXCEPTION",
                    "reason": f"Exception during execution: {type(e).__name__}: {e}",
                    "is_valid": False,
                    "raw_response": "",
                    "intermediate_output": {},
                    "runtime_s": round(elapsed, 2),
                })

        return results


class RevisorHandler:
    def __init__(self, react_generator: ReactAgent):
        self.react_generator = react_generator

    def revise(
        self,
        problem: Dict[str, Any],
        a0_choice: int,
        a0_reason: str,
        a0_io: Dict[str, Any],
        aggregated_eval: AggregatedEvaluation,
        prompts: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Executes the Revisor agent with validated structured evaluator feedback.
        If revision output cannot be parsed, records failure and retains previous valid answer (A0).
        Preserves complete revision history.
        """
        t0 = time.time()
        revisor_spec = prompts["team"]["Revisor"]
        revisor_tools = revisor_spec.get("tools", [4])
        revisor_prompt = revisor_spec.get("prompt", "")

        revisor_member_fn = self.react_generator.loadMember(
            "Revisor", revisor_tools, revisor_prompt, "Default Supervisor"
        )

        formatted_input = format_revisor_prompt_text(
            problem, a0_choice, a0_reason, aggregated_eval
        )

        revisor_state_io = {
            "answer": {"choice": a0_choice, "Reason": a0_reason},
            "evaluation": {
                name: {
                    "Correctness Score": score if score is not None else "INVALID",
                    "Status": aggregated_eval.individual_statuses.get(name, "UNKNOWN"),
                    "Reason": aggregated_eval.individual_reasons.get(name, ""),
                }
                for name, score in aggregated_eval.individual_scores.items()
            },
            "aggregation": aggregated_eval.to_dict(),
        }

        state = {
            "history": {
                "Revisor": [HumanMessage(content=formatted_input, name="Default_Supervisor")],
                "Default Supervisor": [HumanMessage(content=formatted_input, name="Default_Supervisor")],
                "all": [HumanMessage(content=formatted_input, name="Default_Supervisor")],
            },
            "initial_prompt": revisor_prompt,
            "background": AIMessage(content=formatted_input, name="Default Supervisor"),
            "intermediate_output": revisor_state_io,
            "next": "Revisor",
            "messages": [],
        }

        parse_failed = False
        raw_output_text = ""
        try:
            revisor_result = revisor_member_fn(state)
            raw_msg = revisor_result.get("messages")
            raw_output_text = raw_msg.content if hasattr(raw_msg, "content") else str(raw_msg)
            io_out = revisor_result.get("intermediate_output", {})

            parsed = parse_intermediate_output(io_out, None)
            if parsed is None or not isinstance(parsed, dict):
                parsed = parse_intermediate_output(raw_output_text, None)

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
                new_reason = "Revisor output was unparseable; retained previous valid answer A0."
                decision = "PARSE_FAILURE_RETAINED_A0"
        except Exception as e:
            parse_failed = True
            final_choice = a0_choice
            new_reason = f"Revisor crashed with {type(e).__name__}: {e}; retained A0."
            decision = "PARSE_FAILURE_RETAINED_A0"

        elapsed = time.time() - t0

        revision_history = [
            {
                "step": "A0",
                "choice": a0_choice,
                "reason": a0_reason,
                "intermediate_output": a0_io,
            },
            {
                "step": "Revisor",
                "choice": final_choice,
                "reason": new_reason,
                "decision": decision,
                "parse_failed": parse_failed,
                "raw_response": raw_output_text,
                "runtime_s": round(elapsed, 2),
            },
        ]

        return {
            "final_choice": final_choice,
            "revisor_decision": decision,
            "revisor_reason": new_reason,
            "parse_failed": parse_failed,
            "raw_revisor_response": raw_output_text,
            "revision_history": revision_history,
            "revisor_runtime_s": round(elapsed, 2),
        }


def run_controlled_evaluator_pipeline(
    problem: Dict[str, Any],
    config: Dict[str, Any],
    domain: str = "formal_logic",
    prompts: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Complete end-to-end controlled evaluator dispatch pipeline (Condition B).
    1. Answer Generator produces initial answer A0.
    2. All 5 evaluators are explicitly invoked.
    3. Evaluator outputs are validated and aggregated transparently.
    4. Revisor is invoked with structured feedback.
    5. Returns full results and complete traces.
    """
    total_t0 = time.time()
    if prompts is None:
        prompts = MMLUPrompt.getPrompts(domain, problem)

    react_generator = ReactAgent(config=config, llm=LLM(config).llm)

    # 1. Answer Generator
    choice_info = ", ".join([f"{i}) {x}" for i, x in enumerate(problem["choices"])])
    ans_spec = prompts["team"]["Answer Generator"]
    ans_node = react_generator.loadMember("Answer Generator", ans_spec["tools"], ans_spec["prompt"], "Default Supervisor")

    ans_prompt_text = (
        f"You are an expert in {domain}. Find the answer to the following question:\n"
        f"{problem['question']}\n\nChoices:\n{choice_info}\n\n"
        f"Return output strictly in dictionary format: {{\"choice\": <int 0~{len(problem['choices'])-1}>, \"Reason\": \"<string>\"}}"
    )

    ans_state = {
        "history": {
            "Answer Generator": [HumanMessage(content=ans_prompt_text, name="Default_Supervisor")],
            "Default Supervisor": [HumanMessage(content=ans_prompt_text, name="Default_Supervisor")],
            "all": [HumanMessage(content=ans_prompt_text, name="Default_Supervisor")],
        },
        "initial_prompt": ans_spec["prompt"],
        "background": AIMessage(content=problem["question"], name="Default Supervisor"),
        "intermediate_output": {},
        "next": "Answer Generator",
        "messages": [],
    }

    t_ans0 = time.time()
    ans_result = ans_node(ans_state)
    ans_runtime = round(time.time() - t_ans0, 2)

    raw_ans_msg = ans_result.get("messages")
    raw_ans_text = raw_ans_msg.content if hasattr(raw_ans_msg, "content") else str(raw_ans_msg)
    ans_io = ans_result.get("intermediate_output", {})

    parsed_a0 = parse_intermediate_output(ans_io, None)
    if parsed_a0 is None:
        parsed_a0 = parse_intermediate_output(raw_ans_text, {})

    a0_choice = parsed_a0.get("choice", parsed_a0.get("answer", {}).get("choice", 0))
    try:
        a0_choice = int(a0_choice)
    except Exception:
        a0_choice = 0
    a0_reason = parsed_a0.get("Reason", parsed_a0.get("reason", parsed_a0.get("answer", {}).get("Reason", "")))

    # 2. Controlled Evaluator Dispatch
    dispatcher = ControlledEvaluatorDispatcher(config, react_generator)
    evaluator_results = dispatcher.dispatch_all(
        problem=problem,
        a0_choice=a0_choice,
        a0_reason=a0_reason,
        prompts=prompts,
        expected_evaluators=EVALUATOR_NAMES_FORMAL_LOGIC,
    )

    # 3. Transparent Aggregation
    aggregated_eval = EvaluationAggregator.aggregate(
        evaluations=evaluator_results,
        expected_evaluators=EVALUATOR_NAMES_FORMAL_LOGIC,
    )

    # 4. Revisor Execution
    revisor_handler = RevisorHandler(react_generator)
    revisor_outcome = revisor_handler.revise(
        problem=problem,
        a0_choice=a0_choice,
        a0_reason=a0_reason,
        a0_io=parsed_a0,
        aggregated_eval=aggregated_eval,
        prompts=prompts,
    )

    total_runtime = round(time.time() - total_t0, 2)
    final_choice = revisor_outcome["final_choice"]
    ground_truth = problem["answer"]

    return {
        "problem_id": problem.get("id", None),
        "ground_truth": ground_truth,
        "a0_choice": a0_choice,
        "a0_reason": a0_reason,
        "final_choice": final_choice,
        "a0_correct": (a0_choice == ground_truth),
        "final_correct": (final_choice == ground_truth),
        "answer_changed": (final_choice != a0_choice),
        "all_five_evaluators_invoked": (aggregated_eval.evaluators_invoked == 5),
        "evaluators_invoked_count": aggregated_eval.evaluators_invoked,
        "valid_scores_count": aggregated_eval.valid_scores_count,
        "individual_scores": aggregated_eval.individual_scores,
        "individual_statuses": aggregated_eval.individual_statuses,
        "mean_score": aggregated_eval.mean_score,
        "is_complete": aggregated_eval.is_complete,
        "consensus_type": aggregated_eval.consensus_type,
        "supports_initial_answer": aggregated_eval.supports_initial_answer,
        "missing_or_invalid": aggregated_eval.missing_or_invalid,
        "revisor_decision": revisor_outcome["revisor_decision"],
        "parse_failed": revisor_outcome["parse_failed"],
        "revision_history": revisor_outcome["revision_history"],
        "runtime_s": total_runtime,
        "answer_gen_runtime_s": ans_runtime,
        "revisor_runtime_s": revisor_outcome["revisor_runtime_s"],
        "raw_evaluator_traces": evaluator_results,
        "raw_answer_gen_response": raw_ans_text,
        "raw_revisor_response": revisor_outcome["raw_revisor_response"],
    }

