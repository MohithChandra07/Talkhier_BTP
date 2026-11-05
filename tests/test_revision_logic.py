import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))
from multiagent.agent_team import parse_intermediate_output


class TestRevisionLogic(unittest.TestCase):

    def test_parse_intermediate_output_formats(self):
        fallback = {"answer": {"choice": 0, "Reason": "fallback"}}

        # Clean JSON
        raw_json = '{"answer": {"choice": 2, "Reason": "valid"}}'
        res = parse_intermediate_output(raw_json, fallback)
        self.assertEqual(res["answer"]["choice"], 2)

        # Markdown wrapped codeblock
        raw_md = '```json\n{"answer": {"choice": 3}}\n```'
        res = parse_intermediate_output(raw_md, fallback)
        self.assertEqual(res["answer"]["choice"], 3)

        # Think tag preceded
        raw_think = '<think>I should select 1.</think>\n{"answer": {"choice": 1}}'
        res = parse_intermediate_output(raw_think, fallback)
        self.assertEqual(res["answer"]["choice"], 1)

        # Python single-quoted dict
        raw_py = "{'answer': {'choice': 0}}"
        res = parse_intermediate_output(raw_py, fallback)
        self.assertEqual(res["answer"]["choice"], 0)

        # Malformed / unparseable output falls back to fallback
        raw_bad = "I think the answer is 2 because..."
        res = parse_intermediate_output(raw_bad, fallback)
        self.assertEqual(res, fallback)

    def test_empty_or_whitespace_output_preserves_fallback(self):
        fallback = {"answer": {"choice": 1}}
        self.assertEqual(parse_intermediate_output("", fallback), fallback)
        self.assertEqual(parse_intermediate_output("   ", fallback), fallback)
        self.assertEqual(parse_intermediate_output("{}", fallback), fallback)
        self.assertEqual(parse_intermediate_output("{{}}", fallback), fallback)
        self.assertEqual(parse_intermediate_output(None, fallback), fallback)

    def test_get_prompts_formal_logic(self):
        import prompts.mmlu as MMLUPrompt
        dummy_problem = {
            "question": "What is A -> B?",
            "choices": ["Option 1", "Option 2"],
            "answer": 0,
        }
        prompt = MMLUPrompt.getPrompts("formal_logic", dummy_problem)
        self.assertIn("team", prompt)
        self.assertIn("at least 3 of the 5 evaluations support each answer", prompt["team"]["Revisor"]["prompt"])


if __name__ == "__main__":
    unittest.main()
