import unittest
import sys
import os

# Add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))
from multiagent.agent_team import extract_evaluator_score, parse_intermediate_output


class TestEvaluatorScoring(unittest.TestCase):

    def test_never_default_malformed_to_ten(self):
        """Verify that malformed or missing scores NEVER default to 10."""
        # 1. Missing evaluation key
        score, status, reason = extract_evaluator_score({"answer": {"choice": 0}})
        self.assertIsNone(score)
        self.assertEqual(status, "NO_EVALUATION")

        # 2. Non-dict intermediate output
        score, status, reason = extract_evaluator_score("not a dict")
        self.assertIsNone(score)
        self.assertEqual(status, "INVALID_STRUCTURE")

        # 3. Malformed score string (e.g., text instead of number)
        malformed = {
            "answer": {"choice": 0},
            "evaluation": {
                "Truth Table": {
                    "Correctness Score": "unclear/bad",
                    "Reason": "Invalid proposition",
                }
            },
        }
        score, status, reason = extract_evaluator_score(malformed, "Truth Table")
        self.assertIsNone(score)
        self.assertEqual(status, "MALFORMED_SCORE")

        # 4. Out of range score
        out_of_range = {
            "answer": {"choice": 0},
            "evaluation": {
                "Truth Table": {
                    "Correctness Score": 15,
                    "Reason": "Way too high",
                }
            },
        }
        score, status, reason = extract_evaluator_score(out_of_range, "Truth Table")
        self.assertIsNone(score)
        self.assertEqual(status, "OUT_OF_RANGE")

    def test_valid_evaluator_score_parsing(self):
        """Verify correct parsing of valid integer and fractional scores."""
        # Int 10
        data1 = {
            "evaluation": {
                "Formal Logic": {
                    "Correctness Score": 10,
                    "Reason": "Translation matches",
                }
            }
        }
        score, status, reason = extract_evaluator_score(data1, "Formal Logic")
        self.assertEqual(score, 10)
        self.assertEqual(status, "OK")

        # String fraction "8/10"
        data2 = {
            "evaluation": {
                "Logical Argument": {
                    "Correctness Score": "8/10",
                    "Reason": "Minor flaw in premise 2",
                }
            }
        }
        score, status, reason = extract_evaluator_score(data2, "Logical Argument")
        self.assertEqual(score, 8)
        self.assertEqual(status, "OK")

        # Low score
        data3 = {
            "evaluation": {
                "Counterexample": {
                    "Correctness Score": 2,
                    "Reason": "Counterexample found",
                }
            }
        }
        score, status, reason = extract_evaluator_score(data3)
        self.assertEqual(score, 2)
        self.assertEqual(status, "OK")


if __name__ == "__main__":
    unittest.main()

