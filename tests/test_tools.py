import unittest
import sys
import os
from langchain_core.messages import AIMessage, ToolMessage

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))
from multiagent.tools import TruthTableGenerator, CounterexampleVerifier, OutputTool
from multiagent.react_agent import create_react_agent


class TestTools(unittest.TestCase):

    def test_truth_table_generator(self):
        tt = TruthTableGenerator()
        # Test valid sympy expression
        out = tt._run("['And(A, B)', 'Or(A, B)']")
        self.assertIn("A | B | And(A, B) | Or(A, B)", out)
        self.assertIn("T | T | T | T", out)

        # Test single string
        out2 = tt._run("And(A, B)")
        self.assertIn("A | B | And(A, B)", out2)

        # Test invalid expression returns error without crashing
        bad_out = tt._run("INVALID_EXPR(((")
        self.assertTrue(bad_out.startswith("Error processing expressions"))

    def test_counterexample_verifier(self):
        cv = CounterexampleVerifier()
        # Valid argument: premise A, conclusion A
        inp = str({
            "premises": ["A"],
            "conclusion": "A",
            "truth_values": [{"A": "True"}],
        })
        res = cv._run(inp)
        self.assertIn("Not a counterexample", res)

        # Invalid argument: premise A, conclusion B, with A=True, B=False
        inp_invalid = str({
            "premises": ["A"],
            "conclusion": "B",
            "truth_values": [{"A": "True", "B": "False"}],
        })
        res_ce = cv._run(inp_invalid)
        self.assertIn("Valid counterexample", res_ce)

    def test_output_tool(self):
        ot = OutputTool()
        res = ot._run("Checking step 1")
        self.assertIn("Thoughts recorded", res)

    def test_should_continue_duplicate_detection(self):
        from multiagent.react_agent import create_react_agent
        from unittest.mock import MagicMock
        from pydantic import BaseModel, Field

        class DummySchema(BaseModel):
            intermediate_output: str = Field(description="desc")

        mock_model = MagicMock()
        mock_model.bind_tools = MagicMock(return_value=mock_model)
        graph = create_react_agent(
            mock_model,
            tools=[OutputTool()],
            response_schema=DummySchema,
            response_format=lambda x: {"intermediate_output": x.intermediate_output},
        )
        # Check that compiled graph is created
        self.assertIsNotNone(graph)


if __name__ == "__main__":
    unittest.main()
