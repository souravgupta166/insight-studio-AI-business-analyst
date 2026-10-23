
import numpy as np
import pandas as pd
import pytest

from src.analytics.anomaly_detection import detect_anomalies
from src.analytics.investigate_sales_anomaly import (
    compare_categories,
    decompose_sales_change,
)


def test_sales_decomposition_reconciles():
    """Volume and average-value effects must sum to the sales change."""

    october = {
        "orders_with_items": 4568,
        "item_sales_value": 664219.43,
    }

    november = {
        "orders_with_items": 7451,
        "item_sales_value": 1010271.37,
    }

    result = decompose_sales_change(october, november)

    assert result is not None
    assert result["order_volume_effect"] > 0
    assert result["average_item_value_effect"] < 0

    assert result["total_sales_change"] == pytest.approx(
        result["order_volume_effect"]
        + result["average_item_value_effect"],
        abs=0.01,
    )

    assert result["reconciliation_difference"] == pytest.approx(
        0.0,
        abs=0.01,
    )


def test_decomposition_rejects_zero_item_orders():
    """Decomposition should not divide by zero."""

    previous = {
        "orders_with_items": 0,
        "item_sales_value": 0.0,
    }

    current = {
        "orders_with_items": 10,
        "item_sales_value": 100.0,
    }

    assert decompose_sales_change(previous, current) is None


def test_category_comparison_handles_new_and_disappearing_categories():
    """New and disappearing categories should remain in the comparison."""

    previous = pd.DataFrame(
        {
            "category": ["books", "computers"],
            "item_sales_value": [100.0, 200.0],
        }
    )

    current = pd.DataFrame(
        {
            "category": ["books", "toys"],
            "item_sales_value": [120.0, 50.0],
        }
    )

    result = compare_categories(previous, current)
    changes = result.set_index("category")["sales_change"]

    assert changes["books"] == pytest.approx(20.0)
    assert changes["computers"] == pytest.approx(-200.0)
    assert changes["toys"] == pytest.approx(50.0)


def test_coverage_excluded_months_are_not_anomalies():
    """Months excluded for coverage must not be flagged."""

    monthly = pd.DataFrame(
        {
            "month": pd.to_datetime(
                [
                    "2020-01-01",
                    "2020-02-01",
                    "2020-03-01",
                    "2020-04-01",
                    "2020-05-01",
                    "2020-06-01",
                ]
            ),
            "total_orders": [10, 200, 200, 200, 200, 200],
            "orders_with_items": [10, 200, 200, 200, 200, 200],
            "item_sales_value": [
                100.0,
                1000.0,
                1100.0,
                1050.0,
                1200.0,
                50000.0,
            ],
            "average_item_value_per_order": [
                10.0,
                5.0,
                5.5,
                5.25,
                6.0,
                250.0,
            ],
        }
    )

    result = detect_anomalies(monthly)

    excluded = result[result["coverage_flag"] != "eligible"]

    assert not excluded["is_anomaly"].any()
    assert result.iloc[0]["coverage_flag"] == "first_month"
    assert result.iloc[-1]["coverage_flag"] == "last_month"


def test_insufficient_history_is_reported():
    """The detector must not score a month with too little history."""

    monthly = pd.DataFrame(
        {
            "month": pd.date_range(
                "2020-01-01", periods=7, freq="MS"
            ),
            "total_orders": [10, 200, 200, 200, 200, 200, 200],
            "orders_with_items": [10, 200, 200, 200, 200, 200, 200],
            "item_sales_value": [
                100.0,
                1000.0,
                1100.0,
                1050.0,
                1200.0,
                1150.0,
                50000.0,
            ],
            "average_item_value_per_order": [
                10.0,
                5.0,
                5.5,
                5.25,
                6.0,
                5.75,
                250.0,
            ],
        }
    )

    result = detect_anomalies(monthly)

    february = result.loc[
        result["month"] == pd.Timestamp("2020-02-01")
    ].iloc[0]

    assert february["scoring_status"] == "insufficient_history"
    assert pd.isna(february["robust_z_score"])


def test_anomaly_detector_does_not_use_current_value_in_baseline():
    """The current month must not enter its own rolling baseline."""

    monthly = pd.DataFrame(
        {
            "month": pd.date_range(
                "2020-01-01", periods=8, freq="MS"
            ),
            "total_orders": [
                10, 200, 200, 200, 200, 200, 200, 200
            ],
            "orders_with_items": [
                10, 200, 200, 200, 200, 200, 200, 200
            ],
            "item_sales_value": [
                100.0,
                1000.0,
                1100.0,
                1050.0,
                1200.0,
                1150.0,
                50000.0,
                1300.0,
            ],
            "average_item_value_per_order": [
                10.0,
                5.0,
                5.5,
                5.25,
                6.0,
                5.75,
                250.0,
                6.5,
            ],
        }
    )

    result = detect_anomalies(monthly)

    july = result.loc[
        result["month"] == pd.Timestamp("2020-07-01")
    ].iloc[0]

    # January is excluded for low volume.
    # February through June provide five prior eligible observations.
    # July is an interior month because August follows it.
    expected_history = np.array(
        [1000.0, 1100.0, 1050.0, 1200.0, 1150.0]
    )[-6:]

    expected_median = np.median(expected_history)
    expected_mad = np.median(
        np.abs(expected_history - expected_median)
    )

    assert july["coverage_flag"] == "eligible"
    assert july["scoring_status"] == "scored"
    assert july["rolling_median"] == pytest.approx(expected_median)
    assert july["rolling_mad"] == pytest.approx(expected_mad)

    # The extreme July value must not influence July's own baseline.
    assert july["rolling_median"] != pytest.approx(50000.0)
