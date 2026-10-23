
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "processed" / "olist.duckdb"


def calculate_kpis(connection) -> dict:
    """Calculate initial descriptive KPIs from the Olist database."""

    order_metrics = connection.execute("""
        SELECT
            COUNT(DISTINCT order_id) AS total_orders,
            COUNT(DISTINCT order_id) FILTER (
                WHERE order_status = 'delivered'
            ) AS delivered_orders,
            COUNT(DISTINCT order_id) FILTER (
                WHERE order_status = 'canceled'
            ) AS canceled_orders,
            COUNT(DISTINCT order_id) FILTER (
                WHERE order_status = 'unavailable'
            ) AS unavailable_orders
        FROM orders
    """).fetchone()

    financial_metrics = connection.execute("""
        WITH item_by_order AS (
            SELECT
                order_id,
                SUM(price) AS item_value,
                SUM(freight_value) AS freight_value
            FROM order_items
            GROUP BY order_id
        ),
        payment_by_order AS (
            SELECT
                order_id,
                SUM(payment_value) AS payment_value
            FROM order_payments
            GROUP BY order_id
        )
        SELECT
            (SELECT SUM(price) FROM order_items),
            (SELECT SUM(freight_value) FROM order_items),
            (SELECT SUM(payment_value) FROM order_payments),
            (SELECT COUNT(*) FROM item_by_order),
            (SELECT AVG(item_value) FROM item_by_order),
            (SELECT AVG(item_value + freight_value)
             FROM item_by_order),
            (SELECT COUNT(*) FROM payment_by_order)
    """).fetchone()

    total_orders, delivered, canceled, unavailable = order_metrics

    (
        item_sales,
        freight,
        payments,
        orders_with_items,
        average_item_value,
        average_items_plus_freight,
        orders_with_payments,
    ) = financial_metrics

    delivery_rate = (
        delivered / total_orders * 100
        if total_orders else None
    )

    return {
        "total_orders": total_orders,
        "delivered_orders": delivered,
        "canceled_orders": canceled,
        "unavailable_orders": unavailable,
        "delivery_rate_pct": delivery_rate,
        "orders_with_item_records": orders_with_items,
        "orders_with_payment_records": orders_with_payments,
        "item_sales_value_brl": item_sales,
        "freight_value_brl": freight,
        "recorded_payment_value_brl": payments,
        "average_item_value_per_order_brl": average_item_value,
        "average_items_plus_freight_per_order_brl":
            average_items_plus_freight,
    }


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    connection = duckdb.connect(str(DB_PATH), read_only=True)

    try:
        metrics = calculate_kpis(connection)

        print("OLIST KPI ENGINE — INITIAL BASELINE")
        print("=" * 65)

        for name, value in metrics.items():
            if value is None:
                formatted = "N/A"
            elif isinstance(value, float):
                formatted = f"{value:,.2f}"
            else:
                formatted = f"{value:,}"

            print(f"{name:<48} {formatted}")

        print("\nKPIs calculated successfully.")
        print("Database opened read-only.")

    finally:
        connection.close()


if __name__ == "__main__":
    main()
