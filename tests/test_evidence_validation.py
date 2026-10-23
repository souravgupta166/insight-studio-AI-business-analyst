
import pytest

from src.agent.schemas import EvidenceItem, InvestigationReport, ToolResult
from src.agent.evidence_validation import (
    EvidenceValidationError,
    validate_anomaly_evidence,
    validate_category_changes,
    validate_decomposition,
    validate_tool_result,
    validate_report_against_tool_result,
)


def test_valid_sales_decomposition_passes():
    result = validate_decomposition({
        "total_sales_change": 100.0,
        "order_volume_effect": 120.0,
        "average_item_value_effect": -20.0,
        "reconciliation_difference": 0.0,
    })

    assert result["passed"] is True


def test_invalid_sales_decomposition_fails():
    with pytest.raises(EvidenceValidationError):
        validate_decomposition({
            "total_sales_change": 100.0,
            "order_volume_effect": 120.0,
            "average_item_value_effect": -10.0,
            "reconciliation_difference": 0.0,
        })


def test_valid_scored_anomaly_passes():
    result = validate_anomaly_evidence({
        "scoring_status": "scored",
        "coverage_flag": "eligible",
        "is_anomaly": True,
        "robust_z_score": 5.02,
    })

    assert result["passed"] is True


def test_unscored_month_cannot_be_an_anomaly():
    with pytest.raises(EvidenceValidationError):
        validate_anomaly_evidence({
            "scoring_status": "coverage_excluded",
            "coverage_flag": "low_order_count",
            "is_anomaly": True,
            "robust_z_score": None,
        })


def test_scored_month_requires_a_score():
    with pytest.raises(EvidenceValidationError):
        validate_anomaly_evidence({
            "scoring_status": "scored",
            "coverage_flag": "eligible",
            "is_anomaly": False,
            "robust_z_score": None,
        })


def test_category_directions_are_checked():
    result = validate_category_changes([
        {"category": "A", "sales_change_brl": 10.0, "direction": "increase"},
        {"category": "B", "sales_change_brl": -5.0, "direction": "decrease"},
    ])

    assert result["categories_checked"] == 2


def test_incorrect_category_direction_fails():
    with pytest.raises(EvidenceValidationError):
        validate_category_changes([
            {
                "category": "A",
                "sales_change_brl": -10.0,
                "direction": "increase",
            }
        ])


def test_investigation_tool_result_is_checked():
    result = ToolResult(
        tool_name="investigate_month",
        status="success",
        data={
            "investigation_status": "potential_anomaly",
            "anomaly_evidence": {
                "scoring_status": "scored",
                "coverage_flag": "eligible",
                "is_anomaly": True,
                "robust_z_score": 5.02,
            },
            "sales_decomposition": {
                "total_sales_change": 100.0,
                "order_volume_effect": 120.0,
                "average_item_value_effect": -20.0,
                "reconciliation_difference": 0.0,
            },
            "category_changes": [],
        },
    )

    checks = validate_tool_result(result)

    assert len(checks) == 4
    assert all(check["passed"] for check in checks)


def test_report_evidence_must_match_tool_evidence():
    evidence = EvidenceItem(
        evidence_id="kpi-total_orders",
        evidence_type="observed_metric",
        claim="total_orders: 99441 orders",
        source_tool="get_kpi",
        metric_name="total_orders",
        value=99441,
        unit="orders",
    )

    result = ToolResult(
        tool_name="get_kpi",
        status="success",
        data={"kpi": "total_orders", "value": 99441, "unit": "orders"},
        evidence=[evidence],
    )

    report = InvestigationReport(
        question="How many total orders?",
        intent="kpi_lookup",
        status="success",
        summary="There were 99,441 orders.",
        findings=[evidence],
        tools_used=["get_kpi"],
    )

    checks = validate_report_against_tool_result(report, result)

    assert checks[0]["passed"] is True


def test_report_cannot_add_unsupported_evidence():
    source_evidence = EvidenceItem(
        evidence_id="kpi-total_orders",
        evidence_type="observed_metric",
        claim="total_orders: 99441 orders",
        source_tool="get_kpi",
        metric_name="total_orders",
        value=99441,
        unit="orders",
    )

    invented_evidence = EvidenceItem(
        evidence_id="invented-profit",
        evidence_type="observed_metric",
        claim="Profit increased.",
        source_tool="get_kpi",
        metric_name="profit",
        value=100,
        unit="BRL",
    )

    result = ToolResult(
        tool_name="get_kpi",
        status="success",
        data={"kpi": "total_orders", "value": 99441},
        evidence=[source_evidence],
    )

    report = InvestigationReport(
        question="How many total orders?",
        intent="kpi_lookup",
        status="success",
        summary="Orders increased profit.",
        findings=[source_evidence, invented_evidence],
        tools_used=["get_kpi"],
    )

    with pytest.raises(EvidenceValidationError):
        validate_report_against_tool_result(report, result)


def test_report_cannot_claim_causation():
    result = ToolResult(
        tool_name="get_kpi",
        status="success",
        data={},
    )

    report = InvestigationReport(
        question="How many total orders?",
        intent="kpi_lookup",
        status="success",
        summary="A result.",
        tools_used=["get_kpi"],
        causal_conclusion_established=True,
    )

    with pytest.raises(EvidenceValidationError):
        validate_report_against_tool_result(report, result)
