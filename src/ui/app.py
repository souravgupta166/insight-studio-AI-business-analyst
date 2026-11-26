"""Insight Studio — multi-page AI Business Analyst (calm sage theme)."""

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
    "Overview": ("⌂", "#52796F"),
    "KPI Explorer": ("▦", "#52796F"),
    "Sales & Revenue": ("◈", "#52796F"),
    "Monthly Trends": ("↗", "#52796F"),
    "Anomaly Investigation": ("◎", "#52796F"),
    "AI Assistant": ("✦", "#52796F"),
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
# STYLING — calm, consistent sage / warm-neutral palette
# =========================================================

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');

    :root {
        --ink: #263631;
        --muted: #718078;
        --line: #E1E8E2;
        --accent: #52796F;
        --accent-dark: #355D53;
        --accent-soft: #EAF1ED;
        --paper: #F6F8F5;
        --card: #FFFFFF;
        --shadow: 0 5px 18px rgba(38, 54, 49, .055);
    }

    .stApp {
        background: var(--paper);
        color: var(--ink);
    }

    html, body, .stApp,
    .stApp :is(p, li, label, input, textarea, button, summary, td, th) {
        font-family: 'DM Sans', 'Segoe UI', system-ui, sans-serif;
    }

    .stApp :is(h1, h2, h3, h4, h5, h6) {
        font-family: 'Manrope', 'DM Sans', system-ui, sans-serif;
        color: var(--ink);
        letter-spacing: -.025em;
    }

    .stApp :is(p, li, td, th) { color: var(--ink); }
    [data-testid="stHeader"] { background: transparent; }

    .block-container {
        max-width: 1420px;
        padding: 1.8rem 2.3rem 3rem 2.3rem;
    }

    hr { border-color: var(--line); }
    .muted { color: var(--muted); font-size: .9rem; }

    /* Overview hero */
    .hero {
        position: relative;
        overflow: hidden;
        background: linear-gradient(125deg, #355D53 0%, #52796F 100%);
        border: 1px solid rgba(255,255,255,.12);
        border-radius: 22px;
        padding: 2.6rem 2.8rem 2.35rem;
        box-shadow: 0 12px 30px rgba(53, 93, 83, .13);
        margin-bottom: 1.8rem;
    }
    .hero::after {
        content: "";
        position: absolute;
        right: -65px;
        top: -105px;
        width: 290px;
        height: 290px;
        border: 1px solid rgba(255,255,255,.13);
        border-radius: 50%;
        box-shadow: 0 0 0 35px rgba(255,255,255,.035),
                    0 0 0 70px rgba(255,255,255,.025);
    }
    .hero > * { position: relative; z-index: 1; }
    .hero-pill {
        display: inline-block;
        background: rgba(255,255,255,.14);
        color: #F5FAF6;
        border: 1px solid rgba(255,255,255,.24);
        font-weight: 600;
        font-size: .78rem;
        padding: .32rem .8rem;
        border-radius: 999px;
        margin-bottom: 1rem;
    }
    .hero-title {
        font-family: 'Manrope', 'DM Sans', sans-serif;
        color: #FFFFFF;
        font-size: clamp(2rem, 4vw, 3.15rem);
        font-weight: 800;
        letter-spacing: -.045em;
        line-height: 1.08;
        max-width: min(740px, 88%);
        margin-bottom: .85rem;
    }
    .hero-text {
        color: rgba(255,255,255,.88);
        font-size: 1.04rem;
        line-height: 1.65;
        max-width: min(650px, 85%);
        margin-bottom: 1.2rem;
    }
    .hero-tags span {
        display: inline-block;
        color: #F5FAF6;
        background: rgba(255,255,255,.10);
        border: 1px solid rgba(255,255,255,.20);
        border-radius: 999px;
        padding: .28rem .8rem;
        font-size: .82rem;
        font-weight: 500;
        margin: 0 .4rem .35rem 0;
    }

    /* Page headers */
    .page-head {
        display: flex;
        gap: 1rem;
        align-items: flex-start;
        background: var(--card);
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: 1.25rem 1.5rem;
        box-shadow: var(--shadow);
        margin-bottom: 1.35rem;
    }
    .page-icon {
        flex: 0 0 auto;
        width: 3.15rem;
        height: 3.15rem;
        border-radius: 14px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
        color: var(--accent-dark);
        background: var(--accent-soft);
    }
    .crumb {
        color: var(--accent-dark);
        font-weight: 700;
        font-size: .8rem;
        margin-bottom: .2rem;
    }
    .page-title {
        font-family: 'Manrope', 'DM Sans', sans-serif;
        color: var(--ink);
        font-size: clamp(1.65rem, 3vw, 2.2rem);
        font-weight: 800;
        letter-spacing: -.04em;
        line-height: 1.12;
        margin-bottom: .35rem;
    }
    .page-description {
        color: var(--muted);
        font-size: .96rem;
        line-height: 1.6;
        max-width: 880px;
    }

    /* Sections and cards */
    .section-title {
        font-family: 'Manrope', 'DM Sans', sans-serif;
        color: var(--ink);
        font-size: 1.35rem;
        font-weight: 800;
        letter-spacing: -.03em;
        margin: .8rem 0 .15rem;
    }
    .section-description {
        color: var(--muted);
        font-size: .92rem;
        margin-bottom: .9rem;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--card);
        border: 1px solid var(--line);
        border-radius: 16px;
        box-shadow: var(--shadow);
    }
    .tile {
        width: 2.85rem;
        height: 2.85rem;
        border-radius: 13px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.35rem;
        color: var(--accent-dark);
        background: var(--accent-soft) !important;
        margin-bottom: .65rem;
    }
    .card-title {
        font-family: 'Manrope', 'DM Sans', sans-serif;
        color: var(--ink);
        font-size: 1.08rem;
        font-weight: 800;
        letter-spacing: -.02em;
        margin-bottom: .15rem;
    }
    .accent-bar {
        height: 3px;
        background: var(--accent) !important;
        border-radius: 4px;
        margin: .1rem 0 .85rem;
    }
    .step-num {
        width: 2.1rem;
        height: 2.1rem;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        background: var(--accent-soft);
        color: var(--accent-dark);
        font-weight: 800;
        margin-bottom: .65rem;
    }
    .count-chip {
        display: inline-block;
        background: var(--accent-soft);
        color: var(--accent-dark);
        font-weight: 700;
        font-size: .76rem;
        padding: .18rem .6rem;
        border-radius: 999px;
        margin-bottom: .6rem;
    }

    /* Investigation result */
    .result-head {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 1rem;
        flex-wrap: wrap;
        background: var(--card);
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 1rem 1.25rem;
        box-shadow: var(--shadow);
        margin-bottom: 1rem;
    }
    .result-label { color: var(--muted); font-size: .8rem; font-weight: 600; }
    .result-question {
        font-family: 'Manrope', 'DM Sans', sans-serif;
        color: var(--ink);
        font-size: 1.15rem;
        font-weight: 800;
        letter-spacing: -.02em;
    }
    .badge {
        display: inline-block;
        font-weight: 700;
        font-size: .8rem;
        padding: .32rem .78rem;
        border-radius: 999px;
        border: 1px solid transparent;
    }
    .badge.ok { background: #EAF1ED; color: #355D53; border-color: #D2E1D8; }
    .badge.warn { background: #F5F1E6; color: #78643B; border-color: #E9DFC4; }
    .badge.bad { background: #F6ECEA; color: #8A5149; border-color: #EBD8D4; }

    /* Metrics */
    div[data-testid="stMetric"] {
        background: var(--card);
        border: 1px solid var(--line);
        border-top: 3px solid var(--accent);
        border-radius: 14px;
        padding: .95rem 1rem;
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
        color: var(--accent-dark) !important;
        font-weight: 800;
        font-size: 1.65rem;
        white-space: normal !important;
        overflow: visible !important;
        text-overflow: clip !important;
    }

    /* Buttons */
    .stButton > button,
    .stDownloadButton > button {
        border: 1px solid #D7E1DA;
        border-radius: 11px;
        min-height: 2.65rem;
        background: #FFFFFF;
        color: var(--ink);
        font-weight: 600;
        box-shadow: 0 1px 2px rgba(38,54,49,.035);
        transition: background .15s ease, border-color .15s ease,
                    transform .15s ease, box-shadow .15s ease;
    }
    .stButton > button p,
    .stDownloadButton > button p { color: inherit; }
    .stButton > button:hover,
    .stDownloadButton > button:hover {
        border-color: var(--accent);
        color: var(--accent-dark);
        background: #F2F6F2;
        transform: translateY(-1px);
        box-shadow: 0 5px 12px rgba(53,93,83,.09);
    }
    .stButton > button[kind="primary"],
    .stButton > button[data-testid="stBaseButton-primary"] {
        background: var(--accent-dark);
        border-color: var(--accent-dark);
        color: #FFFFFF;
    }
    .stButton > button[kind="primary"] p,
    .stButton > button[data-testid="stBaseButton-primary"] p { color: #FFFFFF; }
    .stButton > button[kind="primary"]:hover,
    .stButton > button[data-testid="stBaseButton-primary"]:hover {
        background: #294B42;
        border-color: #294B42;
        color: #FFFFFF;
    }
    .stButton > button[kind="primary"]:hover p,
    .stButton > button[data-testid="stBaseButton-primary"]:hover p { color: #FFFFFF; }

    /* Inputs */
    div[data-testid="stWidgetLabel"] p { color: var(--ink); font-weight: 600; }
    div[data-baseweb="textarea"],
    div[data-baseweb="base-input"],
    div[data-baseweb="input"] {
        background: #FFFFFF !important;
        border-radius: 11px !important;
    }
    div[data-testid="stTextArea"] textarea,
    div[data-testid="stTextInput"] input {
        background: #FFFFFF !important;
        color: var(--ink) !important;
        border: 1px solid #D7E1DA;
        border-radius: 11px;
        font-size: .98rem;
    }
    div[data-testid="stTextArea"] textarea::placeholder,
    div[data-testid="stTextInput"] input::placeholder {
        color: #87948C !important;
        opacity: 1;
    }
    div[data-testid="stTextArea"] textarea:focus,
    div[data-testid="stTextInput"] input:focus {
        border-color: var(--accent);
        box-shadow: 0 0 0 3px rgba(82,121,111,.12);
    }
    div[data-baseweb="select"] > div {
        background: #FFFFFF;
        border: 1px solid #D7E1DA;
        border-radius: 11px;
    }
    div[data-baseweb="select"] *,
    div[data-baseweb="popover"] li,
    div[data-baseweb="popover"] li * { color: var(--ink); }

    /* Alerts, expanders and tables */
    div[data-testid="stAlert"] {
        border-radius: 12px;
        border: 1px solid var(--line);
    }
    div[data-testid="stAlert"] * { color: var(--ink); }
    div[data-testid="stExpander"] {
        background: var(--card);
        border: 1px solid var(--line);
        border-radius: 13px;
        box-shadow: none;
    }
    div[data-testid="stExpander"] details { border: none !important; }
    div[data-testid="stExpander"] summary,
    div[data-testid="stExpander"] summary * {
        color: var(--ink);
        font-weight: 600;
    }
    div[data-testid="stDataFrame"] {
        border: 1px solid var(--line);
        border-radius: 11px;
        overflow: hidden;
        background: #FFFFFF;
    }
    div[data-testid="stTable"] { overflow-x: auto; }
    div[data-testid="stTable"] table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        background: #FFFFFF;
        border: 1px solid var(--line);
        border-radius: 11px;
        overflow: hidden;
    }
    div[data-testid="stTable"] th {
        background: #EDF2EE;
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
        border-bottom: 1px solid #EDF1ED;
        white-space: normal;
        word-break: break-word;
        vertical-align: top;
    }
    div[data-testid="stTable"] tbody tr:nth-child(even) td { background: #F8FAF8; }
    div[data-testid="stTable"] tbody tr:last-child td { border-bottom: none; }

    pre, code { color: var(--ink); }
    .footer {
        color: var(--muted);
        font-size: .8rem;
        line-height: 1.7;
    }

    /* Sidebar — quiet neutral surface */
    [data-testid="stSidebar"] {
        background: #EEF3EF;
        border-right: 1px solid #E0E8E1;
    }
    [data-testid="stSidebar"] .block-container { padding-top: 1.5rem; }
    [data-testid="stSidebar"] :is(p, span, label, li, strong) { color: var(--ink); }
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"],
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] * {
        color: var(--muted) !important;
    }
    [data-testid="stSidebar"] hr { border-color: #DCE5DE; }
    .brand {
        font-family: 'Manrope', 'DM Sans', sans-serif;
        font-size: 1.48rem;
        font-weight: 800;
        letter-spacing: -.045em;
        color: var(--ink);
    }
    [data-testid="stSidebar"] .brand-mark { color: var(--accent); }
    .brand-caption {
        color: var(--muted);
        font-size: .82rem;
        margin-top: .12rem;
    }
    .sidebar-label {
        color: #263631;
        font-size: .76rem;
        font-weight: 800;
        letter-spacing: .06em;
        text-transform: uppercase;
        margin: .9rem 0 .55rem;
    }
    .session-box {
        background: #FFFFFF;
        border: 1px solid #DCE5DE;
        border-radius: 11px;
        padding: .65rem .8rem;
        color: var(--accent-dark);
        font-size: .86rem;
        font-weight: 600;
    }
    /* Workspace navigation — soft sage cards matching the main dashboard */
    [data-testid="stSidebar"] div[role="radiogroup"] {
        display: flex;
        flex-direction: column;
        gap: .42rem;
        background: #F5F8F5;
        border: 1px solid #E1E8E2;
        border-radius: 14px;
        padding: .55rem;
        margin: .3rem 0 1rem;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label {
        display: flex !important;
        align-items: center !important;
        width: 100% !important;
        min-height: 44px;
        box-sizing: border-box;
        background: #FFFFFF;
        border: 1px solid #E1E8E2;
        border-radius: 10px;
        padding: .62rem .78rem !important;
        margin: 0 !important;
        cursor: pointer;
        transition: background .15s ease, border-color .15s ease, transform .15s ease, box-shadow .15s ease;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
        background: #F0F5F1;
        border-color: #C9D9CE;
        transform: translateX(2px);
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child {
        flex: 0 0 auto;
        margin-right: .62rem;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label > div:last-child,
    [data-testid="stSidebar"] div[role="radiogroup"] > label p,
    [data-testid="stSidebar"] div[role="radiogroup"] > label span {
        color: #355D53 !important;
        font-size: .91rem !important;
        font-weight: 650 !important;
        line-height: 1.3;
        opacity: 1 !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
        background: #EAF1ED;
        border-color: #BFD2C6;
        box-shadow: 0 1px 4px rgba(38,54,49,.07);
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) > div:last-child,
    [data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) p,
    [data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) span {
        color: #263631 !important;
        font-weight: 800 !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] input {
        accent-color: #52796F;
    }
    [data-testid="stSidebar"] .stButton > button {
        background: var(--accent-dark);
        border: 1px solid var(--accent-dark);
        color: #FFFFFF;
        font-weight: 700;
    }
    [data-testid="stSidebar"] .stButton > button * { color: #FFFFFF !important; }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: #294B42;
        border-color: #294B42;
        transform: translateY(-1px);
    }

    @media (max-width: 768px) {
        .block-container { padding: 1.1rem 1rem 2rem; }
        .hero { padding: 1.8rem 1.4rem; }
        .hero-title, .hero-text { max-width: 100%; }
        .page-head { padding: 1rem; }
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
                        color="#52796F",
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

    question_cards("KPIs & Performance", "#52796F", "Run KPI →", primary=True)

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

    question_cards("Sales & Revenue", "#52796F", "Investigate metric →")

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
        accent_bar("#52796F")
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
        accent_bar("#52796F")
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