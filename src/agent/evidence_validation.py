
"""Validation rules for analytical tool outputs and investigation reports."""

import re
from math import isclose, isfinite
from typing import Any

from src.agent.schemas import InvestigationReport, ToolResult


class EvidenceValidationError(ValueError):
    """Raised when analytical evidence fails validation."""


MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

COUNT_KPIS = {
    "total_orders",
    "delivered_orders",
    "canceled_orders",
    "unavailable_orders",
    "orders_with_item_records",
    "orders_with_payment_records",
}

PERCENT_KPIS = {"delivery_rate_pct"}

BRL_KPIS = {
    "item_sales_value_brl",
    "freight_value_brl",
    "recorded_payment_value_brl",
    "average_item_value_per_order_brl",
    "average_items_plus_freight_per_order_brl",
}

SUPPORTED_KPIS = COUNT_KPIS | PERCENT_KPIS | BRL_KPIS

# Must match the unit values returned by src/tools/kpi_lookup.py.
EXPECTED_UNITS = {
    **{name: "orders" for name in COUNT_KPIS},
    **{name: "percent" for name in PERCENT_KPIS},
    **{name: "BRL" for name in BRL_KPIS},
}


def _number(value: Any, field_name: str) -> float:
    """Require a finite number, excluding booleans."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EvidenceValidationError(
            f"{field_name} must be a numeric value"
        )

    number = float(value)

    if not isfinite(number):
        raise EvidenceValidationError(
            f"{field_name} must be finite"
        )

    return number


def _require_mapping(value: Any, field_name: str) -> dict:
    """Require a dictionary."""
    if not isinstance(value, dict):
        raise EvidenceValidationError(
            f"{field_name} must be a dictionary"
        )

    return value


def _require_nonnegative(value: Any, field_name: str) -> float:
    """Require a finite, nonnegative number."""
    number = _number(value, field_name)

    if number < 0:
        raise EvidenceValidationError(
            f"{field_name} must be nonnegative"
        )

    return number


def _require_month(value: Any, field_name: str = "month") -> str:
    """Require strict YYYY-MM formatting."""
    if not isinstance(value, str) or not MONTH_RE.fullmatch(value):
        raise EvidenceValidationError(
            f"{field_name} must use YYYY-MM format"
        )

    return value


def _passed(message: str, **details: Any) -> dict:
    """Return a successful validation result."""
    return {
        "passed": True,
        "message": message,
        **details,
    }


def validate_kpi_result(data: Any) -> dict:
    """Validate a KPI result's name, value, unit, and database mode."""
    data = _require_mapping(data, "KPI result")
    kpi = data.get("kpi")

    if kpi not in SUPPORTED_KPIS:
        raise EvidenceValidationError(
            f"Unsupported KPI: {kpi!r}"
        )

    value = _number(data.get("value"), f"{kpi}.value")

    if value < 0:
        raise EvidenceValidationError(
            f"{kpi}.value must be nonnegative"
        )

    if kpi in COUNT_KPIS and not value.is_integer():
        raise EvidenceValidationError(
            f"{kpi}.value must be an integer"
        )

    if kpi in PERCENT_KPIS and value > 100:
        raise EvidenceValidationError(
            f"{kpi}.value must not exceed 100"
        )

    expected_unit = EXPECTED_UNITS[kpi]

    if data.get("unit") != expected_unit:
        raise EvidenceValidationError(
            f"{kpi}.unit must be {expected_unit!r}"
        )

    if data.get("database_mode") != "read-only":
        raise EvidenceValidationError(
            "KPI result must use read-only database access"
        )

    description = data.get("description")

    if not isinstance(description, str) or not description.strip():
        raise EvidenceValidationError(
            "KPI result must include a non-empty description"
        )

    return _passed(
        "KPI result validated.",
        kpi=kpi,
        unit=expected_unit,
    )


def validate_monthly_trend_result(data: Any) -> dict:
    """Validate monthly trend values and comparison eligibility."""
    data = _require_mapping(data, "Monthly trend result")

    _require_month(data.get("month"))

    if data.get("database_mode") != "read-only":
        raise EvidenceValidationError(
            "Monthly trend must use read-only database access"
        )

    comparison_status = data.get("comparison_status")
    coverage_flag = data.get("coverage_flag")

    if not isinstance(comparison_status, str) or not comparison_status.strip():
        raise EvidenceValidationError(
            "comparison_status must be a non-empty string"
        )

    if not isinstance(coverage_flag, str) or not coverage_flag.strip():
        raise EvidenceValidationError(
            "coverage_flag must be a non-empty string"
        )

    for field in ("total_orders", "orders_with_items"):
        value = _require_nonnegative(data.get(field), field)

        if not value.is_integer():
            raise EvidenceValidationError(
                f"{field} must be an integer"
            )

    if data["orders_with_items"] > data["total_orders"]:
        raise EvidenceValidationError(
            "orders_with_items cannot exceed total_orders"
        )

    for field in (
        "item_sales_value_brl",
        "average_item_value_per_order_brl",
    ):
        _require_nonnegative(data.get(field), field)

    percentage_fields = ("orders_mom_pct", "sales_mom_pct")

    if comparison_status == "comparable":
        if coverage_flag != "eligible":
            raise EvidenceValidationError(
                "Comparable trends must have eligible coverage"
            )

        for field in percentage_fields:
            _number(data.get(field), field)
    else:
        for field in percentage_fields:
            if data.get(field) is not None:
                raise EvidenceValidationError(
                    f"{field} must be None when the trend is not comparable"
                )

    return _passed(
        "Monthly trend result validated.",
        month=data["month"],
        comparison_status=comparison_status,
    )


def validate_decomposition(decomposition: Any) -> dict:
    """Verify that the sales decomposition reconciles."""
    decomposition = _require_mapping(
        decomposition, "sales decomposition"
    )

    total_change = _number(
        decomposition.get("total_sales_change"),
        "total_sales_change",
    )
    volume_effect = _number(
        decomposition.get("order_volume_effect"),
        "order_volume_effect",
    )
    average_value_effect = _number(
        decomposition.get("average_item_value_effect"),
        "average_item_value_effect",
    )
    reported_difference = _number(
        decomposition.get("reconciliation_difference"),
        "reconciliation_difference",
    )

    calculated_difference = (
        total_change - volume_effect - average_value_effect
    )

    if not isclose(
        calculated_difference, 0.0, rel_tol=0.0, abs_tol=0.02
    ):
        raise EvidenceValidationError(
            "Sales decomposition components do not reconcile"
        )

    if not isclose(
        reported_difference,
        calculated_difference,
        rel_tol=0.0,
        abs_tol=0.02,
    ):
        raise EvidenceValidationError(
            "Reported reconciliation difference is inconsistent"
        )

    return _passed(
        "Sales decomposition reconciles.",
        calculated_difference=calculated_difference,
    )


def validate_anomaly_evidence(anomaly: Any) -> dict:
    """Validate anomaly scoring and coverage evidence."""
    anomaly = _require_mapping(anomaly, "anomaly evidence")

    is_anomaly = anomaly.get("is_anomaly")

    if not isinstance(is_anomaly, bool):
        raise EvidenceValidationError(
            "is_anomaly must be a boolean"
        )

    scoring_status = anomaly.get("scoring_status")
    coverage_flag = anomaly.get("coverage_flag")
    score = anomaly.get("robust_z_score")

    if scoring_status == "scored":
        if coverage_flag != "eligible":
            raise EvidenceValidationError(
                "Scored anomalies must have eligible coverage"
            )

        if score is None:
            raise EvidenceValidationError(
                "Scored anomalies must include a robust z-score"
            )

        _number(score, "robust_z_score")
    else:
        if is_anomaly:
            raise EvidenceValidationError(
                "An anomaly cannot be flagged without a valid score"
            )

        if score is not None:
            raise EvidenceValidationError(
                "Unscored evidence cannot contain a robust z-score"
            )

    return _passed(
        "Anomaly evidence validated.",
        scoring_status=scoring_status,
        is_anomaly=is_anomaly,
    )


def validate_category_changes(categories: Any) -> dict:
    """Validate category sales changes, directions, and reconciliation."""
    if not isinstance(categories, list):
        raise EvidenceValidationError(
            "categories must be a list"
        )

    for index, category in enumerate(categories):
        if not isinstance(category, dict):
            raise EvidenceValidationError(
                f"categories[{index}] must be a dictionary"
            )

        change = _number(
            category.get("sales_change_brl"),
            f"categories[{index}].sales_change_brl",
        )

        if change > 0:
            expected_direction = "increase"
        elif change < 0:
            expected_direction = "decrease"
        else:
            expected_direction = "unchanged"

        if category.get("direction") != expected_direction:
            raise EvidenceValidationError(
                f"categories[{index}] direction does not match its sales change"
            )

        previous = category.get("previous_sales_brl")
        current = category.get("current_sales_brl")

        if previous is not None:
            _require_nonnegative(
                previous,
                f"categories[{index}].previous_sales_brl",
            )

        if current is not None:
            _require_nonnegative(
                current,
                f"categories[{index}].current_sales_brl",
            )

        if previous is not None and current is not None:
            calculated_change = float(current) - float(previous)

            if not isclose(
                calculated_change,
                change,
                rel_tol=0.0,
                abs_tol=0.02,
            ):
                raise EvidenceValidationError(
                    f"categories[{index}] sales change does not reconcile"
                )

    return _passed(
        "Category sales changes and directions validated.",
        categories_checked=len(categories),
    )


def validate_tool_result(result: ToolResult) -> list[dict]:
    """Validate a tool result according to its tool type and payload."""
    checks: list[dict] = []

    if result.status == "error":
        if not result.error_message:
            raise EvidenceValidationError(
                "Error tool results must include an error_message"
            )

        if result.evidence:
            raise EvidenceValidationError(
                "Error tool results must not contain evidence"
            )

        return [
            _passed("Error tool result structure validated.")
        ]

    if result.error_message is not None:
        raise EvidenceValidationError(
            "Non-error tool results must not include an error_message"
        )

    if result.tool_name == "get_kpi":
        checks.append(validate_kpi_result(result.data))

    elif result.tool_name == "get_monthly_trend":
        checks.append(validate_monthly_trend_result(result.data))

    elif result.tool_name == "investigate_month":
        data = _require_mapping(
            result.data, "Investigation result"
        )

        if data.get("month") is not None:
            _require_month(data["month"])

        anomaly = _require_mapping(
            data.get("anomaly_evidence"),
            "anomaly_evidence",
        )

        investigation_status = data.get("investigation_status")
        scoring_status = anomaly.get("scoring_status")
        coverage_flag = anomaly.get("coverage_flag")
        is_anomaly = anomaly.get("is_anomaly")

        if investigation_status == "potential_anomaly":
            if not (
                scoring_status == "scored"
                and coverage_flag == "eligible"
                and is_anomaly is True
            ):
                raise EvidenceValidationError(
                    "potential_anomaly status conflicts with anomaly evidence"
                )

        elif investigation_status == "not_flagged":
            if not (
                scoring_status == "scored"
                and coverage_flag == "eligible"
                and is_anomaly is False
            ):
                raise EvidenceValidationError(
                    "not_flagged status conflicts with anomaly evidence"
                )

        elif investigation_status == "partial_insufficient_coverage_or_history":
            if (
                scoring_status == "scored"
                and coverage_flag == "eligible"
            ) or is_anomaly:
                raise EvidenceValidationError(
                    "Partial investigation status conflicts with anomaly evidence"
                )

        else:
            raise EvidenceValidationError(
                f"Unsupported investigation status: {investigation_status!r}"
            )

        checks.append(
            _passed(
                "Investigation status is consistent with anomaly evidence.",
                investigation_status=investigation_status,
            )
        )

        checks.append(
            validate_anomaly_evidence(anomaly)
        )

        decomposition = data.get("sales_decomposition")

        if decomposition is not None:
            checks.append(
                validate_decomposition(decomposition)
            )

        categories = data.get("category_changes", [])
        checks.append(
            validate_category_changes(categories)
        )

    return checks


def validate_report_against_tool_result(
    report: InvestigationReport,
    result: ToolResult,
) -> list[dict]:
    """Check that report findings faithfully match tool evidence."""
    if result.status == "error":
        if report.status != "error":
            raise EvidenceValidationError(
                "An error tool result must produce an error report"
            )

        if report.findings:
            raise EvidenceValidationError(
                "Error reports must not contain findings"
            )
    else:
        if report.status == "error":
            raise EvidenceValidationError(
                "A successful tool result must not produce an error report"
            )

        if result.tool_name not in report.tools_used:
            raise EvidenceValidationError(
                "The report must identify the tool used"
            )

    if report.causal_conclusion_established:
        raise EvidenceValidationError(
            "Causal conclusions cannot be asserted by this engine"
        )

    evidence_by_id = {
        item.evidence_id: item
        for item in result.evidence
    }

    seen_ids: set[str] = set()

    for finding in report.findings:
        if finding.evidence_id in seen_ids:
            raise EvidenceValidationError(
                f"Duplicate evidence reference: {finding.evidence_id}"
            )

        seen_ids.add(finding.evidence_id)
        source = evidence_by_id.get(finding.evidence_id)

        if source is None:
            raise EvidenceValidationError(
                f"Finding references unknown evidence: {finding.evidence_id}"
            )

        if finding.model_dump() != source.model_dump():
            raise EvidenceValidationError(
                f"Finding differs from its source evidence: {finding.evidence_id}"
            )

    return [
        _passed(
            "Report and tool evidence are consistent.",
            findings_checked=len(report.findings),
        )
    ]
