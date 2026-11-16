#!/usr/bin/env python3
import os

with open('/Users/mohithchandra/BTP/talkhier/src/generate_btp_18slides_deck.py') as f:
    code = f.read()

# 1. Palette
old_palette = '''    # Dark Modern Research Palette
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
    ACCENT_AMBER = RGBColor(251, 191, 36)# Amber 400'''

new_palette = '''    # White & Grey Minimalist Editorial Palette (Matches Canva "White Grey Minimalist" Template)
    BG_DARK = RGBColor(255, 255, 255)    # Slide Background: Pure White
    CARD_BG = RGBColor(248, 249, 251)    # Card Background: Soft Light Grey (#F8F9FB)
    CARD_BORDER = RGBColor(226, 232, 240)# Thin Slate Border (#E2E8F0)
    CARD_INNER = RGBColor(241, 245, 249) # Subcard/Code Background (#F1F5F9)
    TEXT_LIGHT = RGBColor(17, 24, 39)    # Main Headings & Text: Ink Charcoal (#111827)
    TEXT_MUTED = RGBColor(71, 85, 105)   # Secondary Text: Slate 600 (#475569)
    TEXT_DIM = RGBColor(148, 163, 184)   # Dim / Meta Text: Slate 400 (#94A3B8)

    ACCENT_CYAN = RGBColor(15, 23, 42)   # Category Tags: Deep Ink Black/Charcoal (#0F172A)
    ACCENT_BLUE = RGBColor(37, 99, 235)  # Royal Blue (#2563EB)
    ACCENT_GREEN = RGBColor(16, 149, 93) # Verified Emerald (#10955D)
    ACCENT_ROSE = RGBColor(225, 29, 72)  # Refined Crimson Rose (#E11D48)
    ACCENT_AMBER = RGBColor(217, 119, 6) # Refined Amber (#D97706)'''

assert old_palette in code, "Old palette not found!"
code = code.replace(old_palette, new_palette)

# 2. Header function adjustments for serif titles and bottom pill
old_header = '''    def add_header(slide, category, title, subtitle=None, slide_num=None):
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
            p_num.font.color.rgb = TEXT_DIM'''

new_header = '''    def add_header(slide, category, title, subtitle=None, slide_num=None):
        apply_dark_background(slide)
        
        # Category Tag (Minimalist Clean Sans)
        cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.0), Inches(0.28))
        tf_cat = cat_box.text_frame
        tf_cat.word_wrap = True
        tf_cat.margin_left = tf_cat.margin_top = tf_cat.margin_right = tf_cat.margin_bottom = 0
        p_cat = tf_cat.paragraphs[0]
        p_cat.text = category.upper()
        p_cat.font.name = "Calibri"
        p_cat.font.size = Pt(9.5)
        p_cat.font.bold = True
        p_cat.font.color.rgb = ACCENT_CYAN

        # Title (High-Contrast Editorial Serif matching template)
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.68), Inches(10.5), Inches(0.55))
        tf_title = title_box.text_frame
        tf_title.word_wrap = True
        tf_title.margin_left = tf_title.margin_top = tf_title.margin_right = tf_title.margin_bottom = 0
        p_title = tf_title.paragraphs[0]
        p_title.text = title
        p_title.font.name = "Georgia"
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
            p_sub.font.name = "Calibri"
            p_sub.font.size = Pt(12)
            p_sub.font.color.rgb = TEXT_MUTED

        # Slide Number Badge & Bottom Minimalist Pill
        if slide_num:
            num_box = slide.shapes.add_textbox(Inches(11.3), Inches(0.4), Inches(1.2), Inches(0.3))
            tf_num = num_box.text_frame
            tf_num.margin_left = tf_num.margin_top = tf_num.margin_right = tf_num.margin_bottom = 0
            p_num = tf_num.paragraphs[0]
            p_num.text = f"{slide_num:02d} / 18"
            p_num.alignment = PP_ALIGN.RIGHT
            p_num.font.name = "Calibri"
            p_num.font.size = Pt(11)
            p_num.font.bold = True
            p_num.font.color.rgb = TEXT_DIM

            # Bottom-Right Minimalist Outline Page Pill (Matches template 'Page 01' pill)
            pill = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(11.4), Inches(6.8), Inches(1.15), Inches(0.32))
            pill.fill.solid()
            pill.fill.fore_color.rgb = RGBColor(255, 255, 255)
            pill.line.color.rgb = RGBColor(203, 213, 225)
            pill.line.width = Pt(1)
            tf_pill = pill.text_frame
            tf_pill.margin_top = tf_pill.margin_bottom = tf_pill.margin_left = tf_pill.margin_right = 0
            p_pill = tf_pill.paragraphs[0]
            p_pill.text = f"Page {slide_num:02d}"
            p_pill.font.name = "Calibri"
            p_pill.font.size = Pt(9.5)
            p_pill.font.bold = True
            p_pill.font.color.rgb = RGBColor(100, 116, 139)
            p_pill.alignment = PP_ALIGN.CENTER'''

assert old_header in code, "Old header not found!"
code = code.replace(old_header, new_header)

# 3. Slide 1 adjustments
old_s1 = '''    # Decorative header glow
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
    p1.text = "Enhancing Hierarchical Multi-Agent Reasoning\\nThrough Deterministic Logical Verification"
    p1.font.size = Pt(32)
    p1.font.bold = True
    p1.font.color.rgb = TEXT_LIGHT
    p1.space_after = Pt(14)

    p2 = tf1.add_paragraph()
    p2.text = "Investigating Vulnerabilities in Sony's TalkHier Framework & Integrating SymPy DPLL SAT Refutation"
    p2.font.size = Pt(15)
    p2.font.color.rgb = TEXT_MUTED'''

new_s1 = '''    # Minimalist subtle divider
    top_bar = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(0.7), Inches(11.733), Inches(0.02))
    top_bar.fill.solid()
    top_bar.fill.fore_color.rgb = RGBColor(226, 232, 240)
    top_bar.line.fill.background()

    # Title & Subtitle Box (Editorial Serif matching template)
    t_box = s1.shapes.add_textbox(Inches(0.8), Inches(0.95), Inches(11.733), Inches(2.3))
    tf1 = t_box.text_frame
    tf1.word_wrap = True
    
    p0 = tf1.paragraphs[0]
    p0.text = "MINIMALIST  •  BTP RESEARCH PRESENTATION"
    p0.font.name = "Calibri"
    p0.font.size = Pt(10.5)
    p0.font.bold = True
    p0.font.color.rgb = ACCENT_CYAN
    p0.space_after = Pt(10)

    p1 = tf1.add_paragraph()
    p1.text = "Enhancing Hierarchical Multi-Agent Reasoning\\nThrough Deterministic Logical Verification"
    p1.font.name = "Georgia"
    p1.font.italic = True
    p1.font.size = Pt(31)
    p1.font.bold = True
    p1.font.color.rgb = TEXT_LIGHT
    p1.space_after = Pt(12)

    p2 = tf1.add_paragraph()
    p2.text = "Investigating Vulnerabilities in Sony's TalkHier Framework & Integrating SymPy DPLL SAT Refutation"
    p2.font.name = "Calibri"
    p2.font.size = Pt(14)
    p2.font.color.rgb = TEXT_MUTED

    # Slide 1 Bottom-Right Pill
    pill1 = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(11.4), Inches(6.8), Inches(1.15), Inches(0.32))
    pill1.fill.solid()
    pill1.fill.fore_color.rgb = RGBColor(255, 255, 255)
    pill1.line.color.rgb = RGBColor(203, 213, 225)
    pill1.line.width = Pt(1)
    tf_pill1 = pill1.text_frame
    tf_pill1.margin_top = tf_pill1.margin_bottom = tf_pill1.margin_left = tf_pill1.margin_right = 0
    p_pill1 = tf_pill1.paragraphs[0]
    p_pill1.text = "Page 01"
    p_pill1.font.name = "Calibri"
    p_pill1.font.size = Pt(9.5)
    p_pill1.font.bold = True
    p_pill1.font.color.rgb = RGBColor(100, 116, 139)
    p_pill1.alignment = PP_ALIGN.CENTER'''

assert old_s1 in code, "Old s1 not found!"
code = code.replace(old_s1, new_s1)

# 4. Global font pass before prs.save
old_save = '    prs.save(output_pptx_path)'
new_save = '''    # Apply clean fonts across all shapes and tables
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                for p in shape.text_frame.paragraphs:
                    if not getattr(p.font, 'name', None):
                        p.font.name = 'Calibri'
            if shape.has_table:
                for row in shape.table.rows:
                    for cell in row.cells:
                        for p in cell.text_frame.paragraphs:
                            if not getattr(p.font, 'name', None):
                                p.font.name = 'Calibri'
    prs.save(output_pptx_path)'''

assert old_save in code, "Old save not found!"
code = code.replace(old_save, new_save)

with open('/Users/mohithchandra/BTP/talkhier/src/generate_btp_minimalist_deck.py', 'w') as f:
    f.write(code)

print("generate_btp_minimalist_deck.py written successfully!")

