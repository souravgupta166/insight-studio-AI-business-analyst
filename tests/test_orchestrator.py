
import pytest
from pydantic import ValidationError

from src.agent import orchestrator
from src.agent.schemas import InvestigationReport, ToolResult


def test_total_orders_routes_to_kpi():
    result = orchestrator.classify_question(
        "How many total orders do we have?"
    )
    assert result["intent"] == "kpi_lookup"
    assert result["kpi_name"] == "total_orders"


def test_delivery_rate_routes_to_kpi():
    result = orchestrator.classify_question(
        "What is the delivery rate?"
    )
    assert result["intent"] == "kpi_lookup"
    assert result["kpi_name"] == "delivery_rate_pct"


def test_monthly_trend_routes_correctly():
    result = orchestrator.classify_question(
        "Show the monthly sales trend for 2017-11."
    )
    assert result["intent"] == "monthly_trend"
    assert result["month"] == "2017-11"


def test_anomaly_investigation_routes_correctly():
    result = orchestrator.classify_question(
        "Investigate the sales anomaly in 2017-11."
    )
    assert result["intent"] == "anomaly_investigation"
    assert result["month"] == "2017-11"


def test_anomaly_question_without_month_is_rejected():
    with pytest.raises(orchestrator.UnsupportedQuestionError):
        orchestrator.classify_question("Investigate the sales anomaly.")


def test_trend_question_without_month_is_rejected():
    with pytest.raises(orchestrator.UnsupportedQuestionError):
        orchestrator.classify_question("Show the monthly sales trend.")


@pytest.mark.parametrize("question", ["", "   "])
def test_empty_question_is_rejected(question):
    with pytest.raises(ValidationError):
        orchestrator.classify_question(question)


def test_non_string_question_is_rejected():
    with pytest.raises((ValidationError, TypeError)):
        orchestrator.classify_question(None)


def test_overlong_question_is_rejected():
    with pytest.raises(ValidationError):
        orchestrator.classify_question("a" * 1001)


def test_invalid_month_is_rejected():
    with pytest.raises(ValueError):
        orchestrator.classify_question(
            "Investigate the sales anomaly in 2017-13."
        )


def test_multiple_months_are_rejected():
    with pytest.raises(orchestrator.UnsupportedQuestionError):
        orchestrator.classify_question(
            "Investigate the sales anomaly from 2017-10 to 2017-11."
        )


def test_unsupported_question_is_rejected():
    with pytest.raises(orchestrator.UnsupportedQuestionError):
        orchestrator.classify_question("Predict next year's profit.")


def test_multiple_kpis_are_rejected():
    with pytest.raises(orchestrator.UnsupportedQuestionError):
        orchestrator.classify_question(
            "Compare total orders and delivery rate."
        )


def test_execution_returns_validated_report(monkeypatch):
    monkeypatch.setattr(
        orchestrator,
        "get_kpi",
        lambda name: {
            "kpi": name,
            "value": 99441,
            "unit": "orders",
            "description": "Number of orders.",
            "database_mode": "read-only",
        },
    )

    report = orchestrator.execute_question(
        "How many total orders do we have?"
    )

    assert isinstance(report, InvestigationReport)
    assert report.status == "success"
    assert report.intent == "kpi_lookup"
    assert report.tools_used == ["get_kpi"]
    assert report.findings[0].value == 99441
    assert report.database_access == "read-only"
    assert report.causal_conclusion_established is False


def test_tool_execution_failure_returns_error_report(monkeypatch):
    def fail_tool(name):
        raise RuntimeError("Database unavailable")

    monkeypatch.setattr(orchestrator, "get_kpi", fail_tool)

    report = orchestrator.execute_question(
        "How many total orders do we have?"
    )

    assert isinstance(report, InvestigationReport)
    assert report.status == "error"
    assert report.findings == []
    assert report.causal_conclusion_established is False
    assert "could not be completed" in report.summary


def test_execute_tool_returns_validated_tool_result(monkeypatch):
    monkeypatch.setattr(
        orchestrator,
        "get_kpi",
        lambda name: {
            "kpi": name,
            "value": 99441,
            "unit": "orders",
        },
    )

    route = orchestrator.classify_question(
        "How many total orders do we have?"
    )
    result = orchestrator.execute_tool(route)

    assert isinstance(result, ToolResult)
    assert result.status == "success"
    assert result.data["value"] == 99441


def test_tool_failure_returns_error_tool_result(monkeypatch):
    monkeypatch.setattr(
        orchestrator,
        "get_kpi",
        lambda name: (_ for _ in ()).throw(RuntimeError("database error")),
    )

    route = orchestrator.classify_question(
        "How many total orders do we have?"
    )
    result = orchestrator.execute_tool(route)

    assert isinstance(result, ToolResult)
    assert result.status == "error"
    assert result.error_message
    assert result.data == {}


def test_build_evidence_from_kpi_result():
    result = ToolResult(
        tool_name="get_kpi",
        status="success",
        data={
            "kpi": "total_orders",
            "value": 99441,
            "unit": "orders",
        },
    )

    evidence = orchestrator.build_evidence(result)

    assert len(evidence) == 1
    assert evidence[0].metric_name == "total_orders"
    assert evidence[0].value == 99441
    assert evidence[0].supports_causal_claim is False


def test_tool_result_schema_rejects_missing_error_message():
    with pytest.raises(ValidationError):
        ToolResult(
            tool_name="get_kpi",
            status="error",
        )
