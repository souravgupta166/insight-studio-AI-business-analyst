
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = PROJECT_ROOT / "data" / "processed" / "olist.duckdb"

HISTORY_WINDOW = 6
MIN_HISTORY = 4
MIN_ORDERS = 100
ROBUST_Z_THRESHOLD = 3.5


# ---------------------------------------------------------
# DATA EXTRACTION
# ---------------------------------------------------------

def load_monthly_data():
    """
    Load monthly order and item-sales metrics from DuckDB.

    The database is opened read-only.
    Item sales are the sum of order-item prices, excluding freight.
    """

    connection = duckdb.connect(
        str(DATABASE_PATH),
        read_only=True,
    )

    try:
        query = """
            WITH monthly_orders AS (
                SELECT
                    DATE_TRUNC(
                        'month',
                        CAST(order_purchase_timestamp AS TIMESTAMP)
                    )::DATE AS month,
                    COUNT(*) AS total_orders
                FROM orders
                WHERE order_purchase_timestamp IS NOT NULL
                GROUP BY 1
            ),
            monthly_sales AS (
                SELECT
                    DATE_TRUNC(
                        'month',
                        CAST(o.order_purchase_timestamp AS TIMESTAMP)
                    )::DATE AS month,
                    SUM(i.price) AS item_sales_value,
                    COUNT(DISTINCT o.order_id) AS orders_with_items
                FROM orders o
                INNER JOIN order_items i
                    ON o.order_id = i.order_id
                WHERE o.order_purchase_timestamp IS NOT NULL
                GROUP BY 1
            ),
            date_bounds AS (
                SELECT
                    DATE_TRUNC(
                        'month',
                        MIN(CAST(order_purchase_timestamp AS TIMESTAMP))
                    )::DATE AS first_month,
                    DATE_TRUNC(
                        'month',
                        MAX(CAST(order_purchase_timestamp AS TIMESTAMP))
                    )::DATE AS last_month
                FROM orders
                WHERE order_purchase_timestamp IS NOT NULL
            ),
            calendar AS (
                SELECT
                    UNNEST(
                        GENERATE_SERIES(
                            first_month,
                            last_month,
                            INTERVAL 1 MONTH
                        )
                    )::DATE AS month
                FROM date_bounds
            )
            SELECT
                c.month,
                COALESCE(o.total_orders, 0) AS total_orders,
                s.item_sales_value,
                COALESCE(s.orders_with_items, 0) AS orders_with_items
            FROM calendar c
            LEFT JOIN monthly_orders o
                ON c.month = o.month
            LEFT JOIN monthly_sales s
                ON c.month = s.month
            ORDER BY c.month
        """

        monthly = connection.execute(query).fetchdf()

    finally:
        connection.close()

    monthly["month"] = pd.to_datetime(monthly["month"])
    monthly["total_orders"] = monthly["total_orders"].astype(int)
    monthly["orders_with_items"] = monthly[
        "orders_with_items"
    ].astype(int)

    monthly["average_item_value_per_order"] = np.where(
        monthly["orders_with_items"] > 0,
        monthly["item_sales_value"] / monthly["orders_with_items"],
        np.nan,
    )

    return monthly


# ---------------------------------------------------------
# COVERAGE CLASSIFICATION
# ---------------------------------------------------------

def classify_coverage(monthly):
    """
    Mark months that should not be scored.

    Excluded months include:
    - First and last observed calendar months
    - Months with no orders or no sales
    - Months with fewer than MIN_ORDERS
    """

    result = monthly.copy()

    first_month = result["month"].min()
    last_month = result["month"].max()

    conditions = [
        result["month"].eq(first_month),
        result["month"].eq(last_month),
        result["total_orders"].eq(0),
        result["item_sales_value"].isna(),
        result["total_orders"].lt(MIN_ORDERS),
    ]

    labels = [
        "first_month",
        "last_month",
        "no_orders",
        "missing_sales",
        "low_order_count",
    ]

    result["coverage_flag"] = np.select(
        conditions,
        labels,
        default="eligible",
    )

    return result


# ---------------------------------------------------------
# ROBUST ANOMALY DETECTION
# ---------------------------------------------------------

def detect_anomalies(monthly):
    """
    Detect unusual monthly item-sales values using a past-only
    rolling median and median absolute deviation (MAD).

    Only prior eligible months enter the baseline. The current
    month is never included in its own baseline.
    """

    result = classify_coverage(monthly)

    result["rolling_median"] = np.nan
    result["rolling_mad"] = np.nan
    result["robust_z_score"] = np.nan
    result["scoring_status"] = "coverage_excluded"
    result["is_anomaly"] = False

    eligible_history = []

    for index, row in result.iterrows():
        if row["coverage_flag"] != "eligible":
            continue

        history = eligible_history[-HISTORY_WINDOW:]

        if len(history) < MIN_HISTORY:
            result.at[index, "scoring_status"] = (
                "insufficient_history"
            )
        else:
            values = np.asarray(history, dtype=float)

            median = float(np.median(values))
            mad = float(np.median(np.abs(values - median)))

            result.at[index, "rolling_median"] = median
            result.at[index, "rolling_mad"] = mad

            current_value = float(row["item_sales_value"])

            if np.isclose(mad, 0.0):
                result.at[index, "scoring_status"] = (
                    "zero_baseline_dispersion"
                )
            else:
                robust_z = (
                    0.6745 * (current_value - median) / mad
                )

                result.at[index, "robust_z_score"] = robust_z
                result.at[index, "scoring_status"] = "scored"
                result.at[index, "is_anomaly"] = (
                    abs(robust_z) >= ROBUST_Z_THRESHOLD
                )

        # Add the current month only after scoring it.
        # The baseline therefore uses past observations only.
        eligible_history.append(float(row["item_sales_value"]))

    return result


# ---------------------------------------------------------
# SUPPORTING EVIDENCE
# ---------------------------------------------------------

def add_interpretation(anomalies):
    """
    Add cautious, descriptive interpretations.

    These labels do not establish causation.
    """

    result = anomalies.copy()
    interpretations = []

    for _, row in result.iterrows():
        if row["coverage_flag"] != "eligible":
            interpretation = (
                f"Excluded from scoring: {row['coverage_flag']}."
            )

        elif row["scoring_status"] == "insufficient_history":
            interpretation = (
                "Not scored: insufficient prior eligible history."
            )

        elif row["scoring_status"] == "zero_baseline_dispersion":
            interpretation = (
                "Not scored: historical MAD is zero."
            )

        elif row["is_anomaly"]:
            interpretation = (
                "Potential item-sales anomaly; investigate order "
                "volume, average item value, and underlying records."
            )

        else:
            interpretation = (
                "No anomaly detected at the configured threshold."
            )

        interpretations.append(interpretation)

    result["interpretation"] = interpretations
    return result


# ---------------------------------------------------------
# OUTPUT HELPERS
# ---------------------------------------------------------

def print_rounded_table(dataframe):
    """Round numeric columns only, leaving dates untouched."""

    display_df = dataframe.copy()
    numeric_columns = display_df.select_dtypes(
        include=["number"]
    ).columns

    display_df[numeric_columns] = (
        display_df[numeric_columns].round(2)
    )

    print(display_df.to_string(index=False))


def main():
    print("MONTHLY ITEM-SALES ANOMALY DETECTION")
    print("=" * 100)
    print(f"Database: {DATABASE_PATH}")
    print("Database mode: READ-ONLY")
    print(f"Rolling history window: {HISTORY_WINDOW} eligible months")
    print(f"Minimum history required: {MIN_HISTORY}")
    print(f"Minimum orders for eligibility: {MIN_ORDERS}")
    print(f"Robust-score threshold: {ROBUST_Z_THRESHOLD}")
    print()

    monthly = load_monthly_data()
    anomalies = detect_anomalies(monthly)
    anomalies = add_interpretation(anomalies)

    print(f"Months examined: {len(anomalies)}")
    print("\nCOVERAGE FLAGS")
    print(anomalies["coverage_flag"].value_counts().to_string())

    print("\nSCORING STATUS")
    print(anomalies["scoring_status"].value_counts().to_string())

    columns = [
        "month",
        "total_orders",
        "item_sales_value",
        "average_item_value_per_order",
        "coverage_flag",
        "rolling_median",
        "rolling_mad",
        "robust_z_score",
        "scoring_status",
        "is_anomaly",
    ]

    print("\nMONTHLY ANOMALY SCORES")
    print_rounded_table(anomalies[columns])

    flagged = anomalies.loc[anomalies["is_anomaly"]].copy()

    print("\nFLAGGED MONTHS")
    if flagged.empty:
        print("No months crossed the configured threshold.")
    else:
        print_rounded_table(
            flagged[
                [
                    "month",
                    "total_orders",
                    "item_sales_value",
                    "average_item_value_per_order",
                    "rolling_median",
                    "rolling_mad",
                    "robust_z_score",
                    "interpretation",
                ]
            ]
        )

    print("\nINTERPRETATION")
    print(
        "- A flagged month is a screening signal, not a causal finding."
    )
    print(
        "- The baseline uses prior eligible months only."
    )
    print(
        "- Coverage-excluded months are not scored."
    )
    print(
        "- Insufficient history and zero-MAD cases are reported explicitly."
    )
    print(
        "- Item sales exclude freight and are not profit."
    )
    print(
        "- Order volume and average item value provide supporting "
        "descriptive evidence, not causal proof."
    )

    print("\nAnomaly detection completed.")
    print("Database opened read-only.")


if __name__ == "__main__":
    main()
