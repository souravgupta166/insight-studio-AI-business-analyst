"""Insight Studio — multi-page AI Business Analyst (bright theme, v2)."""

import sys
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agent.orchestrator import (  # noqa: E402
    UnsupportedQuestionError,
    execute_question,
)

st.set_page_config(
    page_title="Insight Studio | Business Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================================================
# CONFIGURATION
# =========================================================

QUESTION_LIBRARY = {
    "KPIs & Performance": {
        "icon": "📦",
        "description": "Orders and operational performance",
        "questions": [
            ("Total orders", "How many total orders do we have?",
             "Count recorded orders."),
            ("Delivery rate", "What is the delivery rate?",
             "Measure delivered orders as a percentage."),
            ("Delivered orders", "How many orders were delivered?",
             "Count delivered orders."),
            ("Canceled orders", "How many orders were canceled?",
             "Count canceled orders."),
            ("Unavailable orders", "How many orders were unavailable?",
             "Count unavailable orders."),
        ],
    },
    "Sales & Revenue": {
        "icon": "💰",
        "description": "Recorded sales, freight and payments",
        "questions": [
            ("Recorded item sales", "What is the total item sales value?",
             "Item prices excluding freight."),
            ("Freight value", "What is the total freight value?",
             "Sum recorded freight charges."),
            ("Recorded payments", "What is the total recorded payment value?",
             "Sum values recorded in payment records."),
            ("Average item value per order",
             "What is the average item value per order?",
             "Average item sales per order with items."),
            ("Items plus freight per order",
             "What is the average items plus freight value per order?",
             "Item value and freight per order."),
        ],
    },
    "Monthly Trends": {
        "icon": "📈",
        "description": "Monthly sales and order movements",
        "questions": [
            ("November 2017", "Show the monthly sales trend for 2017-11.",
             "Investigate November 2017."),
            ("December 2017", "Show the monthly sales trend for 2017-12.",
             "Investigate December 2017."),
            ("January 2018", "Show the monthly sales trend for 2018-01.",
             "Investigate January 2018."),
            ("February 2018", "Show the monthly sales trend for 2018-02.",
             "Investigate February 2018."),
        ],
    },
    "Anomaly Investigation": {
        "icon": "🚨",
        "description": "Investigate potentially unusual activity",
        "questions": [
            ("November 2017", "Investigate the sales anomaly in 2017-11.",
             "Screen November activity."),
            ("December 2017", "Investigate the sales anomaly in 2017-12.",
             "Screen December activity."),
            ("January 2018", "Investigate the sales anomaly in 2018-01.",
             "Screen January activity."),
            ("February 2018", "Investigate the sales anomaly in 2018-02.",
             "Screen February activity."),
        ],
    },
}

PAGES = [
    "Overview",
    "KPI Explorer",
    "Sales & Revenue",
    "Monthly Trends",
    "Anomaly Investigation",
    "AI Assistant",
]

# page -> (emoji icon, accent colour)
PAGE_META = {
    "Overview": ("🏠", "#2F4BFF"),
    "KPI Explorer": ("📦", "#2F4BFF"),
    "Sales & Revenue": ("💰", "#00A878"),
    "Monthly Trends": ("📈", "#7B4DFF"),
    "Anomaly Investigation": ("🚨", "#FF5A5F"),
    "AI Assistant": ("🤖", "#FF8A1F"),
}

# page -> question-library category
PAGE_CATEGORY = {
    "KPI Explorer": "KPIs & Performance",
    "Sales & Revenue": "Sales & Revenue",
    "Monthly Trends": "Monthly Trends",
    "Anomaly Investigation": "Anomaly Investigation",
}

QUICK_QUESTIONS = [
    ("Total orders", "How many total orders do we have?"),
    ("Delivery rate", "What is the delivery rate?"),
    ("Recorded item sales", "What is the total item sales value?"),
    ("November sales trend", "Show the monthly sales trend for 2017-11."),
    ("Investigate anomaly", "Investigate the sales anomaly in 2017-11."),
]

HISTORY_LIMIT = 8

TOTAL_QUESTIONS = sum(
    len(group["questions"]) for group in QUESTION_LIBRARY.values()
)

# =========================================================
# SESSION STATE
# =========================================================

DEFAULTS = {
    "page": "Overview",
    "business_question": "",
    "last_question": "",
    "last_report": None,
    "pending_question": None,
    "history": [],
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


def navigate_to(page: str):
    """Navigate to a different workspace page via a widget callback."""
    st.session_state.page = page


def choose_question(question: str, page: str = "AI Assistant"):
    """Send a question to the assistant page and run it there."""
    st.session_state.business_question = question
    st.session_state.page = page
    st.session_state.pending_question = question


def run_here(question: str):
    """Run a question and show the result on the current page."""
    st.session_state.pending_question = question


def open_history(index: int):
    """Re-open a previous result from this session."""
    history = st.session_state.history
    if 0 <= index < len(history):
        item = history[index]
        st.session_state.last_question = item["question"]
        st.session_state.last_report = item["report"]
        st.session_state.business_question = item["question"]
        st.session_state.page = "AI Assistant"


def clear_history():
    st.session_state.history = []


def clear_workspace():
    st.session_state.business_question = ""
    st.session_state.last_question = ""
    st.session_state.last_report = None
    st.session_state.pending_question = None


def money_or_number(value, unit=""):
    if value is None:
        return "N/A"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (int, float)):
        if unit == "BRL":
            return f"R$ {value:,.2f}"
        if unit in {"%", "percent"}:
            return f"{value:,.2f}%"
        if unit == "orders":
            return f"{value:,.0f}"
        if isinstance(value, float):
            return f"{value:,.2f}"
        return f"{value:,}"
    return f"{value} {unit}".strip()


# =========================================================
# STYLING  (bright theme: cobalt + sunshine, high contrast)
# =========================================================

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700;12..96,800&family=DM+Sans:wght@400;500;600;700&display=swap');

:root {
    --ink: #0F1B3D;
    --muted: #56637F;
    --line: #D5DDF2;
    --cobalt: #2F4BFF;
    --violet: #7B4DFF;
    --sun: #FFC933;
    --mint: #00A878;
    --coral: #FF5A5F;
    --paper: #F5F7FC;
    --card: #FFFFFF;
    --shadow: 0 8px 24px rgba(40, 60, 140, .09);
}

/* ---------- Base ---------- */
.stApp {
    background:
        radial-gradient(900px 420px at 100% -5%, #FFF1BF 0%, rgba(255,241,191,0) 60%),
        radial-gradient(800px 500px at -5% 105%, #DCE4FF 0%, rgba(220,228,255,0) 60%),
        var(--paper);
    color: var(--ink);
}

html, body, .stApp,
.stApp :is(p, li, label, input, textarea, button, summary, td, th) {
    font-family: 'DM Sans', 'Segoe UI', system-ui, sans-serif;
}

.stApp :is(h1, h2, h3, h4, h5, h6) {
    font-family: 'Bricolage Grotesque', 'DM Sans', system-ui, sans-serif;
    color: var(--ink);
    letter-spacing: -.02em;
}

.stApp :is(p, li, td, th) { color: var(--ink); }

[data-testid="stHeader"] { background: transparent; }

.block-container {
    max-width: 1500px;
    padding: 1.6rem 2.2rem 3rem 2.2rem;
}

hr { border-color: var(--line); }

.muted { color: var(--muted); font-size: .9rem; }

/* ---------- Hero (Overview) ---------- */
.hero {
    position: relative;
    overflow: hidden;
    background: linear-gradient(120deg, #2F4BFF 0%, #5B3DF5 60%, #7B4DFF 100%);
    border-radius: 26px;
    padding: 2.6rem 2.8rem 2.3rem 2.8rem;
    box-shadow: 0 18px 40px rgba(47, 75, 255, .28);
    margin-bottom: 1.8rem;
}
.hero::after {
    content: "";
    position: absolute;
    right: -70px; top: -70px;
    width: 250px; height: 250px;
    border-radius: 50%;
    background: var(--sun);
}
.hero::before {
    content: "";
    position: absolute;
    right: 100px; bottom: -85px;
    width: 170px; height: 170px;
    border-radius: 50%;
    background: var(--coral);
    opacity: .92;
}
.hero > * { position: relative; z-index: 1; }
.hero-pill {
    display: inline-block;
    background: var(--sun);
    color: var(--ink);
    font-weight: 700;
    font-size: .8rem;
    padding: .3rem .85rem;
    border-radius: 999px;
    margin-bottom: 1rem;
}
.hero-title {
    font-family: 'Bricolage Grotesque', 'DM Sans', sans-serif;
    color: #FFFFFF;
    font-size: clamp(2.1rem, 4.2vw, 3.3rem);
    font-weight: 800;
    letter-spacing: -.04em;
    line-height: 1.06;
    max-width: min(740px, 80%);
    margin-bottom: .85rem;
}
.hero-text {
    color: rgba(255,255,255,.95);
    font-size: 1.07rem;
    line-height: 1.6;
    max-width: min(640px, 78%);
    margin-bottom: 1.2rem;
}
.hero-tags span {
    display: inline-block;
    color: #FFFFFF;
    background: rgba(255,255,255,.18);
    border: 1px solid rgba(255,255,255,.38);
    border-radius: 999px;
    padding: .28rem .85rem;
    font-size: .84rem;
    font-weight: 600;
    margin: 0 .45rem .35rem 0;
}

/* ---------- Page header ---------- */
.page-head {
    display: flex;
    gap: 1.1rem;
    align-items: flex-start;
    background: var(--card);
    border: 1px solid var(--line);
    border-left: 7px solid var(--accent, var(--cobalt));
    border-radius: 20px;
    padding: 1.3rem 1.6rem;
    box-shadow: var(--shadow);
    margin-bottom: 1.4rem;
}
.page-icon {
    flex: 0 0 auto;
    width: 3.4rem; height: 3.4rem;
    border-radius: 16px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.7rem;
    background: var(--accent, var(--cobalt));
}
.crumb {
    color: var(--accent, var(--cobalt));
    font-weight: 700;
    font-size: .85rem;
    margin-bottom: .15rem;
}
.page-title {
    font-family: 'Bricolage Grotesque', 'DM Sans', sans-serif;
    color: var(--ink);
    font-size: clamp(1.7rem, 3vw, 2.3rem);
    font-weight: 800;
    letter-spacing: -.035em;
    line-height: 1.12;
    margin-bottom: .35rem;
}
.page-description {
    color: var(--muted);
    font-size: 1rem;
    line-height: 1.6;
    max-width: 880px;
}

/* ---------- Section titles ---------- */
.section-title {
    font-family: 'Bricolage Grotesque', 'DM Sans', sans-serif;
    color: var(--ink);
    font-size: 1.45rem;
    font-weight: 800;
    letter-spacing: -.03em;
    margin: .8rem 0 .15rem 0;
}
.section-description {
    color: var(--muted);
    font-size: .95rem;
    margin-bottom: .9rem;
}

/* ---------- Cards ---------- */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: 18px;
    box-shadow: var(--shadow);
}
.tile {
    width: 3rem; height: 3rem;
    border-radius: 14px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.5rem;
    margin-bottom: .6rem;
}
.card-title {
    font-family: 'Bricolage Grotesque', 'DM Sans', sans-serif;
    color: var(--ink);
    font-size: 1.15rem;
    font-weight: 800;
    letter-spacing: -.02em;
    margin-bottom: .15rem;
}
.accent-bar {
    height: 6px;
    border-radius: 6px;
    margin: .1rem 0 .9rem 0;
}
.step-num {
    width: 2.2rem; height: 2.2rem;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    background: var(--cobalt);
    color: #FFFFFF;
    font-weight: 800;
    margin-bottom: .6rem;
}
.count-chip {
    display: inline-block;
    background: #EAEFFF;
    color: var(--cobalt);
    font-weight: 700;
    font-size: .78rem;
    padding: .15rem .6rem;
    border-radius: 999px;
    margin-bottom: .6rem;
}

/* ---------- Result header ---------- */
.result-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    flex-wrap: wrap;
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 1rem 1.3rem;
    box-shadow: var(--shadow);
    margin-bottom: 1rem;
}
.result-label { color: var(--muted); font-size: .82rem; font-weight: 600; }
.result-question {
    font-family: 'Bricolage Grotesque', 'DM Sans', sans-serif;
    color: var(--ink);
    font-size: 1.25rem;
    font-weight: 800;
    letter-spacing: -.02em;
}
.badge {
    display: inline-block;
    font-weight: 700;
    font-size: .85rem;
    padding: .35rem .9rem;
    border-radius: 999px;
    border: 1px solid transparent;
}
.badge.ok { background: #DDF7EC; color: #006B45; border-color: #9BE3C4; }
.badge.warn { background: #FFF3CC; color: #7A5600; border-color: #F2D675; }
.badge.bad { background: #FFE1E2; color: #A3191E; border-color: #F5A9AC; }

/* ---------- Metrics (never truncated) ---------- */
div[data-testid="stMetric"] {
    background: var(--card);
    border: 1px solid var(--line);
    border-left: 6px solid var(--cobalt);
    border-radius: 14px;
    padding: 1rem 1.1rem;
    box-shadow: var(--shadow);
}
div[data-testid="stMetricLabel"],
div[data-testid="stMetricLabel"] * {
    color: var(--muted) !important;
    font-weight: 600;
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: clip !important;
}
div[data-testid="stMetricValue"],
div[data-testid="stMetricValue"] * {
    color: var(--cobalt) !important;
    font-weight: 800;
    font-size: 1.7rem;
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: clip !important;
}

/* ---------- Buttons ---------- */
.stButton > button,
.stDownloadButton > button {
    border: 1.5px solid var(--line);
    border-radius: 12px;
    min-height: 2.7rem;
    background: #FFFFFF;
    color: var(--ink);
    font-weight: 600;
    box-shadow: 0 1px 2px rgba(15, 27, 61, .06);
    transition: transform .15s ease, box-shadow .15s ease, border-color .15s ease;
}
.stButton > button p,
.stDownloadButton > button p { color: inherit; }
.stButton > button:hover,
.stDownloadButton > button:hover {
    border-color: var(--cobalt);
    color: var(--cobalt);
    background: #F0F3FF;
    transform: translateY(-1px);
    box-shadow: 0 6px 14px rgba(47, 75, 255, .18);
}
.stButton > button[kind="primary"],
.stButton > button[data-testid="stBaseButton-primary"] {
    background: linear-gradient(135deg, var(--cobalt), var(--violet));
    border-color: transparent;
    color: #FFFFFF;
}
.stButton > button[kind="primary"] p,
.stButton > button[data-testid="stBaseButton-primary"] p { color: #FFFFFF; }
.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="stBaseButton-primary"]:hover {
    color: #FFFFFF;
    border-color: transparent;
    filter: brightness(1.08);
}
.stButton > button[kind="primary"]:hover p,
.stButton > button[data-testid="stBaseButton-primary"]:hover p { color: #FFFFFF; }

/* ---------- Inputs ---------- */
div[data-testid="stWidgetLabel"] p { color: var(--ink); font-weight: 600; }

div[data-baseweb="textarea"],
div[data-baseweb="base-input"],
div[data-baseweb="input"] {
    background: #FFFFFF !important;
    border-radius: 12px !important;
}
div[data-testid="stTextArea"] textarea,
div[data-testid="stTextInput"] input {
    background: #FFFFFF !important;
    color: var(--ink) !important;
    border: 1.5px solid var(--line);
    border-radius: 12px;
    font-size: 1rem;
}
div[data-testid="stTextArea"] textarea::placeholder,
div[data-testid="stTextInput"] input::placeholder {
    color: #6B7898 !important;
    opacity: 1;
}
div[data-testid="stTextArea"] textarea:focus,
div[data-testid="stTextInput"] input:focus {
    border-color: var(--cobalt);
    box-shadow: 0 0 0 3px rgba(47, 75, 255, .18);
}
div[data-baseweb="select"] > div {
    background: #FFFFFF;
    border: 1.5px solid var(--line);
    border-radius: 12px;
}
div[data-baseweb="select"] *,
div[data-baseweb="popover"] li,
div[data-baseweb="popover"] li * { color: var(--ink); }

/* ---------- Alerts, expanders, tables ---------- */
div[data-testid="stAlert"] {
    border-radius: 14px;
    border: 1px solid rgba(15, 27, 61, .08);
}
div[data-testid="stAlert"] * { color: var(--ink); }

div[data-testid="stExpander"] {
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: 14px;
    box-shadow: var(--shadow);
}
div[data-testid="stExpander"] details { border: none !important; }
div[data-testid="stExpander"] summary,
div[data-testid="stExpander"] summary * {
    color: var(--ink);
    font-weight: 600;
}

div[data-testid="stDataFrame"] {
    border: 1px solid var(--line);
    border-radius: 12px;
    overflow: hidden;
    background: #FFFFFF;
}

/* st.table: full text always visible, wraps long findings */
div[data-testid="stTable"] { overflow-x: auto; }
div[data-testid="stTable"] table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    background: #FFFFFF;
    border: 1px solid var(--line);
    border-radius: 12px;
    overflow: hidden;
}
div[data-testid="stTable"] th {
    background: #EAEFFF;
    color: var(--ink);
    font-weight: 700;
    text-align: left;
    padding: .65rem .8rem;
    border-bottom: 1px solid var(--line);
    white-space: nowrap;
}
div[data-testid="stTable"] td {
    color: var(--ink);
    padding: .6rem .8rem;
    border-bottom: 1px solid #E8EDF8;
    white-space: normal;
    word-break: break-word;
    vertical-align: top;
}
div[data-testid="stTable"] tbody tr:nth-child(even) td { background: #F8FAFF; }
div[data-testid="stTable"] tbody tr:last-child td { border-bottom: none; }

pre, code { color: var(--ink); }

/* ---------- Footer ---------- */
.footer {
    color: var(--muted);
    font-size: .82rem;
    line-height: 1.7;
}

/* ---------- Sidebar (bold cobalt panel) ---------- */
[data-testid="stSidebar"] {
    background: linear-gradient(185deg, #1A2BD6 0%, #2F4BFF 50%, #6A3FF5 100%);
    border-right: none;
}
[data-testid="stSidebar"] .block-container { padding-top: 1.5rem; }
[data-testid="stSidebar"] :is(p, span, label, li, strong) { color: #FFFFFF; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] * {
    color: rgba(255,255,255,.85) !important;
}
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.28); }

.brand {
    font-family: 'Bricolage Grotesque', 'DM Sans', sans-serif;
    font-size: 1.6rem;
    font-weight: 800;
    letter-spacing: -.04em;
    color: #FFFFFF;
}
[data-testid="stSidebar"] .brand-mark { color: var(--sun); }
.brand-caption {
    color: rgba(255,255,255,.85);
    font-size: .85rem;
    margin-top: .15rem;
}
.sidebar-label {
    color: #FFE08A;
    font-size: .8rem;
    font-weight: 700;
    margin: .9rem 0 .45rem 0;
}
.session-box {
    background: rgba(255,255,255,.14);
    border: 1px solid rgba(255,255,255,.3);
    border-radius: 12px;
    padding: .6rem .85rem;
    color: #FFFFFF;
    font-size: .88rem;
    font-weight: 600;
}

[data-testid="stSidebar"] div[role="radiogroup"] { gap: .3rem; }
[data-testid="stSidebar"] div[role="radiogroup"] label {
    background: rgba(255,255,255,.10);
    border-radius: 12px;
    padding: .55rem .85rem;
    width: 100%;
    transition: background .15s ease;
}
[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
    background: rgba(255,255,255,.22);
}
[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-of-type {
    display: none;
}
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
    background: #FFFFFF;
    box-shadow: 0 8px 18px rgba(10, 20, 90, .35);
}
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) * {
    color: var(--ink) !important;
    font-weight: 700;
}

[data-testid="stSidebar"] .stButton > button {
    background: var(--sun);
    border: none;
    color: var(--ink);
    font-weight: 700;
}
[data-testid="stSidebar"] .stButton > button * { color: var(--ink) !important; }
[data-testid="stSidebar"] .stButton > button:hover {
    background: #FFD95C;
    transform: translateY(-1px);
}

@media (prefers-reduced-motion: reduce) {
    * { transition: none !important; }
}
</style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# SIDEBAR NAVIGATION
# =========================================================

with st.sidebar:
    st.markdown(
        '<div class="brand"><span class="brand-mark">◈</span> Insight Studio</div>'
        '<div class="brand-caption">AI Business Analyst</div>',
        unsafe_allow_html=True,
    )

    st.divider()
    st.markdown('<div class="sidebar-label">Workspace</div>',
                unsafe_allow_html=True)

    st.radio(
        "Workspace navigation",
        PAGES,
        key="page",
        format_func=lambda name: f"{PAGE_META[name][0]}  {name}",
        label_visibility="collapsed",
    )

    st.divider()
    st.markdown('<div class="sidebar-label">This session</div>',
                unsafe_allow_html=True)
    count = len(st.session_state.history)
    st.markdown(
        f'<div class="session-box">{count} investigation'
        f'{"" if count == 1 else "s"} completed</div>',
        unsafe_allow_html=True,
    )

    st.divider()
    st.markdown('<div class="sidebar-label">Data source</div>',
                unsafe_allow_html=True)
    st.markdown("**Olist e-commerce**")
    st.caption("DuckDB · Read-only")
    st.caption("Structured analytical workflows")

    st.divider()
    st.markdown('<div class="sidebar-label">How to read results</div>',
                unsafe_allow_html=True)
    st.caption(
        "Results depend on supported workflows and available evidence. "
        "Descriptive patterns do not establish causality."
    )

    st.button(
        "＋  New investigation",
        on_click=clear_workspace,
        use_container_width=True,
    )

page = st.session_state.page

# =========================================================
# REUSABLE COMPONENTS
# =========================================================


def table_height(rows: int) -> int:
    """Height that shows every row (capped so very long tables scroll)."""
    return min(35 * (rows + 1) + 3, 720)


def section(title, description=None):
    html = f'<div class="section-title">{escape(title)}</div>'
    if description:
        html += f'<div class="section-description">{escape(description)}</div>'
    st.markdown(html, unsafe_allow_html=True)


def page_header(eyebrow, title, description):
    icon, color = PAGE_META.get(st.session_state.page, ("◈", "#2F4BFF"))
    st.markdown(
        f'<div class="page-head" style="--accent:{color}">'
        f'<div class="page-icon">{icon}</div>'
        f'<div><div class="crumb">{escape(eyebrow)}</div>'
        f'<div class="page-title">{escape(title)}</div>'
        f'<div class="page-description">{escape(description)}</div></div></div>',
        unsafe_allow_html=True,
    )


def accent_bar(color):
    st.markdown(
        f'<div class="accent-bar" style="background:{color}"></div>',
        unsafe_allow_html=True,
    )


def status_badge(status):
    css = {"success": "ok", "partial": "warn"}.get(status, "bad")
    label = {
        "success": "Completed",
        "partial": "Completed with limitations",
    }.get(status, f"Status: {status}")
    return f'<span class="badge {css}">{escape(label)}</span>'


def run_pending():
    """Execute a requested question (if any) and store the report."""
    question = st.session_state.pending_question
    if not question:
        return

    st.session_state.pending_question = None
    st.session_state.last_question = question
    st.session_state.last_report = None

    with st.spinner("Investigating the available evidence..."):
        try:
            report = execute_question(question)

        except UnsupportedQuestionError as exc:
            st.error("This question is not supported yet.")
            st.write(str(exc))
            st.info(
                "Try one of the supplied questions. The backend supports "
                "only the analytical workflows implemented in the current "
                "project."
            )

        except (ValueError, TypeError) as exc:
            st.error("The question could not be processed.")
            st.exception(exc)

        except Exception as exc:
            st.error("The investigation failed.")
            st.exception(exc)

        else:
            st.session_state.last_report = report
            history = [
                item for item in st.session_state.history
                if item["question"] != question
            ]
            history.insert(0, {"question": question, "report": report})
            st.session_state.history = history[:HISTORY_LIMIT]


def render_report(report, question=None):
    """Render the project's existing InvestigationReport."""
    question = question or st.session_state.last_question

    st.markdown(
        '<div class="result-head"><div>'
        '<div class="result-label">Question</div>'
        f'<div class="result-question">{escape(question or "—")}</div>'
        f'</div>{status_badge(report.status)}</div>',
        unsafe_allow_html=True,
    )

    if report.status == "partial":
        st.warning("Analysis completed with limitations.")
    elif report.status != "success":
        st.error(f"Analysis status: {report.status}")

    st.markdown("#### Executive summary")
    with st.container(border=True):
        st.write(report.summary)

    evidence = None

    if report.findings:
        findings = [item.model_dump() for item in report.findings]

        numeric = [
            item for item in findings
            if isinstance(item.get("value"), (int, float))
            and not isinstance(item.get("value"), bool)
        ]

        if numeric:
            st.markdown("#### Key metrics")
            cols = st.columns(min(4, len(numeric)))

            for index, item in enumerate(numeric):
                label = (
                    item.get("metric_name")
                    or item.get("claim")
                    or "Metric"
                )
                cols[index % len(cols)].metric(
                    label=label.replace("_", " ").title(),
                    value=money_or_number(
                        item.get("value"),
                        item.get("unit") or "",
                    ),
                )

        st.markdown("#### Evidence")
        evidence = pd.DataFrame(
            [
                {
                    "Type": item.evidence_type,
                    "Metric": item.metric_name or "—",
                    "Value": money_or_number(item.value, item.unit or ""),
                    "Period": item.period or "—",
                    "Finding": item.claim,
                    "Source": item.source_tool,
                }
                for item in report.findings
            ]
        )
        shown = evidence.copy()
        shown.index = range(1, len(shown) + 1)
        # st.table wraps text, so long findings are never cut off.
        st.table(shown)
    else:
        st.info("No analytical findings were returned.")

    data = getattr(report, "data", None)

    if isinstance(data, dict):
        anomaly = data.get("anomaly_evidence")
        if isinstance(anomaly, dict):
            st.markdown("#### Anomaly assessment")

            if anomaly.get("is_anomaly") is True:
                st.warning(
                    "The detector flagged a potential anomaly. "
                    "This does not establish the cause."
                )
            elif anomaly.get("is_anomaly") is False:
                st.info("The detector did not flag this period.")

            score = anomaly.get("robust_z_score")
            if isinstance(score, (int, float)):
                st.metric("Robust anomaly score", f"{score:.2f}")

            with st.expander("Anomaly evidence details"):
                st.json(anomaly)

        decomposition = data.get("sales_decomposition")
        if isinstance(decomposition, dict):
            st.markdown("#### Sales change decomposition")

            names = {
                "total_sales_change": "Total sales change",
                "order_volume_effect": "Order-volume contribution",
                "average_item_value_effect": "Average-item-value contribution",
                "reconciliation_difference": "Reconciliation difference",
            }

            rows = [
                {
                    "Component": names.get(
                        key, key.replace("_", " ").title()
                    ),
                    "Value (BRL)": f"R$ {value:,.2f}",
                }
                for key, value in decomposition.items()
                if isinstance(value, (int, float))
                and not isinstance(value, bool)
            ]

            if rows:
                table = pd.DataFrame(rows)
                table.index = range(1, len(table) + 1)
                st.table(table)

        category_changes = data.get("category_changes")
        if isinstance(category_changes, list) and category_changes:
            frame = pd.DataFrame(category_changes)
            st.markdown("#### Category-level changes")

            if "sales_change_brl" in frame.columns:
                frame["sales_change_brl"] = pd.to_numeric(
                    frame["sales_change_brl"], errors="coerce"
                )
                frame = frame.sort_values("sales_change_brl")

                if "category" in frame.columns:
                    st.bar_chart(
                        frame.set_index("category")["sales_change_brl"],
                        color="#2F4BFF",
                    )

            st.dataframe(
                frame,
                use_container_width=True,
                hide_index=True,
                height=table_height(len(frame)),
            )

    if report.recommendations:
        st.markdown("#### Recommended next steps")
        for recommendation in report.recommendations:
            st.markdown(f"- {recommendation}")

    if report.limitations:
        st.markdown("#### Limitations")
        for limitation in report.limitations:
            st.markdown(f"- {limitation}")

    st.markdown("#### Export")
    export_cols = st.columns(2)
    key_base = f"{st.session_state.page}_{abs(hash(question or ''))}"

    with export_cols[0]:
        st.download_button(
            "⬇  Download report (JSON)",
            data=report.model_dump_json(indent=2),
            file_name="insight_report.json",
            mime="application/json",
            key=f"dl_json_{key_base}",
            use_container_width=True,
        )

    with export_cols[1]:
        if evidence is not None:
            st.download_button(
                "⬇  Download evidence (CSV)",
                data=evidence.to_csv(index=False).encode("utf-8"),
                file_name="insight_evidence.csv",
                mime="text/csv",
                key=f"dl_csv_{key_base}",
                use_container_width=True,
            )

    with st.expander("Technical details and report JSON"):
        st.write("**Intent:**", report.intent)
        st.write("**Tools used:**", ", ".join(report.tools_used))
        st.write("**Database access:**", report.database_access)
        st.write(
            "**Causal conclusion established:**",
            report.causal_conclusion_established,
        )
        st.code(report.model_dump_json(indent=2), language="json")


def render_question_buttons(items, prefix):
    """Display reusable question shortcuts (route to the assistant)."""
    columns = st.columns(min(3, len(items)))

    for index, item in enumerate(items):
        with columns[index % len(columns)]:
            title, question = item[0], item[1]
            st.button(
                title,
                key=f"{prefix}_{index}_{title}",
                on_click=choose_question,
                args=(question, "AI Assistant"),
                use_container_width=True,
            )


def question_cards(category, accent, button_label, per_row=3, primary=False):
    """Grid of question cards that run in place on the current page."""
    questions = QUESTION_LIBRARY[category]["questions"]

    for start in range(0, len(questions), per_row):
        group = questions[start:start + per_row]
        columns = st.columns(per_row)

        for column, (title, question, description) in zip(columns, group):
            with column:
                with st.container(border=True):
                    accent_bar(accent)
                    st.markdown("#### " + title)
                    st.caption(description)
                    st.button(
                        button_label,
                        key=f"{st.session_state.page}_{title}",
                        on_click=run_here,
                        args=(question,),
                        type="primary" if primary else "secondary",
                        use_container_width=True,
                    )


# =========================================================
# OVERVIEW PAGE
# =========================================================

if page == "Overview":
    st.markdown(
        '<div class="hero">'
        '<div class="hero-pill">● Read-only data</div>'
        '<div class="hero-title">Business intelligence, grounded in evidence.</div>'
        '<div class="hero-text">A central workspace for exploring the Olist '
        'dataset, reviewing business KPIs and investigating monthly '
        'performance.</div>'
        '<div class="hero-tags">'
        f'<span>{len(QUESTION_LIBRARY)} analytical workflows</span>'
        f'<span>{TOTAL_QUESTIONS} ready-made questions</span>'
        '<span>Olist e-commerce</span><span>DuckDB</span></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    section("Start an investigation", "Choose a workflow to get started.")

    overview_cards = [
        ("KPI Explorer", "Orders and delivery performance",
         "Open KPI Explorer"),
        ("Sales & Revenue", "Recorded sales and payment metrics",
         "Open Sales & Revenue"),
        ("Monthly Trends", "Explore monthly sales movements",
         "Open Monthly Trends"),
        ("Anomaly Investigation", "Inspect potentially unusual activity",
         "Open Anomaly Investigation"),
    ]

    columns = st.columns(4)

    for column, card in zip(columns, overview_cards):
        title, description, button_label = card
        icon, color = PAGE_META[title]
        total = len(QUESTION_LIBRARY[PAGE_CATEGORY[title]]["questions"])

        with column:
            with st.container(border=True):
                st.markdown(
                    f'<div class="tile" style="background:{color}">{icon}</div>'
                    f'<div class="card-title">{escape(title)}</div>',
                    unsafe_allow_html=True,
                )
                st.caption(description)
                st.markdown(
                    f'<span class="count-chip">{total} questions</span>',
                    unsafe_allow_html=True,
                )
                st.button(
                    button_label,
                    key=f"overview_{title}",
                    use_container_width=True,
                    on_click=navigate_to,
                    args=(title,),
                )

    st.divider()

    section("How it works")
    steps = [
        ("1", "Pick a question",
         "Choose a ready-made question or type your own."),
        ("2", "The backend runs it",
         "The question is validated and routed to a supported workflow."),
        ("3", "Read the evidence",
         "Get a summary, metrics, an evidence table and limitations."),
    ]
    step_cols = st.columns(3)
    for column, (num, title, text) in zip(step_cols, steps):
        with column:
            with st.container(border=True):
                st.markdown(
                    f'<div class="step-num">{num}</div>'
                    f'<div class="card-title">{escape(title)}</div>',
                    unsafe_allow_html=True,
                )
                st.caption(text)

    st.divider()

    section("Ask the analyst", "Start with one of these common questions.")
    render_question_buttons(QUICK_QUESTIONS, "overview_question")

    st.divider()
    section("Recent investigations")

    history = st.session_state.history
    if history:
        for index, item in enumerate(history):
            with st.container(border=True):
                left, middle, right = st.columns([6, 2, 1.4])
                with left:
                    st.markdown(f"**{item['question']}**")
                with middle:
                    st.markdown(
                        status_badge(item["report"].status),
                        unsafe_allow_html=True,
                    )
                with right:
                    st.button(
                        "Open",
                        key=f"history_{index}",
                        on_click=open_history,
                        args=(index,),
                        use_container_width=True,
                    )
        st.button("Clear history", key="clear_history", on_click=clear_history)
    else:
        st.info(
            "No investigation has been run in this session yet. "
            "Choose a workflow or open AI Assistant to begin."
        )

# =========================================================
# KPI EXPLORER
# =========================================================

elif page == "KPI Explorer":
    page_header(
        "Analytics / KPI Explorer",
        "KPI Explorer",
        "Inspect the available order and delivery metrics. Select a question "
        "to run the corresponding supported backend workflow.",
    )

    question_cards("KPIs & Performance", "#2F4BFF", "Run KPI →", primary=True)

    run_pending()

    st.divider()
    section("Result")

    if st.session_state.last_report is not None:
        render_report(st.session_state.last_report)
    else:
        st.info("Run a KPI above to populate this area with real findings.")

# =========================================================
# SALES & REVENUE PAGE
# =========================================================

elif page == "Sales & Revenue":
    page_header(
        "Analytics / Financial metrics",
        "Sales & Revenue",
        "Explore recorded item prices, freight charges and payment values. "
        "These are distinct measures and should not be treated as profit.",
    )

    question_cards("Sales & Revenue", "#00A878", "Investigate metric →")

    run_pending()

    st.divider()
    section("Result")

    if st.session_state.last_report is not None:
        render_report(st.session_state.last_report)
    else:
        st.info("Run a metric above to see its findings here.")

    st.divider()
    section("Metric definitions")

    definitions = [
        ("Recorded item sales",
         "Sum of item prices recorded in order-item records. "
         "This measure excludes freight and does not establish profit."),
        ("Freight value",
         "Freight charges recorded in order-item records. "
         "This is separate from item sales."),
        ("Recorded payment value",
         "Payment amounts recorded in payment records. "
         "Interpretation depends on the backend metric definition."),
    ]

    def_cols = st.columns(3)
    for column, (name, text) in zip(def_cols, definitions):
        with column:
            with st.container(border=True):
                st.markdown(f"**{name}**")
                st.write(text)

# =========================================================
# MONTHLY TRENDS PAGE
# =========================================================

elif page == "Monthly Trends":
    page_header(
        "Analytics / Time series",
        "Monthly Trends",
        "Select a month to run the existing monthly sales-trend workflow. "
        "Charts appear only when the backend provides the relevant data.",
    )

    trend_questions = QUESTION_LIBRARY["Monthly Trends"]["questions"]

    selected_month = st.selectbox(
        "Select month",
        options=[item[0] for item in trend_questions],
        key="trend_month",
    )

    chosen = next(
        item for item in trend_questions if item[0] == selected_month
    )

    st.markdown("")
    with st.container(border=True):
        accent_bar("#7B4DFF")
        st.markdown("#### Monthly trend investigation")
        st.markdown(f"**Period:** {selected_month}")
        st.caption(chosen[2])

        st.button(
            "Run monthly analysis →",
            key="run_monthly_trend",
            type="primary",
            on_click=run_here,
            args=(chosen[1],),
            use_container_width=True,
        )

    run_pending()

    st.divider()

    if (
        st.session_state.last_report is not None
        and "trend" in st.session_state.last_question.casefold()
    ):
        section("Latest trend results")
        render_report(st.session_state.last_report)
    else:
        st.info(
            "No monthly result is displayed yet. Run a monthly analysis "
            "to see its summary and supporting evidence."
        )

# =========================================================
# ANOMALY INVESTIGATION PAGE
# =========================================================

elif page == "Anomaly Investigation":
    page_header(
        "Investigations / Anomaly screening",
        "Anomaly Investigation",
        "Screen selected months using the existing analytical workflow. "
        "A flagged anomaly indicates unusual activity, not its cause.",
    )

    anomaly_questions = QUESTION_LIBRARY["Anomaly Investigation"]["questions"]

    chosen_month = st.selectbox(
        "Period to investigate",
        options=[item[0] for item in anomaly_questions],
        key="anomaly_month",
    )

    chosen = next(
        item for item in anomaly_questions if item[0] == chosen_month
    )

    with st.container(border=True):
        accent_bar("#FF5A5F")
        st.markdown("#### Investigation setup")
        st.markdown(f"**Selected period:** {chosen_month}")
        st.caption(chosen[2])

        st.button(
            "Run anomaly investigation →",
            key="run_anomaly",
            type="primary",
            on_click=run_here,
            args=(chosen[1],),
            use_container_width=True,
        )

    run_pending()

    st.divider()

    if (
        st.session_state.last_report is not None
        and (
            "anomaly" in st.session_state.last_question.casefold()
            or "investigate" in st.session_state.last_question.casefold()
        )
    ):
        section("Latest investigation")
        render_report(st.session_state.last_report)
    else:
        st.info(
            "Run an investigation to review the returned summary, evidence "
            "and limitations."
        )

# =========================================================
# AI ASSISTANT PAGE
# =========================================================

elif page == "AI Assistant":
    page_header(
        "Assistant / Question workspace",
        "Ask the business analyst.",
        "Enter a question or select a supported example. The backend "
        "validates and executes the relevant analytical workflow.",
    )

    section("Question composer")

    with st.container(border=True):
        st.text_area(
            "Your business question",
            key="business_question",
            height=135,
            max_chars=1000,
            placeholder=(
                "What is the delivery rate?\n"
                "Show the monthly sales trend for 2017-11."
            ),
            label_visibility="collapsed",
        )

        run_col, clear_col = st.columns([2, 1])

        with run_col:
            submitted = st.button(
                "✦  Run investigation",
                key="assistant_run",
                type="primary",
                use_container_width=True,
            )

        with clear_col:
            st.button(
                "Clear question",
                key="assistant_clear",
                on_click=clear_workspace,
                use_container_width=True,
            )

    section("Suggested questions")
    render_question_buttons(QUICK_QUESTIONS, "assistant_question")

    with st.expander("Search all question examples"):
        query = st.text_input(
            "Find a question",
            key="assistant_library_search",
            placeholder="Search KPIs, sales, months or anomalies...",
        )

        for category, details in QUESTION_LIBRARY.items():
            matches = [
                item for item in details["questions"]
                if query.strip().casefold() in (
                    category + " " + " ".join(item)
                ).casefold()
            ]

            if not matches:
                continue

            st.markdown(f"#### {details['icon']} {category}")

            for title, question, description in matches:
                left, right = st.columns([5, 1])

                with left:
                    st.markdown(f"**{title}**")
                    st.caption(description)

                with right:
                    st.button(
                        "Run →",
                        key=f"assistant_library_{category}_{title}",
                        on_click=choose_question,
                        args=(question, "AI Assistant"),
                        use_container_width=True,
                    )

    # Normal submission; suggested-question callbacks set pending_question.
    if submitted:
        typed = st.session_state.business_question.strip()
        if not typed:
            st.warning("Enter a question or choose a suggested question.")
        else:
            st.session_state.pending_question = typed

    run_pending()

    if st.session_state.last_report is not None:
        st.divider()
        section("Investigation results")
        render_report(st.session_state.last_report)

        section("Continue exploring")

        followups = [
            ("Delivery rate", "What is the delivery rate?"),
            ("Recorded item sales", "What is the total item sales value?"),
            ("Monthly trend", "Show the monthly sales trend for 2017-11."),
        ]

        render_question_buttons(followups, "followup")

# =========================================================
# FOOTER
# =========================================================

st.divider()

st.markdown(
    '<div class="footer">'
    "<b>Insight Studio</b> · AI Business Analyst<br>"
    "Olist dataset · Read-only analytics · Evidence-led reporting<br>"
    "Recorded item sales exclude freight and do not represent profit. "
    "Descriptive evidence does not establish causality."
    "</div>",
    unsafe_allow_html=True,
)