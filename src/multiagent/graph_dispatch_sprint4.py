"""
Sprint 4.2: Deterministic Evidence-Guided Multi-Agent Graph Dispatch

Extends Sprint 3 Optimized with graph-level deterministic propositional logic verification:
1. Deterministic Verifier Node:
   - Runs immediately after Evaluator Prep.
   - Pre-validates formula extraction and choice candidate mapping.
   - Invokes SymPy SAT verification via `verify_argument_validity()` and `verify_counterexample_candidate()`.
   - Unsupported or ambiguous problems safely default to NOT_APPLICABLE or PARSE_FAILURE.
2. Evidence Injection:
   - Truth Table & Counterexample evaluators receive precomputed mathematical proofs.
   - Aggregator summarizes both LLM evaluations and deterministic evidence.
   - Revisor enforces Deterministic Override when mathematical proof is established.
3. Fallback Integrity:
   - First-order predicate logic and natural-language problems remain on the proven Sprint 3 LLM path.
   - Zero ground-truth leakage.
   - Preserves A0 when evidence is unavailable or inconclusive.
"""

import time
import copy
import json
import re
from typing import Dict, Any, List, Optional, Tuple, Sequence
from typing_extensions import TypedDict, Annotated
import operator

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, START, END

from multiagent.agent_team import (
    ReactAgent,
    parse_intermediate_output,
)
from multiagent.evaluator_dispatch import (
    EVALUATOR_NAMES_FORMAL_LOGIC,
)
from multiagent.graph_dispatch import evaluate_revision_quality
from multiagent.graph_dispatch_opt import (
    EVALUATOR_SPECIALIZED_GUIDANCE,
    classify_evaluation_status_opt,
    run_evaluator_node_optimized,
    aggregate_evaluations_optimized,
)
from multiagent.logic_verifier import (
    parse_to_sympy,
    _is_unsupported,
    verify_argument_validity,
    verify_counterexample_candidate,
)


class GraphAgentStateSprint4(TypedDict):
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
    _deterministic_evidence: Dict[str, Any]
    _revision_history: List[Dict[str, Any]]


# =============================================================================
# Extraction & Candidate Assignment Mapping
# =============================================================================

def extract_propositional_argument(question_text: str) -> Tuple[Optional[List[str]], Optional[str], str, str]:
    """
    Extracts premises and conclusion from an MMLU argument question.
    Standard MMLU format uses slash separator:
      [Premises...]
      [Premise_n] / [Conclusion]

    Returns: (premises, conclusion, status, reason)
    - status is 'OK', 'NOT_APPLICABLE', or 'PARSE_FAILURE'.
    """
    if not question_text or not isinstance(question_text, str):
        return None, None, "NOT_APPLICABLE", "Question text is empty or invalid."

    lines = [line.strip() for line in question_text.split("\n") if line.strip()]

    # Look for slash notation: e.g. '~H / G' or '/ G'
    slash_lines = [i for i, line in enumerate(lines) if "/" in line]
    if not slash_lines:
        return None, None, "NOT_APPLICABLE", "No propositional argument structure (slash separator) found."

    slash_idx = slash_lines[0]
    slash_line = lines[slash_idx]

    parts = slash_line.split("/")
    if len(parts) != 2:
        return None, None, "PARSE_FAILURE", f"Malformed slash line: {slash_line!r}"

    left_part = parts[0].strip()
    conclusion = parts[1].strip()

    if not conclusion:
        return None, None, "PARSE_FAILURE", "Conclusion after slash is empty."

    premises = []
    # Lines before slash_line are premises
    for i in range(slash_idx):
        line = lines[i]
        # Ignore instructional headers
        if any(w in line.lower() for w in [
            "construct", "determine", "truth table", "argument", "following", "consider", "using", "select", "translate", "indirect"
        ]):
            continue
        if line:
            # Clean symbols: middle dot to bullet, brackets to parens
            clean_p = line.replace("·", "•").replace("[", "(").replace("]", ")")
            premises.append(clean_p)

    if left_part:
        clean_lp = left_part.replace("·", "•").replace("[", "(").replace("]", ")")
        premises.append(clean_lp)

    clean_concl = conclusion.replace("·", "•").replace("[", "(").replace("]", ")")

    if not premises:
        return None, None, "PARSE_FAILURE", "No premises found before conclusion."

    # Pre-validation: ensure premises and conclusion are not natural language or predicate relations
    for p in premises:
        if _is_unsupported(p):
            return None, None, "NOT_APPLICABLE", f"Premise {p!r} involves non-propositional logic or natural language."

    if _is_unsupported(clean_concl):
        return None, None, "NOT_APPLICABLE", f"Conclusion {clean_concl!r} involves non-propositional logic or natural language."

    # Validate that formulas can be parsed by SymPy engine
    try:
        for p in premises:
            parse_to_sympy(p)
        parse_to_sympy(clean_concl)
    except Exception as e:
        return None, None, "PARSE_FAILURE", f"Formula parse validation failed: {e}"

    return premises, clean_concl, "OK", "Successfully extracted and validated propositional argument."


def extract_choice_candidate_assignment(choice_text: str) -> Tuple[Optional[Dict[str, bool]], bool, str]:
    """
    Parses a multiple-choice option to extract candidate truth assignment and validity claim.

    Handles natural English phrasing in formal logic benchmarks (e.g. MMLU), such as:
    - 'Valid'
    - 'Invalid. Counterexample when G and H are true'
    - 'Invalid. Counterexample when H and I are true and J is false'
    - 'Invalid. Counterexample when P, R, and Q are true'
    - 'Invalid. Counterexample when L, M, O, Q, and R are true and N and P are false'
    - 'Invalid: G = true, H = false'

    Returns: (assignment, is_valid_claim, choice_type)
    - choice_type: 'VALID', 'INVALID_COUNTEREXAMPLE', 'INVALID_UNSPECIFIED', 'OTHER'
    """
    text = choice_text.strip()
    if re.match(r"^valid\b", text, re.I):
        return None, True, "VALID"

    if not re.search(r"\binvalid\b", text, re.I):
        return None, False, "OTHER"

    assign: Dict[str, bool] = {}

    # Split text after 'when' or ':' if present
    after_when = re.split(r"\bwhen\b|:", text, flags=re.I)
    body = after_when[-1] if len(after_when) > 1 else text

    # Extract clauses: e.g. "H and I are true", "J is false", "G = True, H = False"
    clauses = re.findall(
        r"([^,]+?(?:,\s*[^,]+?)*?)\s+(?:is|are|=|==)\s*(true|false|t|f)",
        body,
        flags=re.I,
    )

    if clauses:
        for var_part, val_str in clauses:
            val = val_str.lower() in ("true", "t")
            # Extract variables (single letters, e.g. A, B, C, ... Z)
            vars_found = re.findall(r"\b[A-Za-z]\b", var_part)
            for v in vars_found:
                assign[v.upper()] = val

        if assign:
            return assign, False, "INVALID_COUNTEREXAMPLE"

    return None, False, "INVALID_UNSPECIFIED"


def run_deterministic_verification(problem: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes authoritative SymPy-based deterministic verification on the problem.
    Operates strictly on question text and choices (Zero ground-truth exposure).
    """
    q_text = problem.get("question", "")
    choices = problem.get("choices", [])

    prems, concl, status, reason = extract_propositional_argument(q_text)

    det_record: Dict[str, Any] = {
        "status": status,
        "is_valid": None,
        "premises": prems,
        "conclusion": concl,
        "reason": reason,
        "counterexample": None,
        "proven_choice_index": None,
        "choice_verifications": {},
        "has_authoritative_proof": False,
    }

    if status != "OK" or not prems or not concl:
        return det_record

    # Run argument validity check
    val_res = verify_argument_validity(prems, concl)
    det_record["status"] = val_res["status"]
    det_record["is_valid"] = val_res["is_valid"]
    det_record["counterexample"] = val_res["counterexample"]
    det_record["reason"] = val_res["reason"]

    # Verify each choice
    choice_verifications = {}
    proven_choice = None

    for i, c in enumerate(choices):
        assign, is_valid_claim, c_type = extract_choice_candidate_assignment(c)
        c_info: Dict[str, Any] = {
            "choice_index": i,
            "choice_text": c,
            "choice_type": c_type,
            "claims_valid": is_valid_claim,
            "candidate_assignment": assign,
            "evaluation": "UNKNOWN",
            "reason": "",
        }

        if val_res["status"] == "VALID":
            if c_type == "VALID":
                c_info["evaluation"] = "PROVEN_CORRECT"
                c_info["reason"] = "Argument is mathematically proven VALID via SAT UNSAT."
                if proven_choice is None:
                    proven_choice = i
            elif c_type == "INVALID_COUNTEREXAMPLE" and assign:
                ce_check = verify_counterexample_candidate(prems, concl, assign)
                c_info["evaluation"] = "PROVEN_INCORRECT"
                c_info["reason"] = f"Argument is VALID; candidate cannot be a counterexample: {ce_check['reason']}"
            else:
                c_info["evaluation"] = "CONTRADICTS_PROOF"
                c_info["reason"] = "Argument is mathematically proven VALID; cannot be invalid."
        elif val_res["status"] == "INVALID":
            if c_type == "VALID":
                c_info["evaluation"] = "CONTRADICTS_PROOF"
                c_info["reason"] = "Argument is mathematically proven INVALID."
            elif c_type == "INVALID_COUNTEREXAMPLE" and assign:
                ce_check = verify_counterexample_candidate(prems, concl, assign)
                if ce_check["is_counterexample"]:
                    c_info["evaluation"] = "PROVEN_CORRECT"
                    c_info["reason"] = "Candidate is a mathematically verified genuine counterexample."
                    if proven_choice is None:
                        proven_choice = i
                else:
                    c_info["evaluation"] = "PROVEN_INCORRECT"
                    c_info["reason"] = ce_check["reason"]
            else:
                c_info["evaluation"] = "UNVERIFIED_INVALID"
                c_info["reason"] = "Invalid claim without verifiable counterexample."

        choice_verifications[i] = c_info

    det_record["choice_verifications"] = choice_verifications
    det_record["proven_choice_index"] = proven_choice
    det_record["has_authoritative_proof"] = (proven_choice is not None)

    return det_record


# =============================================================================
# Prompt Formatting with Deterministic Evidence
# =============================================================================

def format_revisor_prompt_sprint4(
    problem: Dict[str, Any],
    a0_choice: int,
    a0_reason: str,
    agg: Dict[str, Any],
    det_evidence: Dict[str, Any],
) -> str:
    """
    Sprint 4 Revisor Prompt:
    - Injects Authoritative Deterministic Logic Verification (when established).
    - Preserves LLM Evaluator Aggregation.
    - Deterministic Override: Mathematical proof strictly overrides parametric opinions.
    - Zero ground-truth leakage.
    """
    choices_str = ", ".join([f"{i}) {c}" for i, c in enumerate(problem.get("choices", []))])

    # 1. Deterministic Proof Section
    det_status = det_evidence.get("status", "NOT_APPLICABLE")
    if det_evidence.get("has_authoritative_proof", False):
        proven_idx = det_evidence.get("proven_choice_index")
        det_block = (
            f"### 🛡️ Authoritative Deterministic Verification (SymPy Mathematical Engine):\n"
            f"- Status: {det_status} (Proved via SAT Solver)\n"
            f"- Mathematical Proof: {det_evidence.get('reason')}\n"
            f"- Proven Choice: Choice {proven_idx} ('{problem.get('choices', [])[proven_idx]}')\n"
            f"- Verified Candidate Choices:\n"
        )
        for idx, cv in det_evidence.get("choice_verifications", {}).items():
            det_block += f"  * Choice {idx}: {cv['evaluation']} ({cv['reason']})\n"
        det_block += (
            f"\n⚡ MANDATORY DETERMINISTIC OVERRIDE: Mathematical proof is established and infallible. "
            f"You MUST select Choice {proven_idx}.\n"
        )
    else:
        det_block = (
            f"### Deterministic Logic Verification (SymPy Mathematical Engine):\n"
            f"- Status: {det_status} ({det_evidence.get('reason', 'Not applicable for this question type')})\n"
            f"- Note: No deterministic proof established. Rely on evaluator consensus and A0 presumption.\n"
        )

    # 2. Evaluator block
    eval_lines = []
    for name, status in agg["individual_statuses"].items():
        score = agg["individual_scores"].get(name)
        reason = agg["individual_reasons"].get(name, "")
        if status == "VALID":
            status_desc = f"{score}/10 [VALID - Applicable]"
        elif status == "NOT_APPLICABLE":
            status_desc = "NOT APPLICABLE (Excluded from score)"
        else:
            status_desc = f"NO EVALUATION ({status})"
        eval_lines.append(f"- **{name} Evaluator**: {status_desc}\n  Reason: {reason}")
    eval_block = "\n".join(eval_lines)

    disagreement_warning = ""
    if agg.get("disagreement_detected", False):
        disagreement_warning = (
            f"\n⚠️ ALERT: Evaluator Disagreement Detected! (Scores: {agg['applicable_scores']}). "
            "Do NOT treat numerical consensus as proof."
        )

    return (
        f"You are the Answer Revisor. Review the problem, initial answer A0, deterministic evidence, and all evaluations below.\n\n"
        f"### Problem:\n{problem.get('question', '')}\n\n"
        f"### Choices:\n{choices_str}\n\n"
        f"### Proposed Initial Answer (A0):\n"
        f"- Choice: {a0_choice}\n"
        f"- Reason: {a0_reason}\n\n"
        f"{det_block}\n"
        f"### Individual Evaluator Results (5 Dispatched):\n"
        f"{eval_block}\n\n"
        f"### Aggregation Summary:\n"
        f"- Applicable: {agg['applicable_count']} | Not Applicable: {agg['not_applicable_count']} | Mean Score: {agg['mean_score']}\n"
        f"- Consensus: {agg['consensus_type']}{disagreement_warning}\n\n"
        f"### Hierarchical Decision Guidelines:\n"
        f"1. Deterministic Proof Authority: If the Deterministic SymPy Engine has established proof (VALID or INVALID), mathematical proof strictly overrides all evaluator opinions and A0.\n"
        f"2. Presumption of A0 Validity: If deterministic verification is NOT_APPLICABLE or PARSE_FAILURE, do NOT revise A0 unless an evaluator provides logically sound proof of error. If evaluations are divided, RETAIN A0.\n"
        f"3. Counterexample Fallacy Check: If an evaluator claims a counterexample where the conclusion is TRUE, IGNORE IT and retain A0.\n"
        f"4. Output format: Return strictly in JSON dictionary format: {{\"choice\": <int>, \"Reason\": \"<string>\"}}.\n"
    )


# =============================================================================
# Graph Builder
# =============================================================================

def build_sprint4_graph_dispatch_team(
    prompt: Dict[str, Any],
    react_generator: ReactAgent,
    problem: Dict[str, Any],
    inject_evaluator_evidence: bool = True,
    enable_revisor_override: bool = True,
):
    """
    Constructs the Sprint 4 LangGraph sequential pipeline:
    START -> Answer Generator -> Evaluator Prep -> Deterministic Verifier ->
    Truth Table -> Counterexample -> Predicate Logic -> Logical Argument ->
    Formal Logic -> Aggregator -> Revisor -> END.

    Parameters:
    - inject_evaluator_evidence: Whether to augment Truth Table & Counterexample evaluator contexts with SAT proof.
    - enable_revisor_override: Whether the Revisor hard override gate is active.
    """
    workflow = StateGraph(GraphAgentStateSprint4)

    # 1. Answer Generator node
    ans_spec = prompt["team"]["Answer Generator"]
    ans_node = react_generator.loadMember(
        "Answer Generator", ans_spec["tools"], ans_spec["prompt"], "Default Supervisor"
    )

    # 2. Build 5 evaluator member functions
    eval_spec_dict = prompt["team"]["Evaluator"]
    eval_member_fns = {}
    for name in EVALUATOR_NAMES_FORMAL_LOGIC:
        spec = eval_spec_dict[name]
        guidance = EVALUATOR_SPECIALIZED_GUIDANCE.get(name, "")
        enhanced_prompt = f"{spec['prompt']}\n\n### Specialized Domain Guidance:\n{guidance}"
        eval_member_fns[name] = react_generator.loadMember(
            name, spec["tools"], enhanced_prompt, "Evaluator Supervisor"
        )

    # 3. Revisor node
    rev_spec = prompt["team"]["Revisor"]
    rev_node = react_generator.loadMember(
        "Revisor", rev_spec["tools"], rev_spec["prompt"], "Default Supervisor"
    )

    choice_info = ", ".join([f"{i}) {x}" for i, x in enumerate(problem.get("choices", []))])

    # Node: Answer Generator Runner
    def answer_generator_runner(state: GraphAgentStateSprint4):
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
    def evaluator_prep_runner(state: GraphAgentStateSprint4):
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
            "next": "Deterministic Verifier",
        }

    # Node: Deterministic Verifier (Sprint 4 Addition)
    def deterministic_verifier_runner(state: GraphAgentStateSprint4):
        det_evidence = run_deterministic_verification(problem)

        new_history = dict(state["history"])
        # Inject deterministic proof into Truth Table and Counterexample prompts only if enabled
        if inject_evaluator_evidence and det_evidence.get("has_authoritative_proof", False):
            proof_summary = (
                f"\n\n### 🛡️ Precomputed Deterministic Logic Verification (SymPy):\n"
                f"- Argument Validity: {det_evidence['status']}\n"
                f"- Mathematical Evidence: {det_evidence['reason']}\n"
                f"- Proven Answer Choice: Choice {det_evidence['proven_choice_index']}\n"
            )

            # Augment Truth Table prompt
            if "Truth Table" in new_history and new_history["Truth Table"]:
                orig_tt_msg = new_history["Truth Table"][0].content
                new_history["Truth Table"] = [
                    HumanMessage(content=orig_tt_msg + proof_summary, name="Evaluator_Supervisor")
                ]

            # Augment Counterexample prompt
            if "Counterexample" in new_history and new_history["Counterexample"]:
                ce_analysis = "\n- Candidate Counterexample Analysis:\n"
                for idx, cv in det_evidence.get("choice_verifications", {}).items():
                    ce_analysis += f"  * Choice {idx}: {cv['evaluation']} - {cv['reason']}\n"
                orig_ce_msg = new_history["Counterexample"][0].content
                new_history["Counterexample"] = [
                    HumanMessage(content=orig_ce_msg + proof_summary + ce_analysis, name="Evaluator_Supervisor")
                ]

        return {
            "_deterministic_evidence": det_evidence,
            "history": new_history,
            "next": "Truth Table",
        }

    # Evaluator Node Factory
    def make_evaluator_node(eval_name: str, next_node: str):
        def evaluator_runner(state: GraphAgentStateSprint4):
            eval_fn = eval_member_fns[eval_name]
            record, agent_result = run_evaluator_node_optimized(
                eval_fn, state, eval_name, max_retries=2
            )

            updated_trace = list(state.get("_evaluator_trace", [])) + [record]
            updated_evals = dict(state.get("_individual_evaluations", {}))
            updated_evals[eval_name] = record

            # Preserved immutable A0
            preserved_a0 = copy.deepcopy(state["_initial_intermediate_output"])

            # Merge histories
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
    def aggregator_runner(state: GraphAgentStateSprint4):
        agg = aggregate_evaluations_optimized(
            state.get("_individual_evaluations", {}),
            EVALUATOR_NAMES_FORMAL_LOGIC,
        )

        a0_dict = state["_initial_intermediate_output"]
        a0_choice = a0_dict.get("choice", 0)
        a0_reason = a0_dict.get("Reason", "")
        det_evidence = state.get("_deterministic_evidence", {})

        revisor_prompt_text = format_revisor_prompt_sprint4(
            problem, a0_choice, a0_reason, agg, det_evidence
        )

        new_history = dict(state["history"])
        new_history["Revisor"] = [HumanMessage(content=revisor_prompt_text, name="Default_Supervisor")]

        return {
            "_evaluation_aggregation": agg,
            "intermediate_output": {"answer": a0_dict, "aggregation": agg, "deterministic_evidence": det_evidence},
            "history": new_history,
            "next": "Revisor",
            "background": AIMessage(content=revisor_prompt_text, name="Default Supervisor"),
            "_initial_intermediate_output": copy.deepcopy(a0_dict),
        }

    # Node: Revisor Runner with Deterministic Override
    def revisor_runner(state: GraphAgentStateSprint4):
        t0 = time.time()
        result = rev_node(dict(state))
        elapsed = round(time.time() - t0, 2)

        raw_msg = result.get("messages")
        raw_text = raw_msg.content if hasattr(raw_msg, "content") else str(raw_msg)
        io_out = result.get("intermediate_output", {})

        a0_dict = state["_initial_intermediate_output"]
        a0_choice = a0_dict.get("choice", 0)
        det_evidence = state.get("_deterministic_evidence", {})
        has_det_proof = det_evidence.get("has_authoritative_proof", False)
        proven_choice = det_evidence.get("proven_choice_index")

        parsed = parse_intermediate_output(io_out, None)
        if parsed is None or not isinstance(parsed, dict):
            parsed = parse_intermediate_output(raw_text, None)

        parse_failed = False
        revisor_choice = a0_choice
        revisor_reason = ""

        if parsed and isinstance(parsed, dict):
            new_choice = parsed.get("choice")
            if new_choice is None and "answer" in parsed and isinstance(parsed["answer"], dict):
                new_choice = parsed["answer"].get("choice")

            if new_choice is not None and isinstance(new_choice, (int, str)):
                try:
                    revisor_choice = int(new_choice)
                    revisor_reason = parsed.get("Reason", parsed.get("reason", parsed.get("answer", {}).get("Reason", "")))
                except Exception:
                    parse_failed = True
                    revisor_choice = a0_choice
                    revisor_reason = "Could not parse choice to int; fallback to A0."
            else:
                parse_failed = True
                revisor_choice = a0_choice
                revisor_reason = "No valid choice key found in Revisor JSON; fallback to A0."
        else:
            parse_failed = True
            revisor_choice = a0_choice
            revisor_reason = "Revisor output unparseable; fallback to A0."

        # DETERMINISTIC OVERRIDE GATE
        if enable_revisor_override and has_det_proof and proven_choice is not None:
            if revisor_choice != proven_choice:
                # Override LLM revisor error with mathematical proof
                final_choice = proven_choice
                final_reason = (
                    f"DETERMINISTIC OVERRIDE: Revisor selected Choice {revisor_choice}, but SymPy SAT Engine "
                    f"mathematically proved Choice {proven_choice} ({det_evidence['reason']}). "
                    f"Mathematical proof takes absolute precedence over parametric reasoning."
                )
                decision = "DETERMINISTIC_OVERRIDE"
            else:
                final_choice = proven_choice
                final_reason = revisor_reason or f"Confirmed by SymPy deterministic proof: {det_evidence['reason']}"
                decision = "REVISED" if final_choice != a0_choice else "RETAINED"
        elif not enable_revisor_override and has_det_proof and proven_choice is not None:
            # Hard override disabled (Ablation B): Revisor received evidence, but its choice is respected
            if parse_failed:
                final_choice = a0_choice
                final_reason = revisor_reason
                decision = "PARSE_FAILURE_RETAINED_A0"
            else:
                final_choice = revisor_choice
                final_reason = revisor_reason
                decision = "REVISED" if final_choice != a0_choice else "RETAINED"
        else:
            # Fallback path: preserve A0 on parse failure or use Revisor decision
            if parse_failed:
                final_choice = a0_choice
                final_reason = revisor_reason
                decision = "PARSE_FAILURE_RETAINED_A0"
            else:
                final_choice = revisor_choice
                final_reason = revisor_reason
                decision = "REVISED" if final_choice != a0_choice else "RETAINED"

        revision_step = {
            "step": "Revisor",
            "choice": final_choice,
            "revisor_raw_choice": revisor_choice,
            "reason": final_reason,
            "decision": decision,
            "parse_failed": parse_failed,
            "deterministic_override": (decision == "DETERMINISTIC_OVERRIDE"),
            "raw_response": raw_text,
            "runtime_s": elapsed,
        }

        updated_history = list(state.get("_revision_history", [])) + [revision_step]

        return {
            "intermediate_output": {"choice": final_choice, "Reason": final_reason},
            "_revision_history": updated_history,
            "_initial_intermediate_output": a0_dict,
            "messages": result.get("messages"),
        }

    # Add all nodes to graph
    workflow.add_node("Answer Generator", answer_generator_runner)
    workflow.add_node("Evaluator Prep", evaluator_prep_runner)
    workflow.add_node("Deterministic Verifier", deterministic_verifier_runner)
    workflow.add_node("Truth Table", make_evaluator_node("Truth Table", "Counterexample"))
    workflow.add_node("Counterexample", make_evaluator_node("Counterexample", "Predicate Logic"))
    workflow.add_node("Predicate Logic", make_evaluator_node("Predicate Logic", "Logical Argument"))
    workflow.add_node("Logical Argument", make_evaluator_node("Logical Argument", "Formal Logic"))
    workflow.add_node("Formal Logic", make_evaluator_node("Formal Logic", "Aggregator"))
    workflow.add_node("Aggregator", aggregator_runner)
    workflow.add_node("Revisor", revisor_runner)

    # Add sequential edges
    workflow.add_edge(START, "Answer Generator")
    workflow.add_edge("Answer Generator", "Evaluator Prep")
    workflow.add_edge("Evaluator Prep", "Deterministic Verifier")
    workflow.add_edge("Deterministic Verifier", "Truth Table")
    workflow.add_edge("Truth Table", "Counterexample")
    workflow.add_edge("Counterexample", "Predicate Logic")
    workflow.add_edge("Predicate Logic", "Logical Argument")
    workflow.add_edge("Logical Argument", "Formal Logic")
    workflow.add_edge("Formal Logic", "Aggregator")
    workflow.add_edge("Aggregator", "Revisor")
    workflow.add_edge("Revisor", END)

    return workflow.compile(debug=False)

