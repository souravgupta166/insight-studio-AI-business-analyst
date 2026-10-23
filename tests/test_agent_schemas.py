
import pytest
from pydantic import ValidationError

from src.agent.schemas import (
    BusinessQuestion,
    EvidenceItem,
    InvestigationReport,
    ToolResult,
)


def test_valid_business_question():
    request = BusinessQuestion(
        question="What is the delivery rate?"
    )

    assert request.question == "What is the delivery rate?"


@pytest.mark.parametrize("question", ["", " ", "\t"])
def test_blank_business_question_rejected(question):
    with pytest.raises(ValidationError):
        BusinessQuestion(question=question)


def test_question_length_limit():
    with pytest.raises(ValidationError):
        BusinessQuestion(question="x" * 1001)


def test_extra_request_fields_rejected():
    with pytest.raises(ValidationError):
        BusinessQuestion(
            question="What is the delivery rate?",
            arbitrary_sql="DROP TABLE orders",
        )


def test_valid_evidence_item():
    evidence = EvidenceItem(
        evidence_id="evidence-001",
        evidence_type="observed_metric",
        claim="There were 99,441 orders.",
        source_tool="get_kpi",
        metric_name="total_orders",
        value=99441,
        unit="orders",
        supports_causal_claim=False,
    )

    assert evidence.value == 99441
    assert evidence.supports_causal_claim is False


def test_invalid_evidence_type_rejected():
    with pytest.raises(ValidationError):
        EvidenceItem(
            evidence_id="evidence-001",
            evidence_type="unsupported_type",
            claim="Example finding",
            source_tool="get_kpi",
        )


def test_tool_result_defaults_to_read_only():
    result = ToolResult(
        tool_name="get_kpi",
        status="success",
        data={"value": 99441},
    )

    assert result.database_access == "read-only"
    assert result.evidence == []


def test_error_tool_result_requires_message():
    with pytest.raises(ValidationError):
        ToolResult(
            tool_name="get_kpi",
            status="error",
        )


def test_success_tool_result_rejects_error_message():
    with pytest.raises(ValidationError):
        ToolResult(
            tool_name="get_kpi",
            status="success",
            error_message="Unexpected failure",
        )


def test_valid_investigation_report():
    report = InvestigationReport(
        question="What is the delivery rate?",
        intent="kpi_lookup",
        status="success",
        summary="The recorded delivery rate is 97.02%.",
        tools_used=["get_kpi"],
        causal_conclusion_established=False,
    )

    assert report.database_access == "read-only"
    assert report.status == "success"
    assert report.generated_at_utc.tzinfo is not None


def test_invalid_report_intent_rejected():
    with pytest.raises(ValidationError):
        InvestigationReport(
            question="What is the delivery rate?",
            intent="predict_future_profit",
            status="success",
            summary="Example",
        )


def test_naive_timestamp_rejected():
    with pytest.raises(ValidationError):
        InvestigationReport(
            question="What is the delivery rate?",
            intent="kpi_lookup",
            status="success",
            summary="Example",
            generated_at_utc="2026-10-23T10:00:00",
        )
