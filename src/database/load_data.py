
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
DB_DIR = PROJECT_ROOT / "data" / "processed"
DB_PATH = DB_DIR / "olist.duckdb"

# Source filename -> database table name
TABLES = {
    "olist_customers_dataset.csv": "customers",
    "olist_geolocation_dataset.csv": "geolocation",
    "olist_orders_dataset.csv": "orders",
    "olist_order_items_dataset.csv": "order_items",
    "olist_order_payments_dataset.csv": "order_payments",
    "olist_order_reviews_dataset.csv": "order_reviews",
    "olist_products_dataset.csv": "products",
    "olist_sellers_dataset.csv": "sellers",
    "product_category_name_translation.csv": "category_translation",
}

# Expected counts from our initial CSV profiling.
EXPECTED_ROWS = {
    "customers": 99_441,
    "geolocation": 1_000_163,
    "orders": 99_441,
    "order_items": 112_650,
    "order_payments": 103_886,
    "order_reviews": 99_224,
    "products": 32_951,
    "sellers": 3_095,
    "category_translation": 71,
}


def main() -> None:
    if not RAW_DIR.exists():
        raise FileNotFoundError(f"Raw data directory not found: {RAW_DIR}")

    missing_files = [
        filename
        for filename in TABLES
        if not (RAW_DIR / filename).exists()
    ]

    if missing_files:
        raise FileNotFoundError(
            "Missing source CSV files:\n"
            + "\n".join(missing_files)
        )

    DB_DIR.mkdir(parents=True, exist_ok=True)

    print("OLIST DUCKDB DATA LOADER")
    print(f"Source directory: {RAW_DIR}")
    print(f"Database path: {DB_PATH}")
    print("\nLoading source tables...")

    connection = duckdb.connect(str(DB_PATH))

    try:
        # Rebuild only the tables managed by this script.
        # The source CSV files are never changed.
        for filename, table_name in TABLES.items():
            csv_path = (RAW_DIR / filename).as_posix()
            escaped_path = csv_path.replace("'", "''")

            connection.execute(
                f"CREATE OR REPLACE TABLE {table_name} AS "
                f"SELECT * FROM read_csv_auto('{escaped_path}')"
            )

            actual_rows = connection.execute(
                f"SELECT COUNT(*) FROM {table_name}"
            ).fetchone()[0]

            expected_rows = EXPECTED_ROWS[table_name]
            status = "PASS" if actual_rows == expected_rows else "FAIL"

            print(
                f"[{status}] {table_name:<22} "
                f"{actual_rows:>10,} rows "
                f"(expected {expected_rows:,})"
            )

            if actual_rows != expected_rows:
                raise ValueError(
                    f"Row-count mismatch for {table_name}: "
                    f"expected {expected_rows}, got {actual_rows}"
                )

        # Record a simple ingestion manifest for reproducibility.
        connection.execute("""
            CREATE OR REPLACE TABLE ingestion_manifest AS
            SELECT
                current_timestamp AS loaded_at,
                'Olist Brazilian E-Commerce Public Dataset' AS source_name,
                'Initial CSV row-count validation' AS validation_stage
        """)

        print("\nAll nine tables loaded and row counts validated.")
        print("Ingestion manifest created.")
        print("Source CSV files were not modified.")

    finally:
        connection.close()


if __name__ == "__main__":
    main()
