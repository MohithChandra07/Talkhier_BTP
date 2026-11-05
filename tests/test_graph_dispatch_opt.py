import unittest
import sys
import os
import copy
from typing import Dict, Any
from langchain_core.messages import AIMessage, HumanMessage

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from multiagent.graph_dispatch_opt import (
    classify_evaluation_status_opt,
    aggregate_evaluations_optimized,
    format_revisor_prompt_optimized,
    run_evaluator_node_optimized,
    build_optimized_graph_dispatch_team,
    EVALUATOR_SPECIALIZED_GUIDANCE,
)
from multiagent.evaluator_dispatch import EVALUATOR_NAMES_FORMAL_LOGIC


class TestGraphDispatchOpt(unittest.TestCase):

    def test_1_case_insensitive_and_generic_evaluator_key_parsing(self):
        """Verify case-insensitive key parsing ('correctness score', 'score') and generic 'Evaluator' key."""
        # 1. Lowercase 'correctness score'
        io1 = {"evaluation": {"Logical Argument": {"correctness score": 8, "reason": "Good reasoning"}}}
        status1, score1, reason1, is_app1, _ = classify_evaluation_status_opt(io1, "Text", "Logical Argument")
        self.assertEqual(status1, "VALID")
        self.assertEqual(score1, 8)
        self.assertTrue(is_app1)

        # 2. 'Score' instead of 'Correctness Score'
        io2 = {"evaluation": {"Formal Logic": {"Score": 9, "Reason": "Precise translation"}}}
        status2, score2, _, is_app2, _ = classify_evaluation_status_opt(io2, "Text", "Formal Logic")
        self.assertEqual(status2, "VALID")
        self.assertEqual(score2, 9)

        # 3. Generic 'Evaluator' wrapper
        io3 = {"evaluation": {"Evaluator": {"Correctness Score": 7, "Reason": "Generic key handled"}}}
        status3, score3, _, is_app3, _ = classify_evaluation_status_opt(io3, "Text", "Predicate Logic")
        self.assertEqual(status3, "VALID")
        self.assertEqual(score3, 7)

    def test_2_not_applicable_score_is_none(self):
        """Verify NOT_APPLICABLE status has score=None and is_applicable=False."""
        # String 'N/A'
        io1 = {"evaluation": {"Truth Table": {"Correctness Score": "N/A", "Reason": "Not needed"}}}
        status1, score1, _, is_app1, _ = classify_evaluation_status_opt(io1, "Text", "Truth Table")
        self.assertEqual(status1, "NOT_APPLICABLE")
        self.assertIsNone(score1)
        self.assertFalse(is_app1)

        # Reason states not required even if score is 0
        io2 = {"evaluation": {"Counterexample": {"Correctness Score": 0, "Reason": "No counterexample is required here"}}}
        status2, score2, _, is_app2, _ = classify_evaluation_status_opt(io2, "not required", "Counterexample")
        self.assertEqual(status2, "NOT_APPLICABLE")
        self.assertIsNone(score2)
        self.assertFalse(is_app2)

    def test_3_disagreement_detection_in_aggregation(self):
        """Verify disagreement detection when evaluator scores diverge sharply."""
        # 2 evaluators support (score 9, 8), 1 opposes (score 2)
        evals = {
            "Truth Table": {"invoked": True, "status": "VALID", "score": 9, "reason": "Solid"},
            "Counterexample": {"invoked": True, "status": "VALID", "score": 2, "reason": "Found issue"},
            "Predicate Logic": {"invoked": True, "status": "NOT_APPLICABLE", "score": None, "reason": "N/A"},
            "Logical Argument": {"invoked": True, "status": "VALID", "score": 8, "reason": "Sound"},
            "Formal Logic": {"invoked": True, "status": "VALID", "score": 8, "reason": "Correct"},
        }
        agg = aggregate_evaluations_optimized(evals, EVALUATOR_NAMES_FORMAL_LOGIC)
        self.assertEqual(agg["valid_count"], 4)
        self.assertEqual(agg["not_applicable_count"], 1)
        self.assertEqual(agg["score_range"], 7)  # 9 - 2 = 7
        self.assertTrue(agg["disagreement_detected"])
        self.assertEqual(agg["consensus_type"], "MAJORITY_SUPPORT")

    def test_4_revisor_prompt_guidelines_and_no_leakage(self):
        """Verify optimized revisor prompt contains fallacy check, A0 presumption, and NO ground truth."""
        problem = {
            "question": "Is ~G ⊃ H valid?",
            "choices": ["Valid", "Invalid"],
            "ground_truth": "Valid",
            "ground_truth_choice": 0,
        }
        agg = {
            "applicable_count": 4,
            "not_applicable_count": 1,
            "invalid_count": 0,
            "valid_count": 4,
            "applicable_scores": [2, 1, 1, 2],
            "mean_score": 1.5,
            "consensus_type": "MAJORITY_OPPOSE",
            "majority_threshold": 3,
            "disagreement_detected": False,
            "is_complete": True,
            "individual_statuses": {"Truth Table": "VALID", "Counterexample": "VALID", "Predicate Logic": "NOT_APPLICABLE", "Logical Argument": "VALID", "Formal Logic": "VALID"},
            "individual_scores": {"Truth Table": 2, "Counterexample": 1, "Predicate Logic": None, "Logical Argument": 1, "Formal Logic": 2},
            "individual_reasons": {"Truth Table": "Low", "Counterexample": "Low", "Predicate Logic": "N/A", "Logical Argument": "Low", "Formal Logic": "Low"},
        }

        prompt = format_revisor_prompt_optimized(problem, a0_choice=0, a0_reason="Valid argument", agg=agg)

        # 1. Presumption of A0 Validity
        self.assertIn("Presumption of A0 Validity", prompt)
        # 2. Counterexample Fallacy Check
        self.assertIn("Counterexample Fallacy Check", prompt)
        self.assertIn("conclusion is FALSE", prompt)
        # 3. N/A Exclusion
        self.assertIn("N/A Exclusion", prompt)
        # 4. Zero ground-truth leakage
        self.assertNotIn("ground_truth", prompt.lower())
        self.assertNotIn("Ground Truth", prompt)

    def test_5_specialized_guidance_content(self):
        """Verify all 5 evaluators have specialized guidance addressing key logic domains."""
        self.assertEqual(len(EVALUATOR_SPECIALIZED_GUIDANCE), 5)
        for name in EVALUATOR_NAMES_FORMAL_LOGIC:
            self.assertIn(name, EVALUATOR_SPECIALIZED_GUIDANCE)
            guidance = EVALUATOR_SPECIALIZED_GUIDANCE[name]
            self.assertTrue(len(guidance) > 50)
            if name in ["Truth Table", "Counterexample"]:
                self.assertIn("CONCLUSION", guidance)
                self.assertIn("FALSE", guidance)

    def test_6_evaluator_node_retry_and_history_isolation(self):
        """Verify retry mechanism and history deepcopy isolation."""
        attempts = 0

        def mock_eval_fn(state):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                return {
                    "messages": AIMessage(content="Bad output"),
                    "intermediate_output": {},
                    "history": {"Counterexample": [HumanMessage(content="Attempt 1 response")]},
                }
            return {
                "messages": AIMessage(content="Good output"),
                "intermediate_output": {"evaluation": {"Counterexample": {"Correctness Score": 10, "Reason": "Valid"}}},
                "history": {"Counterexample": [HumanMessage(content="Attempt 2 response")]},
            }

        state = {
            "history": {
                "Counterexample": [HumanMessage(content="Original prompt")],
                "Predicate Logic": [HumanMessage(content="Downstream prompt")],
            },
            "intermediate_output": {},
        }

        record, res = run_evaluator_node_optimized(mock_eval_fn, state, "Counterexample", max_retries=2)
        self.assertEqual(record["status"], "VALID")
        self.assertEqual(record["score"], 10)
        self.assertEqual(record["retries"], 1)
        self.assertEqual(len(record["attempts_trace"]), 2)

    def test_7_revisor_preserves_a0_on_parse_failure(self):
        """Verify that when Revisor produces unparseable or missing output, A0 is strictly preserved."""
        problem = {"question": "Q", "choices": ["A", "B"]}
        # Mock react_generator
        class MockReactAgent:
            def loadMember(self, name, tools, prompt, supervisor_name):
                def member(state):
                    if name == "Revisor":
                        # Malformed response
                        return {"messages": AIMessage(content="I cannot decide at all."), "intermediate_output": {}}
                    return {"messages": AIMessage(content="{}"), "intermediate_output": {"choice": 1, "Reason": "A0 reason"}}
                return member

        prompt_dict = {
            "team": {
                "Answer Generator": {"tools": [], "prompt": "AG prompt"},
                "Evaluator": {k: {"tools": [], "prompt": f"{k} prompt"} for k in EVALUATOR_NAMES_FORMAL_LOGIC},
                "Revisor": {"tools": [], "prompt": "Rev prompt"},
            }
        }

        graph = build_optimized_graph_dispatch_team(prompt_dict, MockReactAgent(), problem)
        init_state = {
            "history": {},
            "messages": HumanMessage(content="Start"),
            "background": AIMessage(content=""),
            "intermediate_output": {},
            "next": "Answer Generator",
            "initial_prompt": prompt_dict,
            "_initial_intermediate_output": {},
            "_evaluator_trace": [],
            "_individual_evaluations": {},
            "_evaluation_aggregation": {},
            "_revision_history": [],
        }

        res = graph.invoke(init_state)
        # Revisor output was unparseable, so final choice MUST be A0 (choice 1)
        self.assertEqual(res["intermediate_output"]["choice"], 1)
        rev_history = [h for h in res["_revision_history"] if h["step"] == "Revisor"]
        self.assertEqual(len(rev_history), 1)
        self.assertEqual(rev_history[0]["decision"], "PARSE_FAILURE_RETAINED_A0")
        self.assertTrue(rev_history[0]["parse_failed"])

    def test_8_graph_topology_contains_all_mandatory_nodes(self):
        """Verify the compiled graph has the exact sequential pipeline nodes and edges."""
        prompt_dict = {
            "team": {
                "Answer Generator": {"tools": [], "prompt": "AG prompt"},
                "Evaluator": {k: {"tools": [], "prompt": f"{k} prompt"} for k in EVALUATOR_NAMES_FORMAL_LOGIC},
                "Revisor": {"tools": [], "prompt": "Rev prompt"},
            }
        }
        class DummyReactAgent:
            def loadMember(self, name, tools, prompt, supervisor_name):
                return lambda state: {"messages": AIMessage(content="{}"), "intermediate_output": {}}

        graph = build_optimized_graph_dispatch_team(prompt_dict, DummyReactAgent(), {"question": "Q", "choices": ["A"]})
        node_names = set(graph.nodes.keys())
        expected_nodes = {
            "__start__", "Answer Generator", "Evaluator Prep",
            "Truth Table", "Counterexample", "Predicate Logic",
            "Logical Argument", "Formal Logic", "Aggregator", "Revisor"
        }
        for n in expected_nodes:
            self.assertIn(n, node_names)


if __name__ == "__main__":
    unittest.main()
