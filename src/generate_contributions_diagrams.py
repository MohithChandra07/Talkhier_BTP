#!/usr/bin/env python3
"""
Generate Draw.io XML files and ultra-high-resolution PNG / SVG diagrams
for BTP Technical Contributions (Slide 16: "WHAT THIS BTP IMPLEMENTED").
Matches the Futuristic Dark Cyber / Liquid Chrome theme as well as the
White Minimalist theme.
"""

import os
import subprocess
import html

# -------------------------------------------------------------------------
# 1. DRAW.IO XML GENERATION (DARK THEME & LIGHT THEME)
# -------------------------------------------------------------------------

CONTRIBUTIONS = [
    {
        "id": "1",
        "num": "01",
        "tag": "EMPIRICAL AUDIT",
        "title": "1. Empirical Vulnerability Discovery",
        "desc": "First systematic audit identifying <b>Evaluator Bypass (&gt;60%)</b>, simulated scoring, and sycophantic harmful revisions in hierarchical multi-agent frameworks.",
        "dark_stroke": "#f43f5e", # Rose / Crimson
        "dark_bg": "#131722",
        "dark_badge_bg": "#271724",
        "dark_badge_fg": "#fb7185",
        "light_stroke": "#e11d48",
        "light_bg": "#fff5f5",
        "light_badge_bg": "#ffe4e6",
        "light_badge_fg": "#e11d48"
    },
    {
        "id": "2",
        "num": "02",
        "tag": "GRAPH DISPATCH",
        "title": "2. Graph-Level Deterministic Dispatch",
        "desc": "Engineered an authoritative LangGraph state machine enforcing <b>100% evaluator execution compliance</b>, taxonomy classification, and immutable state baselines.",
        "dark_stroke": "#38bdf8", # Electric Cyan
        "dark_bg": "#0f172a",
        "dark_badge_bg": "#0c2847",
        "dark_badge_fg": "#38bdf8",
        "light_stroke": "#2563eb",
        "light_bg": "#eff6ff",
        "light_badge_bg": "#dbeafe",
        "light_badge_fg": "#1d4ed8"
    },
    {
        "id": "3",
        "num": "03",
        "tag": "SAT ENGINE",
        "title": "3. Propositional SAT Verification Engine",
        "desc": "Implemented automated formula normalization, Pratt AST parsing, <b>SymPy DPLL satisfiability refutation</b>, and minimal truth-value countermodel synthesis.",
        "dark_stroke": "#10b981", # Cyber Emerald
        "dark_bg": "#0d1e1c",
        "dark_badge_bg": "#062e22",
        "dark_badge_fg": "#34d399",
        "light_stroke": "#059669",
        "light_bg": "#ecfdf5",
        "light_badge_bg": "#d1fae5",
        "light_badge_fg": "#047857"
    },
    {
        "id": "4",
        "num": "04",
        "tag": "REVISOR SAFEGUARD",
        "title": "4. Evidence-Guided Revisor Safeguard",
        "desc": "Coupled neural deliberation with symbolic proofs. Achieved <b>0 harmful revisions across 17 revisions</b> (zero regression on deductive validity).",
        "dark_stroke": "#a855f7", # Violet / Metallic Purple
        "dark_bg": "#181428",
        "dark_badge_bg": "#281845",
        "dark_badge_fg": "#c084fc",
        "light_stroke": "#7c3aed",
        "light_bg": "#f5f3ff",
        "light_badge_bg": "#ede9fe",
        "light_badge_fg": "#6d28d9"
    },
    {
        "id": "5",
        "num": "05",
        "tag": "BENCHMARK SUITE",
        "title": "5. Reproducible Benchmark & Test Suite",
        "desc": "Constructed a 35-problem MMLU formal logic benchmark, 4 ablation configurations, 63 raw execution traces, and <b>69 passing unit &amp; integration tests</b>.",
        "dark_stroke": "#f59e0b", # Liquid Amber
        "dark_bg": "#1c1810",
        "dark_badge_bg": "#332205",
        "dark_badge_fg": "#fbbf24",
        "light_stroke": "#d97706",
        "light_bg": "#fffbeb",
        "light_badge_bg": "#fef3c7",
        "light_badge_fg": "#b45309"
    }
]

def generate_drawio_xml(theme="dark"):
    is_dark = (theme == "dark")
    page_bg = "#000000" if is_dark else "#ffffff"
    text_color = "#f8fafc" if is_dark else "#0f172a"
    sub_text = "#cbd5e1" if is_dark else "#475569"

    xml_lines = [
        '<mxfile host="app.diagrams.net" modified="2026-11-09T09:30:00.000Z" agent="Antigravity" version="24.0.0" type="device">',
        f'  <diagram id="btp_{theme}_contributions" name="Key Technical Contributions ({theme.capitalize()})">',
        f'    <mxGraphModel dx="1600" dy="900" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1500" pageHeight="720" background="{page_bg}" math="0" shadow="1">',
        '      <root>',
        '        <mxCell id="0"/>',
        '        <mxCell id="1" parent="0"/>'
    ]

    start_y = 40
    card_height = 100
    card_gap = 22
    card_width = 1400
    start_x = 50

    cell_id = 2
    for idx, c in enumerate(CONTRIBUTIONS):
        y_pos = start_y + idx * (card_height + card_gap)
        bg = c["dark_bg"] if is_dark else c["light_bg"]
        stroke = c["dark_stroke"] if is_dark else c["light_stroke"]
        badge_bg = c["dark_badge_bg"] if is_dark else c["light_badge_bg"]
        badge_fg = c["dark_badge_fg"] if is_dark else c["light_badge_fg"]

        # Outer Card Container
        card_style = (
            f"rounded=1;whiteSpace=wrap;html=1;arcSize=14;fillColor={bg};strokeColor={stroke};"
            f"strokeWidth=1.8;shadow=1;"
        )
        xml_lines.append(
            f'        <mxCell id="{cell_id}" value="" style="{card_style}" vertex="1" parent="1">'
        )
        xml_lines.append(
            f'          <mxGeometry x="{start_x}" y="{y_pos}" width="{card_width}" height="{card_height}" as="geometry"/>'
        )
        xml_lines.append('        </mxCell>')
        parent_card_id = cell_id
        cell_id += 1

        # Left Number Pill Badge
        badge_style = (
            f"rounded=1;whiteSpace=wrap;html=1;arcSize=24;fillColor={badge_bg};strokeColor={stroke};"
            f"strokeWidth=1.2;fontColor={badge_fg};fontStyle=1;fontSize=16;align=center;"
        )
        xml_lines.append(
            f'        <mxCell id="{cell_id}" value="{c["num"]}" style="{badge_style}" vertex="1" parent="1">'
        )
        xml_lines.append(
            f'          <mxGeometry x="{start_x + 20}" y="{y_pos + 26}" width="{48}" height="{48}" as="geometry"/>'
        )
        xml_lines.append('        </mxCell>')
        cell_id += 1

        # Text Content (Title & Description)
        content_val = (
            f'&lt;div style=&quot;font-family: Inter, Helvetica, Arial, sans-serif; text-align: left;&quot;&gt;'
            f'&lt;span style=&quot;color: {stroke}; font-size: 17px; font-weight: 700;&quot;&gt;{c["title"]}&lt;/span&gt;'
            f'&lt;span style=&quot;color: #64748b; font-size: 16px;&quot;&gt; &amp;nbsp;—&amp;nbsp; &lt;/span&gt;'
            f'&lt;span style=&quot;color: {sub_text}; font-size: 14.5px; line-height: 1.4;&quot;&gt;{c["desc"]}&lt;/span&gt;'
            f'&lt;/div&gt;'
        )
        text_style = "text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;whiteSpace=wrap;rounded=0;"
        xml_lines.append(
            f'        <mxCell id="{cell_id}" value="{content_val}" style="{text_style}" vertex="1" parent="1">'
        )
        xml_lines.append(
            f'          <mxGeometry x="{start_x + 85}" y="{y_pos + 12}" width="{card_width - 240}" height="{card_height - 24}" as="geometry"/>'
        )
        xml_lines.append('        </mxCell>')
        cell_id += 1

        # Right Tag Badge
        tag_style = (
            f"rounded=1;whiteSpace=wrap;html=1;arcSize=20;fillColor={badge_bg};strokeColor={stroke};"
            f"strokeWidth=1;fontColor={badge_fg};fontStyle=1;fontSize=10;align=center;"
        )
        xml_lines.append(
            f'        <mxCell id="{cell_id}" value="{c["tag"]}" style="{tag_style}" vertex="1" parent="1">'
        )
        xml_lines.append(
            f'          <mxGeometry x="{start_x + card_width - 135}" y="{y_pos + 34}" width="{115}" height="{30}" as="geometry"/>'
        )
        xml_lines.append('        </mxCell>')
        cell_id += 1

    xml_lines.extend([
        '      </root>',
        '    </mxGraphModel>',
        '  </diagram>',
        '</mxfile>'
    ])
    return '\n'.join(xml_lines)

# -------------------------------------------------------------------------
# 2. HTML / CSS TEMPLATES FOR CHROME HIGH-RESOLUTION RENDERING
# -------------------------------------------------------------------------

def generate_html_template(theme="transparent"):
    is_transparent = (theme == "transparent")
    is_dark = (theme in ["dark", "transparent"])

    bg_css = "background: transparent;" if is_transparent else (
        "background: #000000;" if is_dark else "background: #ffffff;"
    )

    cards_html = []
    for c in CONTRIBUTIONS:
        border_col = c["dark_stroke"] if is_dark else c["light_stroke"]
        card_bg = (
            "rgba(15, 20, 32, 0.78)" if is_dark else "#f8f9fa"
        )
        badge_bg = (
            f"rgba({int(border_col[1:3], 16)}, {int(border_col[3:5], 16)}, {int(border_col[5:7], 16)}, 0.15)"
            if is_dark else c["light_badge_bg"]
        )
        badge_fg = border_col
        text_title_col = border_col
        desc_col = "#e2e8f0" if is_dark else "#334155"
        tag_bg = badge_bg

        cards_html.append(f"""
        <div class="card" style="border-color: {border_col}; background: {card_bg};">
          <div class="card-glow" style="background: radial-gradient(circle at 10% 50%, {border_col}22, transparent 60%);"></div>
          <div class="badge-num" style="background: {badge_bg}; color: {badge_fg}; border-color: {border_col};">{c['num']}</div>
          <div class="card-content">
            <span class="card-title" style="color: {text_title_col};">{c['title']}</span>
            <span class="dash">—</span>
            <span class="card-desc" style="color: {desc_col};">{c['desc']}</span>
          </div>
          <div class="tag-pill" style="background: {tag_bg}; color: {badge_fg}; border-color: {border_col};">{c['tag']}</div>
        </div>
        """)

    full_html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html, body {{
      width: 1500px;
      height: 720px;
      overflow: hidden;
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      {bg_css}
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      padding: 20px 40px;
      -webkit-font-smoothing: antialiased;
    }}

    .container {{
      width: 100%;
      display: flex;
      flex-direction: column;
      gap: 18px;
    }}

    .card {{
      position: relative;
      display: flex;
      align-items: center;
      padding: 16px 26px;
      border-radius: 16px;
      border-width: 1.8px;
      border-style: solid;
      backdrop-filter: blur(24px);
      -webkit-backdrop-filter: blur(24px);
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.12);
      transition: all 0.3s ease;
      overflow: hidden;
    }}

    .card-glow {{
      position: absolute;
      top: 0; left: 0; right: 0; bottom: 0;
      pointer-events: none;
      z-index: 0;
    }}

    .badge-num {{
      position: relative;
      z-index: 1;
      width: 48px;
      height: 48px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: 'Syne', sans-serif;
      font-size: 1.15rem;
      font-weight: 800;
      border: 1.5px solid;
      flex-shrink: 0;
      margin-right: 22px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
    }}

    .card-content {{
      position: relative;
      z-index: 1;
      flex: 1;
      line-height: 1.45;
      padding-right: 20px;
    }}

    .card-title {{
      font-weight: 700;
      font-size: 1.08rem;
      letter-spacing: -0.01em;
    }}

    .dash {{
      color: #64748b;
      margin: 0 10px;
      font-size: 1.05rem;
    }}

    .card-desc {{
      font-size: 0.94rem;
      font-weight: 400;
    }}

    .card-desc b {{
      font-weight: 600;
      color: #ffffff;
      text-decoration: underline dotted rgba(255, 255, 255, 0.3);
      text-underline-offset: 3px;
    }}

    .tag-pill {{
      position: relative;
      z-index: 1;
      font-size: 0.72rem;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      padding: 6px 14px;
      border-radius: 9999px;
      border: 1px solid;
      flex-shrink: 0;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
    }}
  </style>
</head>
<body>
  <div class="container">
    {''.join(cards_html)}
  </div>
</body>
</html>"""
    return full_html


# -------------------------------------------------------------------------
# 3. SVG EXPORT GENERATION
# -------------------------------------------------------------------------

def generate_svg():
    width = 1440
    height = 680
    start_y = 20
    card_h = 105
    gap = 22

    svg_cards = []
    for idx, c in enumerate(CONTRIBUTIONS):
        y = start_y + idx * (card_h + gap)
        border = c["dark_stroke"]
        num = c["num"]
        tag = c["tag"]
        title = html.escape(c["title"])
        # Clean HTML tags for SVG text
        desc_clean = c["desc"].replace("<b>", "").replace("</b>", "").replace("&gt;", ">").replace("&amp;", "&")
        desc_esc = html.escape(desc_clean)

        svg_cards.append(f"""
        <g id="card-{idx+1}">
          <!-- Card Background & Border -->
          <rect x="20" y="{y}" width="1400" height="{card_h}" rx="16" ry="16" fill="#0f1422" fill-opacity="0.85" stroke="{border}" stroke-width="1.8" filter="url(#shadow)"/>
          
          <!-- Number Badge -->
          <rect x="42" y="{y + 26}" width="50" height="50" rx="12" ry="12" fill="{border}" fill-opacity="0.18" stroke="{border}" stroke-width="1.5"/>
          <text x="67" y="{y + 58}" fill="{border}" font-family="Inter, sans-serif" font-weight="800" font-size="20" text-anchor="middle">{num}</text>

          <!-- Text Title & Desc -->
          <text x="110" y="{y + 46}" font-family="Inter, sans-serif" font-weight="700" font-size="18" fill="{border}">{title}</text>
          <text x="110" y="{y + 76}" font-family="Inter, sans-serif" font-weight="400" font-size="15" fill="#cbd5e1">{desc_esc}</text>

          <!-- Tag Badge -->
          <rect x="1275" y="{y + 36}" width="125" height="32" rx="16" ry="16" fill="{border}" fill-opacity="0.15" stroke="{border}" stroke-width="1.2"/>
          <text x="1337" y="{y + 57}" fill="{border}" font-family="Inter, sans-serif" font-weight="700" font-size="11" letter-spacing="1" text-anchor="middle">{tag}</text>
        </g>
        """)

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="100%">
  <defs>
    <filter id="shadow" x="-5%" y="-10%" width="110%" height="130%" filterUnits="userSpaceOnUse">
      <feDropShadow dx="0" dy="8" stdDeviation="12" flood-color="#000000" flood-opacity="0.5"/>
    </filter>
  </defs>
  {''.join(svg_cards)}
</svg>"""
    return svg_content


# -------------------------------------------------------------------------
# 4. EXECUTION CONTROLLER
# -------------------------------------------------------------------------

def main():
    diagrams_dir = "/Users/mohithchandra/BTP/talkhier/diagrams"
    root_dir = "/Users/mohithchandra/BTP"
    os.makedirs(diagrams_dir, exist_ok=True)

    # 1. Generate Draw.io XML files
    dark_drawio_path = os.path.join(diagrams_dir, "btp_contributions_dark.drawio")
    light_drawio_path = os.path.join(diagrams_dir, "btp_contributions_light.drawio")
    
    with open(dark_drawio_path, "w", encoding="utf-8") as f:
        f.write(generate_drawio_xml("dark"))
    with open(light_drawio_path, "w", encoding="utf-8") as f:
        f.write(generate_drawio_xml("light"))
    
    print(f"Generated Draw.io (Dark): {dark_drawio_path}")
    print(f"Generated Draw.io (Light): {light_drawio_path}")

    # Copy dark drawio to root for convenient access
    with open(os.path.join(root_dir, "btp_contributions.drawio"), "w", encoding="utf-8") as f:
        f.write(generate_drawio_xml("dark"))

    # 2. Generate SVG
    svg_path = os.path.join(diagrams_dir, "btp_contributions.svg")
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(generate_svg())
    with open(os.path.join(root_dir, "btp_contributions.svg"), "w", encoding="utf-8") as f:
        f.write(generate_svg())
    print(f"Generated SVG: {svg_path}")

    # 3. Generate High-Res PNGs using Headless Chrome
    chrome_bin = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if os.path.exists(chrome_bin):
        # A) Transparent PNG (Ideal for drag-and-drop onto the liquid chrome slide!)
        html_trans = generate_html_template("transparent")
        temp_html_trans = "/tmp/btp_trans.html"
        with open(temp_html_trans, "w", encoding="utf-8") as f:
            f.write(html_trans)

        png_trans_path = os.path.join(diagrams_dir, "btp_contributions_transparent.png")
        cmd_trans = [
            chrome_bin,
            "--headless=new",
            f"--screenshot={png_trans_path}",
            "--window-size=1500,720",
            "--default-background-color=00000000",
            "--hide-scrollbars",
            "--force-device-scale-factor=2", # 2x Retina resolution: 3000 x 1440 px!
            temp_html_trans
        ]
        subprocess.run(cmd_trans, check=True)
        # Copy to root BTP
        import shutil
        shutil.copy(png_trans_path, os.path.join(root_dir, "btp_contributions_transparent.png"))
        print(f"Generated Retina 2x Transparent PNG: {png_trans_path}")

        # B) Dark Solid PNG (Pitch Black background #000000)
        html_dark = generate_html_template("dark")
        temp_html_dark = "/tmp/btp_dark.html"
        with open(temp_html_dark, "w", encoding="utf-8") as f:
            f.write(html_dark)

        png_dark_path = os.path.join(diagrams_dir, "btp_contributions_dark.png")
        cmd_dark = [
            chrome_bin,
            "--headless=new",
            f"--screenshot={png_dark_path}",
            "--window-size=1500,720",
            "--default-background-color=000000ff",
            "--hide-scrollbars",
            "--force-device-scale-factor=2",
            temp_html_dark
        ]
        subprocess.run(cmd_dark, check=True)
        shutil.copy(png_dark_path, os.path.join(root_dir, "btp_contributions_dark.png"))
        print(f"Generated Retina 2x Dark Solid PNG: {png_dark_path}")

        # C) Light Minimalist PNG (For white templates / reports)
        html_light = generate_html_template("light")
        temp_html_light = "/tmp/btp_light.html"
        with open(temp_html_light, "w", encoding="utf-8") as f:
            f.write(html_light)

        png_light_path = os.path.join(diagrams_dir, "btp_contributions_light.png")
        cmd_light = [
            chrome_bin,
            "--headless=new",
            f"--screenshot={png_light_path}",
            "--window-size=1500,720",
            "--default-background-color=ffffffff",
            "--hide-scrollbars",
            "--force-device-scale-factor=2",
            temp_html_light
        ]
        subprocess.run(cmd_light, check=True)
        shutil.copy(png_light_path, os.path.join(root_dir, "btp_contributions_light.png"))
        print(f"Generated Retina 2x Light Minimalist PNG: {png_light_path}")

if __name__ == "__main__":
    main()

