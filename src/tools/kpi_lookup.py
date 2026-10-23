
"""Read-only KPI lookup for the AI Business Analyst engine."""

from pathlib import Path
from typing import Any

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "processed" / "olist.duckdb"


KPI_DEFINITIONS = {
    "total_orders": {
        "sql": "SELECT COUNT(DISTINCT order_id) FROM orders",
        "unit": "orders",
        "description": "Total number of distinct orders.",
    },
    "delivered_orders": {
        "sql": """
            SELECT COUNT(DISTINCT order_id)
            FROM orders
            WHERE order_status = 'delivered'
        """,
        "unit": "orders",
        "description": "Number of orders with delivered status.",
    },
    "canceled_orders": {
        "sql": """
            SELECT COUNT(DISTINCT order_id)
            FROM orders
            WHERE order_status = 'canceled'
        """,
        "unit": "orders",
        "description": "Number of orders with canceled status.",
    },
    "unavailable_orders": {
        "sql": """
            SELECT COUNT(DISTINCT order_id)
            FROM orders
            WHERE order_status = 'unavailable'
        """,
        "unit": "orders",
        "description": "Number of orders with unavailable status.",
    },
    "orders_with_item_records": {
        "sql": """
            SELECT COUNT(DISTINCT order_id)
            FROM order_items
        """,
        "unit": "orders",
        "description": (
            "Number of distinct orders represented in order item records."
        ),
    },
    "orders_with_payment_records": {
        "sql": """
            SELECT COUNT(DISTINCT order_id)
            FROM order_payments
        """,
        "unit": "orders",
        "description": (
            "Number of distinct orders represented in payment records."
        ),
    },
    "delivery_rate_pct": {
        "sql": """
            SELECT
                100.0 * COUNT(DISTINCT CASE
                    WHEN order_status = 'delivered' THEN order_id
                END)
                / NULLIF(COUNT(DISTINCT order_id), 0)
            FROM orders
        """,
        "unit": "percent",
        "description": (
            "Delivered orders divided by all distinct orders, multiplied "
            "by 100. This is not the delivery rate among only eligible "
            "orders."
        ),
    },
    "item_sales_value_brl": {
        "sql": """
            SELECT COALESCE(SUM(price), 0)
            FROM order_items
        """,
        "unit": "BRL",
        "description": (
            "Total recorded item price across order item records, in BRL."
        ),
    },
    "freight_value_brl": {
        "sql": """
            SELECT COALESCE(SUM(freight_value), 0)
            FROM order_items
        """,
        "unit": "BRL",
        "description": (
            "Total recorded freight value across order item records, in BRL."
        ),
    },
    "recorded_payment_value_brl": {
        "sql": """
            SELECT COALESCE(SUM(payment_value), 0)
            FROM order_payments
        """,
        "unit": "BRL",
        "description": (
            "Total recorded payment value across payment records, in BRL."
        ),
    },
    "average_item_value_per_order_brl": {
        "sql": """
            SELECT COALESCE(
                SUM(item_value) / NULLIF(COUNT(*), 0),
                0
            )
            FROM (
                SELECT order_id, SUM(price) AS item_value
                FROM order_items
                GROUP BY order_id
            ) AS item_by_order
        """,
        "unit": "BRL",
        "description": (
            "Total item sales value divided by distinct orders with item "
            "records, in BRL per order."
        ),
    },
    "average_items_plus_freight_per_order_brl": {
        "sql": """
            SELECT COALESCE(
                SUM(item_value + freight_value) / NULLIF(COUNT(*), 0),
                0
            )
            FROM (
                SELECT
                    order_id,
                    SUM(price) AS item_value,
                    SUM(freight_value) AS freight_value
                FROM order_items
                GROUP BY order_id
            ) AS item_by_order
        """,
        "unit": "BRL",
        "description": (
            "Total item price plus freight divided by distinct orders with "
            "item records, in BRL per order."
        ),
    },
}


def list_kpis() -> list[str]:
    """Return the supported KPI names."""
    return sorted(KPI_DEFINITIONS)


def get_kpi(kpi_name: str) -> dict[str, Any]:
    """Calculate a predefined KPI using a read-only DuckDB connection."""
    if not isinstance(kpi_name, str):
        raise ValueError("Unknown KPI: KPI name must be a string.")

    normalized_name = kpi_name.strip().lower()

    if normalized_name not in KPI_DEFINITIONS:
        raise ValueError(f"Unknown KPI: {kpi_name!r}")

    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    definition = KPI_DEFINITIONS[normalized_name]
    connection = duckdb.connect(str(DB_PATH), read_only=True)

    try:
        row = connection.execute(definition["sql"]).fetchone()
    finally:
        connection.close()

    if row is None or row[0] is None:
        value = 0
    else:
        value = float(row[0])

    if definition["unit"] == "orders":
        value = int(value)
    else:
        value = round(value, 2)

    return {
        "kpi": normalized_name,
        "value": value,
        "unit": definition["unit"],
        "description": definition["description"],
        "database_mode": "read-only",
    }
