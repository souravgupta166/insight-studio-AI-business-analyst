
from pathlib import Path
import re

import duckdb
import pandas as pd


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = PROJECT_ROOT / "data" / "processed" / "olist.duckdb"

MIN_ORDERS = 100


# ---------------------------------------------------------
# DATA EXTRACTION
# ---------------------------------------------------------

def load_monthly_trends():
    """Load monthly order and item-sales metrics from DuckDB."""

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

    monthly["average_item_value_per_order"] = (
        monthly["item_sales_value"]
        / monthly["orders_with_items"].replace(0, float("nan"))
    )

    return monthly


# ---------------------------------------------------------
# COVERAGE CLASSIFICATION
# ---------------------------------------------------------

def classify_coverage(monthly):
    """
    Identify periods that should not be used in trend comparisons.

    First and last observed months are excluded because they may
    represent partial data coverage. Low-volume months are also
    excluded from comparison.
    """

    result = monthly.copy()

    if result.empty:
        result["coverage_flag"] = pd.Series(
            index=result.index,
            dtype="object",
        )
        return result

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

    result["coverage_flag"] = pd.Series(
        "eligible",
        index=result.index,
        dtype="object",
    )

    for condition, label in zip(conditions, labels):
        result.loc[
            condition & result["coverage_flag"].eq("eligible"),
            "coverage_flag",
        ] = label

    return result


# ---------------------------------------------------------
# MONTH-OVER-MONTH CALCULATIONS
# ---------------------------------------------------------

def calculate_trends(monthly=None):
    """
    Calculate monthly growth only when both adjacent months
    are eligible and the previous value is positive.

    Coverage exclusions are retained in the output rather than
    silently removed from the calendar.
    """

    if monthly is None:
        monthly = load_monthly_trends()

    result = classify_coverage(monthly)

    result["previous_month_sales"] = (
        result["item_sales_value"].shift(1)
    )

    result["previous_month_orders"] = (
        result["total_orders"].shift(1)
    )

    result["sales_mom_pct"] = float("nan")
    result["orders_mom_pct"] = float("nan")
    result["comparison_status"] = "comparison_unavailable"

    if result.empty:
        return result

    for position in range(len(result)):
        index = result.index[position]

        if position == 0:
            result.at[index, "comparison_status"] = (
                "no_previous_month"
            )
            continue

        previous_index = result.index[position - 1]

        current = result.loc[index]
        previous = result.loc[previous_index]

        if (
            current["coverage_flag"] != "eligible"
            or previous["coverage_flag"] != "eligible"
        ):
            result.at[index, "comparison_status"] = (
                "coverage_excluded"
            )
            continue

        previous_sales = previous["item_sales_value"]
        current_sales = current["item_sales_value"]

        previous_orders = previous["total_orders"]
        current_orders = current["total_orders"]

        if (
            pd.notna(previous_sales)
            and pd.notna(current_sales)
            and previous_sales > 0
        ):
            result.at[index, "sales_mom_pct"] = (
                (current_sales - previous_sales)
                / previous_sales
                * 100
            )

        if previous_orders > 0:
            result.at[index, "orders_mom_pct"] = (
                (current_orders - previous_orders)
                / previous_orders
                * 100
            )

        result.at[index, "comparison_status"] = "comparable"

    return result


# ---------------------------------------------------------
# STRUCTURED KPI TOOL RESPONSE
# ---------------------------------------------------------

def get_monthly_trend(month):
    """
    Return monthly metrics in a structured dictionary.

    Input must use strict YYYY-MM format, for example 2017-11.
    """

    if not isinstance(month, str):
        raise TypeError(
            "month must be a string in YYYY-MM format."
        )

    month = month.strip()

    if not re.fullmatch(r"\d{4}-\d{2}", month):
        raise ValueError(
            "Invalid month. Use YYYY-MM, for example 2017-11."
        )

    try:
        requested_month = pd.Period(month, freq="M")
    except (ValueError, TypeError) as exc:
        raise ValueError(
            "Invalid month. Use YYYY-MM, for example 2017-11."
        ) from exc

    trends = calculate_trends()

    matches = trends[
        trends["month"].dt.to_period("M") == requested_month
    ]

    if matches.empty:
        raise ValueError(f"No data found for month {month}.")

    row = matches.iloc[0]

    def optional_float(value):
        if pd.isna(value):
            return None
        return round(float(value), 2)

    return {
        "month": requested_month.strftime("%Y-%m"),
        "total_orders": int(row["total_orders"]),
        "orders_with_items": int(row["orders_with_items"]),
        "item_sales_value_brl": optional_float(
            row["item_sales_value"]
        ),
        "average_item_value_per_order_brl": optional_float(
            row["average_item_value_per_order"]
        ),
        "coverage_flag": row["coverage_flag"],
        "sales_mom_pct": optional_float(
            row["sales_mom_pct"]
        ),
        "orders_mom_pct": optional_float(
            row["orders_mom_pct"]
        ),
        "comparison_status": row["comparison_status"],
        "database_mode": "read-only",
    }


# ---------------------------------------------------------
# OUTPUT FORMATTING
# ---------------------------------------------------------

def print_rounded_table(dataframe):
    """Round numeric columns without affecting date or text fields."""

    display = dataframe.copy()

    numeric_columns = display.select_dtypes(
        include=["number"]
    ).columns

    display[numeric_columns] = display[numeric_columns].round(2)

    print(display.to_string(index=False))


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():
    trends = calculate_trends()

    print("MONTHLY TREND ANALYSIS TOOL")
    print("=" * 100)
    print(f"Database: {DATABASE_PATH}")
    print(f"Months examined: {len(trends)}")
    print(f"Minimum orders for eligibility: {MIN_ORDERS}")
    print("Database mode: READ-ONLY")

    print("\nCOVERAGE FLAGS")
    if trends.empty:
        print("No monthly data available.")
    else:
        print(trends["coverage_flag"].value_counts().to_string())

    print("\nMONTHLY TRENDS")

    columns = [
        "month",
        "total_orders",
        "orders_with_items",
        "item_sales_value",
        "average_item_value_per_order",
        "coverage_flag",
        "sales_mom_pct",
        "orders_mom_pct",
        "comparison_status",
    ]

    print_rounded_table(trends[columns])

    print("\nSAMPLE TOOL RESPONSE")

    try:
        print(get_monthly_trend("2017-11"))
    except ValueError as exc:
        print(f"Unable to retrieve sample: {exc}")

    print("\nInterpretation notes:")
    print("- Item sales are based on item prices and exclude freight.")
    print("- Growth rates are descriptive, not causal.")
    print("- Comparisons are suppressed if either adjacent month is excluded.")
    print("- First and last observed months are excluded from comparisons.")

    print("\nTrend analysis completed.")
    print("Database opened read-only.")


if __name__ == "__main__":
    main()
