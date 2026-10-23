
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "processed" / "olist.duckdb"

# Provisional quality rule: months with fewer than this many
# orders receive a low-volume warning. This is not proof of
# incomplete source data.
LOW_ORDER_COUNT_THRESHOLD = 100


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"DuckDB database not found: {DB_PATH}"
        )

    connection = duckdb.connect(
        str(DB_PATH),
        read_only=True,
    )

    try:
        query = f"""
            WITH date_bounds AS (
                SELECT
                    DATE_TRUNC(
                        'month',
                        MIN(
                            TRY_CAST(
                                order_purchase_timestamp AS TIMESTAMP
                            )
                        )
                    )::DATE AS first_month,
                    DATE_TRUNC(
                        'month',
                        MAX(
                            TRY_CAST(
                                order_purchase_timestamp AS TIMESTAMP
                            )
                        )
                    )::DATE AS last_month,
                    MAX(
                        TRY_CAST(
                            order_purchase_timestamp AS TIMESTAMP
                        )
                    ) AS latest_purchase
                FROM orders
            ),

            calendar AS (
                SELECT
                    unnest(
                        generate_series(
                            first_month,
                            last_month,
                            INTERVAL '1 month'
                        )
                    )::DATE AS month
                FROM date_bounds
            ),

            monthly_orders AS (
                SELECT
                    DATE_TRUNC(
                        'month',
                        TRY_CAST(
                            order_purchase_timestamp AS TIMESTAMP
                        )
                    )::DATE AS month,
                    COUNT(*) AS total_orders,
                    COUNT(*) FILTER (
                        WHERE order_status = 'delivered'
                    ) AS delivered_orders
                FROM orders
                GROUP BY 1
            ),

            monthly_items AS (
                SELECT
                    DATE_TRUNC(
                        'month',
                        TRY_CAST(
                            o.order_purchase_timestamp AS TIMESTAMP
                        )
                    )::DATE AS month,
                    SUM(i.price) AS item_sales_value,
                    SUM(i.freight_value) AS freight_value,
                    COUNT(DISTINCT i.order_id)
                        AS orders_with_items
                FROM orders o
                JOIN order_items i
                    ON o.order_id = i.order_id
                GROUP BY 1
            ),

            combined AS (
                SELECT
                    c.month,
                    COALESCE(o.total_orders, 0)
                        AS total_orders,
                    COALESCE(o.delivered_orders, 0)
                        AS delivered_orders,
                    i.item_sales_value,
                    i.freight_value,
                    COALESCE(i.orders_with_items, 0)
                        AS orders_with_items,
                    CASE
                        WHEN i.orders_with_items > 0
                        THEN i.item_sales_value
                             / i.orders_with_items
                        ELSE NULL
                    END AS average_item_value_per_order,
                    b.first_month,
                    b.last_month,
                    b.latest_purchase
                FROM calendar c
                CROSS JOIN date_bounds b
                LEFT JOIN monthly_orders o
                    ON c.month = o.month
                LEFT JOIN monthly_items i
                    ON c.month = i.month
            ),

            with_previous AS (
                SELECT
                    *,
                    LAG(total_orders) OVER (
                        ORDER BY month
                    ) AS previous_month_orders,
                    LAG(item_sales_value) OVER (
                        ORDER BY month
                    ) AS previous_month_item_sales
                FROM combined
            )

            SELECT
                month,
                total_orders,
                delivered_orders,

                ROUND(
                    100.0 * delivered_orders
                    / NULLIF(total_orders, 0),
                    2
                ) AS delivery_rate_pct,

                ROUND(item_sales_value, 2)
                    AS item_sales_value,

                ROUND(freight_value, 2)
                    AS freight_value,

                orders_with_items,

                ROUND(
                    average_item_value_per_order,
                    2
                ) AS average_item_value_per_order,

                CASE
                    WHEN previous_month_item_sales > 0
                     AND item_sales_value IS NOT NULL
                    THEN ROUND(
                        100.0 * (
                            item_sales_value
                            - previous_month_item_sales
                        ) / previous_month_item_sales,
                        2
                    )
                    ELSE NULL
                END AS item_sales_mom_change_pct,

                CASE
                    WHEN previous_month_orders IS NOT NULL
                    THEN total_orders - previous_month_orders
                    ELSE NULL
                END AS order_count_mom_change,

                CASE
                    WHEN month = first_month
                        THEN 'first_month'
                    WHEN month = last_month
                        THEN 'last_month'
                    WHEN total_orders = 0
                        THEN 'no_orders'
                    WHEN total_orders < {LOW_ORDER_COUNT_THRESHOLD}
                        THEN 'low_order_count'
                    ELSE 'interior_month'
                END AS coverage_flag,

                latest_purchase

            FROM with_previous
            ORDER BY month
        """

        result = connection.execute(query).fetchdf()

        print("MONTHLY KPI TREND ANALYSIS — COVERAGE-AWARE")
        print("=" * 110)
        print(f"Database: {DB_PATH}")
        print(f"Calendar months: {len(result)}")
        print(
            "Low-order-count warning threshold: "
            f"{LOW_ORDER_COUNT_THRESHOLD} orders"
        )

        print("\nFIRST 6 MONTHS")
        print(result.head(6).to_string(index=False))

        print("\nLAST 6 MONTHS")
        print(result.tail(6).to_string(index=False))

        print("\nMONTHS WITH ZERO ORDERS")
        zero_order_months = result.loc[
            result["coverage_flag"] == "no_orders",
            ["month", "coverage_flag"],
        ]

        if zero_order_months.empty:
            print("None")
        else:
            print(zero_order_months.to_string(index=False))

        print("\nMONTHS FLAGGED FOR LOW ORDER COUNT")
        low_volume_months = result.loc[
            result["coverage_flag"] == "low_order_count",
            [
                "month",
                "total_orders",
                "item_sales_value",
                "coverage_flag",
            ],
        ]

        if low_volume_months.empty:
            print("None")
        else:
            print(low_volume_months.to_string(index=False))

        print("\nCOVERAGE FLAG COUNTS")
        print(
            result["coverage_flag"]
            .value_counts()
            .to_string()
        )

        print("\nDAILY ORDER COVERAGE — SEPTEMBER/OCTOBER 2018")
        daily = connection.execute("""
            SELECT
                CAST(
                    TRY_CAST(
                        order_purchase_timestamp AS TIMESTAMP
                    ) AS DATE
                ) AS purchase_date,
                COUNT(*) AS orders
            FROM orders
            WHERE TRY_CAST(
                order_purchase_timestamp AS TIMESTAMP
            ) >= TIMESTAMP '2018-09-01'
              AND TRY_CAST(
                order_purchase_timestamp AS TIMESTAMP
            ) < TIMESTAMP '2018-11-01'
            GROUP BY 1
            ORDER BY 1
        """).fetchdf()

        if daily.empty:
            print("No records found for the selected period.")
        else:
            print(daily.to_string(index=False))

        print("\nVALIDATION CHECKS")

        expected_months = 26
        actual_months = len(result)

        print(
            f"Calendar month count: {actual_months} "
            f"(expected {expected_months})"
        )

        if actual_months != expected_months:
            print(
                "WARNING: Month count differs from the expected "
                "26 months. Inspect the source date range."
            )
        else:
            print("PASS: All 26 calendar months are represented.")

        if "2016-11-01" in result["month"].astype(str).values:
            print("PASS: November 2016 is present.")
        else:
            print("WARNING: November 2016 is missing.")

        december = result.loc[
            result["month"].astype(str) == "2016-12-01"
        ]

        if not december.empty:
            december_growth = december.iloc[0][
                "item_sales_mom_change_pct"
            ]

            print(
                "December 2016 item-sales MoM change: "
                f"{december_growth}"
            )

            if december_growth is None or (
                not isinstance(december_growth, float)
                or december_growth != december_growth
            ):
                print(
                    "PASS: Growth is undefined because the "
                    "previous month has no sales baseline."
                )

        print("\nTrend analysis completed.")
        print("Database opened read-only.")
        print("No source data or persistent database tables modified.")

    finally:
        connection.close()


if __name__ == "__main__":
    main()
