
from pathlib import Path
import re

import duckdb
import pandas as pd

from src.analytics.anomaly_detection import load_monthly_data, detect_anomalies
from src.analytics.investigate_sales_anomaly import (
    load_monthly_metrics,
    load_category_sales,
    decompose_sales_change,
    compare_categories,
)
from src.tools.trend_analysis_tool import get_monthly_trend


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = PROJECT_ROOT / "data" / "processed" / "olist.duckdb"


def validate_month(month):
    """Validate a calendar month using strict YYYY-MM formatting."""
    if not isinstance(month, str):
        raise TypeError("month must be a string in YYYY-MM format.")

    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
        raise ValueError(
            "Invalid month. Use YYYY-MM, for example 2017-11."
        )

    return pd.Period(month, freq="M")


def optional_float(value):
    """Convert a numeric value to a rounded float, or None if missing."""
    if pd.isna(value):
        return None
    return round(float(value), 2)


def find_anomaly(month):
    """Return anomaly evidence for one month."""
    period = validate_month(month)

    monthly_data = load_monthly_data()
    anomaly_data = detect_anomalies(monthly_data)

    matches = anomaly_data[
        anomaly_data["month"].dt.to_period("M") == period
    ]

    if matches.empty:
        raise ValueError(f"No anomaly data found for {month}.")

    row = matches.iloc[0]

    return {
        "month": str(period),
        "total_orders": int(row["total_orders"]),
        "item_sales_value_brl": optional_float(
            row["item_sales_value"]
        ),
        "coverage_flag": row["coverage_flag"],
        "scoring_status": row["scoring_status"],
        "rolling_median_brl": optional_float(
            row["rolling_median"]
        ),
        "rolling_mad_brl": optional_float(
            row["rolling_mad"]
        ),
        "robust_z_score": optional_float(
            row["robust_z_score"]
        ),
        "is_anomaly": bool(row["is_anomaly"]),
    }


def investigate_month(month):
    """
    Combine anomaly, trend, sales decomposition and category evidence.

    This investigation is descriptive and does not establish causation.
    """
    period = validate_month(month)

    target_month = str(period)
    previous_month = str(period - 1)

    anomaly = find_anomaly(target_month)
    trend = get_monthly_trend(target_month)

    report = {
        "month": target_month,
        "investigation_status": None,
        "anomaly_evidence": anomaly,
        "trend_evidence": trend,
        "sales_decomposition": None,
        "category_changes": [],
        "evidence_summary": None,
        "recommended_next_step": None,
        "limitations": [
            "The findings are descriptive and do not establish causation.",
            "Item sales use recorded order-item prices and exclude freight.",
            "Item sales are not profit.",
            "Category changes do not establish why demand changed.",
        ],
    }

    # Do not investigate drivers when the month was excluded from scoring.
    if (
        anomaly["scoring_status"] != "scored"
        or anomaly["coverage_flag"] != "eligible"
    ):
        report["investigation_status"] = (
            "partial_insufficient_coverage_or_history"
        )
        report["recommended_next_step"] = (
            "Use a month with sufficient historical coverage for "
            "anomaly investigation. Do not interpret this month as "
            "a confirmed normal period."
        )
        report["limitations"].append(
            "The detector did not score this month; no anomaly conclusion "
            "is made for it."
        )
        return report

    report["investigation_status"] = (
        "potential_anomaly" if anomaly["is_anomaly"] else "not_flagged"
    )

    connection = duckdb.connect(
        str(DATABASE_PATH),
        read_only=True,
    )

    try:
        previous_metrics = load_monthly_metrics(
            connection,
            f"{previous_month}-01",
        )
        current_metrics = load_monthly_metrics(
            connection,
            f"{target_month}-01",
        )

        previous_orders = int(previous_metrics["orders_with_items"])
        current_orders = int(current_metrics["orders_with_items"])

        previous_sales = float(previous_metrics["item_sales_value"])
        current_sales = float(current_metrics["item_sales_value"])

        if previous_orders > 0 and current_orders > 0:
            decomposition = decompose_sales_change(
                previous_metrics,
                current_metrics,
            )

            report["sales_decomposition"] = {
                key: (
                    round(float(value), 2)
                    if isinstance(value, (int, float))
                    else value
                )
                for key, value in decomposition.items()
            }

        previous_categories = load_category_sales(
            connection,
            f"{previous_month}-01",
        )
        current_categories = load_category_sales(
            connection,
            f"{target_month}-01",
        )

        comparison = compare_categories(
            previous_categories,
            current_categories,
        )

        positive = comparison[
            comparison["sales_change"] > 0
        ].sort_values("sales_change", ascending=False).head(5)

        negative = comparison[
            comparison["sales_change"] < 0
        ].sort_values("sales_change", ascending=True).head(5)

        for direction, frame in (
            ("increase", positive),
            ("decrease", negative),
        ):
            for _, row in frame.iterrows():
                report["category_changes"].append({
                    "category": row["category"],
                    "previous_sales_brl": round(
                        float(row["previous_sales"]), 2
                    ),
                    "current_sales_brl": round(
                        float(row["current_sales"]), 2
                    ),
                    "sales_change_brl": round(
                        float(row["sales_change"]), 2
                    ),
                    "direction": direction,
                })

    finally:
        connection.close()

    report["evidence_summary"] = {
        "comparison_month": previous_month,
        "item_sales_change_brl": round(
            current_sales - previous_sales, 2
        ),
        "category_comparison_period": (
            f"{previous_month} to {target_month}"
        ),
        "causal_explanation_established": False,
    }

    if anomaly["is_anomaly"]:
        report["recommended_next_step"] = (
            "Investigate order-volume contribution, average item value, "
            "category changes and relevant order-level records. Assess "
            "seasonality before attributing the change to a business event."
        )
    else:
        report["recommended_next_step"] = (
            "Review the trend and category evidence if further analysis "
            "is needed. The detector did not flag this month as an anomaly."
        )

    return report


def main():
    month = "2017-11"
    report = investigate_month(month)

    print("=" * 80)
    print("EVIDENCE-BACKED ANOMALY INVESTIGATION")
    print("=" * 80)
    print("Database mode: READ-ONLY")
    print(f"Month: {report['month']}")
    print(f"Status: {report['investigation_status']}")

    print("\nANOMALY EVIDENCE")
    for key, value in report["anomaly_evidence"].items():
        print(f"{key}: {value}")

    print("\nTREND EVIDENCE")
    for key, value in report["trend_evidence"].items():
        print(f"{key}: {value}")

    print("\nSALES DECOMPOSITION")
    print(report["sales_decomposition"])

    print("\nCATEGORY CHANGES")
    for item in report["category_changes"]:
        print(item)

    print("\nEVIDENCE SUMMARY")
    print(report["evidence_summary"])

    print("\nRECOMMENDED NEXT STEP")
    print(report["recommended_next_step"])

    print("\nLIMITATIONS")
    for item in report["limitations"]:
        print(f"- {item}")

    print("\nInvestigation completed.")


if __name__ == "__main__":
    main()
