import sys
sys.path.append("../")

from langchain_openai import AzureChatOpenAI
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from langgraph.graph import END, StateGraph, START


from pydantic import BaseModel, Field, field_validator
from typing import Annotated, Literal, Sequence, Dict, Any
from typing_extensions import TypedDict
import operator
import ast
import traceback
import functools

from multiagent.react_agent import create_react_agent
import multiagent.tools as tools
import multiagent.colors as colors
import json

def parse_intermediate_output(val, fallback):
    if isinstance(val, dict):
        return val if val != {} else fallback
    if not isinstance(val, str):
        return fallback

    s = val.strip()
    if s in ["", "{}", "{{}}"]:
        return fallback
    if "</think>" in s:
        s = s.split("</think>")[-1].strip()
    if s.startswith("```"):
        lines = s.splitlines()
        if len(lines) >= 2 and lines[0].startswith("```"):
            s = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:]).strip()

    for parser in (json.loads, ast.literal_eval):
        try:
            res = parser(s)
            if isinstance(res, dict):
                return res if res != {} else fallback
        except Exception:
            pass

    start = s.find('{')
    end = s.rfind('}')
    if start != -1 and end != -1 and end > start:
        sub = s[start:end+1]
        for parser in (json.loads, ast.literal_eval):
            try:
                res = parser(sub)
                if isinstance(res, dict):
                    return res if res != {} else fallback
            except Exception:
                pass

    print("Could not parse intermediate output:", s[:100] if len(s) > 100 else s)
    return fallback

def extract_evaluator_score(intermediate_output, evaluator_name=None):
    """
    Extracts and validates an evaluator correctness score from intermediate_output.
    Returns: (score: Optional[int], status: str, reason: str)
    NEVER defaults a malformed or missing score to 10.
    """
    if not isinstance(intermediate_output, dict):
        return None, "INVALID_STRUCTURE", "intermediate_output is not a dictionary"

    evaluation = intermediate_output.get("evaluation")
    target_dict = None

    if isinstance(evaluation, dict):
        if evaluator_name and evaluator_name in evaluation:
            target_dict = evaluation[evaluator_name]
        elif evaluator_name:
            for k, v in evaluation.items():
                if isinstance(v, dict) and (evaluator_name.lower() in k.lower() or k.lower() in evaluator_name.lower()):
                    target_dict = v
                    break
        if target_dict is None:
            for k, v in evaluation.items():
                if isinstance(v, dict) and "Correctness Score" in v:
                    target_dict = v
                    break
    elif "Correctness Score" in intermediate_output:
        target_dict = intermediate_output
    else:
        return None, "NO_EVALUATION", "No 'evaluation' object in intermediate_output"

    if not isinstance(target_dict, dict):
        return None, "EVALUATOR_NOT_FOUND", f"Evaluator {evaluator_name or 'any'} not found in evaluation"

    raw_score = target_dict.get("Correctness Score")
    reason = str(target_dict.get("Reason", ""))

    if raw_score is None:
        return None, "MISSING_SCORE", "No 'Correctness Score' field found"

    try:
        if isinstance(raw_score, str):
            clean = raw_score.strip().split("/")[0].strip()
            score = int(float(clean))
        else:
            score = int(raw_score)

        if 0 <= score <= 10:
            return score, "OK", reason
        else:
            return None, "OUT_OF_RANGE", f"Score {score} not in range [0, 10]"
    except Exception as e:
        return None, "MALFORMED_SCORE", f"Cannot parse score {raw_score!r}: {e}"


class AgentTeam():

    def __init__(self, config, llm, member_list=[], member_names=[], member_info=[], team_name="Default", supervisor_name="FINISH",
                 intermediate_output_desc="", final_output_form="", fullshared_memory=False):
        self.config = config
        self.llm = llm
        self.graph = None

        self.member_list = member_list
        self.member_info = member_info
        self.member_names = member_names
        self.team_name = team_name
        self.sup_name = supervisor_name
        
        self.intermediate_output_desc = intermediate_output_desc
        self.final_output_form = final_output_form
        self.fullshared_memory = fullshared_memory

        self.message_prompt = f"If the next agent is one of {", ".join(member_names)}, give detailed instructions and requests. If {supervisor_name}, report a summary of all results."
        self.thought_prompt = "Output a detailed analysis on the most recent message. In detail, state what you think should be done next, and who you should contact next."
    


    def loadSuperviser(self, additional_prompt=""):
        options = [self.sup_name] + self.member_names
        job_list = "\n".join([mem + ": " + pr for mem, pr in zip(self.member_names, self.member_info)])
        prompt_list = [
                ("system",
                 "You are a supervisor tasked with managing a conversation between the following workers: {members}. "
                 "Given the following messages, respond with the worker to act next."
                 "Each worker will perform a task and respond with their results and status."
                 "\nJoblist: \n{joblist}"),
                
                ("system", "The current background is: {background}"),
                
                ("system", "Conversation History:"),
                
                MessagesPlaceholder(variable_name="messages", n_messages=20),
                
                ("system",
                 "Given the conversation above, output the following in this exact order:\n"
                 "1. 'thoughts': {thought_prompt}\n"
                 "2. 'messages': {message_prompt}\n"
                 "3. Who should act next? Select one of: {options} and output as 'next'."
                 " When you have determined that the final output is gained, report back with {finish} as 'next'.\n"
                 "4. The detailed background of the problem you are trying to solve (given in the first message) as 'background'.\n"
                 "5. The intermediate outputs to give as 'intermediate_output'.\n"
                 "" + additional_prompt + ""
                 "{error}"),
            ]
        if self.team_name == "Default":
            prompt_list.pop(1)
        
        prompt = ChatPromptTemplate.from_messages(prompt_list).partial(options=str(options), members=", ".join(self.member_names), joblist=job_list,\
                  finish=self.sup_name, sup_name=self.team_name + " Supervisor",\
                  thought_prompt=self.thought_prompt, message_prompt=self.message_prompt)



        class routeResponse(BaseModel):
            thoughts: str = Field(description=self.thought_prompt)
            next: Literal[*options] # type: ignore
            messages: str = Field(description=self.message_prompt)
            intermediate_output: str = Field(description=self.intermediate_output_desc)
            background: str
                
            @field_validator('messages', 'intermediate_output', mode="before")
            def cast_to_string(cls, v):
                return str(v)
            
        
        def supervisor_agent(state):
            prev_history = state["history"]

            if self.fullshared_memory:
                state["messages"] = list(state["history"]["all"])
            else:
                state["messages"] = list(state["history"][self.team_name + " Supervisor"])

            state["error"] = ""
            state["messages"] = state["messages"][-15:]
            state["history"] = {}

            # If this is the main team, there is no background.
            if self.team_name == "Default":
                state["background"] = ""
            else:
                state["background"] = state["background"].content

            supervisor_chain = prompt | self.llm.with_structured_output(routeResponse)

            result = None
            last_error = None

            for attempt in range(3):
                try:
                    result = supervisor_chain.invoke(state)
                    if result is not None:
                        break
                    last_error = ValueError("Supervisor structured output returned None")
                    print(f"Supervisor attempt {attempt + 1}/3 failed: {last_error}", flush=True)
                except Exception as e:
                    last_error = e
                    print(f"Supervisor attempt {attempt + 1}/3 failed: {type(e).__name__}: {e}", flush=True)
                state['error'] = f"Previous output failed: {type(last_error).__name__}: {last_error}."

            if result is None:
                raise RuntimeError(
                    f"Supervisor failed after 3 attempts. Last error: {last_error}"
                ) from last_error

            new_msg = AIMessage(content=result.messages, name=self.team_name + "_Supervisor")
            if not ("Intermediate Output" in new_msg.content or "Final Output" in new_msg.content):
                if result.intermediate_output in ["", "{{}}"]:
                    result.intermediate_output = state["intermediate_output"]
                if not str(result.intermediate_output) in new_msg.content:
                    new_msg.content = new_msg.content + "\n\nFinal Output: " + str(result.intermediate_output)

            result.intermediate_output = parse_intermediate_output(result.intermediate_output, state["intermediate_output"])
            
            if self.fullshared_memory:
                new_history = {
                        **prev_history,
                        self.team_name + " Supervisor": prev_history.get(self.team_name + " Supervisor", []) + [new_msg.model_copy()],
                        result.next: prev_history.get(result.next, []) + [new_msg.model_copy()],
                        "all": prev_history.get("all", []) + [new_msg.model_copy()]
                    }
            else:
                new_history = {
                        **prev_history,
                        self.team_name + " Supervisor": prev_history.get(self.team_name + " Supervisor", []) + [new_msg.model_copy()],
                        result.next: prev_history.get(result.next, []) + [new_msg.model_copy()]
                    }
            
            new_history[self.team_name + " Supervisor"][-1].content = "{Thoughts: " + result.thoughts + "}\n\n" + new_history[self.team_name + " Supervisor"][-1].content
                    

            return {
                "intermediate_output": result.intermediate_output,
                "messages": new_msg,
                "background": AIMessage(content=result.background, name=self.team_name + " Supervisor"),
                "next": result.next,
                "history": new_history
            }
        

        return supervisor_agent
    

    def createStateGraph(self, additional_prompt=""):
            class AgentState(TypedDict):
                # history: Annotated[Sequence[BaseMessage], operator.add]
                history: Dict[str, Annotated[Sequence[BaseMessage], operator.add]]
                messages: BaseMessage
                background: BaseMessage
                # pyrefly: ignore [bad-class-definition]
                intermediate_output: Dict[str, Any] = Field(description=self.intermediate_output_desc)
                next: str
                initial_prompt: BaseMessage

            if self.llm is None:
                self.loadLLM()
            workflow = StateGraph(AgentState)

            for member, member_name in zip(self.member_list, self.member_names):
                workflow.add_node(member_name, member)
            
            workflow.add_node(self.team_name + " Supervisor", self.loadSuperviser(additional_prompt=additional_prompt))
            for member in self.member_names:
                workflow.add_edge(member, self.team_name + " Supervisor")
            
            
            
            conditional_map = {k: k for k in self.member_names}
            conditional_map[self.sup_name] = END
            workflow.add_conditional_edges(self.team_name + " Supervisor", lambda x: x["next"], conditional_map)
            # Finally, add entrypoint
            workflow.add_edge(START, self.team_name + " Supervisor")

            self.graph = workflow.compile(debug = False)
            return functools.partial(AgentTeam.prompt, graph=self.graph, team_name=self.team_name, sup_name=self.sup_name if self.sup_name != "FINISH" else "", fullshared_memory=self.fullshared_memory)


    def prompt(state, config, graph, team_name, sup_name, fullshared_memory):
        int_output = {}
        revision_history = []
        executed_agents = []
        color_assign = colors.TerminalColor()
        prev_len = len(state["history"][team_name + " Supervisor"])

        if "initial_prompt" in state:
            prev_initial_prompt = state["initial_prompt"]
            if not fullshared_memory:
                last_msg = state["history"][team_name + " Supervisor"][-1]
                p_name = last_msg.name or "Supervisor"
                p_content = last_msg.content or ""
                state["initial_prompt"] = f"Prompter: {p_name}\n{p_content}"
        else:
            prev_initial_prompt = state["history"][team_name + " Supervisor"][-1].content
            state["initial_prompt"] = prev_initial_prompt

        for s in graph.stream(
            state, config
        ):
            if "__end__" not in s:
                key = list(s.keys())[0]
                executed_agents.append(key)
                if key in ['history', 'messages', 'background', 'intermediate_output', 'next']:
                    result = s
                    try:
                        key = result['background'].name
                    except Exception as e:
                        print(e)
                        print(s["background"])
                        assert "Background error"
                    if prev_len == len(result["history"][team_name + " Supervisor"]):
                        continue
                else:
                    result = s[key]

                cur_io = result.get("intermediate_output", {})
                if isinstance(cur_io, dict) and cur_io != {}:
                    choice_val = None
                    if "choice" in cur_io:
                        choice_val = cur_io["choice"]
                    elif "choice" in cur_io.get("answer", {}):
                        choice_val = cur_io["answer"]["choice"]

                    if int_output == {}:
                        int_output = cur_io

                    if choice_val is not None:
                        revision_history.append({
                            "agent": key,
                            "choice": choice_val,
                            "intermediate_output": cur_io,
                        })

                print("Agent:", color_assign.colorText(key + f" ({len(result['history'][key])})", key))
                if key == team_name + " Supervisor":
                    print("Messages:")
                    print(color_assign.colorText(result["history"][key][-1].pretty_repr(), key))
                    print()

                if result["next"] != sup_name:
                    print("Background:")
                    print(color_assign.colorText(str(result["background"].content), key))
                    print()
                    if key != result["next"]:
                        print(color_assign.colorText(key, key), "->", color_assign.colorText(result["next"], result["next"]))
                    else:
                        print(color_assign.colorText(key, key), "->", color_assign.colorText(team_name + " Supervisor", team_name + " Supervisor"))
                    print()
        # print(s)
        state["initial_prompt"] = prev_initial_prompt
        result["_executed_agents"] = executed_agents
        if sup_name == "":
            result["_revision_history"] = revision_history
            result["_initial_intermediate_output"] = int_output
            result["_executed_agents"] = executed_agents
            return [result, int_output]
        return result
    


class ReactAgent():

    def __init__(self, config, intermediate_output_desc="", llm=None, key_type="GPT4", fullshared_memory=False):
        self.intermediate_output_desc = intermediate_output_desc
        self.config = config
        self.llm = llm

        self.key_type = key_type
        self.fullshared_memory = fullshared_memory

    def responseFormatter(result) -> dict:
        return {
                "intermediate_output": result.intermediate_output
            }


    def loadMember(self, name, sel_tools, member_prompt, sup_name):
        agent_tools = tools.getTools(sel_tools, self.config)


        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", member_prompt),
                ("system", "Background: {background}"),
                # ("system", "Incoming Instructions:\n{initial_prompt}"),
                ("system", "Conversation History:"),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        class routeResponse(BaseModel):
            intermediate_output: str = Field(description=self.intermediate_output_desc)
                
            @field_validator('intermediate_output', mode="before")
            def cast_to_string(cls, v):
                return str(v)

        agent = create_react_agent(self.llm, tools=agent_tools, debug=False, state_modifier=prompt, response_schema=routeResponse, \
                                   response_format=ReactAgent.responseFormatter)
        return functools.partial(ReactAgent.agent_node, agent=agent, name=name, sup_name=sup_name, fullshared_memory=self.fullshared_memory)
    
    
    
    def agent_node(state, agent, name, sup_name="", fullshared_memory=False):
        color_assign = colors.TerminalColor()

        if fullshared_memory:
            state["messages"] = state.get("history", {}).get("all", [])[-15:]
        else:
            if name in state.get("history", {}):
                state["messages"] = state["history"][name][-15:]
            elif "all" in state.get("history", {}):
                state["messages"] = state["history"]["all"][-15:]
            else:
                default_prompt = state.get("initial_prompt", "")
                p_text = default_prompt if isinstance(default_prompt, str) else getattr(default_prompt, "content", "")
                state["messages"] = [HumanMessage(content=p_text or "Execute task", name="Prompter")]
        prev_history = dict(state.get("history", {}))
        if name not in prev_history:
            prev_history[name] = list(state["messages"])
        state["history"] = {}

        prev_initial_prompt = state["initial_prompt"]
        
        if not fullshared_memory:
            last_hist = prev_history[name][-1]
            p_name = last_hist.name or "Prompter"
            p_content = last_hist.content or ""
            state["initial_prompt"] = f"Prompter: {p_name}\n{p_content}"

        prev_len = len(state["messages"])
        result = dict(state)

        for step in agent.stream(state, {}, stream_mode="values"):
            if "__end__" not in step:
                msgs = step.get("messages", [])
                if len(msgs) != prev_len:
                    resp = msgs[-1]
                    if isinstance(resp, ToolMessage) and resp.name == "output_tool":
                        continue
                    try:
                        print("Agent:", color_assign.colorText(name + f' ({len(msgs)})', name))
                    except Exception as e:
                        print(e)
                        print(step)
                    print(color_assign.colorText(resp.pretty_repr(), name))
                    print()
                    prev_len = len(msgs)
                result = step

        msgs = result.get("messages", [])
        last_msg_content = msgs[-1].content if msgs else ""
        new_msg = AIMessage(content=last_msg_content, name=name.replace(" ", "_"))

        int_out_str = str(result.get("intermediate_output", ""))
        if not "Final Output" in new_msg.content and int_out_str and not int_out_str in new_msg.content:
            new_msg.content = new_msg.content + "\n\nFinal Output: " + int_out_str

        if fullshared_memory:
            result["history"] = {
                                    **prev_history,  # Keep the existing history
                                    sup_name: prev_history.get(sup_name, []) + [new_msg],
                                    name: prev_history.get(name, []) + [new_msg],
                                    "all": prev_history.get("all", []) + [new_msg]
                                }
        else:
            result["history"] = {
                                    **prev_history,  # Keep the existing history
                                    sup_name: prev_history.get(sup_name, []) + [new_msg],
                                    name: prev_history.get(name, []) + [new_msg]
                                }
            
        result["messages"] = new_msg
        result["next"] = state.get("next", "")

        if "background" in result and hasattr(result["background"], "name"):
            result["background"].name = name
        result["initial_prompt"] = prev_initial_prompt

        raw_io = result.get("intermediate_output", "")
        parsed_out = parse_intermediate_output(raw_io, None)
        if parsed_out is None and hasattr(new_msg, "content"):
            parsed_out = parse_intermediate_output(new_msg.content, None)
        result["intermediate_output"] = parsed_out if parsed_out is not None else state.get("intermediate_output", {})

        return result





def buildTeam(team_information, react_generator, intermediate_output_desc, int_out_format):
    team_list = []
    member_info = []
    member_names = []

    for key in team_information.keys():
        if isinstance(team_information[key], dict):
            if "team" in team_information[key]:
                team_list.append(buildTeam(team_information[key], react_generator, intermediate_output_desc, int_out_format))
                member_names.append(team_information[key]["team"] + " Supervisor")
                member_info.append(team_information[key]["prompt"])
            else:
                team_list.append(react_generator.loadMember(key, team_information[key]["tools"], team_information[key]["prompt"], team_information["team"] + " Supervisor"))
                member_names.append(key)
                member_info.append(team_information[key]["prompt"])

    agent_team = AgentTeam(None, member_list=team_list, member_info=member_info, member_names=member_names, llm=react_generator.llm, \
                            intermediate_output_desc=intermediate_output_desc, final_output_form=int_out_format, team_name=team_information["team"], supervisor_name=team_information["return"])\
                                .createStateGraph(additional_prompt=team_information["additional_prompt"])
    return agent_team
