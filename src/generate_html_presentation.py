#!/usr/bin/env python3
"""
Generate an interactive, modern, 18-slide web presentation deck
for TalkHier BTP Final Presentation.
Dark Modern Research Theme with keyboard navigation (Arrows/Space), fullscreen, and print-to-PDF styles.
"""

import os

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Enhancing Multi-Agent Reasoning Through Deterministic Logical Verification</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-dark: #0f172a;
      --card-bg: #1e293b;
      --card-inner: #162032;
      --border: #334155;
      --border-accent: #38bdf8;
      --text-light: #f8fafc;
      --text-muted: #94a3b8;
      --text-dim: #64748b;
      --cyan: #38bdf8;
      --blue: #60a5fa;
      --green: #34d399;
      --rose: #fb7185;
      --amber: #fbbf24;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background: var(--bg-dark);
      color: var(--text-light);
      height: 100vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      -webkit-font-smoothing: antialiased;
    }

    /* Top Header */
    header {
      background: rgba(15, 23, 42, 0.95);
      border-bottom: 1px solid var(--border);
      padding: 10px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      z-index: 100;
    }
    .header-title {
      font-size: 0.85rem;
      font-weight: 700;
      color: var(--cyan);
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }
    .header-progress {
      font-size: 0.85rem;
      font-weight: 600;
      color: var(--text-muted);
      background: var(--card-bg);
      padding: 4px 12px;
      border-radius: 9999px;
      border: 1px solid var(--border);
    }

    /* Main Slide Stage */
    #slide-stage {
      flex: 1;
      position: relative;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px;
      overflow: hidden;
    }

    .slide {
      display: none;
      width: 100%;
      max-width: 1200px;
      height: 100%;
      max-height: 700px;
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 40px;
      flex-direction: column;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
      animation: fadeIn 0.25s ease-out;
      overflow-y: auto;
    }
    .slide.active { display: flex; }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(8px); }
      to { opacity: 1; transform: translateY(0); }
    }

    /* Slide Typography */
    .slide-category {
      font-size: 0.8rem;
      font-weight: 700;
      color: var(--cyan);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 6px;
    }
    .slide-title {
      font-size: 1.85rem;
      font-weight: 800;
      color: var(--text-light);
      line-height: 1.25;
      margin-bottom: 8px;
    }
    .slide-subtitle {
      font-size: 1rem;
      color: var(--text-muted);
      margin-bottom: 24px;
      line-height: 1.4;
    }

    /* Grid Layouts */
    .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; flex: 1; }
    .grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; flex: 1; }
    .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }

    /* Content Cards */
    .card {
      background: var(--card-inner);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 20px;
      display: flex;
      flex-direction: column;
    }
    .card.border-cyan { border-color: rgba(56, 189, 248, 0.5); }
    .card.border-green { border-color: rgba(52, 211, 153, 0.5); }
    .card.border-rose { border-color: rgba(251, 113, 133, 0.5); }
    .card.border-amber { border-color: rgba(251, 191, 36, 0.5); }

    .card-title {
      font-size: 0.95rem;
      font-weight: 700;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .card p, .card li {
      font-size: 0.9rem;
      color: var(--text-muted);
      line-height: 1.5;
      margin-bottom: 8px;
    }
    .card li strong, .card p strong {
      color: var(--text-light);
    }
    .card ul { list-style: none; }
    .card ul li::before {
      content: "•";
      color: var(--cyan);
      font-weight: bold;
      display: inline-block;
      width: 1em;
      margin-left: -1em;
    }

    /* Stat Box */
    .stat-card {
      background: var(--card-inner);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px;
      text-align: center;
    }
    .stat-num {
      font-size: 2.2rem;
      font-weight: 800;
      line-height: 1.1;
      margin-bottom: 4px;
    }
    .stat-label {
      font-size: 0.85rem;
      font-weight: 700;
      color: var(--text-light);
    }
    .stat-sub {
      font-size: 0.75rem;
      color: var(--text-muted);
      margin-top: 4px;
    }

    /* Tables */
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.85rem;
      margin-top: 10px;
    }
    th, td {
      padding: 10px 12px;
      text-align: left;
      border-bottom: 1px solid var(--border);
    }
    th {
      background: var(--card-inner);
      color: var(--cyan);
      font-weight: 700;
    }
    td { color: var(--text-muted); }
    td strong { color: var(--text-light); }
    tr:last-child td { border-bottom: none; }

    /* Code Snippets */
    pre, code {
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.8rem;
    }
    pre {
      background: rgba(15, 23, 42, 0.8);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px;
      color: var(--cyan);
      overflow-x: auto;
      margin-top: 10px;
    }

    /* Bottom Control Bar */
    footer {
      background: rgba(15, 23, 42, 0.95);
      border-top: 1px solid var(--border);
      padding: 10px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .btn {
      background: var(--card-bg);
      border: 1px solid var(--border);
      color: var(--text-light);
      padding: 8px 16px;
      border-radius: 8px;
      font-weight: 600;
      font-size: 0.85rem;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.2s;
    }
    .btn:hover {
      background: var(--card-inner);
      border-color: var(--cyan);
      color: var(--cyan);
    }
    .badge {
      display: inline-block;
      padding: 4px 10px;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
    }
    .badge-green { background: rgba(52, 211, 153, 0.15); color: var(--green); border: 1px solid rgba(52, 211, 153, 0.4); }
    .badge-cyan { background: rgba(56, 189, 248, 0.15); color: var(--cyan); border: 1px solid rgba(56, 189, 248, 0.4); }
    .badge-rose { background: rgba(251, 113, 133, 0.15); color: var(--rose); border: 1px solid rgba(251, 113, 133, 0.4); }
    .badge-amber { background: rgba(251, 191, 36, 0.15); color: var(--amber); border: 1px solid rgba(251, 191, 36, 0.4); }
  </style>
</head>
<body>

  <header>
    <div class="header-title">TalkHier BTP • IIT Patna CSE • Final Presentation</div>
    <div class="header-progress" id="progress-indicator">Slide 1 / 18</div>
  </header>

  <main id="slide-stage">

    <!-- SLIDE 1: TITLE SLIDE -->
    <div class="slide active" id="slide-1">
      <div class="slide-category">BTP Progress Presentation • IIT Patna</div>
      <h1 class="slide-title" style="font-size: 2.2rem; margin-top: 8px;">Enhancing Hierarchical Multi-Agent Reasoning<br>Through Deterministic Logical Verification</h1>
      <p class="slide-subtitle">Investigating Vulnerabilities in Sony's TalkHier Framework & Integrating SymPy DPLL SAT Refutation</p>
      
      <div class="grid-2" style="margin-top: 10px;">
        <div class="card border-cyan">
          <div class="card-title" style="color: var(--cyan);">RESEARCHER & AFFILIATION</div>
          <p><strong>Candidate:</strong> Mohith Chandra</p>
          <p><strong>Degree:</strong> Bachelor of Technology (B.Tech)</p>
          <p><strong>Institution:</strong> Indian Institute of Technology Patna (IIT Patna)</p>
          <p><strong>Department:</strong> Computer Science and Engineering</p>
          <p><strong>Presentation Type:</strong> BTP Progress Presentation • November 2026</p>
        </div>

        <div class="card border-green">
          <div class="card-title" style="color: var(--green);">VERIFIED RESEARCH MILESTONES</div>
          <ul>
            <li><strong>100.0% Deductive Accuracy (24/24):</strong> Solved all pure propositional logic arguments in MMLU benchmark.</li>
            <li><strong>0 Harmful Revisions Observed:</strong> Zero regressions across all 17 multi-agent revisions executed.</li>
            <li><strong>69 / 69 Test Cases Passing:</strong> Full regression and integration test suite verified.</li>
            <li><strong>Based on Sony AI TalkHier:</strong> Enhancing the foundational paper (arXiv:2502.11098).</li>
          </ul>
        </div>
      </div>

      <div style="margin-top: 20px; font-size: 0.8rem; color: var(--text-dim); text-align: center;">
        Repository: https://github.com/MohithChandra07/Talkhier_BTP • Preserving all 63 execution traces and artifacts
      </div>
    </div>

    <!-- SLIDE 2: RESEARCH MOTIVATION -->
    <div class="slide" id="slide-2">
      <div class="slide-category">1. Introduction & Research Motivation</div>
      <h2 class="slide-title">The Limits of Multi-Agent Deliberation in Formal Reasoning</h2>
      <p class="slide-subtitle">Why scaling agent debate fails to guarantee deductive correctness without symbolic verification</p>

      <div class="grid-2">
        <div class="card border-cyan">
          <div class="card-title" style="color: var(--cyan);">THE PROMISE OF MULTI-AGENT SYSTEMS</div>
          <ul>
            <li><strong>Distributed Specialization:</strong> Partitioning complex reasoning into Solvers, Evaluators, and Revisors improves initial decomposition.</li>
            <li><strong>Iterative Refinement:</strong> Multi-pass peer critique filters surface-level formatting slips and hallucinated steps in open domains.</li>
            <li><strong>Demonstrated Success:</strong> Empirically superior on open-ended QA, creative generation, and conversational tasks.</li>
          </ul>
        </div>

        <div class="card border-rose">
          <div class="card-title" style="color: var(--rose);">THE FORMAL DEDUCTIVE FAILURE MODE</div>
          <ul>
            <li><strong>Consensus != Truth:</strong> Democratic voting among LLMs cannot verify formal validity or guarantee minimal counterexamples.</li>
            <li><strong>Correlated Hallucinations:</strong> Evaluators evaluate natural language rhetoric, frequently agreeing with fallacious reasoning.</li>
            <li><strong>Sycophantic Flips:</strong> Revisors yield to confident peer consensus, causing harmful revisions (flipping correct answers to wrong).</li>
          </ul>
        </div>
      </div>

      <div class="card border-cyan" style="margin-top: 20px; background: rgba(56, 189, 248, 0.08);">
        <p style="color: var(--cyan); font-weight: 700; text-align: center;">
          CORE RESEARCH THESIS: More agents do not automatically guarantee more reliable reasoning. Formal deductive tasks require deterministic symbolic proof, not probabilistic consensus.
        </p>
      </div>
    </div>

    <!-- SLIDE 3: UNDERSTANDING TALKHIER -->
    <div class="slide" id="slide-3">
      <div class="slide-category">1. Introduction & Research Motivation</div>
      <h2 class="slide-title">Understanding the Foundation: Sony TalkHier Framework</h2>
      <p class="slide-subtitle">A collaborative framework modeling structured agent conversations and hierarchical refinement (Wang et al., 2025)</p>

      <div class="grid-3">
        <div class="card border-cyan">
          <div class="card-title" style="color: var(--cyan);">1. STRUCTURED PROTOCOL</div>
          <p><strong>Message (M_ij):</strong> Core task instruction and generated answer choice.</p>
          <p><strong>Background (B_ij):</strong> Domain context and shared problem constraints.</p>
          <p><strong>Intermediate (I_ij):</strong> Step-by-step reasoning derivation and partial steps.</p>
        </div>

        <div class="card border-blue">
          <div class="card-title" style="color: var(--blue);">2. HIERARCHICAL ROLES</div>
          <p><strong>Supervisor Agents:</strong> Dynamically orchestrate communication flow between agents.</p>
          <p><strong>Member Agents:</strong> Task executors focusing on specific sub-goals.</p>
          <p><strong>Evaluator Teams:</strong> Domain-specific critique agents.</p>
        </div>

        <div class="card border-green">
          <div class="card-title" style="color: var(--green);">3. TWO-PASS REFINEMENT</div>
          <p><strong>Pass 1 (Solve):</strong> Solver agent generates initial answer candidate A0.</p>
          <p><strong>Evaluation:</strong> Evaluator team generates scores & critiques.</p>
          <p><strong>Pass 2 (Revise):</strong> Aggregator summarizes; Revisor produces final answer.</p>
        </div>
      </div>

      <div class="card" style="margin-top: 20px;">
        <div class="card-title" style="color: var(--text-dim); font-size: 0.8rem;">BASELINE ARCHITECTURE PIPELINE (Wang et al., 2025)</div>
        <p style="color: var(--cyan); font-weight: 700; text-align: center; font-size: 0.95rem;">
          Input Question ──▶ Answer Generator (A0) ──▶ Evaluator Supervisor ──▶ Specialized Evaluators ──▶ Aggregator ──▶ Revisor ──▶ Final Answer
        </p>
      </div>
    </div>

    <!-- SLIDE 4: RESEARCH GAPS & 3 LOOPHOLES -->
    <div class="slide" id="slide-4">
      <div class="slide-category">1. Introduction & Research Motivation</div>
      <h2 class="slide-title">Three Critical Loopholes Discovered via Empirical Audit</h2>
      <p class="slide-subtitle">Auditing the original TalkHier codebase across MMLU Formal Logic revealed fundamental architectural vulnerabilities</p>

      <div class="grid-3">
        <div class="card border-rose">
          <div class="badge badge-rose" style="width: fit-content; margin-bottom: 8px;">Loophole 1</div>
          <div class="card-title" style="color: var(--text-light);">Evaluator Bypass<br>(Ad-hoc Routing)</div>
          <p>In the original framework, the supervisor decided routing dynamically. On <strong>>60% of test questions</strong>, the supervisor skipped evaluators completely and fabricated scores itself.</p>
          <p style="color: var(--rose); font-weight: 600;">Impact: Evaluators were essentially dormant.</p>
        </div>

        <div class="card border-amber">
          <div class="badge badge-amber" style="width: fit-content; margin-bottom: 8px;">Loophole 2</div>
          <div class="card-title" style="color: var(--text-light);">Subjective Evaluation<br>(No Formal Proofs)</div>
          <p>Evaluators evaluated formal arguments purely via natural language prompts without formal rubrics, SAT solvers, or truth tables, easily falling for fallacies.</p>
          <p style="color: var(--amber); font-weight: 600;">Impact: Noisy, uncalibrated critiques.</p>
        </div>

        <div class="card border-rose">
          <div class="badge badge-rose" style="width: fit-content; margin-bottom: 8px;">Loophole 3</div>
          <div class="card-title" style="color: var(--text-light);">Harmful Revisions<br>(Sycophantic Flips)</div>
          <p>Revisors had no safeguards against incorrect peer critique. Correct initial answers (A0) were repeatedly flipped to incorrect choices by flawed evaluator consensus.</p>
          <p style="color: var(--rose); font-weight: 600;">Impact: Multi-agent debate degraded accuracy.</p>
        </div>
      </div>
    </div>

    <!-- SLIDE 5: LOOPHOLE 1 ANALYSIS -->
    <div class="slide" id="slide-5">
      <div class="slide-category">2. Loophole 1 & Sprint 3 Resolution</div>
      <h2 class="slide-title">Loophole 1: Evaluator Execution Reliability</h2>
      <p class="slide-subtitle">Auditing how the original Evaluator Supervisor simulated evaluations rather than running actual agents</p>

      <div class="grid-2">
        <div class="card border-rose">
          <div class="card-title" style="color: var(--rose);">ORIGINAL BEHAVIOUR (SIMULATED EVALUATION)</div>
          <p>The original supervisor had full autonomy to coordinate evaluation. In practice, the LLM opted to synthesize mock evaluation scores itself in a single turn:</p>
          <pre>Trace Audit: Problem 3 (Baseline TalkHier)
> Supervisor Invoked: True
> Truth Table Agent Invoked: FALSE (Skipped)
> Counterexample Agent Invoked: FALSE (Skipped)
> Supervisor Output: Synthesized scores directly
> Evaluator Execution Rate: 0% REAL DISPATCH</pre>
          <p style="margin-top: 10px;">The supervisor took the path of least resistance, bypassing specialized evaluators entirely.</p>
        </div>

        <div class="card border-green">
          <div class="card-title" style="color: var(--green);">OUR CORRECTED DISPATCH PIPELINE</div>
          <p>We eliminated supervisor autonomy by moving orchestration into an authoritative LangGraph state machine with explicit node transitions:</p>
          <pre>LangGraph Enforcement (Sprint 3)
> Evaluator Prep Node: Classifies taxonomy
> Truth Table Agent: INVOKED (Attempt 1 Success)
> Counterexample Agent: INVOKED (Attempt 1 Success)
> Formal Logic Agent: INVOKED (Attempt 1 Success)
> Dispatch Compliance: 100% EXPLICIT & AUDITABLE</pre>
          <p style="margin-top: 10px;">Every evaluator executes independently in an isolated sandbox, returning validated Pydantic schemas.</p>
        </div>
      </div>
    </div>

    <!-- SLIDE 6: SPRINT 3 MANDATORY EXECUTION -->
    <div class="slide" id="slide-6">
      <div class="slide-category">2. Loophole 1 & Sprint 3 Resolution</div>
      <h2 class="slide-title">Sprint 3: Graph-Level Mandatory Evaluation Pipeline</h2>
      <p class="slide-subtitle">Replacing probabilistic supervisor routing with a deterministic LangGraph state machine</p>

      <div class="grid-2">
        <div class="card border-cyan">
          <div class="card-title" style="color: var(--cyan);">1. DETERMINISTIC STATE MACHINE</div>
          <p>Built <code>graph_dispatch.py</code> using LangGraph. The execution order is deterministic: <code>Evaluator Prep ──▶ Evaluator Team ──▶ Aggregator ──▶ Revisor</code>. No agent can terminate the graph early.</p>
        </div>

        <div class="card border-blue">
          <div class="card-title" style="color: var(--blue);">2. IMMUTABLE BASELINE ANSWER (A0)</div>
          <p>Initial Answer A0 and its derivation are frozen in state as an immutable baseline. Evaluators critique A0 without mutating it, preventing silent overwrites and enabling strict revision auditing.</p>
        </div>

        <div class="card border-green">
          <div class="card-title" style="color: var(--green);">3. STANDARDIZED EVALUATOR STATUSES</div>
          <p>Standardized evaluator output schema to three explicit states: <code>VALID</code> (score 0-10), <code>NOT_APPLICABLE</code> (domain mismatch), or <code>NO_EVALUATION</code>. Aggregator only weights applicable scores.</p>
        </div>

        <div class="card border-amber">
          <div class="card-title" style="color: var(--amber);">4. TAXONOMY-DRIVEN EVALUATOR PREP</div>
          <p>Added an Evaluator Prep stage prior to dispatch. Automatically categorizes input into Propositional Logic, Predicate Logic, or Rhetorical Fallacies, ensuring only relevant evaluators are activated.</p>
        </div>
      </div>
    </div>

    <!-- SLIDE 7: SPRINT 3 RESULTS -->
    <div class="slide" id="slide-7">
      <div class="slide-category">2. Loophole 1 & Sprint 3 Resolution</div>
      <h2 class="slide-title">Sprint 3 Results: 100% Invocations & 39.2% Latency Reduction</h2>
      <p class="slide-subtitle">Empirical verification across baseline replication and optimized selective dispatch</p>

      <div class="grid-2">
        <div class="card">
          <div class="card-title" style="color: var(--cyan);">PILOT BENCHMARK COMPARISON (5 PROBLEMS)</div>
          <table>
            <thead>
              <tr>
                <th>Metric</th>
                <th>Baseline</th>
                <th>Sprint 3 Opt</th>
                <th>Improvement</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Evaluator Invocations</td>
                <td>25 / 25 (100%)</td>
                <td><strong>25 / 25 (100%)</strong></td>
                <td><span class="badge badge-green">100% Verified</span></td>
              </tr>
              <tr>
                <td>Evaluator Retries</td>
                <td>Multiple failures</td>
                <td><strong>0 / 25 (0%)</strong></td>
                <td><span class="badge badge-green">100% 1st Try</span></td>
              </tr>
              <tr>
                <td>Final Accuracy</td>
                <td>3 / 5 (60.0%)</td>
                <td><strong>4 / 5 (80.0%)</strong></td>
                <td><span class="badge badge-cyan">+20.0% Gain</span></td>
              </tr>
              <tr>
                <td>Harmful Revisions</td>
                <td>1 (Problem 3 wrong)</td>
                <td><strong>0 (Fixed)</strong></td>
                <td><span class="badge badge-green">0% Regression</span></td>
              </tr>
              <tr>
                <td>Total Runtime</td>
                <td>1,919.7s (~32m)</td>
                <td><strong>1,166.6s (~19m)</strong></td>
                <td><span class="badge badge-cyan">39.2% Faster</span></td>
              </tr>
            </tbody>
          </table>
        </div>

        <div style="display: flex; flex-direction: column; gap: 16px;">
          <div class="card border-green">
            <div class="card-title" style="color: var(--green);">100% EVALUATOR COMPLIANCE</div>
            <p>Zero evaluator bypass. Every problem generated full evaluator telemetry across all 5 test questions with explicit audit logs.</p>
          </div>
          <div class="card border-cyan">
            <div class="card-title" style="color: var(--cyan);">35% TOKEN CALL REDUCTION</div>
            <p>Selective dispatch reduced evaluator invocations from 20 to 13 calls by skipping irrelevant domains based on taxonomy.</p>
          </div>
          <div class="card border-amber">
            <div class="card-title" style="color: var(--amber);">37 PASSING UNIT TESTS</div>
            <p>Validated state transition graph, scoring normalization, and revisor safeguards with zero regressions.</p>
          </div>
        </div>
      </div>
    </div>

    <!-- SLIDE 8: LOOPHOLE 2 FAILURE OF CONSENSUS -->
    <div class="slide" id="slide-8">
      <div class="slide-category">3. Loopholes 2 & 3: Sprint 4 Resolution</div>
      <h2 class="slide-title">Loophole 2: Why Pure LLM Consensus Is Insufficient</h2>
      <p class="slide-subtitle">An empirical case study on Problem 6: When all neural evaluators agree on a false derivation</p>

      <div class="card border-amber" style="margin-bottom: 20px;">
        <div class="card-title" style="color: var(--amber);">MMLU FORMAL LOGIC — PROBLEM 6 (CANONICAL FAILURE CASE)</div>
        <p style="font-family: 'JetBrains Mono', monospace; font-size: 0.95rem; color: var(--text-light);">
          Argument:  ~K ≡ L  /  (K · L) ∨ (K · ~L)<br>
          Question: Determine whether the argument is valid or invalid. If invalid, specify the counterexample.
        </p>
        <p style="color: var(--green); font-weight: 700; margin-top: 6px;">Ground Truth: Choice 3 (Invalid with counterexample: L = True, K = False)</p>
      </div>

      <div class="grid-2">
        <div class="card border-rose">
          <div class="card-title" style="color: var(--rose);">PURE LLM TEAM (SPRINT 3 OPT)</div>
          <ul>
            <li><strong>Initial Answer A0:</strong> Selected Choice 0 ('Valid', Incorrect).</li>
            <li><strong>Formal Logic Evaluator:</strong> Hallucinated that Choice 2 was the counterexample.</li>
            <li><strong>Truth Table Evaluator:</strong> Confused by the disjunctive conclusion.</li>
            <li><strong>Revisor Action:</strong> Overruled by peer majority, flipped from Choice 0 to Choice 2 (Still Incorrect!).</li>
          </ul>
          <p style="color: var(--rose); font-weight: 700; margin-top: 10px;">Correlated hallucination replaced an error with another error.</p>
        </div>

        <div class="card border-green">
          <div class="card-title" style="color: var(--green);">DETERMINISTIC VERIFIER (SPRINT 4 FULL)</div>
          <ul>
            <li><strong>SymPy SAT Solver:</strong> Solved satisfiability of Premises ∧ ¬Conclusion.</li>
            <li><strong>Refutation:</strong> SAT proven ──▶ Argument is mathematically INVALID.</li>
            <li><strong>Countermodel Extraction:</strong> Extracted exact model {L: True, K: False}.</li>
            <li><strong>Choice Mapping:</strong> Verified that Choice 3 matches the countermodel.</li>
          </ul>
          <p style="color: var(--green); font-weight: 700; margin-top: 10px;">Revisor immediately revised to Choice 3 (100% Correct Revision!).</p>
        </div>
      </div>
    </div>

    <!-- SLIDE 9: SPRINT 4.1 LOGICAL VERIFIER -->
    <div class="slide" id="slide-9">
      <div class="slide-category">3. Loopholes 2 & 3: Sprint 4 Resolution</div>
      <h2 class="slide-title">Sprint 4.1: Deterministic Propositional Logic Engine</h2>
      <p class="slide-subtitle">SymPy DPLL SAT refutation and automated countermodel synthesis (logic_verifier.py)</p>

      <div class="grid-4" style="flex: 1;">
        <div class="card border-cyan">
          <div class="card-title" style="color: var(--cyan); font-size: 0.85rem;">STEP 1: NORMALIZATION</div>
          <p><strong>Slash Notation Parsing</strong></p>
          <p>Extracts premises and conclusion. Normalizes ASCII & Unicode symbols:</p>
          <p><code>~ ──▶ Not</code><br><code>· ──▶ And</code><br><code>∨ ──▶ Or</code><br><code>⊃ ──▶ Implies</code><br><code>≡ ──▶ Equivalent</code></p>
        </div>

        <div class="card border-blue">
          <div class="card-title" style="color: var(--blue); font-size: 0.85rem;">STEP 2: PRATT PARSER</div>
          <p><strong>Recursive AST Builder</strong></p>
          <p>Deterministic precedence parser constructs exact SymPy Boolean expression trees.</p>
          <p>Validates syntax and detects unsupported first-order predicates or quantifiers safely.</p>
        </div>

        <div class="card border-green">
          <div class="card-title" style="color: var(--green); font-size: 0.85rem;">STEP 3: DPLL SAT SOLVER</div>
          <p><strong>Refutation Prover</strong></p>
          <p>Solves satisfiability of:</p>
          <p style="color: var(--green); font-weight: 700;">⋀(Premises) ∧ ¬Conclusion</p>
          <p>• <strong>UNSAT:</strong> Argument is VALID.<br>• <strong>SAT:</strong> Argument is INVALID.</p>
        </div>

        <div class="card border-amber">
          <div class="card-title" style="color: var(--amber); font-size: 0.85rem;">STEP 4: COUNTERMODEL</div>
          <p><strong>Choice Matching</strong></p>
          <p>For invalid arguments, extracts truth assignment {Var: True/False}.</p>
          <p>Matches countermodel against MCQ options (Choices 0-3), marking proven choice index.</p>
        </div>
      </div>
    </div>

    <!-- SLIDE 10: LOOPHOLE 3 SAFEGUARDING REVISION -->
    <div class="slide" id="slide-10">
      <div class="slide-category">3. Loopholes 2 & 3: Sprint 4 Resolution</div>
      <h2 class="slide-title">Loophole 3: Preventing Harmful Revisions</h2>
      <p class="slide-subtitle">Protecting correct initial answers (A0) from being flipped by noisy evaluator consensus</p>

      <div class="grid-2">
        <div class="card border-rose">
          <div class="card-title" style="color: var(--rose);">BEFORE: HARMFUL REVISION IN BASELINE</div>
          <p><strong>Problem 3:  ~G ⊃ H,  ~H  /  G  (Valid Disjunctive Syllogism)</strong></p>
          <ul>
            <li><strong>Initial Answer A0:</strong> Choice 0 ('Valid', Correct ground truth).</li>
            <li><strong>Peer Evaluator Trap:</strong> Evaluators hallucinated that Choice 2 ('Invalid with G=True, H=False') was a valid counterexample.</li>
            <li><strong>Revisor Yielding:</strong> Revisor accepted consensus and flipped A0 to Choice 2.</li>
          </ul>
          <p style="color: var(--rose); font-weight: 700; margin-top: 10px;">Net Outcome: Correct answer was corrupted by peer debate (Harmful Revision).</p>
        </div>

        <div class="card border-green">
          <div class="card-title" style="color: var(--green);">AFTER: DETERMINISTIC REVISOR SAFEGUARD</div>
          <p><strong>Sprint 4 Solution: Proof Injection & Hard Override</strong></p>
          <ul>
            <li><strong>SymPy SAT Proof:</strong> Proved (~G ⊃ H) ∧ ~H ∧ ~G is UNSAT (No counterexample can mathematically exist).</li>
            <li><strong>Evidence Injection:</strong> Injected proof that Choice 0 is uniquely valid into Truth Table evaluator and Revisor.</li>
            <li><strong>Safeguard Override:</strong> Revisor is bound by deterministic proof, filtering hallucinations.</li>
          </ul>
          <p style="color: var(--green); font-weight: 700; margin-top: 10px;">Net Outcome: Choice 0 retained. Zero harmful revisions across 17 revisions.</p>
        </div>
      </div>
    </div>

    <!-- SLIDE 11: SPRINT 4.2 INTEGRATED PIPELINE -->
    <div class="slide" id="slide-11">
      <div class="slide-category">3. Loopholes 2 & 3: Sprint 4 Resolution</div>
      <h2 class="slide-title">Sprint 4.2: Neuro-Symbolic Multi-Agent Architecture</h2>
      <p class="slide-subtitle">Seamlessly coupling deterministic SAT refutation with hierarchical neural deliberation</p>

      <div style="display: flex; flex-direction: column; gap: 12px; flex: 1;">
        <div class="card border-blue" style="padding: 12px 20px;">
          <p><strong>1. Input & A0 Generation:</strong> MMLU Formal Logic problem passed to Answer Generator; produces initial choice A0 (frozen in state as immutable baseline).</p>
        </div>
        <div class="card border-cyan" style="padding: 12px 20px;">
          <p><strong>2. Evaluator Prep & Extraction:</strong> Parses question text; attempts deterministic premise/conclusion extraction into Boolean AST.</p>
        </div>
        <div class="card border-green" style="padding: 12px 20px;">
          <p><strong>3. SymPy SAT Engine (Bifurcation):</strong> If pure propositional: DPLL solver refutes validity, derives countermodel. If FOL/NL: Clean fallback.</p>
        </div>
        <div class="card border-amber" style="padding: 12px 20px;">
          <p><strong>4. Evidence-Injected Evaluators:</strong> Truth Table, Counterexample, and Formal Logic agents receive formal proof status in their prompt context.</p>
        </div>
        <div class="card border-cyan" style="padding: 12px 20px;">
          <p><strong>5. Aggregator & Hard Override Revisor:</strong> Aggregator synthesizes neural + symbolic signals. Revisor applies hard override if proof is validated.</p>
        </div>
      </div>
    </div>

    <!-- SLIDE 12: SPRINT 4.3 EXPERIMENTAL DESIGN -->
    <div class="slide" id="slide-12">
      <div class="slide-category">3. Loopholes 2 & 3: Sprint 4 Resolution</div>
      <h2 class="slide-title">Sprint 4.3: Experimental Design & Ablation Framework</h2>
      <p class="slide-subtitle">Isolating the causal contribution of each component across 35 stratified benchmark problems</p>

      <div class="grid-2">
        <div class="card border-cyan">
          <div class="card-title" style="color: var(--cyan);">FOUR ISOLATED EXPERIMENTAL CONFIGURATIONS</div>
          <p><strong>1. Sprint 3 Opt (Control):</strong> Pure LLM selective dispatch baseline. No symbolic verifier.</p>
          <p><strong>2. Full Sprint 4 (Proposed):</strong> SAT Verifier + Evaluator Evidence Injection + Revisor Hard Override.</p>
          <p><strong>3. Ablation A (Override Only):</strong> SAT Verifier + Hard Override active, but NO evidence injected into evaluators.</p>
          <p><strong>4. Ablation B (Evidence Only):</strong> SAT Verifier + Evidence Injected, but Hard Override DISABLED.</p>
        </div>

        <div class="card border-green">
          <div class="card-title" style="color: var(--green);">BENCHMARK STRATIFICATION (35 PROBLEMS)</div>
          <ul>
            <li><strong>Target Domain (27 Problems):</strong> Propositional deductive arguments in slash notation.<br>• 24 Pure Propositional Logic Problems<br>• 3 Predicate / FOL Fallback Problems (49, 69, 101)</li>
            <li><strong>Control Domain (8 Problems):</strong> Non-propositional formal logic (Natural language syllogisms, quantifier duality, fallacies).</li>
            <li><strong>18 Paired Problems:</strong> Evaluated head-to-head under identical LLM settings.</li>
            <li><strong>5 Divergence Cases:</strong> Evaluated across all 4 ablations.</li>
          </ul>
        </div>
      </div>
    </div>

    <!-- SLIDE 13: OVERALL BENCHMARK RESULTS -->
    <div class="slide" id="slide-13">
      <div class="slide-category">4. Results & Empirical Evidence</div>
      <h2 class="slide-title">Overall Benchmark Results: Substantial Accuracy Gains</h2>
      <p class="slide-subtitle">Verified results across 35 stratified MMLU Formal Logic problems (results/experiment_sprint4_3/)</p>

      <div class="grid-4" style="margin-bottom: 20px;">
        <div class="stat-card">
          <div class="stat-num" style="color: var(--green);">88.6%</div>
          <div class="stat-label">Overall Accuracy</div>
          <div class="stat-sub">31 / 35 (vs A0 14/35, 40%)</div>
        </div>
        <div class="stat-card">
          <div class="stat-num" style="color: var(--cyan);">100.0%</div>
          <div class="stat-label">Pure Propositional</div>
          <div class="stat-sub">24 / 24 (vs A0 9/24, 37.5%)</div>
        </div>
        <div class="stat-card">
          <div class="stat-num" style="color: var(--blue);">17</div>
          <div class="stat-label">Helpful Revisions</div>
          <div class="stat-sub">15 Target + 2 Control</div>
        </div>
        <div class="stat-card">
          <div class="stat-num" style="color: var(--amber);">0</div>
          <div class="stat-label">Harmful Revisions</div>
          <div class="stat-sub">0.0% Regression Rate</div>
        </div>
      </div>

      <div class="card">
        <div class="card-title" style="color: var(--cyan); font-size: 0.85rem;">BENCHMARK PARTITION BREAKDOWN</div>
        <table>
          <thead>
            <tr>
              <th>Partition</th>
              <th>Count</th>
              <th>Initial A0</th>
              <th>Final Accuracy</th>
              <th>Helpful</th>
              <th>Harmful</th>
              <th>Proof Precision</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Target: Pure Propositional</td>
              <td>24</td>
              <td>37.5% (9/24)</td>
              <td><strong>100.0% (24/24)</strong></td>
              <td>15</td>
              <td>0</td>
              <td><strong>100.0% (24/24)</strong></td>
            </tr>
            <tr>
              <td>Target: Predicate Fallback</td>
              <td>3</td>
              <td>33.3% (1/3)</td>
              <td><strong>33.3% (1/3)</strong></td>
              <td>0</td>
              <td>0</td>
              <td>N/A (Fallback)</td>
            </tr>
            <tr>
              <td>Target Domain Total</td>
              <td>27</td>
              <td>37.0% (10/27)</td>
              <td><strong>92.6% (25/27)</strong></td>
              <td>15</td>
              <td>0</td>
              <td>100.0% (24/24)</td>
            </tr>
            <tr>
              <td>Control Domain (Stratified)</td>
              <td>8</td>
              <td>50.0% (4/8)</td>
              <td><strong>75.0% (6/8)</strong></td>
              <td>2</td>
              <td>0</td>
              <td>N/A (Control)</td>
            </tr>
            <tr>
              <td><strong>Full 35-Problem Benchmark</strong></td>
              <td><strong>35</strong></td>
              <td><strong>40.0% (14/35)</strong></td>
              <td><strong>88.6% (31/35)</strong></td>
              <td><strong>17</strong></td>
              <td><strong>0</strong></td>
              <td><strong>100.0% (24/24)</strong></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- SLIDE 14: HEAD TO HEAD COMPARISON -->
    <div class="slide" id="slide-14">
      <div class="slide-category">4. Results & Empirical Evidence</div>
      <h2 class="slide-title">Head-to-Head Comparison: Sprint 3 Opt vs. Sprint 4 Full</h2>
      <p class="slide-subtitle">Paired evaluation across 18 identical problems under identical LLM inference settings</p>

      <div class="grid-2">
        <div class="card">
          <div class="card-title" style="color: var(--cyan);">PAIRED PERFORMANCE TABLE (18 PROBLEMS)</div>
          <table>
            <thead>
              <tr>
                <th>Partition</th>
                <th>Sprint 3 Opt</th>
                <th>Sprint 4 Full</th>
                <th>Net Gain</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Target Propositional (10)</td>
                <td>60.0% (6/10)</td>
                <td><strong>100.0% (10/10)</strong></td>
                <td><span class="badge badge-green">+40.0% Gain</span></td>
              </tr>
              <tr>
                <td>Control Domain (8)</td>
                <td><strong>87.5% (7/8)</strong></td>
                <td>75.0% (6/8)</td>
                <td><span class="badge badge-rose">-12.5% (Var)</span></td>
              </tr>
              <tr>
                <td><strong>Total Paired Slice (18)</strong></td>
                <td><strong>72.2% (13/18)</strong></td>
                <td><strong>88.9% (16/18)</strong></td>
                <td><span class="badge badge-green">+16.7% Gain</span></td>
              </tr>
            </tbody>
          </table>
          <p style="margin-top: 14px; font-size: 0.85rem;">Target Domain Finding: On the 10 pure propositional arguments, Sprint 4 achieved 100% (10/10) vs Sprint 3 Opt's 60% (6/10), representing a 40.0% accuracy gain driven entirely by deterministic refutation.</p>
        </div>

        <div class="card border-amber">
          <div class="card-title" style="color: var(--amber);">STATISTICAL RIGOR: McNEMAR PAIRED TEST</div>
          <p><strong>Contingency Matrix (18 Paired Problems):</strong></p>
          <pre>• b (Sprint 4 Correct, Opt Wrong) = 4
• c (Opt Correct, Sprint 4 Wrong) = 1
• Discordant Pairs (b + c) = 5
• Chi-Square: χ² = (|4 - 1| - 1)² / 5 = 0.80
• p-value > 0.05 (Not Statistically Significant)</pre>
          <p style="margin-top: 10px;"><strong>Honest Scientific Takeaway:</strong> While target domain gains (+40%) are descriptively dramatic, formal significance is constrained by the paired sample size (N=18). We do not claim proven statistical superiority without larger N.</p>
        </div>
      </div>
    </div>

    <!-- SLIDE 15: ABLATION & ERROR ANALYSIS -->
    <div class="slide" id="slide-15">
      <div class="slide-category">4. Results & Empirical Evidence</div>
      <h2 class="slide-title">Ablation Findings & Systematic Error Analysis</h2>
      <p class="slide-subtitle">Isolating component necessity across 5 failure cases and classifying all remaining errors</p>

      <div class="grid-2">
        <div class="card border-cyan">
          <div class="card-title" style="color: var(--cyan);">ABLATION: 5 A0-FAILURE CASES</div>
          <table>
            <thead>
              <tr>
                <th>Condition</th>
                <th>Accuracy (5)</th>
                <th>Helpful Revisions</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Initial A0 Baseline</td>
                <td>0 / 5 (0.0%)</td>
                <td>0</td>
              </tr>
              <tr>
                <td>Sprint 3 Opt (Control)</td>
                <td>1 / 5 (20.0%)</td>
                <td>1</td>
              </tr>
              <tr>
                <td>Ablation A (Override Only)</td>
                <td><strong>5 / 5 (100.0%)</strong></td>
                <td>5</td>
              </tr>
              <tr>
                <td>Ablation B (Evidence Only)</td>
                <td><strong>5 / 5 (100.0%)</strong></td>
                <td>5</td>
              </tr>
            </tbody>
          </table>
          <p style="margin-top: 12px; font-size: 0.85rem;"><strong>Key Finding — Voluntary Compliance:</strong> Ablation B proves that when structured SAT evidence is injected, LLM Revisors voluntarily adopt the proof in 100% of cases without requiring a hard override.</p>
        </div>

        <div class="card border-rose">
          <div class="card-title" style="color: var(--rose);">ROOT-CAUSE: 4 REMAINING ERRORS</div>
          <ul>
            <li><strong>Control 1 & 4 (Non-Propositional):</strong> Rhetorical natural language ambiguity outside propositional logic.</li>
            <li><strong>Target 49 & 101 (Predicate Fallback):</strong> First-order relational predicates outside parser scope. Clean fallback triggered.</li>
            <li><strong>Target 69:</strong> Successfully answered by LLM fallback.</li>
            <li><strong>Zero False Proofs:</strong> In 100% of unsupported cases, the verifier abstained safely rather than fabricating a false proof.</li>
          </ul>
        </div>
      </div>
    </div>

    <!-- SLIDE 16: TECHNICAL CONTRIBUTIONS -->
    <div class="slide" id="slide-16">
      <div class="slide-category">5. Conclusion & Future Scope</div>
      <h2 class="slide-title">Summary of Key Technical Contributions</h2>
      <p class="slide-subtitle">Deliverables produced across multi-agent stabilization, symbolic reasoning, and empirical evaluation</p>

      <div style="display: flex; flex-direction: column; gap: 10px; flex: 1;">
        <div class="card border-rose" style="padding: 12px 20px;">
          <p><strong>1. Empirical Vulnerability Discovery:</strong> First systematic audit identifying Evaluator Bypass (>60%), simulated scoring, and sycophantic harmful revisions in hierarchical multi-agent frameworks.</p>
        </div>
        <div class="card border-blue" style="padding: 12px 20px;">
          <p><strong>2. Graph-Level Deterministic Dispatch:</strong> Engineered an authoritative LangGraph state machine enforcing 100% evaluator execution compliance, taxonomy classification, and immutable state baselines.</p>
        </div>
        <div class="card border-green" style="padding: 12px 20px;">
          <p><strong>3. Propositional SAT Verification Engine:</strong> Implemented automated formula normalization, Pratt AST parsing, SymPy DPLL satisfiability refutation, and minimal truth-value countermodel synthesis.</p>
        </div>
        <div class="card border-cyan" style="padding: 12px 20px;">
          <p><strong>4. Evidence-Guided Revisor Safeguard:</strong> Coupled neural deliberation with symbolic proofs. Achieved 0 harmful revisions across 17 revisions (zero regression on deductive validity).</p>
        </div>
        <div class="card border-amber" style="padding: 12px 20px;">
          <p><strong>5. Reproducible Benchmark & Test Suite:</strong> Constructed a 35-problem MMLU formal logic benchmark, 4 ablation configurations, 63 raw execution traces, and 69 passing unit & integration tests.</p>
        </div>
      </div>
    </div>

    <!-- SLIDE 17: LIMITATIONS & FUTURE WORK -->
    <div class="slide" id="slide-17">
      <div class="slide-category">5. Conclusion & Future Scope</div>
      <h2 class="slide-title">Current Limitations & Future Research Roadmap</h2>
      <p class="slide-subtitle">Maintaining scientific honesty regarding system boundaries and outlining the path to publication</p>

      <div class="grid-2">
        <div class="card border-amber">
          <div class="card-title" style="color: var(--amber);">CURRENT SYSTEM BOUNDARIES</div>
          <ul>
            <li><strong>Propositional Logic Scope:</strong> Current SAT solver operates on propositional logic. First-order logic with quantifiers (∀, ∃) and relational predicates falls back to LLM.</li>
            <li><strong>Small Paired Sample Size:</strong> Head-to-head baseline comparison was conducted on 18 paired problems. Formal McNemar test p > 0.05.</li>
            <li><strong>Extraction Heuristics:</strong> Complex natural language syntax with deeply nested clauses can occasionally trigger PARSE_FAILURE.</li>
            <li><strong>Inference Overhead:</strong> Multi-agent deliberation with sequential evaluation increases per-problem latency (~240s-320s per problem).</li>
          </ul>
        </div>

        <div class="card border-cyan">
          <div class="card-title" style="color: var(--cyan);">FUTURE RESEARCH ROADMAP</div>
          <ul>
            <li><strong>First-Order SMT Integration:</strong> Incorporate Z3 or Prover9 theorem provers to handle relational predicates, arithmetic constraints, and quantifiers.</li>
            <li><strong>Semantic Formalization:</strong> Train a lightweight semantic parsing model (fine-tuned LLM) to translate messy natural language premises into formal logic.</li>
            <li><strong>Benchmark Expansion:</strong> Scale evaluation across broader formal reasoning datasets (ProofWriter, FOLIO, Big-Bench Hard).</li>
            <li><strong>Research Paper Submission:</strong> Prepare manuscript detailing multi-agent sycophancy vulnerabilities and neuro-symbolic revision safeguards.</li>
          </ul>
        </div>
      </div>
    </div>

    <!-- SLIDE 18: THANK YOU & DISCUSSION -->
    <div class="slide" id="slide-18">
      <div class="slide-category">5. Conclusion & Future Scope</div>
      <h2 class="slide-title" style="font-size: 2.4rem;">Thank You</h2>
      <p class="slide-subtitle">Enhancing Hierarchical Multi-Agent Reasoning Through Deterministic Logical Verification</p>

      <div class="grid-4" style="margin-bottom: 24px;">
        <div class="stat-card">
          <div class="stat-num" style="color: var(--green);">100.0%</div>
          <div class="stat-label">Propositional Acc.</div>
          <div class="stat-sub">24 / 24 Pure Logic</div>
        </div>
        <div class="stat-card">
          <div class="stat-num" style="color: var(--cyan);">88.6%</div>
          <div class="stat-label">Overall Acc.</div>
          <div class="stat-sub">31 / 35 Benchmark Tasks</div>
        </div>
        <div class="stat-card">
          <div class="stat-num" style="color: var(--amber);">0</div>
          <div class="stat-label">Harmful Revisions</div>
          <div class="stat-sub">0.0% Regression Rate</div>
        </div>
        <div class="stat-card">
          <div class="stat-num" style="color: var(--blue);">69 / 69</div>
          <div class="stat-label">Tests Passing</div>
          <div class="stat-sub">Unit & Integration Suite</div>
        </div>
      </div>

      <div class="card border-cyan" style="text-align: center; padding: 24px;">
        <div class="card-title" style="color: var(--cyan); justify-content: center; font-size: 1.1rem;">OPEN FOR QUESTIONS & COMMITTEE FEEDBACK</div>
        <p style="font-size: 1rem; margin-top: 8px;"><strong>Candidate:</strong> Mohith Chandra | Department of Computer Science & Engineering, IIT Patna</p>
        <p style="font-size: 0.9rem; color: var(--text-muted); margin-top: 4px;">GitHub: <strong>https://github.com/MohithChandra07/Talkhier_BTP</strong></p>
        <p style="font-size: 0.8rem; color: var(--text-dim); margin-top: 4px;">Complete implementation, 63 raw execution traces, unit tests, and Sprint 1-4.3 progress reports available online.</p>
      </div>
    </div>

  </main>

  <footer>
    <div style="font-size: 0.8rem; color: var(--text-dim);">Navigate: ◀ Left / Right Arrows ▶ or Spacebar • Press F for Fullscreen</div>
    <div style="display: flex; gap: 12px;">
      <button class="btn" onclick="prevSlide()">◀ Previous</button>
      <button class="btn" onclick="nextSlide()">Next ▶</button>
    </div>
  </footer>

  <script>
    let currentSlide = 1;
    const totalSlides = 18;

    function showSlide(num) {
      if (num < 1) num = 1;
      if (num > totalSlides) num = totalSlides;
      currentSlide = num;

      document.querySelectorAll('.slide').forEach(s => s.classList.remove('active'));
      const activeSlide = document.getElementById(`slide-${num}`);
      if (activeSlide) activeSlide.classList.add('active');

      document.getElementById('progress-indicator').innerText = `Slide ${currentSlide} / ${totalSlides}`;
    }

    function prevSlide() { showSlide(currentSlide - 1); }
    function nextSlide() { showSlide(currentSlide + 1); }

    document.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'PageDown') {
        nextSlide();
      } else if (e.key === 'ArrowLeft' || e.key === 'PageUp') {
        prevSlide();
      } else if (e.key === 'f' || e.key === 'F') {
        if (!document.fullscreenElement) {
          document.documentElement.requestFullscreen();
        } else {
          document.exitFullscreen();
        }
      }
    });
  </script>
</body>
</html>
"""

if __name__ == "__main__":
    out_paths = [
        "/Users/mohithchandra/BTP/talkhier/presentations/presentation.html",
        "/Users/mohithchandra/BTP/presentation.html"
    ]
    for p in out_paths:
        with open(p, "w", encoding="utf-8") as f:
            f.write(HTML_CONTENT)
        print(f"Generated HTML presentation at: {p}")
