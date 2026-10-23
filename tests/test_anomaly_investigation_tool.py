
import pandas as pd
import pytest

from src.tools import anomaly_investigation_tool as tool


class FakeConnection:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def fake_anomaly():
    return {
        "month": "2017-11",
        "total_orders": 7544,
        "item_sales_value_brl": 1010271.37,
        "coverage_flag": "eligible",
        "scoring_status": "scored",
        "rolling_median_brl": 540021.41,
        "rolling_mad_brl": 63185.11,
        "robust_z_score": 5.02,
        "is_anomaly": True,
    }


def fake_trend():
    return {
        "month": "2017-11",
        "total_orders": 7544,
        "orders_with_items": 7451,
        "item_sales_value_brl": 1010271.37,
        "average_item_value_per_order_brl": 135.59,
        "coverage_flag": "eligible",
        "sales_mom_pct": 52.1,
        "orders_mom_pct": 62.9,
        "comparison_status": "comparable",
        "database_mode": "read-only",
    }


def configure_successful_investigation(monkeypatch):
    connection = FakeConnection()

    monkeypatch.setattr(
        tool, "find_anomaly", lambda month: fake_anomaly()
    )
    monkeypatch.setattr(
        tool, "get_monthly_trend", lambda month: fake_trend()
    )
    monkeypatch.setattr(
        tool.duckdb,
        "connect",
        lambda *args, **kwargs: connection,
    )

    def fake_monthly_metrics(connection, month):
        if month == "2017-10-01":
            return {
                "orders_with_items": 4568,
                "item_sales_value": 664219.43,
            }

        return {
            "orders_with_items": 7451,
            "item_sales_value": 1010271.37,
        }

    monkeypatch.setattr(
        tool, "load_monthly_metrics", fake_monthly_metrics
    )
    monkeypatch.setattr(
        tool,
        "decompose_sales_change",
        lambda previous, current: {
            "total_sales_change": 346051.94,
            "order_volume_effect": 405055.38,
            "average_item_value_effect": -59003.44,
            "reconciliation_difference": 0.0,
        },
    )
    monkeypatch.setattr(
        tool,
        "load_category_sales",
        lambda connection, month: pd.DataFrame(),
    )
    monkeypatch.setattr(
        tool,
        "compare_categories",
        lambda previous, current: pd.DataFrame([
            {
                "category": "bed_bath_table",
                "previous_sales": 46198.00,
                "current_sales": 89412.54,
                "sales_change": 43214.54,
            },
            {
                "category": "computers",
                "previous_sales": 40393.92,
                "current_sales": 9768.00,
                "sales_change": -30625.92,
            },
        ]),
    )

    return connection


@pytest.mark.parametrize(
    "month",
    [
        "2017-1",
        "2017-13",
        "2017-00",
        "17-11",
        "2017/11",
        " 2017-11 ",
        "",
    ],
)
def test_invalid_month_is_rejected(month):
    with pytest.raises(ValueError):
        tool.validate_month(month)


@pytest.mark.parametrize("month", [None, 201711, [], {}])
def test_non_string_month_is_rejected(month):
    with pytest.raises(TypeError):
        tool.validate_month(month)


def test_valid_month_is_parsed():
    assert str(tool.validate_month("2017-11")) == "2017-11"


def test_investigation_combines_anomaly_and_trend(monkeypatch):
    connection = configure_successful_investigation(monkeypatch)

    report = tool.investigate_month("2017-11")

    assert report["month"] == "2017-11"
    assert report["investigation_status"] == "potential_anomaly"
    assert report["anomaly_evidence"]["robust_z_score"] == 5.02
    assert report["trend_evidence"]["sales_mom_pct"] == 52.1
    assert report["evidence_summary"]["item_sales_change_brl"] == 346051.94
    assert connection.closed


def test_sales_decomposition_reconciles(monkeypatch):
    configure_successful_investigation(monkeypatch)

    report = tool.investigate_month("2017-11")
    decomposition = report["sales_decomposition"]

    assert decomposition["total_sales_change"] == pytest.approx(
        decomposition["order_volume_effect"]
        + decomposition["average_item_value_effect"]
    )
    assert decomposition["reconciliation_difference"] == pytest.approx(0)


def test_category_changes_include_both_directions(monkeypatch):
    configure_successful_investigation(monkeypatch)

    report = tool.investigate_month("2017-11")

    directions = {
        item["direction"] for item in report["category_changes"]
    }

    assert directions == {"increase", "decrease"}
    assert report["category_changes"][0]["category"] == "bed_bath_table"


def test_unscored_month_returns_partial_report(monkeypatch):
    unscored = {
        **fake_anomaly(),
        "coverage_flag": "low_order_count",
        "scoring_status": "coverage_excluded",
        "robust_z_score": None,
        "is_anomaly": False,
    }

    monkeypatch.setattr(
        tool, "find_anomaly", lambda month: unscored
    )
    monkeypatch.setattr(
        tool, "get_monthly_trend", lambda month: fake_trend()
    )

    def unexpected_connection(*args, **kwargs):
        pytest.fail("Database connection should not be opened.")

    monkeypatch.setattr(
        tool.duckdb, "connect", unexpected_connection
    )

    report = tool.investigate_month("2017-09")

    assert report["investigation_status"] == (
        "partial_insufficient_coverage_or_history"
    )
    assert report["sales_decomposition"] is None
    assert report["category_changes"] == []
    assert report["evidence_summary"] is None


def test_invalid_month_does_not_run_investigation(monkeypatch):
    def unexpected_call(*args, **kwargs):
        pytest.fail("Analytics should not run for an invalid month.")

    monkeypatch.setattr(tool, "find_anomaly", unexpected_call)

    with pytest.raises(ValueError):
        tool.investigate_month("2017-13")
