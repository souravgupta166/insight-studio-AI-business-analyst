
import pytest

from src.agent.evidence_validation import (
    EvidenceValidationError,
    validate_kpi_result,
    validate_monthly_trend_result,
)


def valid_kpi():
    return {
        "database_mode": "read-only",
        "description": "Number of orders in the orders table.",
        "kpi": "total_orders",
        "unit": "orders",
        "value": 99441,
    }


def valid_trend():
    return {
        "average_item_value_per_order_brl": 135.59,
        "comparison_status": "comparable",
        "coverage_flag": "eligible",
        "database_mode": "read-only",
        "item_sales_value_brl": 1010271.37,
        "month": "2017-11",
        "orders_mom_pct": 62.9,
        "orders_with_items": 7451,
        "sales_mom_pct": 52.1,
        "total_orders": 7544,
    }


def test_valid_kpi_passes():
    assert validate_kpi_result(valid_kpi())


@pytest.mark.parametrize("bad_value", [-1, True, float("nan"), float("inf"), 99441.5])
def test_invalid_order_count_is_rejected(bad_value):
    data = valid_kpi()
    data["value"] = bad_value

    with pytest.raises(EvidenceValidationError):
        validate_kpi_result(data)


def test_unknown_kpi_is_rejected():
    data = valid_kpi()
    data["kpi"] = "profit"
    data["unit"] = "BRL"

    with pytest.raises(EvidenceValidationError):
        validate_kpi_result(data)


def test_wrong_kpi_unit_is_rejected():
    data = valid_kpi()
    data["unit"] = "BRL"

    with pytest.raises(EvidenceValidationError):
        validate_kpi_result(data)


def test_non_read_only_kpi_is_rejected():
    data = valid_kpi()
    data["database_mode"] = "read-write"

    with pytest.raises(EvidenceValidationError):
        validate_kpi_result(data)


def test_valid_monthly_trend_passes():
    assert validate_monthly_trend_result(valid_trend())


@pytest.mark.parametrize("bad_month", ["2017-1", "2017-13", "17-11", "2017/11"])
def test_invalid_trend_month_is_rejected(bad_month):
    data = valid_trend()
    data["month"] = bad_month

    with pytest.raises(EvidenceValidationError):
        validate_monthly_trend_result(data)


def test_trend_rejects_negative_order_count():
    data = valid_trend()
    data["total_orders"] = -1

    with pytest.raises(EvidenceValidationError):
        validate_monthly_trend_result(data)


def test_trend_rejects_items_exceeding_total_orders():
    data = valid_trend()
    data["orders_with_items"] = data["total_orders"] + 1

    with pytest.raises(EvidenceValidationError):
        validate_monthly_trend_result(data)


def test_comparable_trend_requires_eligible_coverage():
    data = valid_trend()
    data["coverage_flag"] = "low_volume"

    with pytest.raises(EvidenceValidationError):
        validate_monthly_trend_result(data)


def test_comparable_trend_rejects_missing_percentage():
    data = valid_trend()
    data["sales_mom_pct"] = None

    with pytest.raises(EvidenceValidationError):
        validate_monthly_trend_result(data)


def test_comparable_trend_rejects_non_finite_percentage():
    data = valid_trend()
    data["orders_mom_pct"] = float("nan")

    with pytest.raises(EvidenceValidationError):
        validate_monthly_trend_result(data)


def test_non_comparable_trend_must_suppress_percentages():
    data = valid_trend()
    data["comparison_status"] = "not_comparable"
    data["coverage_flag"] = "low_volume"
    data["sales_mom_pct"] = None
    data["orders_mom_pct"] = None

    assert validate_monthly_trend_result(data)


def test_non_comparable_trend_cannot_return_percentage_changes():
    data = valid_trend()
    data["comparison_status"] = "not_comparable"
    data["coverage_flag"] = "low_volume"
    data["sales_mom_pct"] = 52.1

    with pytest.raises(EvidenceValidationError):
        validate_monthly_trend_result(data)
