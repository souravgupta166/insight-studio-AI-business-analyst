
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "processed" / "olist.duckdb"


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    connection = duckdb.connect(str(DB_PATH), read_only=True)

    try:
        print("OLIST DATABASE SQL VALIDATION")
        print("=" * 65)

        # 1. Inspect the tables stored in DuckDB.
        tables = connection.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'main'
            ORDER BY table_name
        """).fetchall()

        print("\n1. TABLES")
        for (table_name,) in tables:
            print(f"  {table_name}")

        # 2. Verify the number of rows in each business table.
        print("\n2. ROW COUNTS")
        for (table_name,) in tables:
            count = connection.execute(
                f'SELECT COUNT(*) FROM "{table_name}"'
            ).fetchone()[0]
            print(f"  {table_name:<24} {count:>10,}")

        # 3. Understand the order lifecycle.
        print("\n3. ORDER STATUS DISTRIBUTION")
        status_rows = connection.execute("""
            SELECT
                order_status,
                COUNT(*) AS orders
            FROM orders
            GROUP BY order_status
            ORDER BY orders DESC
        """).fetchall()

        for status, count in status_rows:
            print(f"  {str(status):<20} {count:>10,}")

        # 4. Check the date range of the source orders.
        print("\n4. ORDER PURCHASE DATE RANGE")
        date_range = connection.execute("""
            SELECT
                MIN(TRY_CAST(order_purchase_timestamp AS TIMESTAMP)),
                MAX(TRY_CAST(order_purchase_timestamp AS TIMESTAMP)),
                COUNT(*) FILTER (
                    WHERE TRY_CAST(
                        order_purchase_timestamp AS TIMESTAMP
                    ) IS NULL
                )
            FROM orders
        """).fetchone()

        print(f"  Earliest purchase: {date_range[0]}")
        print(f"  Latest purchase:   {date_range[1]}")
        print(f"  Unparseable dates: {date_range[2]:,}")

        # 5. Compare item values and payment values independently.
        # Do not join raw item and payment rows directly.
        print("\n5. REVENUE COMPONENTS")
        item_metrics = connection.execute("""
            SELECT
                COUNT(*) AS item_rows,
                COUNT(DISTINCT order_id) AS orders_with_items,
                ROUND(SUM(price), 2) AS item_price_total,
                ROUND(SUM(freight_value), 2) AS freight_total
            FROM order_items
        """).fetchone()

        payment_metrics = connection.execute("""
            SELECT
                COUNT(*) AS payment_rows,
                COUNT(DISTINCT order_id) AS orders_with_payments,
                ROUND(SUM(payment_value), 2) AS payment_total
            FROM order_payments
        """).fetchone()

        print(
            f"  Item rows:                 {item_metrics[0]:,}"
        )
        print(
            f"  Orders with items:         {item_metrics[1]:,}"
        )
        print(
            f"  Sum of item prices:        {item_metrics[2]:,.2f}"
        )
        print(
            f"  Sum of freight values:     {item_metrics[3]:,.2f}"
        )
        print(
            f"  Payment rows:              {payment_metrics[0]:,}"
        )
        print(
            f"  Orders with payments:      {payment_metrics[1]:,}"
        )
        print(
            f"  Sum of payment values:     {payment_metrics[2]:,.2f}"
        )

        # 6. Quantify order-to-item and order-to-payment multiplicity.
        print("\n6. MULTIPLICITY CHECKS")
        multiplicity = connection.execute("""
            WITH item_counts AS (
                SELECT order_id, COUNT(*) AS item_count
                FROM order_items
                GROUP BY order_id
            ),
            payment_counts AS (
                SELECT order_id, COUNT(*) AS payment_count
                FROM order_payments
                GROUP BY order_id
            )
            SELECT
                (SELECT COUNT(*) FROM item_counts
                 WHERE item_count > 1),
                (SELECT COUNT(*) FROM payment_counts
                 WHERE payment_count > 1)
        """).fetchone()

        print(f"  Orders with multiple items:    {multiplicity[0]:,}")
        print(f"  Orders with multiple payments: {multiplicity[1]:,}")

        print("\nValidation completed. Database opened read-only.")

    finally:
        connection.close()


if __name__ == "__main__":
    main()
