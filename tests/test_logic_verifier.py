import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from multiagent.logic_verifier import (
    normalize_logical_formula,
    verify_argument_validity,
    verify_counterexample_candidate,
)


class TestLogicVerifier(unittest.TestCase):

    # =========================================================================
    # 1. Normalization & Unicode Notation Tests
    # =========================================================================

    def test_normalize_unicode_implication(self):
        """Verify normalization of material implication symbols (⊃, →, ->, >>)."""
        res1 = normalize_logical_formula("A ⊃ B")
        self.assertIsNotNone(res1)
        self.assertIn("Implies(A, B)", res1)

        res2 = normalize_logical_formula("P → Q")
        self.assertIsNotNone(res2)
        self.assertIn("Implies(P, Q)", res2)

    def test_normalize_unicode_conjunction_and_disjunction(self):
        """Verify normalization of conjunction (•, ∧, &) and disjunction (∨, |)."""
        res1 = normalize_logical_formula("A • B")
        self.assertIsNotNone(res1)
        self.assertIn("A & B", res1)

        res2 = normalize_logical_formula("P ∧ Q")
        self.assertIsNotNone(res2)
        self.assertIn("P & Q", res2)

        res3 = normalize_logical_formula("A ∨ B")
        self.assertIsNotNone(res3)
        self.assertIn("A | B", res3)

    def test_normalize_unicode_negation_and_equivalence(self):
        """Verify normalization of negation (¬, ~, !) and equivalence (↔, ≡)."""
        res1 = normalize_logical_formula("¬A")
        self.assertIsNotNone(res1)
        self.assertIn("~A", res1)

        res2 = normalize_logical_formula("P ↔ Q")
        self.assertIsNotNone(res2)
        self.assertIn("Equivalent(P, Q)", res2)

        res3 = normalize_logical_formula("P ≡ Q")
        self.assertIsNotNone(res3)
        self.assertIn("Equivalent(P, Q)", res3)

    def test_normalize_nested_complex_formulas(self):
        """Verify complex MMLU formulas with mixed operators and parentheses."""
        # Problem 4 formula: (~B • E) ⊃ D
        res1 = normalize_logical_formula("(~B • E) ⊃ D")
        self.assertIsNotNone(res1)
        self.assertIn("Implies", res1)

        # De Morgan's: ¬(A ∧ B) ∨ C
        res2 = normalize_logical_formula("¬(A ∧ B) ∨ C")
        self.assertIsNotNone(res2)

        # Right-associative implication chain: A ⊃ B ⊃ C -> Implies(A, Implies(B, C))
        res3 = normalize_logical_formula("A ⊃ B ⊃ C")
        self.assertIsNotNone(res3)
        self.assertIn("Implies(A, Implies(B, C))", res3)

    def test_normalize_functional_syntax(self):
        """Verify SymPy functional syntax is supported directly."""
        res1 = normalize_logical_formula("Implies(Not(G), H)")
        self.assertIsNotNone(res1)
        self.assertIn("Implies(~G, H)", res1)

        res2 = normalize_logical_formula("And(A, Or(B, C))")
        self.assertIsNotNone(res2)
        self.assertIn("A & (B | C)", res2)

    def test_normalize_malformed_and_unsupported_inputs(self):
        """Verify malformed and unsupported inputs return None without crashing."""
        # Malformed formulas
        self.assertIsNone(normalize_logical_formula("A &"))
        self.assertIsNone(normalize_logical_formula("(A | B"))
        self.assertIsNone(normalize_logical_formula("A @ B"))
        self.assertIsNone(normalize_logical_formula(""))
        self.assertIsNone(normalize_logical_formula(None))

        # Unsupported first-order logic / natural language
        self.assertIsNone(normalize_logical_formula("∀x (Px → Qx)"))
        self.assertIsNone(normalize_logical_formula("Txy: x teaches y"))
        self.assertIsNone(normalize_logical_formula("David teaches Chris"))

    # =========================================================================
    # 2. Argument Validity Verification Tests (SymPy SAT)
    # =========================================================================

    def test_valid_argument_modus_ponens(self):
        """Modus Ponens: A ⊃ B, A ⊢ B is deductively VALID."""
        res = verify_argument_validity(premises=["A ⊃ B", "A"], conclusion="B")
        self.assertEqual(res["status"], "VALID")
        self.assertTrue(res["is_valid"])
        self.assertIsNone(res["counterexample"])

    def test_valid_argument_modus_tollens(self):
        """Modus Tollens: A ⊃ B, ~B ⊢ ~A is deductively VALID."""
        res = verify_argument_validity(premises=["A ⊃ B", "~B"], conclusion="~A")
        self.assertEqual(res["status"], "VALID")
        self.assertTrue(res["is_valid"])
        self.assertIsNone(res["counterexample"])

    def test_valid_argument_disjunctive_syllogism(self):
        """Disjunctive Syllogism: A ∨ B, ~A ⊢ B is deductively VALID."""
        res = verify_argument_validity(premises=["A ∨ B", "~A"], conclusion="B")
        self.assertEqual(res["status"], "VALID")
        self.assertTrue(res["is_valid"])
        self.assertIsNone(res["counterexample"])

    def test_valid_argument_problem_3(self):
        """Problem 3: (~G ⊃ H), ~H ⊢ G is deductively VALID."""
        res = verify_argument_validity(premises=["~G ⊃ H", "~H"], conclusion="G")
        self.assertEqual(res["status"], "VALID")
        self.assertTrue(res["is_valid"])
        self.assertIsNone(res["counterexample"])

    def test_invalid_argument_affirming_the_consequent(self):
        """Fallacy of Affirming the Consequent: A ⊃ B, B ⊢ A is INVALID."""
        res = verify_argument_validity(premises=["A ⊃ B", "B"], conclusion="A")
        self.assertEqual(res["status"], "INVALID")
        self.assertFalse(res["is_valid"])
        self.assertIsNotNone(res["counterexample"])
        # Counterexample: B=True, A=False makes A ⊃ B True, B True, and A False
        ce = res["counterexample"]
        self.assertTrue(ce.get("B"))
        self.assertFalse(ce.get("A"))

    def test_invalid_argument_denying_the_antecedent(self):
        """Fallacy of Denying the Antecedent: A ⊃ B, ~A ⊢ ~B is INVALID."""
        res = verify_argument_validity(premises=["A ⊃ B", "~A"], conclusion="~B")
        self.assertEqual(res["status"], "INVALID")
        self.assertFalse(res["is_valid"])
        self.assertIsNotNone(res["counterexample"])
        # Counterexample: A=False, B=True makes A ⊃ B True, ~A True, but ~B False
        ce = res["counterexample"]
        self.assertFalse(ce.get("A"))
        self.assertTrue(ce.get("B"))

    def test_argument_validity_unsupported_and_malformed(self):
        """Verify argument validity gracefully handles unsupported and malformed input."""
        # Empty inputs
        res_empty = verify_argument_validity(premises=[], conclusion="B")
        self.assertEqual(res_empty["status"], "NOT_APPLICABLE")

        # Unsupported natural language
        res_nl = verify_argument_validity(
            premises=["It is hard not to verify in our peers", "Because of this, it is difficult"],
            conclusion="Teaching them what their conscious knowledge contradicts"
        )
        self.assertEqual(res_nl["status"], "NOT_APPLICABLE")

        # Unsupported predicate logic
        res_pred = verify_argument_validity(premises=["Txy", "Tdc"], conclusion="Tcd")
        self.assertEqual(res_pred["status"], "NOT_APPLICABLE")

        # Malformed formula
        res_mal = verify_argument_validity(premises=["A ⊃ (B"], conclusion="C")
        self.assertEqual(res_mal["status"], "PARSE_FAILURE")

    # =========================================================================
    # 3. Counterexample Candidate Verification Tests
    # =========================================================================

    def test_verify_counterexample_candidate_genuine(self):
        """Verify genuine counterexample for Affirming Consequent (A=False, B=True)."""
        res = verify_counterexample_candidate(
            premises=["A ⊃ B", "B"],
            conclusion="A",
            assignment={"A": False, "B": True}
        )
        self.assertEqual(res["status"], "VALID_COUNTEREXAMPLE")
        self.assertTrue(res["is_counterexample"])
        self.assertTrue(res["all_premises_true"])
        self.assertTrue(res["conclusion_false"])

    def test_verify_counterexample_candidate_problem_3_fallacy(self):
        """
        Problem 3 Fallacy Check:
        Argument: (~G ⊃ H), ~H ⊢ G
        Choice 2 Proposed: Invalid with counterexample G is True and H is False.
        Under this assignment, Conclusion G is TRUE, so it CANNOT be a counterexample!
        """
        res = verify_counterexample_candidate(
            premises=["~G ⊃ H", "~H"],
            conclusion="G",
            assignment={"G": True, "H": False}
        )
        self.assertEqual(res["status"], "NOT_A_COUNTEREXAMPLE")
        self.assertFalse(res["is_counterexample"])
        self.assertFalse(res["conclusion_false"])
        self.assertTrue(res["conclusion_evaluation"])  # Conclusion is True!
        self.assertIn("Conclusion evaluated to True", res["reason"])

    def test_verify_counterexample_candidate_premise_false(self):
        """If premises are not all true, the assignment cannot be a counterexample."""
        res = verify_counterexample_candidate(
            premises=["A • B"],
            conclusion="C",
            assignment={"A": True, "B": False, "C": False}
        )
        self.assertEqual(res["status"], "NOT_A_COUNTEREXAMPLE")
        self.assertFalse(res["is_counterexample"])
        self.assertFalse(res["all_premises_true"])
        self.assertIn("Premise(s) evaluated to False", res["reason"])

    def test_verify_counterexample_candidate_string_and_malformed(self):
        """Verify candidate check handles string booleans and malformed assignments."""
        # String booleans
        res_str = verify_counterexample_candidate(
            premises=["A ⊃ B", "B"],
            conclusion="A",
            assignment="{'A': 'False', 'B': 'True'}"
        )
        self.assertEqual(res_str["status"], "VALID_COUNTEREXAMPLE")
        self.assertTrue(res_str["is_counterexample"])

        # Malformed assignment string
        res_bad = verify_counterexample_candidate(
            premises=["A ⊃ B"],
            conclusion="B",
            assignment="not a dict"
        )
        self.assertEqual(res_bad["status"], "PARSE_FAILURE")


if __name__ == "__main__":
    unittest.main()

