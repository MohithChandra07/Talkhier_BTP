# TalkHier BTP — Setup, Verification & Run Commands

This submission contains the complete codebase, automated test suite, empirical evaluations, and frozen dataset manifests for:

> **Reliability-Calibrated, Bias-Robust, and RL-Adaptive Hierarchical Reasoning for LLM Multi-Agent Systems**

---

## 1. Environment Setup (Python 3.10+ / macOS / Linux / Windows)

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements-core.txt
```

---

## 2. Offline Verification (No LLM / API Key Required)

### A. Run the Full Test Suite (81 Passing Tests)
```bash
pytest tests/ -v
```
Validates:
- `tests/test_reliability_framework.py`: Platt scaling, ECE/Brier scores, Isotonic regression, pairwise correlation $\Sigma = [\rho_{ij}]$, redundancy discounting, order-robust set aggregation (0% flip rate), LinUCB RL policy, and wrong-majority resilience.
- `tests/test_datasets_loader.py`: Loaders and frozen manifest integrity across all 5 datasets (MMLU 5 domains, WikiQA, CAMERA, GSM8K, MATH).
- `tests/test_logic_verifier.py`, `tests/test_graph_dispatch_sprint4.py`, `tests/test_graph_dispatch_opt.py`, `tests/test_graph_dispatch.py`, `tests/test_controlled_dispatch.py`, `tests/test_evaluator_scoring.py`, `tests/test_revision_logic.py`, `tests/test_tools.py`, `tests/test_agent_node.py`.

### B. Run Empirical Reliability, Correlation, Permutation & RL Evaluation
```bash
PYTHONPATH=src python3 src/run_reliability_evaluation.py
```
Outputs:
1. **Platt Calibration Curves**: ECE reduction by up to 94.1% across the 5 evaluators.
2. **Empirical Pairwise Correlation Matrix $\Sigma$**: Identifies co-hallucination dependencies ($\rho = 0.66$ between Logical Argument & Predicate Logic).
3. **Permutation Stress Test (700 trials)**: 0.00% flip rate with Order-Robust Aggregator vs 5.29% flip rate on baseline.
4. **RL Policy vs Fixed Threshold**: Dynamic `ACCEPT`, `REVISE`, `VERIFY_MORE`, `SUPPRESS` action distribution.
5. **5-Way Proposal Ablation Matrix**: Saves results to `results/experiment_reliability/`.

### C. Generate All 18 IEEE-Style Publication Figures
```bash
python3 src/generate_18_figures.py
```
Produces `fig01_mmlu_domain_accuracy.pdf` through `fig18_component_ablation.pdf` + 300 DPI PNG previews.

---

## 3. Dataset Manifests (5 Datasets in `manifests/`)

- `manifests/manifest_mmlu_formal_logic.json` (30 items)
- `manifests/manifest_mmlu_college_physics.json` (30 items)
- `manifests/manifest_mmlu_machine_learning.json` (30 items)
- `manifests/manifest_mmlu_moral_scenarios.json` (30 items)
- `manifests/manifest_mmlu_us_foreign_policy.json` (30 items)
- `manifests/manifest_camera.json` (3 ad copy & keyword expansion tasks)
- `manifests/manifest_gsm8k.json` (3 multi-step reasoning items)
- `manifests/manifest_math.json` (2 competition math items)
- `manifests/manifest_wikiqa.json` (2 open-domain QA pairs)

---

## 4. Running Live Inference (Requires Local Ollama)

```bash
ollama serve
ollama pull qwen3:8b

# Run benchmark evaluation
PYTHONPATH=src python3 src/experiment_sprint4_3.py --condition all --resume
```
