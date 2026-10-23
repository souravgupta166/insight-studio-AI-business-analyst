
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = PROJECT_ROOT / "data" / "processed" / "olist.duckdb"

TARGET_MONTH = "2017-11-01"
PREVIOUS_MONTH = "2017-10-01"
NEXT_MONTH = "2017-12-01"


def load_monthly_metrics(connection, month):
    """Load order-level and item-sales metrics for a calendar month."""

    query = """
        SELECT
            COUNT(DISTINCT o.order_id) AS total_orders,
            COUNT(DISTINCT i.order_id) AS orders_with_items,
            COALESCE(SUM(i.price), 0) AS item_sales_value
        FROM orders o
        LEFT JOIN order_items i
            ON o.order_id = i.order_id
        WHERE CAST(o.order_purchase_timestamp AS TIMESTAMP)
              >= CAST(? AS TIMESTAMP)
          AND CAST(o.order_purchase_timestamp AS TIMESTAMP)
              < CAST(? AS TIMESTAMP) + INTERVAL 1 MONTH
    """

    result = connection.execute(
        query, [month, month]
    ).fetchdf()

    return result.iloc[0].to_dict()


def load_category_sales(connection, month):
    """Aggregate item sales by translated product category."""

    query = """
        SELECT
            COALESCE(
                t.product_category_name_english,
                p.product_category_name,
                'unknown'
            ) AS category,
            COUNT(DISTINCT oi.order_id) AS orders,
            COUNT(*) AS item_lines,
            SUM(oi.price) AS item_sales_value
        FROM orders o
        INNER JOIN order_items oi
            ON o.order_id = oi.order_id
        INNER JOIN products p
            ON oi.product_id = p.product_id
        LEFT JOIN category_translation t
            ON p.product_category_name = t.product_category_name
        WHERE CAST(o.order_purchase_timestamp AS TIMESTAMP)
              >= CAST(? AS TIMESTAMP)
          AND CAST(o.order_purchase_timestamp AS TIMESTAMP)
              < CAST(? AS TIMESTAMP) + INTERVAL 1 MONTH
        GROUP BY 1
        ORDER BY item_sales_value DESC
    """

    return connection.execute(
        query, [month, month]
    ).fetchdf()


def decompose_sales_change(previous, current):
    """
    Decompose the change in item sales into:
    - order-volume effect
    - average item value per order effect

    Uses a two-factor midpoint decomposition.

    Sales = orders_with_items * average_item_value_per_order

    The two contributions sum to the total change, subject to
    floating-point rounding, when both periods have valid metrics.
    """

    previous_orders = previous["orders_with_items"]
    current_orders = current["orders_with_items"]

    previous_sales = previous["item_sales_value"]
    current_sales = current["item_sales_value"]

    if previous_orders <= 0 or current_orders <= 0:
        return None

    previous_average = previous_sales / previous_orders
    current_average = current_sales / current_orders

    order_effect = (
        (current_orders - previous_orders)
        * (previous_average + current_average)
        / 2
    )

    average_value_effect = (
        (current_average - previous_average)
        * (previous_orders + current_orders)
        / 2
    )

    total_change = current_sales - previous_sales
    explained_change = order_effect + average_value_effect

    return {
        "previous_orders_with_items": previous_orders,
        "current_orders_with_items": current_orders,
        "previous_average_item_value": previous_average,
        "current_average_item_value": current_average,
        "previous_item_sales": previous_sales,
        "current_item_sales": current_sales,
        "total_sales_change": total_change,
        "order_volume_effect": order_effect,
        "average_item_value_effect": average_value_effect,
        "reconciliation_difference": total_change - explained_change,
    }


def compare_categories(previous_categories, current_categories):
    """Compare category item sales between two months."""

    previous = previous_categories[
        ["category", "item_sales_value"]
    ].rename(
        columns={"item_sales_value": "previous_sales"}
    )

    current = current_categories[
        ["category", "item_sales_value"]
    ].rename(
        columns={"item_sales_value": "current_sales"}
    )

    comparison = previous.merge(
        current,
        on="category",
        how="outer",
    )

    comparison["previous_sales"] = comparison[
        "previous_sales"
    ].fillna(0)

    comparison["current_sales"] = comparison[
        "current_sales"
    ].fillna(0)

    comparison["sales_change"] = (
        comparison["current_sales"]
        - comparison["previous_sales"]
    )

    comparison = comparison.sort_values(
        "sales_change",
        ascending=False,
    ).reset_index(drop=True)

    return comparison


def print_money(value):
    return f"R${value:,.2f}"


def main():
    print("SALES ANOMALY INVESTIGATION")
    print("=" * 88)
    print(f"Database: {DATABASE_PATH}")
    print("Database mode: READ-ONLY")
    print(f"Target month: {TARGET_MONTH}")
    print()

    connection = duckdb.connect(
        str(DATABASE_PATH),
        read_only=True,
    )

    try:
        months = {
            "October 2017": PREVIOUS_MONTH,
            "November 2017": TARGET_MONTH,
            "December 2017": NEXT_MONTH,
        }

        metrics = {
            label: load_monthly_metrics(connection, month)
            for label, month in months.items()
        }

        print("1. MONTHLY COMPARISON")
        print("-" * 88)

        rows = []

        for label, values in metrics.items():
            orders = int(values["total_orders"])
            orders_with_items = int(values["orders_with_items"])
            sales = float(values["item_sales_value"])

            average_value = (
                sales / orders_with_items
                if orders_with_items > 0
                else np.nan
            )

            rows.append(
                {
                    "month": label,
                    "total_orders": orders,
                    "orders_with_items": orders_with_items,
                    "item_sales_value": sales,
                    "average_item_value_per_order": average_value,
                }
            )

        monthly_comparison = pd.DataFrame(rows)

        display = monthly_comparison.copy()
        numeric_columns = display.select_dtypes(
            include=["number"]
        ).columns
        display[numeric_columns] = display[numeric_columns].round(2)

        print(display.to_string(index=False))

        print("\n2. NOVEMBER VS OCTOBER: SALES DECOMPOSITION")
        print("-" * 88)

        decomposition = decompose_sales_change(
            metrics["October 2017"],
            metrics["November 2017"],
        )

        if decomposition is None:
            print(
                "Decomposition unavailable because one period "
                "has no orders with item records."
            )
        else:
            print(
                "October item sales: "
                + print_money(decomposition["previous_item_sales"])
            )
            print(
                "November item sales: "
                + print_money(decomposition["current_item_sales"])
            )
            print(
                "Total item-sales change: "
                + print_money(decomposition["total_sales_change"])
            )
            print(
                "Order-volume contribution: "
                + print_money(decomposition["order_volume_effect"])
            )
            print(
                "Average-item-value contribution: "
                + print_money(
                    decomposition["average_item_value_effect"]
                )
            )
            print(
                "Reconciliation difference: "
                + print_money(
                    decomposition["reconciliation_difference"]
                )
            )

            if abs(decomposition["reconciliation_difference"]) > 0.01:
                print(
                    "WARNING: decomposition does not reconcile "
                    "within R$0.01."
                )
            else:
                print("Decomposition reconciliation: PASS")

        print("\n3. CATEGORY CONTRIBUTIONS: NOVEMBER VS OCTOBER")
        print("-" * 88)

        october_categories = load_category_sales(
            connection, PREVIOUS_MONTH
        )
        november_categories = load_category_sales(
            connection, TARGET_MONTH
        )

        category_comparison = compare_categories(
            october_categories,
            november_categories,
        )

        print("\nTop 10 categories by positive sales change:")
        positive_changes = category_comparison[
            category_comparison["sales_change"] > 0
        ].head(10)

        if positive_changes.empty:
            print("No categories recorded a positive sales change.")
        else:
            display = positive_changes.copy()
            numeric_columns = display.select_dtypes(
                include=["number"]
            ).columns
            display[numeric_columns] = display[
                numeric_columns
            ].round(2)
            print(display.to_string(index=False))

        print("\nTop 10 categories by negative sales change:")
        negative_changes = category_comparison[
            category_comparison["sales_change"] < 0
        ].sort_values("sales_change").head(10)

        if negative_changes.empty:
            print("No categories recorded a negative sales change.")
        else:
            display = negative_changes.copy()
            numeric_columns = display.select_dtypes(
                include=["number"]
            ).columns
            display[numeric_columns] = display[
                numeric_columns
            ].round(2)
            print(display.to_string(index=False))

        print("\n4. NOVEMBER VS DECEMBER CONTEXT")
        print("-" * 88)

        december = metrics["December 2017"]
        november = metrics["November 2017"]

        december_sales = float(december["item_sales_value"])
        november_sales = float(november["item_sales_value"])

        print(
            "November item sales: "
            + print_money(november_sales)
        )
        print(
            "December item sales: "
            + print_money(december_sales)
        )
        print(
            "December minus November: "
            + print_money(december_sales - november_sales)
        )

        print("\n5. INTERPRETATION AND LIMITATIONS")
        print("-" * 88)
        print(
            "- This analysis is descriptive; it does not establish "
            "why sales changed."
        )
        print(
            "- Item sales use order-item prices and exclude freight."
        )
        print(
            "- The decomposition is an arithmetic allocation of "
            "the observed change, not a causal estimate."
        )
        print(
            "- Category sales are based on available product-category "
            "mappings; unknown categories remain visible."
        )
        print(
            "- The adjacent months provide context, but seasonality "
            "and external events have not been tested."
        )

        print("\nInvestigation completed.")
        print("Database opened read-only.")

    finally:
        connection.close()


if __name__ == "__main__":
    main()
