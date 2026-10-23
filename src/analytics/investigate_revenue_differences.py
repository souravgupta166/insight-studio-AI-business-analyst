
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "processed" / "olist.duckdb"


def main() -> None:
    connection = duckdb.connect(str(DB_PATH), read_only=True)

    try:
        # Aggregate each financial table independently at order level.
        connection.execute("""
            CREATE OR REPLACE TEMP VIEW financial_differences AS
            WITH item_totals AS (
                SELECT
                    order_id,
                    COUNT(*) AS item_count,
                    SUM(price) AS item_total,
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
                o.order_id,
                o.order_status,
                i.item_count,
                i.item_total,
                i.freight_total,
                p.payment_count,
                p.payment_total,
                p.payment_total - (i.item_total + i.freight_total)
                    AS difference
            FROM orders o
            LEFT JOIN item_totals i USING (order_id)
            LEFT JOIN payment_totals p USING (order_id)
        """)

        print("REVENUE DIFFERENCE INVESTIGATION")
        print("=" * 70)

        # 1. Check whether discrepancies are concentrated in statuses.
        print("\n1. DISCREPANCIES BY ORDER STATUS")
        rows = connection.execute("""
            SELECT
                order_status,
                COUNT(*) AS order_count,
                ROUND(SUM(difference), 2) AS total_difference,
                ROUND(AVG(difference), 2) AS mean_difference
            FROM financial_differences
            WHERE item_total IS NOT NULL
              AND payment_total IS NOT NULL
              AND ABS(difference) > 0.01
            GROUP BY order_status
            ORDER BY order_count DESC
        """).fetchall()

        for row in rows:
            print(
                f"  Status={row[0]:<15} "
                f"orders={row[1]:>4,} "
                f"total_difference={row[2]:>12,.2f} "
                f"mean_difference={row[3]:>8,.2f}"
            )

        # 2. See whether payment types or installments help explain
        # the differences. Orders may have multiple payment records.
        print("\n2. PAYMENT TYPE AND INSTALLMENT PATTERNS")
        rows = connection.execute("""
            WITH payment_summary AS (
                SELECT
                    order_id,
                    STRING_AGG(DISTINCT payment_type, ', '
                               ORDER BY payment_type) AS payment_types,
                    MAX(payment_installments) AS max_installments,
                    COUNT(*) AS payment_rows
                FROM order_payments
                GROUP BY order_id
            )
            SELECT
                p.payment_types,
                CASE
                    WHEN p.max_installments IS NULL THEN 'unknown'
                    WHEN p.max_installments = 1 THEN '1'
                    WHEN p.max_installments <= 3 THEN '2-3'
                    WHEN p.max_installments <= 6 THEN '4-6'
                    WHEN p.max_installments <= 12 THEN '7-12'
                    ELSE '13+'
                END AS installment_band,
                COUNT(*) AS orders,
                ROUND(AVG(ABS(f.difference)), 2) AS mean_abs_difference
            FROM financial_differences f
            JOIN payment_summary p USING (order_id)
            WHERE f.item_total IS NOT NULL
              AND f.payment_total IS NOT NULL
              AND ABS(f.difference) > 0.01
            GROUP BY p.payment_types, installment_band
            ORDER BY orders DESC
            LIMIT 20
        """).fetchall()

        for row in rows:
            print(
                f"  Types={str(row[0]):<30} "
                f"installments={row[1]:<8} "
                f"orders={row[2]:>4,} "
                f"mean_abs_diff={row[3]:>8,.2f}"
            )

        # 3. Inspect the ten largest differences.
        print("\n3. LARGEST DIFFERENCES WITH STATUS")
        rows = connection.execute("""
            SELECT
                order_id,
                order_status,
                item_count,
                payment_count,
                ROUND(item_total, 2) AS item_total,
                ROUND(freight_total, 2) AS freight,
                ROUND(payment_total, 2) AS payment_total,
                ROUND(difference, 2) AS difference
            FROM financial_differences
            WHERE item_total IS NOT NULL
              AND payment_total IS NOT NULL
            ORDER BY ABS(difference) DESC
            LIMIT 10
        """).fetchall()

        for row in rows:
            print("  " + " | ".join(str(value) for value in row))

        # 4. Identify orders without item or payment records.
        print("\n4. ORDERS WITHOUT FINANCIAL RECORDS")
        rows = connection.execute("""
            SELECT
                order_status,
                COUNT(*) AS orders_without_items,
                COUNT(*) FILTER (
                    WHERE payment_total IS NULL
                ) AS orders_without_payments
            FROM financial_differences
            WHERE item_total IS NULL OR payment_total IS NULL
            GROUP BY order_status
            ORDER BY orders_without_items DESC
        """).fetchall()

        for row in rows:
            print(
                f"  Status={row[0]:<15} "
                f"without_items={row[1]:>5,} "
                f"without_payments={row[2]:>5,}"
            )

        print("\nInvestigation completed; database remains read-only.")

    finally:
        connection.close()


if __name__ == "__main__":
    main()
