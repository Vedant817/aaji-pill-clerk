"""Streamlit theme: ui-ux-pro-max Senior Care palette + Medical Clean type.

Palette #57 Senior Care/Elderly (calm blue + reassuring green).
ASK / lock states use palette #145 Medication & Pill Reminder destructive red.
Type pairing #30 Medical Clean (Figtree + Noto Sans) plus Noto Sans Devanagari.
Style: medical-clean minimalism — large type, high contrast, no brutalism.
"""

from __future__ import annotations

import streamlit as st

PRIMARY = "#0369A1"
ON_PRIMARY = "#FFFFFF"
SECONDARY = "#38BDF8"
ACCENT = "#16A34A"
BACKGROUND = "#F0F9FF"
FOREGROUND = "#0C4A6E"
CARD = "#FFFFFF"
MUTED = "#E7EFF5"
MUTED_FG = "#475569"
BORDER = "#E0F2FE"
ASK = "#DC2626"
ON_ASK = "#FFFFFF"
RING = "#0369A1"

FONTS_HREF = (
    "https://fonts.googleapis.com/css2?"
    "family=Figtree:wght@400;500;600;700&"
    "family=Noto+Sans:wght@400;500;700&"
    "family=Noto+Sans+Devanagari:wght@400;600;700&display=swap"
)

CSS = f"""
@import url('{FONTS_HREF}');

:root {{
  --pc-primary: {PRIMARY};
  --pc-on-primary: {ON_PRIMARY};
  --pc-secondary: {SECONDARY};
  --pc-accent: {ACCENT};
  --pc-bg: {BACKGROUND};
  --pc-fg: {FOREGROUND};
  --pc-card: {CARD};
  --pc-muted: {MUTED};
  --pc-muted-fg: {MUTED_FG};
  --pc-border: {BORDER};
  --pc-ask: {ASK};
  --pc-ring: {RING};
}}

html, body, [data-testid="stAppViewContainer"], .stApp {{
  background: var(--pc-bg) !important;
  color: var(--pc-fg) !important;
  font-family: "Noto Sans", "Noto Sans Devanagari", "Figtree", sans-serif !important;
  font-size: 18px !important;
}}

h1, h2, h3, .stMarkdown h1, .stMarkdown h2 {{
  font-family: "Figtree", "Noto Sans", sans-serif !important;
  color: var(--pc-fg) !important;
  letter-spacing: -0.02em;
}}
h1 {{ font-size: 2.15rem !important; font-weight: 700 !important; }}
h2 {{ font-size: 1.45rem !important; font-weight: 650 !important; }}

[data-testid="stHeader"] {{ background: transparent !important; }}
[data-testid="stSidebar"] {{
  background: var(--pc-card) !important;
  border-right: 1px solid var(--pc-border);
}}
[data-testid="stSidebarNavLink"] {{
  font-size: 1.05rem !important;
  border-radius: 12px !important;
  min-height: 44px;
}}
[data-testid="stSidebarNavLink"][aria-current="page"] {{
  background: var(--pc-muted) !important;
  color: var(--pc-primary) !important;
  font-weight: 600;
}}

[data-testid="stMain"] {{ padding-top: 0.5rem; }}

.stButton > button, .stDownloadButton > button {{
  background: var(--pc-primary) !important;
  color: var(--pc-on-primary) !important;
  border: 0 !important;
  border-radius: 14px !important;
  min-height: 48px !important;
  font-size: 1.05rem !important;
  font-weight: 600 !important;
  padding: 0.65rem 1.2rem !important;
  box-shadow: 0 8px 20px rgba(3, 105, 161, 0.18);
}}
.stButton > button:hover, .stDownloadButton > button:hover {{
  filter: brightness(1.05);
}}
.stButton > button:focus-visible, .stDownloadButton > button:focus-visible,
input:focus-visible, textarea:focus-visible, select:focus-visible {{
  outline: 3px solid var(--pc-ring) !important;
  outline-offset: 2px !important;
}}

[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
textarea {{
  min-height: 44px !important;
  font-size: 1.05rem !important;
  border-radius: 12px !important;
}}
textarea {{ min-height: 180px !important; }}

[data-testid="stAlert"] {{ border-radius: 14px !important; }}
[data-testid="stExpander"] {{
  background: var(--pc-card) !important;
  border: 1px solid var(--pc-border) !important;
  border-radius: 16px !important;
  box-shadow: 0 10px 30px rgba(12, 74, 110, 0.06);
}}

div[data-testid="stCheckbox"] label {{
  font-size: 1.08rem !important;
  font-weight: 600 !important;
}}
div[data-testid="stCheckbox"] input {{
  width: 22px; height: 22px;
}}

.pc-hero, .pc-card, .pc-stepper {{
  background: var(--pc-card);
  border: 1px solid var(--pc-border);
  border-radius: 20px;
  padding: 1.25rem 1.4rem;
  box-shadow: 0 12px 32px rgba(12, 74, 110, 0.07);
}}
.pc-kicker {{
  color: var(--pc-primary);
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-size: 0.78rem;
  margin: 0 0 0.4rem;
}}
.pc-lede {{
  color: var(--pc-muted-fg);
  font-size: 1.05rem;
  line-height: 1.55;
  margin: 0.4rem 0 0;
}}
.pc-stepper {{
  display: flex;
  gap: 0.6rem;
  flex-wrap: wrap;
  margin: 0 0 1.1rem;
  padding: 0.7rem 0.85rem;
}}
.pc-step {{
  flex: 1;
  min-width: 110px;
  text-align: center;
  padding: 0.55rem 0.4rem;
  border-radius: 12px;
  font-weight: 650;
  color: var(--pc-muted-fg);
  background: var(--pc-muted);
}}
.pc-step.is-now {{
  background: var(--pc-primary);
  color: var(--pc-on-primary);
}}
.pc-step.is-done {{
  background: #DCFCE7;
  color: #166534;
}}
.pc-ask {{
  background: #FEF2F2;
  border: 2px solid var(--pc-ask);
  color: var(--pc-ask);
  border-radius: 12px;
  padding: 0.7rem 0.9rem;
  font-weight: 700;
}}
.pc-ok {{
  background: #DCFCE7;
  color: #166534;
  border-radius: 12px;
  padding: 0.7rem 0.9rem;
  font-weight: 700;
}}
.pc-grid {{
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.9rem;
  margin: 1rem 0;
}}
.pc-tile {{
  background: var(--pc-card);
  border: 1px solid var(--pc-border);
  border-radius: 18px;
  padding: 1rem 1.1rem;
}}
.pc-tile b {{ color: var(--pc-primary); font-size: 1.35rem; }}
.pc-badge {{
  display: inline-block;
  background: var(--pc-muted);
  color: var(--pc-primary);
  border-radius: 999px;
  padding: 0.2rem 0.7rem;
  font-size: 0.85rem;
  font-weight: 650;
}}
@media (max-width: 720px) {{
  .pc-grid {{ grid-template-columns: 1fr; }}
  h1 {{ font-size: 1.7rem !important; }}
}}
"""

STEPS = ("Scan", "Review", "Chart")


def apply_theme(page_title: str = "Aaji's Pill Clerk") -> None:
    try:
        st.set_page_config(page_title=page_title, layout="wide", initial_sidebar_state="expanded")
    except Exception:
        pass
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


def stepper(current: str) -> None:
    order = list(STEPS)
    idx = order.index(current) if current in order else -1
    bits: list[str] = []
    for i, name in enumerate(order):
        cls = "pc-step"
        if i < idx:
            cls += " is-done"
        elif i == idx:
            cls += " is-now"
        bits.append(f'<div class="{cls}">{i + 1}. {name}</div>')
    st.markdown(f'<div class="pc-stepper">{"".join(bits)}</div>', unsafe_allow_html=True)
