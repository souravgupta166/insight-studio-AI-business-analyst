
"""
Deterministic orchestration layer for the AI Business Analyst.

Execution flow:
1. Validate the user's question.
2. Route it to an approved analytical tool.
3. Execute the tool and validate its result.
4. Convert validated results into evidence items.
5. Build and validate the investigation report.
6. Return an explicit error report if validation fails.

No dynamically generated SQL or LLM execution is used here.
"""

import re
from typing import Any

from src.agent.schemas import (
    BusinessQuestion,
    EvidenceItem,
    InvestigationReport,
    ToolResult,
)
from src.agent.evidence_validation import (
    EvidenceValidationError,
    validate_tool_result,
    validate_report_against_tool_result,
)
from src.tools.kpi_lookup import get_kpi
from src.tools.trend_analysis_tool import get_monthly_trend
from src.tools.anomaly_investigation_tool import investigate_month


MONTH_PATTERN = re.compile(r"(?<!\d)(\d{4})-(\d{2})(?!\d)")

KPI_KEYWORDS = {
    "total_orders": (
        "total orders",
        "number of orders",
        "order count",
        "how many orders",
    ),
    "delivered_orders": (
        "delivered orders",
        "number delivered",
        "orders delivered",
    ),
    "canceled_orders": (
        "canceled orders",
        "cancelled orders",
        "orders canceled",
        "orders cancelled",
    ),
    "unavailable_orders": (
        "unavailable orders",
        "orders unavailable",
    ),
    "delivery_rate_pct": (
        "delivery rate",
        "delivery percentage",
        "percentage delivered",
    ),
    "orders_with_item_records": (
        "orders with item records",
        "orders with items",
    ),
    "orders_with_payment_records": (
        "orders with payment records",
        "orders with payments",
    ),
    "item_sales_value_brl": (
        "item sales",
        "item sales value",
        "sales value",
        "sales revenue",
    ),
    "freight_value_brl": (
        "freight value",
        "total freight",
        "freight charges",
    ),
    "recorded_payment_value_brl": (
        "recorded payment value",
        "total payments",
        "payment value",
        "payments received",
    ),
}

ANOMALY_TERMS = (
    "anomaly",
    "anomalies",
    "unusual",
    "investigate",
    "investigation",
    "why did",
    "what drove",
    "what caused",
    "explain the increase",
    "explain the decrease",
    "sales spike",
    "sales drop",
)

TREND_TERMS = (
    "trend",
    "month over month",
    "monthly change",
    "monthly sales",
    "growth",
    "decline",
)


class UnsupportedQuestionError(ValueError):
    """Raised when a question cannot be routed safely."""


def normalize_question(question: str) -> str:
    """Validate and normalize a user's question."""
    request = BusinessQuestion(question=question)
    return request.question.lower()


def extract_month(question: str) -> str | None:
    """Extract one valid calendar month in YYYY-MM format."""
    matches = list(MONTH_PATTERN.finditer(question))

    if not matches:
        return None

    months = list(dict.fromkeys(match.group(0) for match in matches))

    if len(months) > 1:
        raise UnsupportedQuestionError(
            "This version supports one month per request. "
            "Multi-month comparisons are not yet implemented."
        )

    month = months[0]
    month_number = int(month.split("-")[1])

    if not 1 <= month_number <= 12:
        raise ValueError(
            f"Invalid month '{month}'. Use YYYY-MM format."
        )

    return month


def classify_question(question: str) -> dict[str, Any]:
    """Map a supported business question to an approved analytical tool."""
    normalized = normalize_question(question)
    month = extract_month(normalized)

    if any(term in normalized for term in ANOMALY_TERMS):
        if month is None:
            raise UnsupportedQuestionError(
                "Include a month in YYYY-MM format for an investigation, "
                "for example 2017-11."
            )

        return {
            "intent": "anomaly_investigation",
            "month": month,
            "tool": "investigate_month",
        }

    if any(term in normalized for term in TREND_TERMS):
        if month is None:
            raise UnsupportedQuestionError(
                "Include a month in YYYY-MM format for a trend query, "
                "for example 2017-11."
            )

        return {
            "intent": "monthly_trend",
            "month": month,
            "tool": "get_monthly_trend",
        }

    matches = [
        name
        for name, aliases in KPI_KEYWORDS.items()
        if any(alias in normalized for alias in aliases)
    ]

    if len(matches) == 1:
        return {
            "intent": "kpi_lookup",
            "kpi_name": matches[0],
            "tool": "get_kpi",
        }

    if len(matches) > 1:
        raise UnsupportedQuestionError(
            "The question matches multiple KPIs: "
            + ", ".join(matches)
            + ". Please ask for one KPI at a time."
        )

    raise UnsupportedQuestionError(
        "This question is not supported yet. Ask for a registered KPI, "
        "a monthly trend, or a monthly anomaly investigation."
    )


def execute_tool(route: dict[str, Any]) -> ToolResult:
    """Execute one approved tool and standardize its result."""
    intent = route["intent"]

    try:
        if intent == "kpi_lookup":
            raw_result = get_kpi(route["kpi_name"])
            tool_name = "get_kpi"

        elif intent == "monthly_trend":
            raw_result = get_monthly_trend(route["month"])
            tool_name = "get_monthly_trend"

        elif intent == "anomaly_investigation":
            raw_result = investigate_month(route["month"])
            tool_name = "investigate_month"

        else:
            raise UnsupportedQuestionError(
                f"Unsupported intent: {intent}"
            )

        if not isinstance(raw_result, dict):
            raise TypeError(
                f"{tool_name} must return a dictionary."
            )

        result_status = (
            "partial"
            if raw_result.get("investigation_status")
            == "partial_insufficient_coverage_or_history"
            else "success"
        )

        return ToolResult(
            tool_name=tool_name,
            status=result_status,
            data=raw_result,
            limitations=raw_result.get("limitations", []),
            database_access="read-only",
        )

    except Exception as exc:
        return ToolResult(
            tool_name=route.get("tool", "unknown"),
            status="error",
            error_message=(
                f"Tool execution failed ({type(exc).__name__})."
            ),
            limitations=[
                "The requested tool did not complete successfully.",
                "No business finding has been inferred from the failure.",
            ],
            database_access="read-only",
        )


def build_evidence(tool_result: ToolResult) -> list[EvidenceItem]:
    """Convert recognized tool outputs into typed evidence."""
    data = tool_result.data
    tool_name = tool_result.tool_name
    evidence: list[EvidenceItem] = []

    def add(
        evidence_id,
        evidence_type,
        claim,
        metric_name=None,
        value=None,
        unit=None,
        period=None,
    ):
        evidence.append(
            EvidenceItem(
                evidence_id=evidence_id,
                evidence_type=evidence_type,
                claim=claim,
                source_tool=tool_name,
                metric_name=metric_name,
                value=value,
                unit=unit,
                period=period,
                supports_causal_claim=False,
            )
        )

    if tool_name == "get_kpi":
        metric = data.get("kpi")
        value = data.get("value")
        unit = data.get("unit", "")

        if metric is not None and value is not None:
            add(
                f"kpi-{metric}",
                "observed_metric",
                f"{metric}: {value} {unit}".strip(),
                metric_name=str(metric),
                value=value,
                unit=unit,
            )

    elif tool_name == "get_monthly_trend":
        period = data.get("month")

        definitions = [
            (
                "item_sales_value_brl",
                "observed_metric",
                "BRL",
                "Recorded item sales",
            ),
            (
                "total_orders",
                "observed_metric",
                "orders",
                "Total orders",
            ),
            (
                "orders_with_items",
                "observed_metric",
                "orders",
                "Orders with item records",
            ),
            (
                "sales_mom_pct",
                "trend",
                "%",
                "Month-over-month item sales change",
            ),
            (
                "orders_mom_pct",
                "trend",
                "%",
                "Month-over-month order change",
            ),
        ]

        for metric, evidence_type, unit, label in definitions:
            value = data.get(metric)

            if value is not None:
                add(
                    f"{metric}-{period}",
                    evidence_type,
                    f"{label} for {period}: {value} {unit}",
                    metric_name=metric,
                    value=value,
                    unit=unit,
                    period=period,
                )

    elif tool_name == "investigate_month":
        period = data.get("month")
        anomaly = data.get("anomaly_evidence", {})
        trend = data.get("trend_evidence", {})
        decomposition = data.get("sales_decomposition") or {}

        score = anomaly.get("robust_z_score")

        if score is not None:
            add(
                f"anomaly-score-{period}",
                "anomaly",
                f"Robust anomaly score for {period}: {score}; "
                f"flagged={anomaly.get('is_anomaly')}.",
                metric_name="robust_z_score",
                value=score,
                unit="robust z-score",
                period=period,
            )

        for metric, label in [
            ("sales_mom_pct", "Month-over-month item sales change"),
            ("orders_mom_pct", "Month-over-month order change"),
        ]:
            value = trend.get(metric)

            if value is not None:
                add(
                    f"{metric}-{period}",
                    "trend",
                    f"{label} for {period}: {value}%.",
                    metric_name=metric,
                    value=value,
                    unit="%",
                    period=period,
                )

        for metric, label in [
            ("total_sales_change", "Total item sales change"),
            ("order_volume_effect", "Order-volume contribution"),
            (
                "average_item_value_effect",
                "Average-item-value contribution",
            ),
        ]:
            value = decomposition.get(metric)

            if value is not None:
                add(
                    f"{metric}-{period}",
                    "decomposition",
                    f"{label} for {period}: R${value}.",
                    metric_name=metric,
                    value=value,
                    unit="BRL",
                    period=period,
                )

        for index, category in enumerate(
            data.get("category_changes", [])
        ):
            add(
                f"category-change-{period}-{index}",
                "category_comparison",
                f"Category {category['category']} had a "
                f"{category['direction']} of "
                f"R${category['sales_change_brl']} from "
                f"{category['previous_sales_brl']} to "
                f"{category['current_sales_brl']}.",
                metric_name="category_sales_change",
                value=category["sales_change_brl"],
                unit="BRL",
                period=period,
            )

    return evidence


def build_summary(intent: str, data: dict[str, Any]) -> str:
    """Build a conservative summary from analytical tool output."""
    if intent == "kpi_lookup":
        return (
            f"{data.get('kpi', 'Requested KPI')} returned "
            f"{data.get('value')} {data.get('unit', '')}."
        )

    if intent == "monthly_trend":
        month = data.get("month", "the requested month")
        sales_change = data.get("sales_mom_pct")

        if sales_change is None:
            return (
                f"Trend data retrieved for {month}; "
                "the comparison is unavailable."
            )

        return (
            f"Item sales for {month} changed by {sales_change}% "
            "compared with the previous eligible month."
        )

    month = data.get("month", "the requested month")
    status = data.get("investigation_status", "unknown")

    if status == "potential_anomaly":
        score = data.get("anomaly_evidence", {}).get("robust_z_score")
        return (
            f"{month} was flagged as a potential anomaly "
            f"(robust z-score: {score}). This is a screening signal, "
            "not a proven explanation."
        )

    if status == "partial_insufficient_coverage_or_history":
        return (
            f"The investigation for {month} is partial because "
            "coverage or scoring history is insufficient."
        )

    return (
        f"The investigation for {month} completed; "
        "the detector did not flag an anomaly."
    )


def build_report_limitations(
    intent: str,
    data: dict[str, Any],
    existing_limitations: list[str] | None = None,
) -> list[str]:
    """Build report limitations from actual analytical evidence."""
    limitations = list(existing_limitations or [])

    def add_once(message: str) -> None:
        if message not in limitations:
            limitations.append(message)

    if intent == "monthly_trend":
        if data.get("comparison_status") != "comparable":
            add_once(
                "Month-over-month percentages are unavailable because "
                "the comparison is not eligible."
            )

        if data.get("coverage_flag") != "eligible":
            add_once(
                "The requested month does not meet the configured "
                "coverage criteria for a reliable comparison."
            )

        add_once(
            "Item sales use recorded order-item prices and exclude freight; "
            "they are not a measure of profit."
        )

    elif intent == "anomaly_investigation":
        add_once(
            "The findings are descriptive and do not establish causation."
        )
        add_once(
            "Item sales use recorded order-item prices and exclude freight."
        )
        add_once("Item sales are not profit.")
        add_once(
            "Category changes do not establish why demand changed."
        )

    return limitations


def _error_report(
    question: str,
    intent: str,
    tool_name: str,
    message: str,
    limitations: list[str],
) -> InvestigationReport:
    """Construct a failure report with no analytical findings."""
    return InvestigationReport(
        question=question,
        intent=intent,
        status="error",
        summary="The requested analysis could not be completed safely.",
        findings=[],
        recommendations=[
            "Inspect the application logs, resolve the reported issue, "
            "and retry the request."
        ],
        limitations=limitations + [message],
        tools_used=[tool_name],
        causal_conclusion_established=False,
    )


def execute_question(question: str) -> InvestigationReport:
    """Execute a question and validate its evidence before returning it."""
    request = BusinessQuestion(question=question)

    # Route validation happens before any analytical tool is executed.
    route = classify_question(request.question)
    result = execute_tool(route)

    if result.status == "error":
        report = _error_report(
            request.question,
            route["intent"],
            result.tool_name,
            result.error_message or "Tool execution failed.",
            result.limitations,
        )

        validate_report_against_tool_result(report, result)
        return report

    try:
        # Validate source-tool consistency before building a report.
        validate_tool_result(result)

        findings = build_evidence(result)

        result_with_evidence = ToolResult(
            tool_name=result.tool_name,
            status=result.status,
            data=result.data,
            evidence=findings,
            limitations=result.limitations,
            error_message=result.error_message,
            database_access=result.database_access,
        )

        recommendations = []

        if route["intent"] == "anomaly_investigation":
            recommendations.append(
                "Review the supporting trend, decomposition, and "
                "category evidence. Assess seasonality and order-level "
                "records before proposing a causal explanation."
            )

        elif route["intent"] == "monthly_trend":
            recommendations.append(
                "Review data coverage and the comparison period "
                "before interpreting the trend."
            )

        report = InvestigationReport(
            question=request.question,
            intent=route["intent"],
            status=result.status,
            summary=build_summary(route["intent"], result.data),
            findings=findings,
            recommendations=recommendations,
            limitations=build_report_limitations(
                route["intent"],
                result.data,
                result.limitations,
            ),
            tools_used=[result.tool_name],
            database_access="read-only",
            causal_conclusion_established=False,
        )

        validate_report_against_tool_result(
            report,
            result_with_evidence,
        )

        return report

    except Exception as exc:
        message = (
            "Evidence validation failed "
            f"({type(exc).__name__}). No findings were returned."
        )

        return _error_report(
            request.question,
            route["intent"],
            result.tool_name,
            message,
            result.limitations,
        )


def main():
    examples = [
        "How many total orders do we have?",
        "What is the delivery rate?",
        "Show the monthly sales trend for 2017-11.",
        "Investigate the sales anomaly in 2017-11.",
    ]

    for question in examples:
        print("\n" + "=" * 80)
        print(f"QUESTION: {question}")

        try:
            report = execute_question(question)
            print(report.model_dump_json(indent=2))
        except (ValueError, TypeError) as exc:
            print(f"REQUEST REJECTED: {exc}")


if __name__ == "__main__":
    main()
