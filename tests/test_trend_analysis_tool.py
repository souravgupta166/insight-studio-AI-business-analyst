
import pandas as pd
import pytest

from src.tools.trend_analysis_tool import (
    calculate_trends,
    classify_coverage,
    get_monthly_trend,
)


def make_monthly_data():
    """Create deterministic monthly data for isolated unit tests."""

    return pd.DataFrame(
        {
            "month": pd.date_range(
                "2020-01-01", periods=8, freq="MS"
            ),
            "total_orders": [
                10, 200, 220, 240, 260, 280, 300, 320
            ],
            "orders_with_items": [
                10, 190, 210, 230, 250, 270, 290, 310
            ],
            "item_sales_value": [
                100.0, 1900.0, 2310.0, 2530.0,
                3000.0, 3240.0, 3480.0, 3720.0
            ],
        }
    )


def test_coverage_classification_excludes_first_and_last_months():
    result = classify_coverage(make_monthly_data())

    assert result.iloc[0]["coverage_flag"] == "first_month"
    assert result.iloc[-1]["coverage_flag"] == "last_month"


def test_low_volume_month_is_excluded():
    monthly = make_monthly_data()
    monthly.loc[monthly.index[3], "total_orders"] = 50

    result = classify_coverage(monthly)

    assert result.loc[3, "coverage_flag"] == "low_order_count"


def test_growth_is_suppressed_when_previous_month_is_excluded():
    result = calculate_trends(make_monthly_data())

    # January is the first month; February cannot be compared to it.
    february = result.loc[
        result["month"] == pd.Timestamp("2020-02-01")
    ].iloc[0]

    assert february["comparison_status"] == "coverage_excluded"
    assert pd.isna(february["sales_mom_pct"])
    assert pd.isna(february["orders_mom_pct"])


def test_growth_is_calculated_for_comparable_months():
    result = calculate_trends(make_monthly_data())

    march = result.loc[
        result["month"] == pd.Timestamp("2020-03-01")
    ].iloc[0]

    assert march["comparison_status"] == "comparable"
    assert march["sales_mom_pct"] == pytest.approx(
        (2310.0 - 1900.0) / 1900.0 * 100
    )
    assert march["orders_mom_pct"] == pytest.approx(
        (220 - 200) / 200 * 100
    )


def test_growth_is_suppressed_for_low_volume_month():
    monthly = make_monthly_data()
    monthly.loc[monthly.index[4], "total_orders"] = 50

    result = calculate_trends(monthly)

    may = result.loc[
        result["month"] == pd.Timestamp("2020-05-01")
    ].iloc[0]

    assert may["coverage_flag"] == "low_order_count"
    assert may["comparison_status"] == "coverage_excluded"
    assert pd.isna(may["sales_mom_pct"])


def test_monthly_tool_returns_structured_result():
    result = get_monthly_trend("2017-11")

    assert result["month"] == "2017-11"
    assert result["total_orders"] == 7544
    assert result["coverage_flag"] == "eligible"
    assert result["comparison_status"] == "comparable"
    assert result["sales_mom_pct"] == pytest.approx(
        52.099039, abs=0.01
    )
    assert result["database_mode"] == "read-only"


def test_invalid_month_format_is_rejected():
    with pytest.raises(ValueError, match="Invalid month"):
        get_monthly_trend("November 2017")


def test_non_string_month_is_rejected():
    with pytest.raises(TypeError, match="month must be a string"):
        get_monthly_trend(201711)
