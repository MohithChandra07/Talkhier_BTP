import unittest
import sys
import os
from langchain_core.messages import AIMessage, HumanMessage

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))
from multiagent.agent_team import AgentTeam, ReactAgent


class TestAgentNode(unittest.TestCase):

    def test_prompter_name_none_does_not_crash(self):
        """Verify that a message with name=None does not cause TypeError in agent_node."""
        state = {
            "history": {
                "TestAgent": [
                    HumanMessage(content="Hello world", name=None)
                ]
            },
            "initial_prompt": "init",
            "messages": [],
            "background": AIMessage(content="bg"),
            "intermediate_output": {"answer": {"choice": 1}},
            "next": "TestAgent",
        }

        class MockAgent:
            def stream(self, state, config, stream_mode=None):
                yield {"messages": [AIMessage(content="Done", name="TestAgent")]}

        # Should execute without TypeError: can only concatenate str (not 'NoneType')
        result = ReactAgent.agent_node(
            state, MockAgent(), "TestAgent", sup_name="Supervisor", fullshared_memory=False
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["initial_prompt"], "init")
        self.assertEqual(result["intermediate_output"]["answer"]["choice"], 1)


if __name__ == "__main__":
    unittest.main()
