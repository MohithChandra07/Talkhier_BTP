import unittest
import sys
import os
import copy
from typing import Dict, Any
from langchain_core.messages import AIMessage, HumanMessage

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from multiagent.graph_dispatch_sprint4 import (
    extract_propositional_argument,
    extract_choice_candidate_assignment,
    run_deterministic_verification,
    format_revisor_prompt_sprint4,
    build_sprint4_graph_dispatch_team,
)
from multiagent.evaluator_dispatch import EVALUATOR_NAMES_FORMAL_LOGIC


class TestGraphDispatchSprint4(unittest.TestCase):

    # =========================================================================
    # 1. Propositional Argument Extraction Tests
    # =========================================================================

    def test_extract_propositional_argument_valid_slash(self):
        """Verify extraction from standard MMLU slash notation (Problem 3 style)."""
        q = (
            "Construct a complete truth table for the following argument. "
            "Then, using the truth table, determine whether the argument is valid or invalid.\n"
            "~G ⊃ H\n"
            "~H / G"
        )
        prems, concl, status, reason = extract_propositional_argument(q)
        self.assertEqual(status, "OK")
        self.assertEqual(prems, ["~G ⊃ H", "~H"])
        self.assertEqual(concl, "G")

    def test_extract_propositional_argument_unsupported_natural_language(self):
        """Verify natural language philosophical questions return NOT_APPLICABLE."""
        q = (
            "Identify the conclusion of the following argument. It is hard not to verify in our peers "
            "the same weakened intelligence due to emotions that we observe in our everyday patients."
        )
        prems, concl, status, reason = extract_propositional_argument(q)
        self.assertEqual(status, "NOT_APPLICABLE")
        self.assertIsNone(prems)
        self.assertIsNone(concl)

    def test_extract_propositional_argument_unsupported_predicate_logic(self):
        """Verify first-order predicate questions return NOT_APPLICABLE."""
        q = "Select the best translation into predicate logic. David teaches Chris. (c: Chris; d: David; Txy: x teaches y)"
        prems, concl, status, reason = extract_propositional_argument(q)
        self.assertEqual(status, "NOT_APPLICABLE")

    def test_extract_propositional_argument_malformed_slash(self):
        """Verify malformed slash lines return PARSE_FAILURE."""
        q1 = "~G ⊃ H\n~H / G / Z"  # Too many slashes
        _, _, status1, _ = extract_propositional_argument(q1)
        self.assertEqual(status1, "PARSE_FAILURE")

        q2 = "~G ⊃ H\n~H / "  # Empty conclusion
        _, _, status2, _ = extract_propositional_argument(q2)
        self.assertEqual(status2, "PARSE_FAILURE")

        q3 = "~G ⊃ (H\n~H / G"  # Unbalanced parenthesis in premise
        _, _, status3, _ = extract_propositional_argument(q3)
        self.assertEqual(status3, "PARSE_FAILURE")

    # =========================================================================
    # 2. Choice Candidate Assignment Extraction Tests
    # =========================================================================

    def test_extract_choice_valid_claim(self):
        """Verify extraction from 'Valid' choice."""
        assign, is_valid, c_type = extract_choice_candidate_assignment("Valid")
        self.assertIsNone(assign)
        self.assertTrue(is_valid)
        self.assertEqual(c_type, "VALID")

    def test_extract_choice_counterexample_assignment(self):
        """Verify extraction of candidate truth assignments from counterexample choices."""
        # Both true
        a1, v1, t1 = extract_choice_candidate_assignment("Invalid. Counterexample when G and H are true")
        self.assertEqual(t1, "INVALID_COUNTEREXAMPLE")
        self.assertFalse(v1)
        self.assertEqual(a1, {"G": True, "H": True})

        # Mixed true/false
        a2, v2, t2 = extract_choice_candidate_assignment("Invalid. Counterexample when G is true and H is false")
        self.assertEqual(t2, "INVALID_COUNTEREXAMPLE")
        self.assertFalse(v2)
        self.assertEqual(a2, {"G": True, "H": False})

        # Colon syntax
        a3, v3, t3 = extract_choice_candidate_assignment("Invalid: G = False, H = True")
        self.assertEqual(t3, "INVALID_COUNTEREXAMPLE")
        self.assertEqual(a3, {"G": False, "H": True})

    # =========================================================================
    # 3. Deterministic Verification on Problems
    # =========================================================================

    def test_run_deterministic_verification_problem_3(self):
        """Verify Problem 3 produces authoritative mathematical proof for Choice 0."""
        problem = {
            "question": "Determine whether the argument is valid or invalid.\n~G ⊃ H\n~H / G",
            "choices": [
                "Valid",
                "Invalid. Counterexample when G and H are true",
                "Invalid. Counterexample when G is true and H is false",
                "Invalid. Counterexample when H is true and G is false",
            ],
        }
        res = run_deterministic_verification(problem)
        self.assertEqual(res["status"], "VALID")
        self.assertTrue(res["is_valid"])
        self.assertTrue(res["has_authoritative_proof"])
        self.assertEqual(res["proven_choice_index"], 0)

        # Choice 0 is proven correct
        self.assertEqual(res["choice_verifications"][0]["evaluation"], "PROVEN_CORRECT")

        # Choice 2 is proven incorrect (conclusion G is true)
        self.assertEqual(res["choice_verifications"][2]["evaluation"], "PROVEN_INCORRECT")

    def test_run_deterministic_verification_invalid_argument_with_counterexample(self):
        """Verify an invalid argument correctly proves the genuine counterexample choice."""
        problem = {
            "question": "Determine whether the argument is valid or invalid.\nA ⊃ B\nB / A",
            "choices": [
                "Valid",
                "Invalid. Counterexample when A is false and B is true",
                "Invalid. Counterexample when A is true and B is false",
            ],
        }
        res = run_deterministic_verification(problem)
        self.assertEqual(res["status"], "INVALID")
        self.assertFalse(res["is_valid"])
        self.assertTrue(res["has_authoritative_proof"])
        self.assertEqual(res["proven_choice_index"], 1)
        self.assertEqual(res["choice_verifications"][1]["evaluation"], "PROVEN_CORRECT")
        self.assertEqual(res["choice_verifications"][0]["evaluation"], "CONTRADICTS_PROOF")

    def test_run_deterministic_verification_not_applicable_on_problem_0(self):
        """Verify natural language Problem 0 returns NOT_APPLICABLE and no proof."""
        problem = {
            "question": "Identify the conclusion of the following argument. It is hard not to verify in our peers...",
            "choices": ["Choice A", "Choice B", "Choice C", "Choice D"],
        }
        res = run_deterministic_verification(problem)
        self.assertEqual(res["status"], "NOT_APPLICABLE")
        self.assertFalse(res["has_authoritative_proof"])
        self.assertIsNone(res["proven_choice_index"])

    # =========================================================================
    # 4. Revisor Deterministic Override & Fallback
    # =========================================================================

    def test_revisor_deterministic_override_enforces_proof(self):
        """
        Verify that when SymPy proves Choice 0, but the Revisor attempts to choose Choice 2,
        the deterministic override gate enforces Choice 0.
        """
        problem = {
            "question": "~G ⊃ H\n~H / G",
            "choices": ["Valid", "Invalid. CE 1", "Invalid. CE 2", "Invalid. CE 3"],
        }
        # Mock react_generator where Revisor hallucinates Choice 2
        class MockReactAgent:
            def loadMember(self, name, tools, prompt, supervisor_name):
                def member(state):
                    if name == "Revisor":
                        # Revisor hallucinates Choice 2
                        return {"messages": AIMessage(content=""), "intermediate_output": {"choice": 2, "Reason": "Hallucinated choice 2"}}
                    return {"messages": AIMessage(content=""), "intermediate_output": {"choice": 0, "Reason": "A0"}}
                return member

        prompt_dict = {
            "team": {
                "Answer Generator": {"tools": [], "prompt": "AG prompt"},
                "Evaluator": {k: {"tools": [], "prompt": f"{k} prompt"} for k in EVALUATOR_NAMES_FORMAL_LOGIC},
                "Revisor": {"tools": [], "prompt": "Rev prompt"},
            }
        }

        graph = build_sprint4_graph_dispatch_team(prompt_dict, MockReactAgent(), problem)
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
            "_deterministic_evidence": {},
            "_revision_history": [],
        }

        res = graph.invoke(init_state)
        # DETERMINISTIC OVERRIDE: Final choice MUST be 0 (the proven choice), NOT 2!
        self.assertEqual(res["intermediate_output"]["choice"], 0)
        rev_history = [h for h in res["_revision_history"] if h["step"] == "Revisor"][0]
        self.assertEqual(rev_history["decision"], "DETERMINISTIC_OVERRIDE")
        self.assertTrue(rev_history["deterministic_override"])
        self.assertEqual(rev_history["revisor_raw_choice"], 2)

    def test_revisor_fallback_when_deterministic_not_applicable(self):
        """
        Verify that when deterministic verification is NOT_APPLICABLE,
        the Revisor decision is respected and A0 fallback rules apply.
        """
        problem = {
            "question": "Natural language question without logic formulas.",
            "choices": ["A", "B", "C", "D"],
        }
        class MockReactAgent:
            def loadMember(self, name, tools, prompt, supervisor_name):
                def member(state):
                    if name == "Revisor":
                        return {"messages": AIMessage(content=""), "intermediate_output": {"choice": 3, "Reason": "Valid NL revision"}}
                    return {"messages": AIMessage(content=""), "intermediate_output": {"choice": 1, "Reason": "A0"}}
                return member

        prompt_dict = {
            "team": {
                "Answer Generator": {"tools": [], "prompt": "AG prompt"},
                "Evaluator": {k: {"tools": [], "prompt": f"{k} prompt"} for k in EVALUATOR_NAMES_FORMAL_LOGIC},
                "Revisor": {"tools": [], "prompt": "Rev prompt"},
            }
        }

        graph = build_sprint4_graph_dispatch_team(prompt_dict, MockReactAgent(), problem)
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
            "_deterministic_evidence": {},
            "_revision_history": [],
        }

        res = graph.invoke(init_state)
        self.assertEqual(res["intermediate_output"]["choice"], 3)
        rev_history = [h for h in res["_revision_history"] if h["step"] == "Revisor"][0]
        self.assertEqual(rev_history["decision"], "REVISED")
        self.assertFalse(rev_history["deterministic_override"])

    def test_graph_topology_sprint4(self):
        """Verify the compiled graph contains all nodes including Deterministic Verifier."""
        prompt_dict = {
            "team": {
                "Answer Generator": {"tools": [], "prompt": "AG"},
                "Evaluator": {k: {"tools": [], "prompt": f"{k}"} for k in EVALUATOR_NAMES_FORMAL_LOGIC},
                "Revisor": {"tools": [], "prompt": "Rev"},
            }
        }
        class DummyReactAgent:
            def loadMember(self, name, tools, prompt, supervisor_name):
                return lambda state: {"messages": AIMessage(content="{}"), "intermediate_output": {}}

        graph = build_sprint4_graph_dispatch_team(prompt_dict, DummyReactAgent(), {"question": "Q", "choices": ["A"]})
        node_names = set(graph.nodes.keys())
        expected_nodes = {
            "__start__", "Answer Generator", "Evaluator Prep", "Deterministic Verifier",
            "Truth Table", "Counterexample", "Predicate Logic", "Logical Argument",
            "Formal Logic", "Aggregator", "Revisor"
        }
        for n in expected_nodes:
            self.assertIn(n, node_names)


if __name__ == "__main__":
    unittest.main()

