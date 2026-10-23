
"""Insight Studio — multi-page AI Business Analyst."""

import sys
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
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================================================
# CONFIGURATION
# =========================================================

QUESTION_LIBRARY = {
    "KPIs & Performance": {
        "icon": "◫",
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
        "icon": "◇",
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
        "icon": "↗",
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
        "icon": "⌁",
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

QUICK_QUESTIONS = [
    ("Total orders", "How many total orders do we have?"),
    ("Delivery rate", "What is the delivery rate?"),
    ("Recorded item sales", "What is the total item sales value?"),
    ("November sales trend", "Show the monthly sales trend for 2017-11."),
    ("Investigate anomaly", "Investigate the sales anomaly in 2017-11."),
]

# =========================================================
# SESSION STATE
# =========================================================

DEFAULTS = {
    "page": "Overview",
    "business_question": "",
    "last_question": "",
    "last_report": None,
    "run_selected_question": False,
    "question_search": "",
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


def choose_question(question: str, page: str = "AI Assistant"):
    """Route a suggested question to the assistant for execution."""
    st.session_state.business_question = question
    st.session_state.page = page
    st.session_state.run_selected_question = True


def clear_workspace():
    st.session_state.business_question = ""
    st.session_state.last_question = ""
    st.session_state.last_report = None
    st.session_state.run_selected_question = False


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
# STYLING
# =========================================================

st.markdown(
    """
    <style>
    :root {
        --bg: #080d19;
        --panel: #101829;
        --panel2: #141f33;
        --border: #27354b;
        --text: #e8eef8;
        --muted: #91a0b7;
        --accent: #8b7cff;
        --green: #35d6a0;
    }

    .stApp {
        background: #0b1020;
        color: var(--text);
    }

    [data-testid="stHeader"] {
        background: rgba(11,16,32,.96);
    }

    .block-container {
        max-width: 1600px;
        padding: 1.7rem 2rem 3rem 2rem;
    }

    [data-testid="stSidebar"] {
        background: #090e1b;
        border-right: 1px solid #202b40;
    }

    [data-testid="stSidebar"] .block-container {
        padding-top: 1.5rem;
    }

    .brand {
        font-size: 1.35rem;
        font-weight: 800;
        letter-spacing: -.045em;
        color: #f3f6fc;
    }

    .brand-mark {
        color: #a69aff;
    }

    .brand-caption {
        color: #7e8ca4;
        font-size: .78rem;
        margin-top: .2rem;
    }

    .sidebar-label {
        color: #687891;
        font-size: .68rem;
        font-weight: 800;
        letter-spacing: .15em;
        margin-top: .9rem;
        margin-bottom: .45rem;
    }

    .eyebrow {
        color: #a99bff;
        text-transform: uppercase;
        letter-spacing: .15em;
        font-size: .72rem;
        font-weight: 800;
        margin-bottom: .65rem;
    }

    .page-title {
        color: #f4f7ff;
        font-size: clamp(1.8rem, 3vw, 2.6rem);
        font-weight: 800;
        letter-spacing: -.055em;
        line-height: 1.15;
        margin-bottom: .5rem;
    }

    .page-description {
        color: #94a3ba;
        font-size: .97rem;
        line-height: 1.65;
        max-width: 850px;
        margin-bottom: 1.4rem;
    }

    .section-title {
        color: #eef3fc;
        font-size: 1.15rem;
        font-weight: 750;
        letter-spacing: -.025em;
        margin: .65rem 0 .25rem 0;
    }

    .section-description {
        color: #91a0b7;
        font-size: .85rem;
        margin-bottom: .85rem;
    }

    .status-pill {
        display: inline-block;
        color: #61e6b8;
        background: #102c2b;
        border: 1px solid #22574e;
        border-radius: 30px;
        padding: .3rem .65rem;
        font-size: .72rem;
        font-weight: 700;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: #101829;
        border: 1px solid #27354b;
        border-radius: 14px;
    }

    div[data-testid="stMetric"] {
        background: #101829;
        border: 1px solid #27354b;
        border-radius: 13px;
        padding: 1rem;
    }

    div[data-testid="stMetricLabel"] {
        color: #9aa8bd;
    }

    div[data-testid="stMetricValue"] {
        color: #b1a5ff;
        font-weight: 750;
    }

    div.stButton > button {
        border: 1px solid #2b3a51;
        border-radius: 9px;
        min-height: 2.55rem;
        background: #141f33;
        color: #e6edf8;
        font-weight: 600;
        transition: all .15s ease;
    }

    div.stButton > button:hover {
        border-color: #8b7cff;
        color: #ffffff;
    }

    div.stButton > button[kind="primary"] {
        background: #7566ef;
        border-color: #7566ef;
        color: #ffffff;
    }

    div[data-testid="stTextArea"] textarea,
    div[data-testid="stTextInput"] input {
        background: #101829;
        border-color: #2b3a51;
        border-radius: 10px;
        color: #edf2fc;
    }

    div[data-testid="stSelectbox"] > div > div {
        background: #101829;
        border-color: #2b3a51;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid #27354b;
        border-radius: 10px;
        overflow: hidden;
    }

    div[data-testid="stExpander"] {
        background: #101829;
        border: 1px solid #27354b;
        border-radius: 11px;
    }

    hr {
        border-color: #263248;
    }

    .muted {
        color: #91a0b7;
        font-size: .82rem;
    }

    .assistant-bubble {
        background: #141f33;
        border: 1px solid #2a3950;
        border-radius: 12px;
        padding: .9rem 1rem;
        color: #dce5f4;
        line-height: 1.65;
    }

    .footer {
        color: #71819a;
        font-size: .77rem;
        line-height: 1.7;
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
        """
        <div class="brand"><span class="brand-mark">◈</span> Insight Studio</div>
        <div class="brand-caption">AI Business Analyst</div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()
    st.markdown('<div class="sidebar-label">WORKSPACE</div>',
                unsafe_allow_html=True)

    st.radio(
        "Workspace navigation",
        PAGES,
        key="page",
        label_visibility="collapsed",
    )

    st.divider()
    st.markdown('<div class="sidebar-label">DATA SOURCE</div>',
                unsafe_allow_html=True)
    st.markdown("**Olist e-commerce**")
    st.caption("DuckDB · Read-only")
    st.caption("Structured analytical workflows")

    st.divider()
    st.markdown('<div class="sidebar-label">INTERPRETATION</div>',
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
# REUSABLE REPORT COMPONENTS
# =========================================================

def render_report(report):
    """Render the project's existing InvestigationReport."""
    if report.status == "success":
        st.success("Analysis completed successfully.")
    elif report.status == "partial":
        st.warning("Analysis completed with limitations.")
    else:
        st.error(f"Analysis status: {report.status}")

    st.markdown("#### Executive summary")
    st.write(report.summary)

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
        evidence = [
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
        st.dataframe(
            pd.DataFrame(evidence),
            use_container_width=True,
            hide_index=True,
        )
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
                    "Value (BRL)": value,
                }
                for key, value in decomposition.items()
                if isinstance(value, (int, float))
                and not isinstance(value, bool)
            ]

            if rows:
                st.dataframe(
                    pd.DataFrame(rows),
                    use_container_width=True,
                    hide_index=True,
                )

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
                        frame.set_index("category")["sales_change_brl"]
                    )

            st.dataframe(frame, use_container_width=True, hide_index=True)

    if report.recommendations:
        st.markdown("#### Recommended next steps")
        for recommendation in report.recommendations:
            st.markdown(f"- {recommendation}")

    if report.limitations:
        st.markdown("#### Limitations")
        for limitation in report.limitations:
            st.markdown(f"- {limitation}")

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
    """Display reusable question shortcuts."""
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


def page_header(eyebrow, title, description):
    st.markdown(
        f"""
        <div class="eyebrow">{eyebrow}</div>
        <div class="page-title">{title}</div>
        <div class="page-description">{description}</div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# OVERVIEW PAGE
# =========================================================

if page == "Overview":
    page_header(
        "WORKSPACE / OVERVIEW",
        "Business intelligence, grounded in evidence.",
        "A central workspace for exploring the Olist dataset, reviewing "
        "business KPIs and investigating monthly performance.",
    )

    left, right = st.columns([3, 1])

    with left:
        st.markdown("### Start an investigation")
        st.markdown(
            '<div class="muted">Choose a workflow to get started.</div>',
            unsafe_allow_html=True,
        )

    with right:
        st.markdown(
            '<div class="status-pill">●  READ-ONLY DATA</div>',
            unsafe_allow_html=True,
        )

    st.markdown("")

    overview_cards = [
        ("◫", "KPI Explorer", "Orders and delivery performance",
         "Open KPI Explorer"),
        ("◇", "Sales & Revenue", "Recorded sales and payment metrics",
         "Open Sales & Revenue"),
        ("↗", "Monthly Trends", "Explore monthly sales movements",
         "Open Monthly Trends"),
        ("⌁", "Anomaly Investigation", "Inspect potentially unusual activity",
         "Open Anomaly Investigation"),
    ]

    columns = st.columns(4)

    for column, card in zip(columns, overview_cards):
        icon, title, description, button_label = card

        with column:
            with st.container(border=True):
                st.markdown(f"### {icon}")
                st.markdown(f"**{title}**")
                st.caption(description)

                if st.button(
                    button_label,
                    key=f"overview_{title}",
                    use_container_width=True,
                ):
                    st.session_state.page = title
                    st.rerun()

    st.divider()

    st.markdown("### Ask the analyst")
    st.markdown(
        '<div class="muted">Start with one of these common questions.</div>',
        unsafe_allow_html=True,
    )

    render_question_buttons(QUICK_QUESTIONS, "overview_question")

    st.divider()
    st.markdown("### Recent investigation")

    if st.session_state.last_report is not None:
        st.markdown(f"**{st.session_state.last_question}**")
        st.caption("Most recent completed report")

        if st.button("Open last result", type="primary"):
            st.session_state.page = "AI Assistant"
            st.rerun()
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
        "ANALYTICS / KPI EXPLORER",
        "KPI Explorer",
        "Inspect the available order and delivery metrics. Select a question "
        "to run the corresponding supported backend workflow.",
    )

    kpi_questions = QUESTION_LIBRARY["KPIs & Performance"]["questions"]

    for start in range(0, len(kpi_questions), 2):
        pair = kpi_questions[start:start + 2]
        columns = st.columns(len(pair))

        for column, (title, question, description) in zip(columns, pair):
            with column:
                with st.container(border=True):
                    st.markdown("#### " + title)
                    st.caption(description)
                    st.markdown(
                        '<div class="muted">Source: Olist analytical workflow</div>',
                        unsafe_allow_html=True,
                    )
                    st.button(
                        "Run KPI →",
                        key=f"kpi_{title}",
                        on_click=choose_question,
                        args=(question, "AI Assistant"),
                        type="primary",
                        use_container_width=True,
                    )

    st.divider()
    st.markdown("### Last available result")

    report = st.session_state.last_report
    if report is not None:
        st.caption(st.session_state.last_question)
        render_report(report)
    else:
        st.info("Run a KPI above to populate this area with real findings.")

# =========================================================
# SALES & REVENUE PAGE
# =========================================================

elif page == "Sales & Revenue":
    page_header(
        "ANALYTICS / FINANCIAL METRICS",
        "Sales & Revenue",
        "Explore recorded item prices, freight charges and payment values. "
        "These are distinct measures and should not be treated as profit.",
    )

    sales_questions = QUESTION_LIBRARY["Sales & Revenue"]["questions"]

    for start in range(0, len(sales_questions), 2):
        pair = sales_questions[start:start + 2]
        columns = st.columns(len(pair))

        for column, (title, question, description) in zip(columns, pair):
            with column:
                with st.container(border=True):
                    st.markdown("#### " + title)
                    st.caption(description)
                    st.button(
                        "Investigate metric →",
                        key=f"sales_{title}",
                        on_click=choose_question,
                        args=(question, "AI Assistant"),
                        use_container_width=True,
                    )

    st.divider()
    st.markdown("### Metric definitions")

    with st.container(border=True):
        st.markdown("**Recorded item sales**")
        st.write(
            "Sum of item prices recorded in order-item records. "
            "This measure excludes freight and does not establish profit."
        )

    with st.container(border=True):
        st.markdown("**Freight value**")
        st.write(
            "Freight charges recorded in order-item records. "
            "This is separate from item sales."
        )

    with st.container(border=True):
        st.markdown("**Recorded payment value**")
        st.write(
            "Payment amounts recorded in payment records. "
            "Interpretation depends on the backend metric definition."
        )

    if st.session_state.last_report is not None:
        st.divider()
        st.markdown("### Most recent result")
        st.caption(st.session_state.last_question)
        render_report(st.session_state.last_report)

# =========================================================
# MONTHLY TRENDS PAGE
# =========================================================

elif page == "Monthly Trends":
    page_header(
        "ANALYTICS / TIME SERIES",
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
        st.markdown("#### Monthly trend investigation")
        st.markdown(f"**Period:** {selected_month}")
        st.caption(chosen[2])

        st.button(
            "Run monthly analysis →",
            key="run_monthly_trend",
            type="primary",
            on_click=choose_question,
            args=(chosen[1], "AI Assistant"),
            use_container_width=True,
        )

    st.divider()

    if (
        st.session_state.last_report is not None
        and "trend" in st.session_state.last_question.casefold()
    ):
        st.markdown("### Latest trend results")
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
        "INVESTIGATIONS / ANOMALY SCREENING",
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
        st.markdown("#### Investigation setup")
        st.markdown(f"**Selected period:** {chosen_month}")
        st.caption(chosen[2])

        st.button(
            "Run anomaly investigation →",
            key="run_anomaly",
            type="primary",
            on_click=choose_question,
            args=(chosen[1], "AI Assistant"),
            use_container_width=True,
        )

    st.divider()

    if (
        st.session_state.last_report is not None
        and (
            "anomaly" in st.session_state.last_question.casefold()
            or "investigate" in st.session_state.last_question.casefold()
        )
    ):
        st.markdown("### Latest investigation")
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
        "ASSISTANT / QUESTION WORKSPACE",
        "Ask the business analyst.",
        "Enter a question or select a supported example. The backend "
        "validates and executes the relevant analytical workflow.",
    )

    st.markdown("### Question composer")

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

    st.markdown("### Suggested questions")
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

    # Handle normal form submission and suggested-question callbacks.
    should_run = submitted or st.session_state.run_selected_question

    if should_run:
        st.session_state.run_selected_question = False
        question = st.session_state.business_question.strip()

        if not question:
            st.warning("Enter a question or choose a suggested question.")
        else:
            st.session_state.last_question = question
            st.session_state.last_report = None

            with st.spinner("Investigating the available evidence..."):
                try:
                    report = execute_question(question)

                except UnsupportedQuestionError as exc:
                    st.error("This question is not supported yet.")
                    st.write(str(exc))
                    st.info(
                        "Try one of the supplied questions. The backend "
                        "supports only the analytical workflows implemented "
                        "in the current project."
                    )

                except (ValueError, TypeError) as exc:
                    st.error("The question could not be processed.")
                    st.exception(exc)

                except Exception as exc:
                    st.error("The investigation failed.")
                    st.exception(exc)

                else:
                    st.session_state.last_report = report

    if st.session_state.last_report is not None:
        st.divider()
        st.markdown("### Investigation results")
        st.caption(f"Question: {st.session_state.last_question}")
        render_report(st.session_state.last_report)

        st.markdown("### Continue exploring")

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
    """
    <div class="footer">
        <b>Insight Studio</b> · AI Business Analyst<br>
        Olist dataset · Read-only analytics · Evidence-led reporting<br>
        Recorded item sales exclude freight and do not represent profit.
        Descriptive evidence does not establish causality.
    </div>
    """,
    unsafe_allow_html=True,
)
