
import pytest

from src.tools.kpi_lookup import get_kpi, list_kpis


def test_kpi_catalog_contains_expected_metrics():
    kpis = list_kpis()

    assert "total_orders" in kpis
    assert "delivery_rate_pct" in kpis
    assert "item_sales_value_brl" in kpis


def test_total_orders_matches_validated_result():
    result = get_kpi("total_orders")

    assert result["value"] == 99441
    assert result["unit"] == "orders"
    assert result["database_mode"] == "read-only"


def test_delivery_rate_matches_validated_result():
    result = get_kpi("delivery_rate_pct")

    assert result["value"] == pytest.approx(97.02, abs=0.01)
    assert result["unit"] == "percent"


def test_item_sales_matches_validated_result():
    result = get_kpi("item_sales_value_brl")

    assert result["value"] == pytest.approx(
        13591643.70,
        abs=0.01,
    )
    assert result["unit"] == "BRL"


def test_unknown_kpi_is_rejected():
    with pytest.raises(ValueError, match="Unknown KPI"):
        get_kpi("profit")


def test_kpi_name_is_normalized():
    result = get_kpi(" TOTAL_ORDERS ")

    assert result["kpi"] == "total_orders"
    assert result["value"] == 99441
