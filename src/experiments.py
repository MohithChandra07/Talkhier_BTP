import configparser
import argparse
import shutil, os
import ast
import atexit

from functools import partial
import time
import threading

from result_manager import ResultManager
import multiagent.agent_team as agent_team
from multiagent.llm import LLM
import prompts.mmlu as MMLUPrompt



def mmlu(problem, prompt, config):
    choice_info = ""
    for i, x in enumerate(problem['choices']):
        choice_info += f"{i}) {x}, "
    choice_info = choice_info[:-2]

    react_generator = agent_team.ReactAgent(intermediate_output_desc=prompt["intermediate_output_desc"], config=config, llm=LLM(config).llm)
    team = agent_team.buildTeam(prompt["team"], react_generator, prompt["intermediate_output_desc"], prompt["int_out_format"])

    from langchain_core.messages import HumanMessage

    iterations = 0
    while iterations < 3:
        try:
            output = team(
                state={
                    "history": {
                        "Default Supervisor": [HumanMessage(content=prompt["team"]["prompt"])],
                        "all": [HumanMessage(content=prompt["team"]["prompt"])],
                    },
                    "intermediate_output": {},
                },
                config={"recursion_limit": int(config["LLM"]["max_attempts"])},
            )
            break
        except Exception as e:
            iterations += 1
            print(
                f"Experiment attempt {iterations}/3 failed: "
                f"{type(e).__name__}: {e}",
                flush=True,
            )
            if iterations >= 3:
                raise
            print("Retrying...", flush=True)


    if isinstance(output, list):
        output, output_int = output[0]["intermediate_output"], output[1]
    else:
        print(output)
        output = ast.literal_eval(output["messages"][-1].content)

    choice = -1
    if "choice" in output:
        choice = output["choice"]
    elif "choice" in output["answer"]:
        choice = output["answer"]["choice"]
    
    choice2 = -1
    if output_int is not None and output_int != {}:
        if "choice" in output_int:
            choice2 = output_int["choice"]
        elif "choice" in output_int["answer"]:
            choice2 = output_int["answer"]["choice"] 
    
    return choice, choice2





def runExperimentMMLU(file_path, domain, config, start_id=0, end_id=-1):
    
    from datasets import load_dataset
    dataset = load_dataset("cais/mmlu", domain)
    results = ResultManager(file_path, columns=["Problem ID", "Answer", "Correct Answer", "Pre-Revision"])

    total = len(dataset["test"])
    actual_end = total if end_id == -1 else min(end_id, total)
    print(f"Running {domain} from index {start_id} to {actual_end} (total {actual_end - start_id} problems)...")

    for problem_id in range(start_id, actual_end):
        runSingleMMLU(domain, config, problem_id, results=results)



def runSingleMMLU(domain, config, problem_id, results=None):
    from datasets import load_dataset
    dataset = load_dataset("cais/mmlu", domain)
    problem = dataset["test"][problem_id]

    if results is not None:
        placeholder = [problem_id, '-', '-', '-']
        if results.is_present(placeholder):
            print(f"Problem {problem_id} already completed, skipping.")
            return
        def remove_checkpoint():
            results.remove(placeholder)

        results.add(placeholder)
        atexit.register(remove_checkpoint)

    t0 = time.time()
    output = mmlu(problem, MMLUPrompt.getPrompts(domain, problem), config)
    elapsed = time.time() - t0
    print(f"Problem {problem_id} finished in {elapsed:.2f}s")
    print("Agent Answer:", output[0])
    print("Agent Answer before Revision:", output[1])
    print("Actual Answer:", problem["answer"])

    if results is not None:
        results.replace(placeholder, [problem_id, output[0], problem["answer"], output[1]])
        atexit.unregister(remove_checkpoint)






def runParallel(function, threads):
    thread_list = []

    for i in range(threads):
        print("Starting thread:", i)
        t = threading.Thread(target=function)
        t.start()
        thread_list.append(t)
        time.sleep(1)

    for t in thread_list:
        t.join()







def loadConfig(path, path2):
    config = configparser.ConfigParser()
    config.read(path, encoding='utf-8')

    cconfig = configparser.ConfigParser()
    cconfig.read(path2, encoding='utf-8')

    for section in cconfig.sections():
        if not config.has_section(section):
            config.add_section(section)
        for key, value in cconfig.items(section):
            config.set(section, key, value)

    return config

def getArgs():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    default_cfg = os.path.abspath(os.path.join(base_dir, "..", "config", "config.ini"))
    default_lcfg = os.path.abspath(os.path.join(base_dir, "..", "config", "config_llm.ini"))

    parser = argparse.ArgumentParser(description="Talk Structurally, Act Hierarchically (TalkHier): A Collaborative Framework for LLM Multi-Agent Systems")
    parser.add_argument('--config', '-cfg',
                        type=str,
                        default=default_cfg,
                        help="Path to config file.")
    parser.add_argument('--llm-config', '-lcfg', 
                        type=str, 
                        default=default_lcfg,
                        help="Path to LLM config file.")
    parser.add_argument('--mode', '-m', 
                        type=str, 
                        choices=["camera", "moral_scenarios", "college_physics", "machine_learning", "formal_logic", "us_foreign_policy", "wiki_qa"], 
                        default="camera",
                        help="Type of dataset to experiment on.")
    parser.add_argument('--problem-id', '-pi',
                        type=int,
                        default=-1,
                        help="Specific problem to execute; -1 for experiments on entire dataset.")
    parser.add_argument('--start-id', '-si',
                        type=int,
                        default=0,
                        help="Start index for problem range.")
    parser.add_argument('--end-id', '-ei',
                        type=int,
                        default=-1,
                        help="End index (exclusive) for problem range; -1 for entire dataset.")
    parser.add_argument('--thread-count', '-tc', 
                        type=int, 
                        default=1,
                        help="Number of experiments to run in parallel.")
    parser.add_argument('--vanilla', '-v', 
                        action="store_true",
                        help="Option to run with unmodified GPT.")
    parser.add_argument('--legacy',
                        action="store_true",
                        default=False,
                        help="Run legacy un-stabilized TalkHier baseline.")
    parser.add_argument('--out-name',
                        type=str,
                        default=None,
                        help="Custom output CSV filename prefix.")

    return parser.parse_args()




if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    args = getArgs()

    if not os.path.exists(args.llm_config):
        shutil.copy("../template/config_llm.ini", args.llm_config)
        print("Initialized config file.")
        print("Please write down the keys into:", args.llm_config)
        exit()

    if not os.path.exists(args.config):
        shutil.copy("../template/config.ini", args.config)

    config = loadConfig(args.config, args.llm_config)
    if "STABILIZATION" not in config:
        config.add_section("STABILIZATION")
    config["STABILIZATION"]["enabled"] = "false" if args.legacy else "true"

    mmlu_list = ["moral_scenarios", "college_physics", "machine_learning", "formal_logic", "us_foreign_policy"]
    if args.out_name:
        prefix = args.out_name
    elif args.legacy:
        prefix = "baseline_qwen3.csv"
    else:
        prefix = "stabilized_qwen3.csv"

    results_dir = os.path.abspath(os.path.join(base_dir, "..", "results", args.mode))
    os.makedirs(results_dir, exist_ok=True)
    out_csv = os.path.join(results_dir, prefix)

    if args.problem_id != -1:
        if args.mode in mmlu_list:
            results = ResultManager(out_csv, columns=["Problem ID", "Answer", "Correct Answer", "Pre-Revision"])
            runSingleMMLU(args.mode, config, args.problem_id, results=results)
    else:
        if args.mode in mmlu_list:
            runParallel(partial(runExperimentMMLU, out_csv, args.mode, config, start_id=args.start_id, end_id=args.end_id), args.thread_count)