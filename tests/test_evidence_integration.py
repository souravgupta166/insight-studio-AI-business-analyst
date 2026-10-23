
from src.agent import orchestrator
from src.agent.schemas import InvestigationReport


def test_kpi_report_passes_integrated_validation(monkeypatch):
    """A valid KPI result should produce a successful validated report."""
    monkeypatch.setattr(
        orchestrator,
        "get_kpi",
        lambda name: {
            "kpi": name,
            "value": 99441,
            "unit": "orders",
            "description": "Number of orders in the orders table.",
            "database_mode": "read-only",
        },
    )

    report = orchestrator.execute_question(
        "How many total orders do we have?"
    )

    assert isinstance(report, InvestigationReport)
    assert report.status == "success"
    assert len(report.findings) == 1
    assert report.findings[0].evidence_type == "observed_metric"
    assert report.findings[0].metric_name == "total_orders"
    assert report.findings[0].value == 99441
    assert report.findings[0].unit == "orders"
    assert report.causal_conclusion_established is False


def test_invalid_investigation_evidence_returns_error(monkeypatch):
    """Inconsistent anomaly evidence must not reach the report."""
    invalid_result = {
        "month": "2017-11",
        "investigation_status": "potential_anomaly",
        "anomaly_evidence": {
            "scoring_status": "coverage_excluded",
            "coverage_flag": "low_order_count",
            "is_anomaly": True,
            "robust_z_score": None,
        },
        "trend_evidence": {},
        "sales_decomposition": None,
        "category_changes": [],
        "limitations": [],
    }

    monkeypatch.setattr(
        orchestrator,
        "investigate_month",
        lambda month: invalid_result,
    )

    report = orchestrator.execute_question(
        "Investigate the sales anomaly in 2017-11."
    )

    assert isinstance(report, InvestigationReport)
    assert report.status == "error"
    assert report.findings == []
    assert report.causal_conclusion_established is False
    assert any(
        "validation failed" in limitation.lower()
        for limitation in report.limitations
    )


def test_valid_investigation_returns_findings():
    """The real November 2017 investigation should pass validation."""
    report = orchestrator.execute_question(
        "Investigate the sales anomaly in 2017-11."
    )

    assert isinstance(report, InvestigationReport)
    assert report.status in ("success", "partial")
    assert report.findings
    assert report.causal_conclusion_established is False


def test_partial_investigation_remains_partial(monkeypatch):
    """An unscored month should remain partial and unflagged."""
    monkeypatch.setattr(
        orchestrator,
        "investigate_month",
        lambda month: {
            "month": month,
            "investigation_status":
                "partial_insufficient_coverage_or_history",
            "anomaly_evidence": {
                "scoring_status": "coverage_excluded",
                "coverage_flag": "low_order_count",
                "is_anomaly": False,
                "robust_z_score": None,
            },
            "trend_evidence": {},
            "sales_decomposition": None,
            "category_changes": [],
            "limitations": ["Insufficient coverage."],
        },
    )

    report = orchestrator.execute_question(
        "Investigate the sales anomaly in 2017-09."
    )

    assert isinstance(report, InvestigationReport)
    assert report.status == "partial"
    assert report.findings == []
    assert report.causal_conclusion_established is False
    assert any(
        "Insufficient coverage." in limitation
        for limitation in report.limitations
    )
