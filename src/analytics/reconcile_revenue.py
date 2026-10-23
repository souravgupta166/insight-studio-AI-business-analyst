
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "processed" / "olist.duckdb"


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    connection = duckdb.connect(str(DB_PATH), read_only=True)

    try:
        print("OLIST ORDER-LEVEL REVENUE RECONCILIATION")
        print("=" * 70)

        # Aggregate items and payments separately before joining.
        # This prevents item-payment row multiplication.
        connection.execute("""
            CREATE OR REPLACE TEMP VIEW order_financials AS
            WITH item_totals AS (
                SELECT
                    order_id,
                    COUNT(*) AS item_count,
                    SUM(price) AS item_price_total,
                    SUM(freight_value) AS freight_total
                FROM order_items
                GROUP BY order_id
            ),
            payment_totals AS (
                SELECT
                    order_id,
                    COUNT(*) AS payment_count,
                    SUM(payment_value) AS payment_total
                FROM order_payments
                GROUP BY order_id
            )
            SELECT
                COALESCE(i.order_id, p.order_id) AS order_id,
                i.item_count,
                i.item_price_total,
                i.freight_total,
                p.payment_count,
                p.payment_total,
                CASE
                    WHEN i.order_id IS NOT NULL
                     AND p.order_id IS NOT NULL
                    THEN p.payment_total
                         - (i.item_price_total + i.freight_total)
                    ELSE NULL
                END AS payment_minus_items_and_freight
            FROM item_totals i
            FULL OUTER JOIN payment_totals p
                ON i.order_id = p.order_id
        """)

        # 1. Overall totals, calculated independently.
        print("\n1. AGGREGATED TOTALS")
        totals = connection.execute("""
            SELECT
                COUNT(*) AS orders_in_either_financial_table,
                COUNT(item_price_total) AS orders_with_items,
                COUNT(payment_total) AS orders_with_payments,
                ROUND(SUM(item_price_total), 2) AS item_price_total,
                ROUND(SUM(freight_total), 2) AS freight_total,
                ROUND(SUM(payment_total), 2) AS payment_total,
                COUNT(*) FILTER (
                    WHERE item_price_total IS NOT NULL
                      AND payment_total IS NOT NULL
                ) AS orders_with_both
            FROM order_financials
        """).fetchone()

        labels = [
            "Orders in either financial table",
            "Orders with items",
            "Orders with payments",
            "Total item prices",
            "Total freight",
            "Total payments",
            "Orders with both items and payments",
        ]

        for label, value in zip(labels, totals):
            if isinstance(value, float):
                print(f"  {label:<42} {value:,.2f}")
            else:
                print(f"  {label:<42} {value:,}")

        # 2. Orders whose item-plus-freight total differs from payments.
        # A difference is a reconciliation signal, not proof of an error.
        print("\n2. ORDER-LEVEL COMPARISON")
        comparison = connection.execute("""
            SELECT
                COUNT(*) AS comparable_orders,
                COUNT(*) FILTER (
                    WHERE ABS(payment_minus_items_and_freight) <= 0.01
                ) AS within_one_cent,
                COUNT(*) FILTER (
                    WHERE payment_minus_items_and_freight > 0.01
                ) AS payments_higher,
                COUNT(*) FILTER (
                    WHERE payment_minus_items_and_freight < -0.01
                ) AS payments_lower,
                ROUND(
                    AVG(payment_minus_items_and_freight), 2
                ) AS mean_difference,
                ROUND(
                    MEDIAN(payment_minus_items_and_freight), 2
                ) AS median_difference,
                ROUND(
                    SUM(payment_minus_items_and_freight), 2
                ) AS total_difference
            FROM order_financials
            WHERE item_price_total IS NOT NULL
              AND payment_total IS NOT NULL
        """).fetchone()

        comparison_labels = [
            "Orders compared",
            "Within R$0.01",
            "Payments higher",
            "Payments lower",
            "Mean difference (R$)",
            "Median difference (R$)",
            "Sum of differences (R$)",
        ]

        for label, value in zip(comparison_labels, comparison):
            if isinstance(value, float):
                print(f"  {label:<42} {value:,.2f}")
            else:
                print(f"  {label:<42} {value:,}")

        # 3. Show the largest absolute discrepancies for investigation.
        print("\n3. TEN LARGEST ABSOLUTE DIFFERENCES")
        examples = connection.execute("""
            SELECT
                order_id,
                item_count,
                payment_count,
                ROUND(item_price_total, 2) AS item_prices,
                ROUND(freight_total, 2) AS freight,
                ROUND(payment_total, 2) AS payments,
                ROUND(payment_minus_items_and_freight, 2) AS difference
            FROM order_financials
            WHERE payment_minus_items_and_freight IS NOT NULL
            ORDER BY ABS(payment_minus_items_and_freight) DESC
            LIMIT 10
        """).fetchdf()

        print(examples.to_string(index=False))

        print("\nReconciliation completed.")
        print("The source tables and persistent database were not modified.")

    finally:
        connection.close()


if __name__ == "__main__":
    main()
