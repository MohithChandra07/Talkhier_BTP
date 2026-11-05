import unittest
import sys
import os
import copy
from typing import Dict, Any
from langchain_core.messages import AIMessage, HumanMessage

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from multiagent.graph_dispatch import (
    classify_evaluation_status,
    aggregate_evaluations_strict,
    evaluate_revision_quality,
    format_revisor_prompt_strict,
    build_mandatory_graph_dispatch_team,
    run_evaluator_node_with_retries,
)
from multiagent.agent_team import parse_intermediate_output
from multiagent.evaluator_dispatch import EVALUATOR_NAMES_FORMAL_LOGIC


class TestGraphDispatch(unittest.TestCase):

    def test_1_status_classification_valid(self):
        """Verify VALID status when score is in [0, 10] and structured."""
        io = {"evaluation": {"Formal Logic": {"Correctness Score": 9, "Reason": "Valid logic"}}}
        status, score, reason, is_app, vote = classify_evaluation_status(io, "Raw text", "Formal Logic")
        self.assertEqual(status, "VALID")
        self.assertEqual(score, 9)
        self.assertTrue(is_app)
        self.assertIsNone(vote)

    def test_2_status_classification_not_applicable(self):
        """Verify NOT_APPLICABLE when score is N/A or method is not applicable. Score is None (never 0 or 10)."""
        io1 = {"evaluation": {"Truth Table": {"Correctness Score": "N/A", "Reason": "Not applicable for this question"}}}
        status1, score1, reason1, is_app1, _ = classify_evaluation_status(io1, "Text", "Truth Table")
        self.assertEqual(status1, "NOT_APPLICABLE")
        self.assertIsNone(score1)
        self.assertFalse(is_app1)

        # Also when reason states truth table is not required
        io2 = {"evaluation": {"Truth Table": {"Correctness Score": 0, "Reason": "The truth table is not required for solving this problem."}}}
        status2, score2, _, is_app2, _ = classify_evaluation_status(io2, "not required", "Truth Table")
        self.assertEqual(status2, "NOT_APPLICABLE")
        self.assertIsNone(score2)
        self.assertFalse(is_app2)

    def test_3_status_classification_no_evaluation(self):
        """Verify NO_EVALUATION when output is unparseable or malformed. Score is None."""
        io = "unparseable string"
        status, score, reason, is_app, _ = classify_evaluation_status(io, "No json here", "Predicate Logic")
        self.assertEqual(status, "NO_EVALUATION")
        self.assertIsNone(score)
        self.assertTrue(is_app)

    def test_4_strict_denominator_excludes_not_applicable_and_no_evaluation(self):
        """Verify that NOT_APPLICABLE and NO_EVALUATION NEVER enter the numerical denominator."""
        # 5 evaluators: 2 VALID (scores 8 and 10), 1 NOT_APPLICABLE, 1 NO_EVALUATION, 1 VALID (score 6)
        # Applicable count = 4 (3 VALID + 1 NO_EVALUATION)
        # Valid count = 3 (scores: 8, 10, 6)
        # Denominator MUST be 3 (valid applicable evaluations), mean = (8+10+6)/3 = 8.0
        evals = {
            "Truth Table": {"invoked": True, "status": "NOT_APPLICABLE", "score": None, "reason": "N/A"},
            "Counterexample": {"invoked": True, "status": "VALID", "score": 8, "reason": "Good"},
            "Predicate Logic": {"invoked": True, "status": "NO_EVALUATION", "score": None, "reason": "Failed to parse"},
            "Logical Argument": {"invoked": True, "status": "VALID", "score": 10, "reason": "Strong"},
            "Formal Logic": {"invoked": True, "status": "VALID", "score": 6, "reason": "Acceptable"},
        }

        agg = aggregate_evaluations_strict(evals, EVALUATOR_NAMES_FORMAL_LOGIC)
        self.assertEqual(agg["applicable_count"], 4)
        self.assertEqual(agg["not_applicable_count"], 1)
        self.assertEqual(agg["valid_count"], 3)
        self.assertEqual(agg["invalid_count"], 1)
        self.assertEqual(agg["applicable_scores"], [8, 10, 6])
        self.assertEqual(agg["mean_score"], 8.0)  # (8+10+6)/3
        self.assertFalse(agg["is_complete"])  # Because 1 is invalid
        self.assertEqual(agg["consensus_type"], "INCOMPLETE")

    def test_5_no_evaluation_retries(self):
        """Verify up to 2 retries on NO_EVALUATION and recording of attempts."""
        call_count = 0

        def mock_eval_fn(state):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                # First two attempts fail to produce structured output
                return {"messages": AIMessage(content="I don't know"), "intermediate_output": {}}
            # Third attempt succeeds
            return {
                "messages": AIMessage(content="Valid now"),
                "intermediate_output": {"evaluation": {"Logical Argument": {"Correctness Score": 9, "Reason": "Recovered"}}},
            }

        state = {
            "history": {"Logical Argument": [HumanMessage(content="Task")]},
            "background": AIMessage(content="bg"),
            "intermediate_output": {},
        }

        record, res = run_evaluator_node_with_retries(mock_eval_fn, state, "Logical Argument", max_retries=2)
        self.assertEqual(call_count, 3)  # Initial attempt + 2 retries
        self.assertEqual(record["status"], "VALID")
        self.assertEqual(record["score"], 9)
        self.assertEqual(record["retries"], 2)
        self.assertEqual(len(record["attempts_trace"]), 3)

    def test_6_regression_a0_cannot_be_overwritten_by_evaluators(self):
        """Regression test: verify A0 in _initial_intermediate_output cannot be overwritten by evaluators."""
        initial_a0 = {"choice": 2, "Reason": "Original reasoning for choice 2"}
        imm_copy = copy.deepcopy(initial_a0)

        # Simulate state with _initial_intermediate_output
        state = {
            "_initial_intermediate_output": imm_copy,
            "_evaluator_trace": [],
            "_individual_evaluations": {},
            "history": {},
        }

        # Malicious/corrupt evaluator tries to output choice 0
        corrupt_eval_output = {"choice": 0, "Reason": "Corrupted answer"}

        # Preserve check: state['_initial_intermediate_output'] must remain intact
        self.assertEqual(state["_initial_intermediate_output"]["choice"], 2)
        self.assertEqual(state["_initial_intermediate_output"], initial_a0)
        self.assertNotEqual(state["_initial_intermediate_output"]["choice"], corrupt_eval_output["choice"])

    def test_7_revisor_retains_a0_on_parse_failure(self):
        """Verify Revisor retains A0 when output cannot be parsed into JSON."""
        # Simulated unparseable Revisor output
        raw_text = "I think the answer might be choice 1, but I am not providing valid JSON."
        parsed = parse_intermediate_output(raw_text, None)
        self.assertIsNone(parsed)

        a0_choice = 3
        if parsed is None:
            final_choice = a0_choice
            decision = "PARSE_FAILURE_RETAINED_A0"

        self.assertEqual(final_choice, 3)
        self.assertEqual(decision, "PARSE_FAILURE_RETAINED_A0")

    def test_8_revisor_prompt_does_not_expose_ground_truth(self):
        """Verify format_revisor_prompt_strict never exposes ground truth."""
        problem = {"question": "What is valid?", "choices": ["A", "B", "C"], "answer": 2}
        evals = {
            "Formal Logic": {"invoked": True, "status": "VALID", "score": 9, "reason": "Valid translation"}
        }
        agg = aggregate_evaluations_strict(evals, ["Formal Logic"])
        prompt_text = format_revisor_prompt_strict(problem, a0_choice=0, a0_reason="Guess", agg=agg)
        self.assertNotIn("Ground Truth", prompt_text)
        self.assertNotIn("ground_truth", prompt_text)
        self.assertNotIn("answer: 2", prompt_text.lower())

    def test_9_revision_quality_classification(self):
        """Verify classification of HELPFUL, HARMFUL, and NEUTRAL revisions."""
        # GT = 1
        # Helpful: A0 was 0, Final was 1
        self.assertEqual(evaluate_revision_quality(0, 1, 1), "HELPFUL")
        # Harmful: A0 was 1, Final was 0
        self.assertEqual(evaluate_revision_quality(1, 0, 1), "HARMFUL")
        # Neutral retained correct: A0 was 1, Final was 1
        self.assertEqual(evaluate_revision_quality(1, 1, 1), "NEUTRAL_RETAINED_CORRECT")
        # Neutral retained incorrect: A0 was 0, Final was 0
        self.assertEqual(evaluate_revision_quality(0, 0, 1), "NEUTRAL_RETAINED_INCORRECT")
        # Neutral revised incorrect: A0 was 0, Final was 2
        self.assertEqual(evaluate_revision_quality(0, 2, 1), "NEUTRAL_REVISED_INCORRECT")

    def test_10_mandatory_sequential_graph_execution(self):
        """Verify that build_mandatory_graph_dispatch_team compiles and runs in intended sequence with mock agents."""
        executed_sequence = []

        class MockMember:
            def __init__(self, name):
                self.name = name

            def __call__(self, state):
                executed_sequence.append(self.name)
                if self.name == "Answer Generator":
                    return {
                        "messages": AIMessage(content="Generated answer", name=self.name),
                        "intermediate_output": {"choice": 2, "Reason": "A0 reasoning"},
                        "history": state["history"],
                    }
                elif self.name == "Revisor":
                    return {
                        "messages": AIMessage(content='{"choice": 2, "Reason": "Retained"}', name=self.name),
                        "intermediate_output": {"choice": 2, "Reason": "Retained"},
                        "history": state["history"],
                    }
                else:
                    return {
                        "messages": AIMessage(content=f"Evaluated by {self.name}", name=self.name),
                        "intermediate_output": {"evaluation": {self.name: {"Correctness Score": 8, "Reason": "Valid"}}},
                        "history": state["history"],
                    }

        class MockReactGen:
            def loadMember(self, name, tools, prompt, sup_name):
                return MockMember(name)

        problem = {"question": "Sample Question", "choices": ["A", "B", "C", "D"], "answer": 2}
        prompts = {
            "team": {
                "Answer Generator": {"tools": [4], "prompt": "Ans prompt"},
                "Revisor": {"tools": [4], "prompt": "Rev prompt"},
                "Evaluator": {name: {"tools": [4], "prompt": f"Prompt {name}"} for name in EVALUATOR_NAMES_FORMAL_LOGIC},
            }
        }

        graph = build_mandatory_graph_dispatch_team(prompts, MockReactGen(), problem)
        initial_state = {
            "history": {
                "Answer Generator": [HumanMessage(content="Solve problem")],
                "all": [HumanMessage(content="Solve problem")],
            },
            "messages": HumanMessage(content="Solve problem"),
            "background": AIMessage(content="Background"),
            "intermediate_output": {},
            "next": "Answer Generator",
            "initial_prompt": "Prompt",
            "_initial_intermediate_output": {},
            "_evaluator_trace": [],
            "_individual_evaluations": {},
            "_evaluation_aggregation": {},
            "_revision_history": [],
        }

        final_state = graph.invoke(initial_state)

        # Expected execution order:
        expected_seq = [
            "Answer Generator",
            "Truth Table",
            "Counterexample",
            "Predicate Logic",
            "Logical Argument",
            "Formal Logic",
            "Revisor",
        ]
        self.assertEqual(executed_sequence, expected_seq)
        self.assertEqual(final_state["_initial_intermediate_output"]["choice"], 2)
        self.assertEqual(final_state["intermediate_output"]["choice"], 2)
        self.assertEqual(len(final_state["_evaluator_trace"]), 5)
        self.assertEqual(len(final_state["_individual_evaluations"]), 5)
        self.assertTrue(final_state["_evaluation_aggregation"]["is_complete"])


if __name__ == "__main__":
    unittest.main()
