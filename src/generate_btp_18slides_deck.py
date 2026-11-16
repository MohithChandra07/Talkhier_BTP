#!/usr/bin/env python3
"""
Generate an 18-slide, publication-grade 16:9 PowerPoint presentation
for TalkHier BTP Final Presentation.
Theme: Dark Modern Research (Slate 900 background, Cyan/Emerald/Amber accents).
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

def build_presentation(output_pptx_path):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Dark Modern Research Palette
    BG_DARK = RGBColor(15, 23, 42)       # Slate 900
    CARD_BG = RGBColor(30, 41, 59)       # Slate 800
    CARD_BORDER = RGBColor(51, 65, 85)   # Slate 700
    CARD_INNER = RGBColor(24, 34, 53)    # Slightly darker slate
    TEXT_LIGHT = RGBColor(248, 250, 252) # Slate 50
    TEXT_MUTED = RGBColor(148, 163, 184) # Slate 400
    TEXT_DIM = RGBColor(100, 116, 139)   # Slate 500

    ACCENT_CYAN = RGBColor(56, 189, 248) # Sky 400
    ACCENT_BLUE = RGBColor(96, 165, 250) # Blue 400
    ACCENT_GREEN = RGBColor(52, 211, 153)# Emerald 400
    ACCENT_ROSE = RGBColor(251, 113, 133)# Rose 400
    ACCENT_AMBER = RGBColor(251, 191, 36)# Amber 400

    def apply_dark_background(slide):
        bg = slide.background
        fill = bg.fill
        fill.solid()
        fill.fore_color.rgb = BG_DARK

    def add_header(slide, category, title, subtitle=None, slide_num=None):
        apply_dark_background(slide)
        
        # Category Tag
        cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.0), Inches(0.28))
        tf_cat = cat_box.text_frame
        tf_cat.word_wrap = True
        tf_cat.margin_left = tf_cat.margin_top = tf_cat.margin_right = tf_cat.margin_bottom = 0
        p_cat = tf_cat.paragraphs[0]
        p_cat.text = category.upper()
        p_cat.font.size = Pt(10)
        p_cat.font.bold = True
        p_cat.font.color.rgb = ACCENT_CYAN

        # Title
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.68), Inches(10.5), Inches(0.55))
        tf_title = title_box.text_frame
        tf_title.word_wrap = True
        tf_title.margin_left = tf_title.margin_top = tf_title.margin_right = tf_title.margin_bottom = 0
        p_title = tf_title.paragraphs[0]
        p_title.text = title
        p_title.font.size = Pt(22)
        p_title.font.bold = True
        p_title.font.color.rgb = TEXT_LIGHT

        # Subtitle if present
        if subtitle:
            sub_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.22), Inches(11.0), Inches(0.35))
            tf_sub = sub_box.text_frame
            tf_sub.word_wrap = True
            tf_sub.margin_left = tf_sub.margin_top = tf_sub.margin_right = tf_sub.margin_bottom = 0
            p_sub = tf_sub.paragraphs[0]
            p_sub.text = subtitle
            p_sub.font.size = Pt(12)
            p_sub.font.color.rgb = TEXT_MUTED

        # Slide Number Badge (Top Right)
        if slide_num:
            num_box = slide.shapes.add_textbox(Inches(11.3), Inches(0.4), Inches(1.2), Inches(0.3))
            tf_num = num_box.text_frame
            tf_num.margin_left = tf_num.margin_top = tf_num.margin_right = tf_num.margin_bottom = 0
            p_num = tf_num.paragraphs[0]
            p_num.text = f"{slide_num:02d} / 18"
            p_num.alignment = PP_ALIGN.RIGHT
            p_num.font.size = Pt(11)
            p_num.font.bold = True
            p_num.font.color.rgb = TEXT_DIM

    def add_card(slide, left, top, width, height, bg=CARD_BG, border=CARD_BORDER):
        shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        shape.fill.solid()
        shape.fill.fore_color.rgb = bg
        shape.line.color.rgb = border
        shape.line.width = Pt(1.2)
        return shape

    def add_badge(slide, left, top, width, height, text, bg=CARD_INNER, text_color=ACCENT_CYAN, font_size=10):
        badge = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        badge.fill.solid()
        badge.fill.fore_color.rgb = bg
        badge.line.color.rgb = text_color
        badge.line.width = Pt(1)
        tf = badge.text_frame
        tf.word_wrap = False
        tf.margin_top = tf.margin_bottom = tf.margin_left = tf.margin_right = 0
        p = tf.paragraphs[0]
        p.text = text
        p.alignment = PP_ALIGN.CENTER
        p.font.size = Pt(font_size)
        p.font.bold = True
        p.font.color.rgb = text_color
        return badge

    def add_stat_box(slide, left, top, width, height, stat_str, label_str, num_color=ACCENT_CYAN, sublabel=None):
        card = add_card(slide, left, top, width, height)
        tf = card.text_frame
        tf.word_wrap = True
        tf.margin_top = Inches(0.12)
        tf.margin_left = tf.margin_right = Inches(0.15)
        
        p0 = tf.paragraphs[0]
        p0.text = stat_str
        p0.alignment = PP_ALIGN.CENTER
        p0.font.size = Pt(28)
        p0.font.bold = True
        p0.font.color.rgb = num_color

        p1 = tf.add_paragraph()
        p1.text = label_str
        p1.alignment = PP_ALIGN.CENTER
        p1.font.size = Pt(11)
        p1.font.bold = True
        p1.font.color.rgb = TEXT_LIGHT

        if sublabel:
            p2 = tf.add_paragraph()
            p2.text = sublabel
            p2.alignment = PP_ALIGN.CENTER
            p2.font.size = Pt(9)
            p2.font.color.rgb = TEXT_MUTED

    # =========================================================================
    # SLIDE 1: TITLE SLIDE
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    apply_dark_background(s1)

    # Decorative header glow
    top_bar = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(0.6), Inches(11.733), Inches(0.08))
    top_bar.fill.solid()
    top_bar.fill.fore_color.rgb = ACCENT_CYAN
    top_bar.line.fill.background()

    # Title & Subtitle Box
    t_box = s1.shapes.add_textbox(Inches(0.8), Inches(1.0), Inches(11.733), Inches(2.2))
    tf1 = t_box.text_frame
    tf1.word_wrap = True
    
    p0 = tf1.paragraphs[0]
    p0.text = "BACHELOR THESIS PROJECT (BTP) PRESENTATION"
    p0.font.size = Pt(11)
    p0.font.bold = True
    p0.font.color.rgb = ACCENT_CYAN
    p0.space_after = Pt(12)

    p1 = tf1.add_paragraph()
    p1.text = "Enhancing Hierarchical Multi-Agent Reasoning\nThrough Deterministic Logical Verification"
    p1.font.size = Pt(32)
    p1.font.bold = True
    p1.font.color.rgb = TEXT_LIGHT
    p1.space_after = Pt(14)

    p2 = tf1.add_paragraph()
    p2.text = "Investigating Vulnerabilities in Sony's TalkHier Framework & Integrating SymPy DPLL SAT Refutation"
    p2.font.size = Pt(15)
    p2.font.color.rgb = TEXT_MUTED

    # Candidate Meta Card
    card_meta = add_card(s1, Inches(0.8), Inches(3.6), Inches(6.0), Inches(2.2))
    tf_m = card_meta.text_frame
    tf_m.word_wrap = True
    tf_m.margin_left = tf_m.margin_top = Inches(0.25)
    
    pm0 = tf_m.paragraphs[0]
    pm0.text = "RESEARCHER & AFFILIATION"
    pm0.font.size = Pt(10)
    pm0.font.bold = True
    pm0.font.color.rgb = ACCENT_BLUE

    pm1 = tf_m.add_paragraph()
    pm1.text = "Candidate: Mohith Chandra"
    pm1.font.size = Pt(14)
    pm1.font.bold = True
    pm1.font.color.rgb = TEXT_LIGHT

    pm2 = tf_m.add_paragraph()
    pm2.text = "Institution: Indian Institute of Technology Patna (IIT Patna)"
    pm2.font.size = Pt(12)
    pm2.font.color.rgb = TEXT_MUTED

    pm3 = tf_m.add_paragraph()
    pm3.text = "Department: Computer Science and Engineering"
    pm3.font.size = Pt(12)
    pm3.font.color.rgb = TEXT_MUTED

    # Project Verified Badges Card
    card_badges = add_card(s1, Inches(7.1), Inches(3.6), Inches(5.433), Inches(2.2))
    tf_b = card_badges.text_frame
    tf_b.word_wrap = True
    tf_b.margin_left = tf_b.margin_top = Inches(0.25)
    
    pb0 = tf_b.paragraphs[0]
    pb0.text = "VERIFIED PROJECT MILESTONES"
    pb0.font.size = Pt(10)
    pb0.font.bold = True
    pb0.font.color.rgb = ACCENT_GREEN

    pb1 = tf_b.add_paragraph()
    pb1.text = "• 100.0% Deductive Accuracy (24/24 on Propositional Logic)"
    pb1.font.size = Pt(12)
    pb1.font.bold = True
    pb1.font.color.rgb = TEXT_LIGHT

    pb2 = tf_b.add_paragraph()
    pb2.text = "• 0 Harmful Revisions Observed Across 35 Benchmark Tasks"
    pb2.font.size = Pt(12)
    pb2.font.bold = True
    pb2.font.color.rgb = TEXT_LIGHT

    pb3 = tf_b.add_paragraph()
    pb3.text = "• 69/69 Unit & Integration Tests Passing in CI Test Suite"
    pb3.font.size = Pt(12)
    pb3.font.bold = True
    pb3.font.color.rgb = TEXT_LIGHT

    pb4 = tf_b.add_paragraph()
    pb4.text = "• Built upon Sony AI TalkHier Framework (arXiv:2502.11098)"
    pb4.font.size = Pt(11)
    pb4.font.color.rgb = TEXT_MUTED

    # Bottom Footer
    foot_box = s1.shapes.add_textbox(Inches(0.8), Inches(6.5), Inches(11.733), Inches(0.4))
    tf_f = foot_box.text_frame
    p_f = tf_f.paragraphs[0]
    p_f.text = "BTP Progress Presentation • November 2026 • Code & Traces: https://github.com/MohithChandra07/Talkhier_BTP"
    p_f.font.size = Pt(10)
    p_f.font.color.rgb = TEXT_DIM

    # =========================================================================
    # SLIDE 2: RESEARCH MOTIVATION
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    add_header(s2, "1. Introduction & Research Motivation", 
               "The Limits of Multi-Agent Deliberation in Formal Reasoning",
               "Why scaling agent debates fails to guarantee deductive correctness without symbolic verification", 2)

    c2_l = add_card(s2, Inches(0.8), Inches(1.8), Inches(5.6), Inches(4.0))
    tf2_l = c2_l.text_frame
    tf2_l.margin_left = tf2_l.margin_top = Inches(0.25)
    tf2_l.word_wrap = True
    
    p = tf2_l.paragraphs[0]
    p.text = "THE PROMISE OF MULTI-AGENT SYSTEMS"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = ACCENT_CYAN

    bullets_l = [
        ("Distributed Specialization:", " Assigning distinct roles (Solvers, Evaluators, Revisors) improves problem decomposition."),
        ("Iterative Refinement:", " Multiple passes of peer critique help catch surface-level hallucinations and formatting slips."),
        ("Broad Empirical Success:", " Shown to outperform single-agent baselines on open-ended QA, creative generation, and code synthesis.")
    ]
    for b_title, b_desc in bullets_l:
        p = tf2_l.add_paragraph()
        p.space_before = Pt(10)
        run1 = p.add_run()
        run1.text = "• " + b_title
        run1.font.bold = True
        run1.font.size = Pt(12)
        run1.font.color.rgb = TEXT_LIGHT
        run2 = p.add_run()
        run2.text = b_desc
        run2.font.size = Pt(12)
        run2.font.color.rgb = TEXT_MUTED

    c2_r = add_card(s2, Inches(6.9), Inches(1.8), Inches(5.6), Inches(4.0))
    tf2_r = c2_r.text_frame
    tf2_r.margin_left = tf2_r.margin_top = Inches(0.25)
    tf2_r.word_wrap = True

    p = tf2_r.paragraphs[0]
    p.text = "THE FORMAL LOGIC BOTTLENECK"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = ACCENT_ROSE

    bullets_r = [
        ("Consensus != Truth:", " Democratic voting among LLMs cannot verify mathematical validity or find rigorous counterexamples."),
        ("Correlated Hallucinations:", " When an initial answer is invalid, evaluators frequently agree with flawed natural language reasoning."),
        ("Sycophantic Flips:", " Uncalibrated revisors accept incorrect peer critiques, causing harmful revisions (flipping right to wrong).")
    ]
    for b_title, b_desc in bullets_r:
        p = tf2_r.add_paragraph()
        p.space_before = Pt(10)
        run1 = p.add_run()
        run1.text = "• " + b_title
        run1.font.bold = True
        run1.font.size = Pt(12)
        run1.font.color.rgb = TEXT_LIGHT
        run2 = p.add_run()
        run2.text = b_desc
        run2.font.size = Pt(12)
        run2.font.color.rgb = TEXT_MUTED

    # Bottom Thesis Banner
    c2_b = add_card(s2, Inches(0.8), Inches(6.0), Inches(11.733), Inches(0.9), bg=CARD_INNER, border=ACCENT_CYAN)
    tf2_b = c2_b.text_frame
    tf2_b.word_wrap = True
    tf2_b.margin_left = Inches(0.3); tf2_b.margin_top = Inches(0.18)
    pb = tf2_b.paragraphs[0]
    pb.text = "CORE RESEARCH THESIS: More agents do not automatically guarantee more reliable reasoning. Formal deductive tasks require deterministic symbolic proof, not probabilistic consensus."
    pb.font.size = Pt(12)
    pb.font.bold = True
    pb.font.color.rgb = ACCENT_CYAN

    # =========================================================================
    # SLIDE 3: UNDERSTANDING ORIGINAL TALKHIER
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    add_header(s3, "1. Introduction & Research Motivation",
               "Understanding the Foundation: Sony TalkHier Framework",
               "A collaborative framework for LLM multi-agent systems via structured communication (Wang et al., Feb 2025)", 3)

    # 3 Horizontal Cards
    card_w = Inches(3.7)
    card_h = Inches(3.6)
    
    c3_1 = add_card(s3, Inches(0.8), Inches(1.8), card_w, card_h)
    tf3_1 = c3_1.text_frame
    tf3_1.margin_left = tf3_1.margin_top = Inches(0.2)
    tf3_1.word_wrap = True
    p = tf3_1.paragraphs[0]
    p.text = "1. STRUCTURED PROTOCOL"
    p.font.size = Pt(11); p.font.bold = True; p.font.color.rgb = ACCENT_BLUE
    items1 = [
        ("Message (M_ij):", " Explicit task instruction and answer content."),
        ("Background (B_ij):", " Shared problem context and constraints."),
        ("Intermediate Output (I_ij):", " Step-by-step reasoning derivations and rationale.")
    ]
    for k, v in items1:
        p = tf3_1.add_paragraph(); p.space_before = Pt(8)
        r1 = p.add_run(); r1.text = k + " "; r1.font.bold = True; r1.font.size = Pt(11); r1.font.color.rgb = TEXT_LIGHT
        r2 = p.add_run(); r2.text = v; r2.font.size = Pt(11); r2.font.color.rgb = TEXT_MUTED

    c3_2 = add_card(s3, Inches(4.8), Inches(1.8), card_w, card_h)
    tf3_2 = c3_2.text_frame
    tf3_2.margin_left = tf3_2.margin_top = Inches(0.2)
    tf3_2.word_wrap = True
    p = tf3_2.paragraphs[0]
    p.text = "2. HIERARCHICAL ROLES"
    p.font.size = Pt(11); p.font.bold = True; p.font.color.rgb = ACCENT_CYAN
    items2 = [
        ("Supervisor Agents:", " Dynamically choose which agent speaks next."),
        ("Member Agents:", " Task executors focusing on specific sub-goals."),
        ("Evaluator Team:", " Domain-specific evaluators (Truth Table, Counterexample, Formal Logic).")
    ]
    for k, v in items2:
        p = tf3_2.add_paragraph(); p.space_before = Pt(8)
        r1 = p.add_run(); r1.text = k + " "; r1.font.bold = True; r1.font.size = Pt(11); r1.font.color.rgb = TEXT_LIGHT
        r2 = p.add_run(); r2.text = v; r2.font.size = Pt(11); r2.font.color.rgb = TEXT_MUTED

    c3_3 = add_card(s3, Inches(8.8), Inches(1.8), card_w, card_h)
    tf3_3 = c3_3.text_frame
    tf3_3.margin_left = tf3_3.margin_top = Inches(0.2)
    tf3_3.word_wrap = True
    p = tf3_3.paragraphs[0]
    p.text = "3. TWO-PASS REFINEMENT"
    p.font.size = Pt(11); p.font.bold = True; p.font.color.rgb = ACCENT_GREEN
    items3 = [
        ("Pass 1 (Solve):", " Solver agent generates initial answer candidate A0."),
        ("Evaluation:", " Evaluator team generates numerical scores & critiques."),
        ("Pass 2 (Revise):", " Aggregator synthesizes feedback; Revisor produces final answer.")
    ]
    for k, v in items3:
        p = tf3_3.add_paragraph(); p.space_before = Pt(8)
        r1 = p.add_run(); r1.text = k + " "; r1.font.bold = True; r1.font.size = Pt(11); r1.font.color.rgb = TEXT_LIGHT
        r2 = p.add_run(); r2.text = v; r2.font.size = Pt(11); r2.font.color.rgb = TEXT_MUTED

    # Bottom Flow Diagram Representation
    c3_bot = add_card(s3, Inches(0.8), Inches(5.6), Inches(11.733), Inches(1.3))
    tf_cb = c3_bot.text_frame
    tf_cb.margin_left = Inches(0.25); tf_cb.margin_top = Inches(0.15)
    p = tf_cb.paragraphs[0]
    p.text = "ORIGINAL TALKHIER ARCHITECTURAL FLOW (Wang et al., 2025)"
    p.font.size = Pt(10); p.font.bold = True; p.font.color.rgb = TEXT_DIM
    
    p2 = tf_cb.add_paragraph(); p2.space_before = Pt(6)
    p2.text = "Problem Input  ──▶  Answer Generator (A0)  ──▶  Evaluator Supervisor  ──▶  Specialized Evaluators  ──▶  Aggregator  ──▶  Revisor  ──▶  Final Answer"
    p2.font.size = Pt(12); p2.font.bold = True; p2.font.color.rgb = ACCENT_CYAN

    # =========================================================================
    # SLIDE 4: RESEARCH GAPS & THREE LOOPHOLES
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    add_header(s4, "1. Introduction & Research Motivation",
               "Three Critical Loopholes Discovered via Empirical Audit",
               "Systematic auditing on MMLU Formal Logic revealed that TalkHier's evaluation system frequently broke down", 4)

    # 3 Failure Mode Columns
    w4 = Inches(3.7)
    h4 = Inches(4.9)

    c4_1 = add_card(s4, Inches(0.8), Inches(1.8), w4, h4)
    tf4_1 = c4_1.text_frame; tf4_1.margin_left = tf4_1.margin_top = Inches(0.25); tf4_1.word_wrap = True
    p = tf4_1.paragraphs[0]; p.text = "LOOPHOLE 1"; p.font.size = Pt(10); p.font.bold = True; p.font.color.rgb = ACCENT_ROSE
    p = tf4_1.add_paragraph(); p.text = "Evaluator Bypass\n(Ad-hoc Routing)"; p.font.size = Pt(15); p.font.bold = True; p.font.color.rgb = TEXT_LIGHT
    p.space_after = Pt(12)
    items_l1 = [
        "In the original implementation, the Evaluator Supervisor decided routing dynamically.",
        "On >60% of formal logic questions, the supervisor terminated immediately, skipping evaluators completely.",
        "The supervisor synthesized mock scores itself without invoking member agents.",
        "Impact: Multi-agent evaluation was essentially dormant in practice."
    ]
    for it in items_l1:
        p = tf4_1.add_paragraph(); p.space_before = Pt(6)
        p.text = "• " + it; p.font.size = Pt(11); p.font.color.rgb = TEXT_MUTED

    c4_2 = add_card(s4, Inches(4.8), Inches(1.8), w4, h4)
    tf4_2 = c4_2.text_frame; tf4_2.margin_left = tf4_2.margin_top = Inches(0.25); tf4_2.word_wrap = True
    p = tf4_2.paragraphs[0]; p.text = "LOOPHOLE 2"; p.font.size = Pt(10); p.font.bold = True; p.font.color.rgb = ACCENT_AMBER
    p = tf4_2.add_paragraph(); p.text = "Subjective Evaluation\n(No Formal Grounding)"; p.font.size = Pt(15); p.font.bold = True; p.font.color.rgb = TEXT_LIGHT
    p.space_after = Pt(12)
    items_l2 = [
        "When evaluators were invoked, they evaluated logic purely via natural language prompting.",
        "Evaluators lacked formal truth tables, SAT solvers, or mathematical proof mechanisms.",
        "Evaluators suffered from false consensus, agreeing with subtle fallacies (e.g. affirming the consequent).",
        "Impact: Evaluator feedback was noisy, uncalibrated, and often incorrect."
    ]
    for it in items_l2:
        p = tf4_2.add_paragraph(); p.space_before = Pt(6)
        p.text = "• " + it; p.font.size = Pt(11); p.font.color.rgb = TEXT_MUTED

    c4_3 = add_card(s4, Inches(8.8), Inches(1.8), w4, h4)
    tf4_3 = c4_3.text_frame; tf4_3.margin_left = tf4_3.margin_top = Inches(0.25); tf4_3.word_wrap = True
    p = tf4_3.paragraphs[0]; p.text = "LOOPHOLE 3"; p.font.size = Pt(10); p.font.bold = True; p.font.color.rgb = ACCENT_ROSE
    p = tf4_3.add_paragraph(); p.text = "Harmful Revisions\n(Sycophantic Drift)"; p.font.size = Pt(15); p.font.bold = True; p.font.color.rgb = TEXT_LIGHT
    p.space_after = Pt(12)
    items_l3 = [
        "The Revisor agent had no verification safeguards or confidence thresholds.",
        "When evaluators produced flawed critiques of a correct initial answer (A0), the Revisor blindly accepted them.",
        "In early benchmarks, correct answers were repeatedly flipped to incorrect answers (Harmful Revision).",
        "Impact: The multi-agent evaluation pass degraded accuracy compared to single agent."
    ]
    for it in items_l3:
        p = tf4_3.add_paragraph(); p.space_before = Pt(6)
        p.text = "• " + it; p.font.size = Pt(11); p.font.color.rgb = TEXT_MUTED

    # =========================================================================
    # SLIDE 5: LOOPHOLE 1 - EVALUATOR EXECUTION RELIABILITY
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    add_header(s5, "2. Loophole 1 & Sprint 3 Resolution",
               "Loophole 1: Evaluator Execution Reliability",
               "Auditing how the original Evaluator Supervisor simulated evaluations rather than running actual agents", 5)

    c5_l = add_card(s5, Inches(0.8), Inches(1.8), Inches(5.6), Inches(4.9))
    tf5_l = c5_l.text_frame; tf5_l.margin_left = tf5_l.margin_top = Inches(0.25); tf5_l.word_wrap = True
    p = tf5_l.paragraphs[0]; p.text = "ORIGINAL BEHAVIOUR (SIMULATED EVALUATION)"; p.font.size = Pt(11); p.font.bold = True; p.font.color.rgb = ACCENT_ROSE
    
    p = tf5_l.add_paragraph(); p.space_before = Pt(10)
    p.text = "In the baseline codebase, the Evaluator Supervisor used unconstrained LLM calls with instructions to 'coordinate evaluation':"
    p.font.size = Pt(11); p.font.color.rgb = TEXT_MUTED

    # Code / trace snippet box
    c_snip1 = add_card(s5, Inches(1.0), Inches(2.7), Inches(5.2), Inches(1.8), bg=CARD_INNER, border=CARD_BORDER)
    tf_snip1 = c_snip1.text_frame; tf_snip1.margin_left = tf_snip1.margin_top = Inches(0.15)
    p = tf_snip1.paragraphs[0]
    p.text = 'Trace Audit: Problem 3 (Baseline TalkHier)\n> Supervisor invoked: True\n> Truth Table Agent invoked: FALSE (Skipped)\n> Counterexample Agent invoked: FALSE (Skipped)\n> Supervisor Output: Synthesized mock scores (8/10)\n> Evaluation status: FABRICATED'
    p.font.size = Pt(9.5); p.font.color.rgb = ACCENT_ROSE

    p = tf5_l.add_paragraph(); p.space_before = Pt(12)
    p.text = "Flaw: The supervisor LLM took the path of least resistance, fabricating evaluation numbers in a single prompt rather than dispatching independent agents."
    p.font.size = Pt(11); p.font.color.rgb = TEXT_LIGHT

    c5_r = add_card(s5, Inches(6.9), Inches(1.8), Inches(5.6), Inches(4.9))
    tf5_r = c5_r.text_frame; tf5_r.margin_left = tf5_r.margin_top = Inches(0.25); tf5_r.word_wrap = True
    p = tf5_r.paragraphs[0]; p.text = "OUR CORRECTED DISPATCH PIPELINE"; p.font.size = Pt(11); p.font.bold = True; p.font.color.rgb = ACCENT_GREEN
    
    p = tf5_r.add_paragraph(); p.space_before = Pt(10)
    p.text = "We eliminated supervisor autonomy by moving orchestration into an authoritative LangGraph state machine:"
    p.font.size = Pt(11); p.font.color.rgb = TEXT_MUTED

    c_snip2 = add_card(s5, Inches(7.1), Inches(2.7), Inches(5.2), Inches(1.8), bg=CARD_INNER, border=CARD_BORDER)
    tf_snip2 = c_snip2.text_frame; tf_snip2.margin_left = tf_snip2.margin_top = Inches(0.15)
    p = tf_snip2.paragraphs[0]
    p.text = 'LangGraph Enforcement (Sprint 3)\n> Evaluator Prep Node: Classifies taxonomy\n> Truth Table Agent: INVOKED (Attempt 1 Success)\n> Counterexample Agent: INVOKED (Attempt 1 Success)\n> Formal Logic Agent: INVOKED (Attempt 1 Success)\n> Aggregator: Reconciles independent scores\n> Dispatch Status: 100% EXPLICIT & AUDITABLE'
    p.font.size = Pt(9.5); p.font.color.rgb = ACCENT_GREEN

    p = tf5_r.add_paragraph(); p.space_before = Pt(12)
    p.text = "Fix: Supervisor can no longer fabricate scores. Every evaluator is an isolated node that must return a structured Pydantic payload or trigger an error."
    p.font.size = Pt(11); p.font.color.rgb = TEXT_LIGHT

    # =========================================================================
    # SLIDE 6: SPRINT 3 - MANDATORY EVALUATOR EXECUTION
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    add_header(s6, "2. Loophole 1 & Sprint 3 Resolution",
               "Sprint 3: Graph-Level Mandatory Evaluation Pipeline",
               "Replacing probabilistic supervisor routing with a deterministic LangGraph state machine", 6)

    # 4 Key Pillars of Sprint 3
    card_w = Inches(5.6)
    card_h = Inches(2.3)

    c6_1 = add_card(s6, Inches(0.8), Inches(1.8), card_w, card_h)
    tf = c6_1.text_frame; tf.margin_left = tf.margin_top = Inches(0.2); tf.word_wrap = True
    p = tf.paragraphs[0]; p.text = "1. SEQUENTIAL STATE MACHINE DISPATCH"; p.font.size = Pt(11); p.font.bold = True; p.font.color.rgb = ACCENT_CYAN
    p = tf.add_paragraph(); p.space_before = Pt(6)
    p.text = "Built graph_dispatch.py using LangGraph StateGraph. The execution order is deterministic: Evaluator Prep ──▶ Evaluator Team ──▶ Aggregator ──▶ Revisor. No agent can terminate the graph early."
    p.font.size = Pt(11); p.font.color.rgb = TEXT_MUTED

    c6_2 = add_card(s6, Inches(6.9), Inches(1.8), card_w, card_h)
    tf = c6_2.text_frame; tf.margin_left = tf.margin_top = Inches(0.2); tf.word_wrap = True
    p = tf.paragraphs[0]; p.text = "2. IMMUTABLE BASELINE ANSWER (A0)"; p.font.size = Pt(11); p.font.bold = True; p.font.color.rgb = ACCENT_BLUE
    p = tf.add_paragraph(); p.space_before = Pt(6)
    p.text = "Initial Answer A0 and its derivation are frozen in state as an immutable baseline. Evaluators critique A0 without mutating it. This prevents silent answer overwrites and enables strict revision auditing."
    p.font.size = Pt(11); p.font.color.rgb = TEXT_MUTED

    c6_3 = add_card(s6, Inches(0.8), Inches(4.4), card_w, card_h)
    tf = c6_3.text_frame; tf.margin_left = tf.margin_top = Inches(0.2); tf.word_wrap = True
    p = tf.paragraphs[0]; p.text = "3. STANDARDIZED EVALUATOR STATUSES"; p.font.size = Pt(11); p.font.bold = True; p.font.color.rgb = ACCENT_GREEN
    p = tf.add_paragraph(); p.space_before = Pt(6)
    p.text = "Standardized evaluator output schema to three explicit states: VALID (score 0-10), NOT_APPLICABLE (domain mismatch), or NO_EVALUATION (retry exhausted). Aggregator only weights applicable scores."
    p.font.size = Pt(11); p.font.color.rgb = TEXT_MUTED

    c6_4 = add_card(s6, Inches(6.9), Inches(4.4), card_w, card_h)
    tf = c6_4.text_frame; tf.margin_left = tf.margin_top = Inches(0.2); tf.word_wrap = True
    p = tf.paragraphs[0]; p.text = "4. TAXONOMY-DRIVEN EVALUATOR PREP"; p.font.size = Pt(11); p.font.bold = True; p.font.color.rgb = ACCENT_AMBER
    p = tf.add_paragraph(); p.space_before = Pt(6)
    p.text = "Added an Evaluator Prep stage prior to dispatch. Automatically categorizes input into Propositional Logic, Predicate Logic, or Rhetorical Fallacies, ensuring only relevant evaluators are activated."
    p.font.size = Pt(11); p.font.color.rgb = TEXT_MUTED

    # =========================================================================
    # SLIDE 7: SPRINT 3 RESULTS & OPTIMIZATION
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    add_header(s7, "2. Loophole 1 & Sprint 3 Resolution",
               "Sprint 3 Results: 100% Invocations & 39.2% Latency Reduction",
               "Empirical verification across baseline replication and optimized selective dispatch", 7)

    # Left: Comparison Table Card
    c7_l = add_card(s7, Inches(0.8), Inches(1.8), Inches(7.5), Inches(4.8))
    tf7 = c7_l.text_frame; tf7.margin_left = tf7.margin_top = Inches(0.25); tf7.word_wrap = True
    p = tf7.paragraphs[0]; p.text = "SPRINT 3 PILOT BENCHMARK COMPARISON (5 PROBLEMS)"; p.font.size = Pt(11); p.font.bold = True; p.font.color.rgb = ACCENT_CYAN

    # Table
    table_shape = s7.shapes.add_table(6, 4, Inches(1.0), Inches(2.3), Inches(7.1), Inches(3.8))
    t = table_shape.table
    t.columns[0].width = Inches(2.4)
    t.columns[1].width = Inches(1.5)
    t.columns[2].width = Inches(1.6)
    t.columns[3].width = Inches(1.6)

    table_data = [
        ["Metric", "Sprint 3 Baseline", "Sprint 3 Opt", "Improvement"],
        ["Evaluator Invocations", "25 / 25 (100%)", "25 / 25 (100%)", "100% Verified"],
        ["Evaluator Retries", "Multiple failures", "0 / 25 (0%)", "100% 1st Attempt"],
        ["Final Accuracy", "3 / 5 (60.0%)", "4 / 5 (80.0%)", "+20.0% Gain"],
        ["Harmful Revisions", "1 (Problem 3 wrong)", "0 (Problem 3 fixed)", "Eliminated (0%)"],
        ["Total Runtime", "1,919.7s (~32 min)", "1,166.6s (~19 min)", "39.2% Faster"]
    ]

    for r_idx, row in enumerate(table_data):
        for c_idx, val in enumerate(row):
            cell = t.cell(r_idx, c_idx)
            cell.text = val
            cell.fill.solid()
            if r_idx == 0:
                cell.fill.fore_color.rgb = CARD_INNER
            else:
                cell.fill.fore_color.rgb = CARD_BG
            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER if c_idx > 0 else PP_ALIGN.LEFT
            p.font.size = Pt(10.5)
            p.font.color.rgb = ACCENT_CYAN if (r_idx == 0 or c_idx == 3) else TEXT_LIGHT
            if r_idx == 0 or c_idx == 3:
                p.font.bold = True

    # Right: 3 Key Achievement Cards
    c7_r1 = add_card(s7, Inches(8.6), Inches(1.8), Inches(3.933), Inches(1.4))
    tf = c7_r1.text_frame; tf.margin_left = tf.margin_top = Inches(0.18); tf.word_wrap = True
    p = tf.paragraphs[0]; p.text = "100% EVALUATOR COMPLIANCE"; p.font.size = Pt(10); p.font.bold = True; p.font.color.rgb = ACCENT_GREEN
    p = tf.add_paragraph(); p.text = "Zero evaluator bypass. Every problem generated full evaluator telemetry across all 5 test questions."
    p.font.size = Pt(10); p.font.color.rgb = TEXT_MUTED

    c7_r2 = add_card(s7, Inches(8.6), Inches(3.4), Inches(3.933), Inches(1.4))
    tf = c7_r2.text_frame; tf.margin_left = tf.margin_top = Inches(0.18); tf.word_wrap = True
    p = tf.paragraphs[0]; p.text = "35% TOKEN CALL REDUCTION"; p.font.size = Pt(10); p.font.bold = True; p.font.color.rgb = ACCENT_CYAN
    p = tf.add_paragraph(); p.text = "Selective dispatch reduced evaluator invocations from 20 to 13 calls by skipping irrelevant domains."
    p.font.size = Pt(10); p.font.color.rgb = TEXT_MUTED

    c7_r3 = add_card(s7, Inches(8.6), Inches(5.0), Inches(3.933), Inches(1.6))
    tf = c7_r3.text_frame; tf.margin_left = tf.margin_top = Inches(0.18); tf.word_wrap = True
    p = tf.paragraphs[0]; p.text = "37 PASSING UNIT TESTS"; p.font.size = Pt(10); p.font.bold = True; p.font.color.rgb = ACCENT_AMBER
    p = tf.add_paragraph(); p.text = "Validated state transition graph, scoring normalization, and revisor safeguards with zero regressions."
    p.font.size = Pt(10); p.font.color.rgb = TEXT_MUTED

    # =========================================================================
    # SLIDE 8: LOOPHOLE 2 - WHY LLM CONSENSUS IS INSUFFICIENT
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    add_header(s8, "3. Loopholes 2 & 3: Sprint 4 Resolution",
               "Loophole 2: Why Pure LLM Consensus Is Insufficient",
               "An empirical case study on Problem 6: When all neural evaluators agree on a false derivation", 8)

    # Problem 6 Case Study
    c8_top = add_card(s8, Inches(0.8), Inches(1.8), Inches(11.733), Inches(1.5), bg=CARD_INNER)
    tf8_t = c8_top.text_frame; tf8_t.margin_left = Inches(0.25); tf8_t.margin_top = Inches(0.15); tf8_t.word_wrap = True
    p = tf8_t.paragraphs[0]; p.text = "MMLU FORMAL LOGIC — PROBLEM 6 (CANONICAL FAILURE CASE)"; p.font.size = Pt(10); p.font.bold = True; p.font.color.rgb = ACCENT_AMBER
    p = tf8_t.add_paragraph(); p.space_before = Pt(4)
    p.text = "Argument:  ~K ≡ L  /  (K · L) ∨ (K · ~L)\nQuestion: Determine whether the argument is valid or invalid. If invalid, specify the counterexample."
    p.font.size = Pt(12); p.font.bold = True; p.font.color.rgb = TEXT_LIGHT
    p = tf8_t.add_paragraph(); p.space_before = Pt(4)
    p.text = "Ground Truth: Choice 3 (Invalid with counterexample: L = True, K = False)"
    p.font.size = Pt(11); p.font.bold = True; p.font.color.rgb = ACCENT_GREEN

    # Split Comparison
    c8_l = add_card(s8, Inches(0.8), Inches(3.5), Inches(5.6), Inches(3.2))
    tf8_l = c8_l.text_frame; tf8_l.margin_left = tf8_l.margin_top = Inches(0.2); tf8_l.word_wrap = True
    p = tf8_l.paragraphs[0]; p.text = "PURE LLM TEAM (SPRINT 3 OPT)"; p.font.size = Pt(11); p.font.bold = True; p.font.color.rgb = ACCENT_ROSE
    items8_l = [
        "Initial Answer A0: Selected Choice 0 ('Valid', Incorrect).",
        "Formal Logic Evaluator: Hallucinated that Choice 2 was the counterexample.",
        "Truth Table Evaluator: Confused by the disjunctive conclusion.",
        "Revisor Action: Overruled by peer majority, flipped from Choice 0 to Choice 2 (Still Incorrect!).",
        "Result: Correlated hallucination replaced an error with another error."
    ]
    for it in items8_l:
        p = tf8_l.add_paragraph(); p.space_before = Pt(4)
        p.text = "• " + it; p.font.size = Pt(10.5); p.font.color.rgb = TEXT_MUTED

    c8_r = add_card(s8, Inches(6.9), Inches(3.5), Inches(5.6), Inches(3.2))
    tf8_r = c8_r.text_frame; tf8_r.margin_left = tf8_r.margin_top = Inches(0.2); tf8_r.word_wrap = True
    p = tf8_r.paragraphs[0]; p.text = "DETERMINISTIC VERIFIER (SPRINT 4 FULL)"; p.font.size = Pt(11); p.font.bold = True; p.font.color.rgb = ACCENT_GREEN
    items8_r = [
        "SymPy SAT Solver: Solved satisfiability of Premises ∧ ¬Conclusion.",
        "Refutation: SAT proven ──▶ Argument is mathematically INVALID.",
        "Countermodel Extraction: Extracted exact model {L: True, K: False}.",
        "Choice Mapping: Verified that Choice 3 matches the countermodel.",
        "Evidence Injection: Injected proof into evaluators & revisor.",
        "Result: Revisor immediately selected Choice 3 (100% Correct Revision!)."
    ]
    for it in items8_r:
        p = tf8_r.add_paragraph(); p.space_before = Pt(4)
        p.text = "• " + it; p.font.size = Pt(10.5); p.font.color.rgb = TEXT_LIGHT

    # =========================================================================
    # SLIDE 9: SPRINT 4.1 - DETERMINISTIC LOGICAL VERIFIER
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    add_header(s9, "3. Loopholes 2 & 3: Sprint 4 Resolution",
               "Sprint 4.1: Deterministic Propositional Logic Engine",
               "SymPy DPLL SAT refutation and automated countermodel synthesis (logic_verifier.py)", 9)

    # 4 Steps Cards
    step_w = Inches(2.7)
    step_h = Inches(4.8)

    c9_1 = add_card(s9, Inches(0.8), Inches(1.8), step_w, step_h)
    tf = c9_1.text_frame; tf.margin_left = tf.margin_top = Inches(0.2); tf.word_wrap = True
    p = tf.paragraphs[0]; p.text = "STEP 1: NORMALIZATION"; p.font.size = Pt(10); p.font.bold = True; p.font.color.rgb = ACCENT_CYAN
    p = tf.add_paragraph(); p.space_before = Pt(8); p.text = "Slash Notation Parsing"; p.font.size = Pt(13); p.font.bold = True; p.font.color.rgb = TEXT_LIGHT
    p = tf.add_paragraph(); p.space_before = Pt(8)
    p.text = "Extracts premises and conclusion separated by slash notation (/). Normalizes ASCII and Unicode logic symbols:\n• ~ / ¬ ──▶ Not\n• · / ∧ / & ──▶ And\n• ∨ / v ──▶ Or\n• ⊃ / -> ──▶ Implies\n• ≡ / <-> ──▶ Equivalent"
    p.font.size = Pt(10.5); p.font.color.rgb = TEXT_MUTED

    c9_2 = add_card(s9, Inches(3.8), Inches(1.8), step_w, step_h)
    tf = c9_2.text_frame; tf.margin_left = tf.margin_top = Inches(0.2); tf.word_wrap = True
    p = tf.paragraphs[0]; p.text = "STEP 2: PRATT PARSER"; p.font.size = Pt(10); p.font.bold = True; p.font.color.rgb = ACCENT_BLUE
    p = tf.add_paragraph(); p.space_before = Pt(8); p.text = "Recursive AST Builder"; p.font.size = Pt(13); p.font.bold = True; p.font.color.rgb = TEXT_LIGHT
    p = tf.add_paragraph(); p.space_before = Pt(8)
    p.text = "A deterministic precedence parser constructs exact SymPy Boolean expression trees:\n• Validates syntax\n• Enforces operator precedence\n• Detects unsupported first-order predicates or quantifiers\n• Returns NOT_APPLICABLE on syntax errors safely."
    p.font.size = Pt(10.5); p.font.color.rgb = TEXT_MUTED

    c9_3 = add_card(s9, Inches(6.8), Inches(1.8), step_w, step_h)
    tf = c9_3.text_frame; tf.margin_left = tf.margin_top = Inches(0.2); tf.word_wrap = True
    p = tf.paragraphs[0]; p.text = "STEP 3: DPLL SAT SOLVER"; p.font.size = Pt(10); p.font.bold = True; p.font.color.rgb = ACCENT_GREEN
    p = tf.add_paragraph(); p.space_before = Pt(8); p.text = "Refutation Prover"; p.font.size = Pt(13); p.font.bold = True; p.font.color.rgb = TEXT_LIGHT
    p = tf.add_paragraph(); p.space_before = Pt(8)
    p.text = "Formulates validity as refutation satisfiability:\n\n⋀(P_i) ∧ ¬Conclusion\n\n• UNSAT ──▶ Argument is VALID (No counterexample possible)\n• SAT ──▶ Argument is INVALID (Satisfying model is a genuine counterexample)"
    p.font.size = Pt(10.5); p.font.color.rgb = TEXT_MUTED

    c9_4 = add_card(s9, Inches(9.8), Inches(1.8), step_w, step_h)
    tf = c9_4.text_frame; tf.margin_left = tf.margin_top = Inches(0.2); tf.word_wrap = True
    p = tf.paragraphs[0]; p.text = "STEP 4: COUNTERMODEL"; p.font.size = Pt(10); p.font.bold = True; p.font.color.rgb = ACCENT_AMBER
    p = tf.add_paragraph(); p.space_before = Pt(8); p.text = "Answer Choice Matching"; p.font.size = Pt(13); p.font.bold = True; p.font.color.rgb = TEXT_LIGHT
    p = tf.add_paragraph(); p.space_before = Pt(8)
    p.text = "For invalid arguments, extracts truth assignment {Var: True/False}.\n\nMatches countermodel against MCQ options (Choices 0-3).\n\nMarks proven choice index for deterministic injection into revisor."
    p.font.size = Pt(10.5); p.font.color.rgb = TEXT_MUTED

    # =========================================================================
    # SLIDE 10: LOOPHOLE 3 - PREVENTING HARMFUL REVISIONS
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    add_header(s10, "3. Loopholes 2 & 3: Sprint 4 Resolution",
               "Loophole 3: Preventing Harmful Revisions",
               "Protecting correct initial answers (A0) from being flipped by noisy evaluator consensus", 10)

    # Before / After Problem 3 Study
    c10_l = add_card(s10, Inches(0.8), Inches(1.8), Inches(5.6), Inches(4.8))
    tf = c10_l.text_frame; tf.margin_left = tf.margin_top = Inches(0.25); tf.word_wrap = True
    p = tf.paragraphs[0]; p.text = "BEFORE: HARMFUL REVISION IN SPRINT 3 BASELINE"; p.font.size = Pt(11); p.font.bold = True; p.font.color.rgb = ACCENT_ROSE
    p = tf.add_paragraph(); p.space_before = Pt(8)
    p.text = "Problem 3:  ~G ⊃ H,  ~H  /  G  (Valid Disjunctive Syllogism)"
    p.font.size = Pt(11); p.font.bold = True; p.font.color.rgb = TEXT_LIGHT

    bullets_b = [
        ("Initial Answer A0:", " Choice 0 ('Valid', Correct ground truth)."),
        ("Peer Evaluator Trap:", " Evaluators hallucinated that Choice 2 ('Invalid with G=True, H=False') was a valid counterexample."),
        ("Revisor Yielding:", " Aggregator reported an average score of 2.5/10. Revisor accepted the consensus and flipped A0 to Choice 2."),
        ("Net Outcome:", " A correct answer was corrupted by peer debate (Harmful Revision).")
    ]
    for b_t, b_d in bullets_b:
        p = tf.add_paragraph(); p.space_before = Pt(6)
        r1 = p.add_run(); r1.text = "• " + b_t + " "; r1.font.bold = True; r1.font.size = Pt(10.5); r1.font.color.rgb = TEXT_LIGHT
        r2 = p.add_run(); r2.text = b_d; r2.font.size = Pt(10.5); r2.font.color.rgb = TEXT_MUTED

    c10_r = add_card(s10, Inches(6.9), Inches(1.8), Inches(5.6), Inches(4.8))
    tf = c10_r.text_frame; tf.margin_left = tf.margin_top = Inches(0.25); tf.word_wrap = True
    p = tf.paragraphs[0]; p.text = "AFTER: DETERMINISTIC REVISOR SAFEGUARD"; p.font.size = Pt(11); p.font.bold = True; p.font.color.rgb = ACCENT_GREEN
    p = tf.add_paragraph(); p.space_before = Pt(8)
    p.text = "Sprint 4 Solution: Proof Injection & Hard Override"
    p.font.size = Pt(11); p.font.bold = True; p.font.color.rgb = TEXT_LIGHT

    bullets_a = [
        ("SymPy SAT Proof:", " Proved (~G ⊃ H) ∧ ~H ∧ ~G is UNSAT (No counterexample can mathematically exist)."),
        ("Evidence Injection:", " Truth Table evaluator and Revisor were injected with authoritative proof that Choice 0 is uniquely valid."),
        ("Safeguard Override:", " Revisor prompt explicitly bound by deterministic evidence. Peer hallucinations are filtered."),
        ("Net Outcome:", " Choice 0 retained (Neutral Retained Correct). Zero harmful revisions across all 17 revisions.")
    ]
    for b_t, b_d in bullets_a:
        p = tf.add_paragraph(); p.space_before = Pt(6)
        r1 = p.add_run(); r1.text = "• " + b_t + " "; r1.font.bold = True; r1.font.size = Pt(10.5); r1.font.color.rgb = TEXT_LIGHT
        r2 = p.add_run(); r2.text = b_d; r2.font.size = Pt(10.5); r2.font.color.rgb = TEXT_MUTED

    # =========================================================================
    # SLIDE 11: SPRINT 4.2 - INTEGRATION INTO TALKHIER
    # =========================================================================
    s11 = prs.slides.add_slide(blank_layout)
    add_header(s11, "3. Loopholes 2 & 3: Sprint 4 Resolution",
               "Sprint 4.2: Neuro-Symbolic Multi-Agent Architecture",
               "Seamlessly coupling deterministic SAT refutation with hierarchical neural deliberation", 11)

    # 5 Sequential Cards depicting the graph
    c_w = Inches(11.733)
    
    c11_main = add_card(s11, Inches(0.8), Inches(1.8), c_w, Inches(4.8))
    tf = c11_main.text_frame; tf.margin_left = tf.margin_top = Inches(0.25); tf.word_wrap = True
    p = tf.paragraphs[0]; p.text = "INTEGRATED TALKHIER SPRINT 4 DATAFLOW PIPELINE"; p.font.size = Pt(11); p.font.bold = True; p.font.color.rgb = ACCENT_CYAN

    stages = [
        ("1. Input & A0 Generation", "MMLU Formal Logic problem passed to Answer Generator; produces initial choice A0 (frozen in state).", ACCENT_BLUE),
        ("2. Evaluator Prep & Extraction", "Parses question text; attempts deterministic premise/conclusion extraction into Boolean AST.", ACCENT_CYAN),
        ("3. SymPy SAT Engine (Bifurcation)", "If pure propositional: DPLL solver refutes validity, derives countermodel. If FOL/NL: Clean fallback.", ACCENT_GREEN),
        ("4. Evidence-Injected Evaluators", "Truth Table, Counterexample, and Formal Logic agents receive formal proof status in their prompt context.", ACCENT_AMBER),
        ("5. Aggregator & Hard Override Revisor", "Aggregator synthesizes neural + symbolic signals. Revisor applies hard override if proof is validated.", ACCENT_CYAN)
    ]

    for idx, (st_name, st_desc, col) in enumerate(stages):
        top_offset = Inches(2.3 + idx * 0.8)
        c_sub = add_card(s11, Inches(1.1), top_offset, Inches(11.133), Inches(0.68), bg=CARD_INNER, border=col)
        tf_s = c_sub.text_frame; tf_s.margin_left = Inches(0.2); tf_s.margin_top = Inches(0.12)
        p = tf_s.paragraphs[0]
        r1 = p.add_run(); r1.text = st_name + " ── "; r1.font.bold = True; r1.font.size = Pt(11); r1.font.color.rgb = col
        r2 = p.add_run(); r2.text = st_desc; r2.font.size = Pt(10.5); r2.font.color.rgb = TEXT_LIGHT

    # =========================================================================
    # SLIDE 12: SPRINT 4.3 - EXPERIMENTAL DESIGN & ABLATIONS
    # =========================================================================
    s12 = prs.slides.add_slide(blank_layout)
    add_header(s12, "3. Loopholes 2 & 3: Sprint 4 Resolution",
               "Sprint 4.3: Experimental Design & Ablation Framework",
               "Isolating the causal contribution of each component across 35 stratified benchmark problems", 12)

    # Left: 4 Experimental Configurations
    c12_l = add_card(s12, Inches(0.8), Inches(1.8), Inches(6.0), Inches(4.8))
    tf = c12_l.text_frame; tf.margin_left = tf.margin_top = Inches(0.2); tf.word_wrap = True
    p = tf.paragraphs[0]; p.text = "FOUR ISOLATED EXPERIMENTAL CONFIGURATIONS"; p.font.size = Pt(11); p.font.bold = True; p.font.color.rgb = ACCENT_CYAN

    configs = [
        ("1. Sprint 3 Opt (Control)", "Pure LLM selective dispatch baseline. No symbolic verifier. Tests performance of multi-agent debate alone.", ACCENT_BLUE),
        ("2. Full Sprint 4 (Proposed)", "SAT Verifier + Evaluator Evidence Injection + Revisor Hard Override. Complete neuro-symbolic system.", ACCENT_GREEN),
        ("3. Ablation A (Override Only)", "SAT Verifier + Hard Override active, but NO evidence injected into evaluators. Isolates safety guardrail.", ACCENT_AMBER),
        ("4. Ablation B (Evidence Only)", "SAT Verifier + Evidence Injected, but Hard Override DISABLED. Tests voluntary LLM revisor compliance.", ACCENT_CYAN)
    ]
    for c_t, c_d, col in configs:
        p = tf.add_paragraph(); p.space_before = Pt(8)
        r1 = p.add_run(); r1.text = c_t + "\n"; r1.font.bold = True; r1.font.size = Pt(11); r1.font.color.rgb = col
        r2 = p.add_run(); r2.text = c_d; r2.font.size = Pt(10); r2.font.color.rgb = TEXT_MUTED

    # Right: Benchmark Stratification Card
    c12_r = add_card(s12, Inches(7.1), Inches(1.8), Inches(5.433), Inches(4.8))
    tf = c12_r.text_frame; tf.margin_left = tf.margin_top = Inches(0.2); tf.word_wrap = True
    p = tf.paragraphs[0]; p.text = "BENCHMARK STRATIFICATION (35 PROBLEMS)"; p.font.size = Pt(11); p.font.bold = True; p.font.color.rgb = ACCENT_GREEN

    strats = [
        ("Target Domain (27 Problems):", " Propositional deductive arguments in slash notation.\n• 24 Pure Propositional Logic Problems\n• 3 Predicate / FOL Fallback Problems (49, 69, 101)"),
        ("Control Domain (8 Problems):", " Non-propositional formal logic (Natural language syllogisms, quantifier duality, rhetorical fallacies). Verifier correctly returns NOT_APPLICABLE."),
        ("18 Paired Problems:", " Evaluated head-to-head between Sprint 3 Opt and Sprint 4 Full under identical LLM settings."),
        ("5 Divergence Cases:", " Difficult problems where A0 failed (Problems 6, 20, 23, 31, 35) evaluated across all 4 ablations.")
    ]
    for s_t, s_d in strats:
        p = tf.add_paragraph(); p.space_before = Pt(8)
        r1 = p.add_run(); r1.text = s_t + " "; r1.font.bold = True; r1.font.size = Pt(10.5); r1.font.color.rgb = TEXT_LIGHT
        r2 = p.add_run(); r2.text = s_d; r2.font.size = Pt(10); r2.font.color.rgb = TEXT_MUTED

    # =========================================================================
    # SLIDE 13: OVERALL BENCHMARK RESULTS
    # =========================================================================
    s13 = prs.slides.add_slide(blank_layout)
    add_header(s13, "4. Results & Empirical Evidence",
               "Overall Benchmark Results: Substantial Accuracy Gains",
               "Verified results across 35 stratified MMLU Formal Logic problems (results/experiment_sprint4_3/)", 13)

    # 4 Top Callout Stats
    box_w = Inches(2.7)
    box_h = Inches(1.4)
    add_stat_box(s13, Inches(0.8), Inches(1.8), box_w, box_h, "88.6%", "Overall Final Accuracy", ACCENT_GREEN, "31 / 35 Correct (vs A0 14/35, 40%)")
    add_stat_box(s13, Inches(3.8), Inches(1.8), box_w, box_h, "100.0%", "Pure Propositional Logic", ACCENT_CYAN, "24 / 24 Correct (vs A0 9/24, 37.5%)")
    add_stat_box(s13, Inches(6.8), Inches(1.8), box_w, box_h, "17", "Helpful Revisions", ACCENT_BLUE, "15 Target + 2 Control corrected")
    add_stat_box(s13, Inches(9.8), Inches(1.8), box_w, box_h, "0", "Harmful Revisions", ACCENT_AMBER, "0.0% Regression Rate (0 / 17)")

    # Bottom Table Card
    c13_t = add_card(s13, Inches(0.8), Inches(3.4), Inches(11.733), Inches(3.2))
    tf13 = c13_t.text_frame; tf13.margin_left = tf13.margin_top = Inches(0.18); tf13.word_wrap = True
    p = tf13.paragraphs[0]; p.text = "AGGREGATE BENCHMARK PERFORMANCE BREAKDOWN"; p.font.size = Pt(10); p.font.bold = True; p.font.color.rgb = ACCENT_CYAN

    # Table
    table_shape = s13.shapes.add_table(6, 7, Inches(1.0), Inches(3.8), Inches(11.333), Inches(2.6))
    t13 = table_shape.table
    t13.columns[0].width = Inches(2.8)
    t13.columns[1].width = Inches(1.0)
    t13.columns[2].width = Inches(1.5)
    t13.columns[3].width = Inches(1.5)
    t13.columns[4].width = Inches(1.2)
    t13.columns[5].width = Inches(1.2)
    t13.columns[6].width = Inches(2.1)

    t13_data = [
        ["Benchmark Partition", "Count", "Initial A0", "Final Accuracy", "Helpful", "Harmful", "Proof Precision"],
        ["Target: Pure Propositional", "24", "37.5% (9/24)", "100.0% (24/24)", "15", "0", "100.0% (24/24)"],
        ["Target: Predicate Fallback", "3", "33.3% (1/3)", "33.3% (1/3)", "0", "0", "N/A (NOT_APPLICABLE)"],
        ["Target Domain Total", "27", "37.0% (10/27)", "92.6% (25/27)", "15", "0", "100.0% (24/24)"],
        ["Control Domain (Stratified)", "8", "50.0% (4/8)", "75.0% (6/8)", "2", "0", "N/A (NOT_APPLICABLE)"],
        ["Full 35-Problem Benchmark", "35", "40.0% (14/35)", "88.6% (31/35)", "17", "0", "100.0% (24/24)"]
    ]

    for r_idx, row in enumerate(t13_data):
        for c_idx, val in enumerate(row):
            cell = t13.cell(r_idx, c_idx)
            cell.text = val
            cell.fill.solid()
            cell.fill.fore_color.rgb = CARD_INNER if r_idx == 0 or r_idx == 5 else CARD_BG
            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER if c_idx > 0 else PP_ALIGN.LEFT
            p.font.size = Pt(9.5)
            p.font.color.rgb = ACCENT_CYAN if (r_idx == 0 or r_idx == 5 or c_idx == 3) else TEXT_LIGHT
            if r_idx == 0 or r_idx == 5 or c_idx == 3:
                p.font.bold = True

    # =========================================================================
    # SLIDE 14: HEAD-TO-HEAD COMPARISON (18 PROBLEMS)
    # =========================================================================
    s14 = prs.slides.add_slide(blank_layout)
    add_header(s14, "4. Results & Empirical Evidence",
               "Head-to-Head Comparison: Sprint 3 Opt vs. Sprint 4 Full",
               "Paired evaluation on 18 identical problems under identical LLM inference settings", 14)

    # Left: Comparison Table
    c14_l = add_card(s14, Inches(0.8), Inches(1.8), Inches(6.8), Inches(4.8))
    tf14_l = c14_l.text_frame; tf14_l.margin_left = tf14_l.margin_top = Inches(0.2); tf14_l.word_wrap = True
    p = tf14_l.paragraphs[0]; p.text = "PAIRED PERFORMANCE ON 18 PROBLEMS"; p.font.size = Pt(11); p.font.bold = True; p.font.color.rgb = ACCENT_CYAN

    t14_shape = s14.shapes.add_table(4, 4, Inches(1.0), Inches(2.4), Inches(6.4), Inches(2.6))
    t14 = t14_shape.table
    t14.columns[0].width = Inches(2.2)
    t14.columns[1].width = Inches(1.4)
    t14.columns[2].width = Inches(1.4)
    t14.columns[3].width = Inches(1.4)

    t14_data = [
        ["Partition", "Sprint 3 Opt", "Sprint 4 Full", "Net Gain"],
        ["Target Propositional (10)", "60.0% (6/10)", "100.0% (10/10)", "+40.0% Gain"],
        ["Control Domain (8)", "87.5% (7/8)", "75.0% (6/8)", "-12.5% (Variance)"],
        ["Total Paired Slice (18)", "72.2% (13/18)", "88.9% (16/18)", "+16.7% Gain"]
    ]
    for r_idx, row in enumerate(t14_data):
        for c_idx, val in enumerate(row):
            cell = t14.cell(r_idx, c_idx)
            cell.text = val
            cell.fill.solid()
            cell.fill.fore_color.rgb = CARD_INNER if r_idx == 0 or r_idx == 3 else CARD_BG
            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER if c_idx > 0 else PP_ALIGN.LEFT
            p.font.size = Pt(10)
            p.font.color.rgb = ACCENT_GREEN if c_idx == 3 and r_idx in [1,3] else TEXT_LIGHT
            if r_idx == 0 or r_idx == 3 or c_idx == 3:
                p.font.bold = True

    p = tf14_l.add_paragraph(); p.space_before = Pt(14)
    p.text = "Target Domain Finding: On the 10 pure propositional arguments, Sprint 4 achieved a perfect 100% (10/10) compared to Sprint 3 Opt's 60% (6/10), representing a 40.0% accuracy gain driven entirely by deterministic refutation."
    p.font.size = Pt(10.5); p.font.color.rgb = TEXT_MUTED

    # Right: Statistical Rigor & McNemar Card
    c14_r = add_card(s14, Inches(7.9), Inches(1.8), Inches(4.633), Inches(4.8))
    tf14_r = c14_r.text_frame; tf14_r.margin_left = tf14_r.margin_top = Inches(0.25); tf14_r.word_wrap = True
    p = tf14_r.paragraphs[0]; p.text = "STATISTICAL RIGOR: McNEMAR PAIRED TEST"; p.font.size = Pt(11); p.font.bold = True; p.font.color.rgb = ACCENT_AMBER

    items_mc = [
        ("Contingency Matrix (18 Pairs):", "\n• b (S4 Correct, Opt Wrong) = 4\n• c (Opt Correct, S4 Wrong) = 1\n• Discordant Pairs (b + c) = 5"),
        ("McNemar Chi-Square:", "\nχ² = (|b - c| - 1)² / (b + c)\nχ² = (|4 - 1| - 1)² / 5 = 4 / 5 = 0.80\np-value > 0.05 (Not Statistically Significant)"),
        ("Honest Scientific Takeaway:", " While target domain gains (+40%) are descriptively dramatic, formal significance is constrained by the paired sample size (N=18). We do not claim proven statistical superiority without larger N.")
    ]
    for m_t, m_d in items_mc:
        p = tf14_r.add_paragraph(); p.space_before = Pt(8)
        r1 = p.add_run(); r1.text = m_t; r1.font.bold = True; r1.font.size = Pt(10.5); r1.font.color.rgb = TEXT_LIGHT
        r2 = p.add_run(); r2.text = m_d; r2.font.size = Pt(10); r2.font.color.rgb = TEXT_MUTED

    # =========================================================================
    # SLIDE 15: ABLATION & ERROR ANALYSIS
    # =========================================================================
    s15 = prs.slides.add_slide(blank_layout)
    add_header(s15, "4. Results & Empirical Evidence",
               "Ablation Findings & Systematic Error Analysis",
               "Isolating component necessity across 5 failure cases and classifying all remaining errors", 15)

    # Left: 5 Failure Cases Ablation
    c15_l = add_card(s15, Inches(0.8), Inches(1.8), Inches(5.6), Inches(4.8))
    tf = c15_l.text_frame; tf.margin_left = tf.margin_top = Inches(0.2); tf.word_wrap = True
    p = tf.paragraphs[0]; p.text = "ABLATION: 5 A0-FAILURE CASES (6, 20, 23, 31, 35)"; p.font.size = Pt(11); p.font.bold = True; p.font.color.rgb = ACCENT_CYAN

    t15_shape = s15.shapes.add_table(5, 3, Inches(1.0), Inches(2.3), Inches(5.2), Inches(2.4))
    t15 = t15_shape.table
    t15.columns[0].width = Inches(2.6)
    t15.columns[1].width = Inches(1.3)
    t15.columns[2].width = Inches(1.3)

    t15_data = [
        ["Condition", "Accuracy (5)", "Helpful Revisions"],
        ["Initial A0 Baseline", "0 / 5 (0.0%)", "0"],
        ["Sprint 3 Opt (Control)", "1 / 5 (20.0%)", "1"],
        ["Ablation A (Override Only)", "5 / 5 (100.0%)", "5"],
        ["Ablation B (Evidence Only)", "5 / 5 (100.0%)", "5"]
    ]
    for r_idx, row in enumerate(t15_data):
        for c_idx, val in enumerate(row):
            cell = t15.cell(r_idx, c_idx)
            cell.text = val
            cell.fill.solid()
            cell.fill.fore_color.rgb = CARD_INNER if r_idx == 0 else CARD_BG
            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER if c_idx > 0 else PP_ALIGN.LEFT
            p.font.size = Pt(10)
            p.font.color.rgb = ACCENT_GREEN if r_idx >= 3 and c_idx > 0 else TEXT_LIGHT
            if r_idx == 0 or r_idx >= 3:
                p.font.bold = True

    p = tf.add_paragraph(); p.space_before = Pt(12)
    p.text = "Key Insight — Voluntary Compliance: Ablation B proves that when structured SAT evidence is injected, LLM Revisors voluntarily adopt the proof in 100% of cases without requiring a hard override."
    p.font.size = Pt(10.5); p.font.color.rgb = TEXT_MUTED

    # Right: Error Analysis Card
    c15_r = add_card(s15, Inches(6.9), Inches(1.8), Inches(5.6), Inches(4.8))
    tf = c15_r.text_frame; tf.margin_left = tf.margin_top = Inches(0.2); tf.word_wrap = True
    p = tf.paragraphs[0]; p.text = "ROOT-CAUSE ANALYSIS: 4 REMAINING ERRORS"; p.font.size = Pt(11); p.font.bold = True; p.font.color.rgb = ACCENT_ROSE

    errors = [
        ("Control Problem 1 (Non-Propositional):", " Transitivity relation problem in predicate logic. Verifier returned NOT_APPLICABLE. LLM evaluators disagreed on directionality (Tdc vs Tcd)."),
        ("Control Problem 4 (Non-Propositional):", " Informal rhetorical argument. Verifier returned NOT_APPLICABLE. Pure LLM evaluators retained flawed initial generation."),
        ("Target Problem 49 (Predicate Fallback):", " First-order relational predicate. Outside propositional parser scope. Verifier safely returned NOT_APPLICABLE."),
        ("Target Problem 101 (Predicate Fallback):", " Complex quantified predicate. Clean fallback to LLM evaluation which failed to revise."),
        ("Zero False Proofs:", " In 100% of unsupported cases, the verifier abstained rather than fabricating a false proof.")
    ]
    for e_t, e_d in errors:
        p = tf.add_paragraph(); p.space_before = Pt(6)
        r1 = p.add_run(); r1.text = "• " + e_t + " "; r1.font.bold = True; r1.font.size = Pt(10); r1.font.color.rgb = TEXT_LIGHT
        r2 = p.add_run(); r2.text = e_d; r2.font.size = Pt(9.5); r2.font.color.rgb = TEXT_MUTED

    # =========================================================================
    # SLIDE 16: TECHNICAL CONTRIBUTIONS
    # =========================================================================
    s16 = prs.slides.add_slide(blank_layout)
    add_header(s16, "5. Conclusion & Future Scope",
               "Summary of Key Technical Contributions",
               "Deliverables produced across multi-agent stabilization, symbolic reasoning, and empirical evaluation", 16)

    # 5 Contribution Blocks
    box_w = Inches(11.733)
    c_h = Inches(0.85)

    contribs = [
        ("1. Empirical Vulnerability Discovery", "First systematic audit identifying Evaluator Bypass (>60%), simulated scoring, and sycophantic harmful revisions in hierarchical multi-agent frameworks.", ACCENT_ROSE),
        ("2. Graph-Level Deterministic Dispatch", "Engineered an authoritative LangGraph state machine enforcing 100% evaluator execution compliance, taxonomy classification, and immutable state baselines.", ACCENT_BLUE),
        ("3. Propositional SAT Verification Engine", "Implemented automated formula normalization, Pratt AST parsing, SymPy DPLL satisfiability refutation, and minimal truth-value countermodel synthesis.", ACCENT_GREEN),
        ("4. Evidence-Guided Revisor Safeguard", "Coupled neural deliberation with symbolic proofs. Achieved 0 harmful revisions across 17 revisions (zero regression on deductive validity).", ACCENT_CYAN),
        ("5. Reproducible Benchmark & Test Suite", "Constructed a 35-problem MMLU formal logic benchmark, 4 ablation configurations, 63 raw execution traces, and 69 passing unit & integration tests.", ACCENT_AMBER)
    ]

    for idx, (c_t, c_d, col) in enumerate(contribs):
        top_offset = Inches(1.8 + idx * 0.95)
        card = add_card(s16, Inches(0.8), top_offset, box_w, c_h, bg=CARD_INNER, border=col)
        tf = card.text_frame; tf.margin_left = Inches(0.2); tf.margin_top = Inches(0.12)
        p = tf.paragraphs[0]
        r1 = p.add_run(); r1.text = c_t + " ── "; r1.font.bold = True; r1.font.size = Pt(11); r1.font.color.rgb = col
        r2 = p.add_run(); r2.text = c_d; r2.font.size = Pt(10.5); r2.font.color.rgb = TEXT_LIGHT

    # =========================================================================
    # SLIDE 17: LIMITATIONS & FUTURE WORK
    # =========================================================================
    s17 = prs.slides.add_slide(blank_layout)
    add_header(s17, "5. Conclusion & Future Scope",
               "Current Limitations & Future Research Roadmap",
               "Maintaining scientific honesty regarding system boundaries and outlining the path to publication", 17)

    c17_l = add_card(s17, Inches(0.8), Inches(1.8), Inches(5.6), Inches(4.8))
    tf = c17_l.text_frame; tf.margin_left = tf.margin_top = Inches(0.25); tf.word_wrap = True
    p = tf.paragraphs[0]; p.text = "CURRENT SYSTEM BOUNDARIES"; p.font.size = Pt(11); p.font.bold = True; p.font.color.rgb = ACCENT_AMBER

    limits = [
        ("Propositional Logic Scope:", " Current SAT solver operates on propositional logic. First-order logic with quantifiers (∀, ∃) and relational predicates falls back to LLM."),
        ("Small Paired Sample Size:", " Head-to-head baseline comparison was conducted on 18 paired problems. Formal McNemar test p > 0.05."),
        ("Extraction Heuristics:", " Complex natural language syntax with deeply nested clauses can occasionally trigger PARSE_FAILURE."),
        ("Inference Overhead:", " Multi-agent deliberation with sequential evaluation increases per-problem latency (~240s-320s per problem).")
    ]
    for l_t, l_d in limits:
        p = tf.add_paragraph(); p.space_before = Pt(8)
        r1 = p.add_run(); r1.text = "• " + l_t + " "; r1.font.bold = True; r1.font.size = Pt(10.5); r1.font.color.rgb = TEXT_LIGHT
        r2 = p.add_run(); r2.text = l_d; r2.font.size = Pt(10); r2.font.color.rgb = TEXT_MUTED

    c17_r = add_card(s17, Inches(6.9), Inches(1.8), Inches(5.6), Inches(4.8))
    tf = c17_r.text_frame; tf.margin_left = tf.margin_top = Inches(0.25); tf.word_wrap = True
    p = tf.paragraphs[0]; p.text = "FUTURE RESEARCH ROADMAP"; p.font.size = Pt(11); p.font.bold = True; p.font.color.rgb = ACCENT_CYAN

    future = [
        ("First-Order SMT Integration:", " Incorporate Z3 or Prover9 theorem provers to handle relational predicates, arithmetic constraints, and quantifiers."),
        ("Semantic Formalization:", " Train a lightweight semantic parsing model (fine-tuned LLM) to translate messy natural language premises into formal logic."),
        ("Benchmark Expansion:", " Scale evaluation across broader formal reasoning datasets (ProofWriter, FOLIO, Big-Bench Hard)."),
        ("Research Paper Submission:", " Prepare manuscript detailing multi-agent sycophancy vulnerabilities and neuro-symbolic revision safeguards.")
    ]
    for f_t, f_d in future:
        p = tf.add_paragraph(); p.space_before = Pt(8)
        r1 = p.add_run(); r1.text = "• " + f_t + " "; r1.font.bold = True; r1.font.size = Pt(10.5); r1.font.color.rgb = TEXT_LIGHT
        r2 = p.add_run(); r2.text = f_d; r2.font.size = Pt(10); r2.font.color.rgb = TEXT_MUTED

    # =========================================================================
    # SLIDE 18: THANK YOU & DISCUSSION
    # =========================================================================
    s18 = prs.slides.add_slide(blank_layout)
    apply_dark_background(s18)

    # Top accent bar
    top_bar = s18.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(0.8), Inches(11.733), Inches(0.08))
    top_bar.fill.solid(); top_bar.fill.fore_color.rgb = ACCENT_CYAN; top_bar.line.fill.background()

    # Title Card
    t_box = s18.shapes.add_textbox(Inches(0.8), Inches(1.3), Inches(11.733), Inches(1.8))
    tf = t_box.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "THANK YOU"
    p.font.size = Pt(36); p.font.bold = True; p.font.color.rgb = TEXT_LIGHT
    
    p = tf.add_paragraph(); p.space_before = Pt(6)
    p.text = "Enhancing Hierarchical Multi-Agent Reasoning Through Deterministic Logical Verification"
    p.font.size = Pt(16); p.font.color.rgb = ACCENT_CYAN

    # 4 Stat Recap Cards
    box_w = Inches(2.7)
    box_h = Inches(1.4)
    add_stat_box(s18, Inches(0.8), Inches(3.2), box_w, box_h, "100.0%", "Propositional Accuracy", ACCENT_GREEN, "24 / 24 Correct (vs A0 37.5%)")
    add_stat_box(s18, Inches(3.8), Inches(3.2), box_w, box_h, "88.6%", "Overall Accuracy", ACCENT_CYAN, "31 / 35 Benchmark Tasks")
    add_stat_box(s18, Inches(6.8), Inches(3.2), box_w, box_h, "0", "Harmful Revisions", ACCENT_AMBER, "0.0% Regression Rate")
    add_stat_box(s18, Inches(9.8), Inches(3.2), box_w, box_h, "69 / 69", "Tests Passing", ACCENT_BLUE, "Unit & Integration Suite")

    # Bottom Contact & Discussion Card
    c18_b = add_card(s18, Inches(0.8), Inches(4.9), Inches(11.733), Inches(1.8), bg=CARD_INNER, border=ACCENT_CYAN)
    tf18 = c18_b.text_frame; tf18.margin_left = Inches(0.3); tf18.margin_top = Inches(0.2); tf18.word_wrap = True
    p = tf18.paragraphs[0]
    p.text = "OPEN FOR QUESTIONS & COMMITTEE FEEDBACK"
    p.font.size = Pt(13); p.font.bold = True; p.font.color.rgb = ACCENT_CYAN

    p = tf18.add_paragraph(); p.space_before = Pt(8)
    p.text = "Candidate: Mohith Chandra | Department of Computer Science & Engineering, IIT Patna\nGitHub Repository: https://github.com/MohithChandra07/Talkhier_BTP\nIncludes full implementation, 63 raw execution traces, unit tests, and Sprint 1-4.3 progress reports."
    p.font.size = Pt(11); p.font.color.rgb = TEXT_LIGHT

    # Save PPTX
    prs.save(output_pptx_path)
    print(f"Successfully generated 18-slide presentation at: {output_pptx_path}")

if __name__ == "__main__":
    out_dir = "/Users/mohithchandra/BTP/talkhier/presentations"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "TalkHier_BTP_Final_18Slides_Presentation.pptx")
    build_presentation(out_path)
    
    # Also save to root /Users/mohithchandra/BTP/
    root_path = "/Users/mohithchandra/BTP/TalkHier_BTP_Final_18Slides_Presentation.pptx"
    import shutil
    shutil.copy(out_path, root_path)
    print(f"Copied presentation to root BTP folder: {root_path}")
