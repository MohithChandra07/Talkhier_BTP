import unittest
import sys
import os
from typing import Dict, Any
from langchain_core.messages import AIMessage, HumanMessage

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

# pyrefly: ignore[missing-import]
from multiagent.evaluator_dispatch import (
    EvaluationAggregator,
    AggregatedEvaluation,
    format_revisor_prompt_text,
    extract_evaluator_score_robust,
    ControlledEvaluatorDispatcher,
    RevisorHandler,
    EVALUATOR_NAMES_FORMAL_LOGIC,
)
# pyrefly: ignore[missing-import]
from multiagent.agent_team import extract_evaluator_score


class TestControlledEvaluatorDispatch(unittest.TestCase):

    def test_1_all_five_evaluators_invoked(self):
        """1. Verify that all five evaluators are invoked in controlled dispatch."""
        invoked_evaluators = []

        class MockMember:
            def __init__(self, name):
                self.name = name

            def __call__(self, state):
                invoked_evaluators.append(self.name)
                return {
                    "messages": AIMessage(content="Evaluated", name=self.name),
                    "intermediate_output": {
                        "evaluation": {
                            self.name: {"Correctness Score": 8, "Reason": f"Approved by {self.name}"}
                        }
                    },
                }

        class MockReactGen:
            def loadMember(self, name, tools, prompt, sup_name):
                return MockMember(name)

        dispatcher = ControlledEvaluatorDispatcher(config={}, react_generator=MockReactGen())
        mock_problem = {"question": "Is argument valid?", "choices": ["No", "Yes"], "answer": 1}
        mock_prompts = {
            "team": {
                "Evaluator": {name: {"tools": [4], "prompt": f"Prompt for {name}"} for name in EVALUATOR_NAMES_FORMAL_LOGIC}
            }
        }

        results = dispatcher.dispatch_all(
            problem=mock_problem,
            a0_choice=1,
            a0_reason="Valid argument",
            prompts=mock_prompts,
        )

        self.assertEqual(len(results), 5)
        self.assertEqual(invoked_evaluators, EVALUATOR_NAMES_FORMAL_LOGIC)
        for r in results:
            self.assertTrue(r["invoked"])
            self.assertEqual(r["score"], 8)
            self.assertEqual(r["status"], "OK")
            self.assertTrue(r["is_valid"])

    def test_2_missing_evaluator_output_detected(self):
        """2. Missing evaluator output is detected and not ignored or defaulted to 10."""
        evaluations = [
            {"name": "Truth Table", "invoked": True, "score": 9, "status": "OK", "is_valid": True, "reason": "Consistent"},
            {"name": "Counterexample", "invoked": False, "score": None, "status": "EXECUTION_EXCEPTION", "is_valid": False, "reason": "Timeout"},
            {"name": "Predicate Logic", "invoked": True, "score": 8, "status": "OK", "is_valid": True, "reason": "Correct"},
            {"name": "Logical Argument", "invoked": True, "score": 7, "status": "OK", "is_valid": True, "reason": "Valid flow"},
            {"name": "Formal Logic", "invoked": True, "score": 8, "status": "OK", "is_valid": True, "reason": "Semantics match"},
        ]

        agg = EvaluationAggregator.aggregate(evaluations, EVALUATOR_NAMES_FORMAL_LOGIC)
        self.assertEqual(agg.evaluators_invoked, 4)
        self.assertEqual(agg.valid_scores_count, 4)
        self.assertFalse(agg.is_complete)
        self.assertIn("Counterexample", agg.missing_or_invalid)
        self.assertIsNone(agg.individual_scores["Counterexample"])
        self.assertNotEqual(agg.individual_scores["Counterexample"], 10)

    def test_3_malformed_scores_rejected(self):
        """3. Malformed scores (e.g. text 'unknown' or invalid format) are rejected and marked invalid."""
        raw_io = {
            "evaluation": {
                "Truth Table": {
                    "Correctness Score": "unclear_not_a_number",
                    "Reason": "Unclear logic",
                }
            }
        }
        score, status, reason = extract_evaluator_score_robust(raw_io, evaluator_name="Truth Table")
        self.assertIsNone(score)
        self.assertEqual(status, "MALFORMED_SCORE")
        self.assertNotEqual(score, 10)

    def test_4_scores_outside_permitted_range_rejected(self):
        """4. Scores outside the permitted [0, 10] range are rejected."""
        raw_io_high = {"evaluation": {"Logical Argument": {"Correctness Score": 11, "Reason": "Over max"}}}
        score_h, status_h, _ = extract_evaluator_score_robust(raw_io_high, evaluator_name="Logical Argument")
        self.assertIsNone(score_h)
        self.assertEqual(status_h, "OUT_OF_RANGE")

        raw_io_low = {"evaluation": {"Logical Argument": {"Correctness Score": -2, "Reason": "Below min"}}}
        score_l, status_l, _ = extract_evaluator_score_robust(raw_io_low, evaluator_name="Logical Argument")
        self.assertIsNone(score_l)
        self.assertEqual(status_l, "OUT_OF_RANGE")

    def test_5_incomplete_evaluations_cannot_be_treated_as_unanimous(self):
        """5. Incomplete evaluations cannot be treated as unanimous, even if all valid scores are 10."""
        # 4 out of 5 valid 10/10, but 1 evaluator is missing/invalid
        evaluations = [
            {"name": "Truth Table", "invoked": True, "score": 10, "status": "OK", "is_valid": True, "reason": "Perfect"},
            {"name": "Counterexample", "invoked": True, "score": 10, "status": "OK", "is_valid": True, "reason": "Perfect"},
            {"name": "Predicate Logic", "invoked": True, "score": 10, "status": "OK", "is_valid": True, "reason": "Perfect"},
            {"name": "Logical Argument", "invoked": True, "score": 10, "status": "OK", "is_valid": True, "reason": "Perfect"},
            {"name": "Formal Logic", "invoked": True, "score": None, "status": "MALFORMED_SCORE", "is_valid": False, "reason": "Bad score"},
        ]

        agg = EvaluationAggregator.aggregate(evaluations, EVALUATOR_NAMES_FORMAL_LOGIC)
        self.assertFalse(agg.is_complete)
        self.assertEqual(agg.consensus_type, "INCOMPLETE")
        self.assertNotEqual(agg.consensus_type, "UNANIMOUS_SUPPORT")

    def test_6_supervisor_summaries_cannot_substitute_for_missing_individual_outputs(self):
        """6. Supervisor summaries cannot substitute for missing individual outputs."""
        # Only 2 evaluators actually ran, supervisor summary claims all 5 are 10
        evaluations = [
            {"name": "Truth Table", "invoked": True, "score": 8, "status": "OK", "is_valid": True, "reason": "Good"},
            {"name": "Formal Logic", "invoked": True, "score": 8, "status": "OK", "is_valid": True, "reason": "Good"},
        ]
        # Supervisor summary text claiming 10/10 cannot fill in the missing 3
        agg = EvaluationAggregator.aggregate(evaluations, EVALUATOR_NAMES_FORMAL_LOGIC)
        self.assertEqual(agg.evaluators_invoked, 2)
        self.assertEqual(agg.valid_scores_count, 2)
        self.assertFalse(agg.is_complete)
        self.assertIn("Counterexample", agg.missing_or_invalid)
        self.assertIn("Predicate Logic", agg.missing_or_invalid)
        self.assertIn("Logical Argument", agg.missing_or_invalid)
        self.assertIsNone(agg.individual_scores["Counterexample"])
        self.assertIsNone(agg.individual_scores["Predicate Logic"])
        self.assertIsNone(agg.individual_scores["Logical Argument"])

    def test_7_revisor_receives_validated_evaluator_results(self):
        """7. The Revisor receives validated evaluator results with explicit validity flags."""
        evaluations = [
            {"name": "Truth Table", "invoked": True, "score": 4, "status": "OK", "is_valid": True, "reason": "Contradiction found"},
            {"name": "Counterexample", "invoked": True, "score": 3, "status": "OK", "is_valid": True, "reason": "Found counterexample"},
            {"name": "Predicate Logic", "invoked": True, "score": 5, "status": "OK", "is_valid": True, "reason": "Quantifier error"},
            {"name": "Logical Argument", "invoked": True, "score": 8, "status": "OK", "is_valid": True, "reason": "Valid flow"},
            {"name": "Formal Logic", "invoked": True, "score": 9, "status": "OK", "is_valid": True, "reason": "Syntax good"},
        ]
        agg = EvaluationAggregator.aggregate(evaluations, EVALUATOR_NAMES_FORMAL_LOGIC)
        self.assertTrue(agg.is_complete)
        self.assertFalse(agg.supports_initial_answer)  # 3 oppose (<6), 2 support (>=6)
        self.assertEqual(agg.consensus_type, "MAJORITY_OPPOSE")

        prompt_text = format_revisor_prompt_text(
            {"question": "Q?", "choices": ["A", "B", "C"]},
            a0_choice=0,
            a0_reason="Initial guess",
            aggregated_eval=agg,
        )

        self.assertIn("**Truth Table Evaluator**: 4/10 [VALID]", prompt_text)
        self.assertIn("**Counterexample Evaluator**: 3/10 [VALID]", prompt_text)
        self.assertIn("Consensus Status: MAJORITY_OPPOSE", prompt_text)
        self.assertIn("Supporting Evaluators: 2", prompt_text)
        self.assertIn("Opposing Evaluators: 3", prompt_text)

    def test_8_failed_revision_parsing_does_not_silently_return_stale_data(self):
        """8. Failed revision parsing does not silently return stale data; records failure and retains A0."""
        class MockRevisorAgent:
            def __call__(self, state):
                # Return unparseable free text without JSON
                return {
                    "messages": AIMessage(content="I think we should reconsider but I have no JSON", name="Revisor"),
                    "intermediate_output": "Not a dict or json",
                }

        class MockReactGen:
            def loadMember(self, name, tools, prompt, sup_name):
                return MockRevisorAgent()

        revisor_handler = RevisorHandler(MockReactGen())
        agg = EvaluationAggregator.aggregate(
            [{"name": name, "invoked": True, "score": 8, "status": "OK", "is_valid": True, "reason": "OK"} for name in EVALUATOR_NAMES_FORMAL_LOGIC],
            EVALUATOR_NAMES_FORMAL_LOGIC,
        )

        outcome = revisor_handler.revise(
            problem={"question": "Test", "choices": ["0", "1", "2"]},
            a0_choice=1,
            a0_reason="Original reason",
            a0_io={"choice": 1, "Reason": "Original reason"},
            aggregated_eval=agg,
            prompts={"team": {"Revisor": {"tools": [4], "prompt": "Revisor prompt"}}},
        )

        self.assertTrue(outcome["parse_failed"])
        self.assertEqual(outcome["revisor_decision"], "PARSE_FAILURE_RETAINED_A0")
        self.assertEqual(outcome["final_choice"], 1)  # Retains A0
        self.assertIn("unparseable", outcome["revisor_reason"].lower())

    def test_9_original_answer_and_revision_history_preserved(self):
        """9. Original answer A0 and complete revision history are preserved."""
        class MockRevisorAgent:
            def __call__(self, state):
                return {
                    "messages": AIMessage(content="Flipping to choice 2", name="Revisor"),
                    "intermediate_output": {"choice": 2, "Reason": "Revised after truth table failure"},
                }

        class MockReactGen:
            def loadMember(self, name, tools, prompt, sup_name):
                return MockRevisorAgent()

        revisor_handler = RevisorHandler(MockReactGen())
        agg = EvaluationAggregator.aggregate(
            [{"name": name, "invoked": True, "score": 4, "status": "OK", "is_valid": True, "reason": "Opposed"} for name in EVALUATOR_NAMES_FORMAL_LOGIC],
            EVALUATOR_NAMES_FORMAL_LOGIC,
        )

        outcome = revisor_handler.revise(
            problem={"question": "Test", "choices": ["0", "1", "2"]},
            a0_choice=0,
            a0_reason="A0 reason",
            a0_io={"choice": 0, "Reason": "A0 reason"},
            aggregated_eval=agg,
            prompts={"team": {"Revisor": {"tools": [4], "prompt": "Revisor prompt"}}},
        )

        self.assertFalse(outcome["parse_failed"])
        self.assertEqual(outcome["revisor_decision"], "REVISED")
        self.assertEqual(outcome["final_choice"], 2)

        history = outcome["revision_history"]
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["step"], "A0")
        self.assertEqual(history[0]["choice"], 0)
        self.assertEqual(history[1]["step"], "Revisor")
        self.assertEqual(history[1]["choice"], 2)
        self.assertEqual(history[1]["decision"], "REVISED")


if __name__ == "__main__":
    unittest.main()
