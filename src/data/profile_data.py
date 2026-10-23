
from pathlib import Path
import pandas as pd

RAW_DIR = Path("data/raw")

EXPECTED_FILES = [
    "olist_customers_dataset.csv",
    "olist_geolocation_dataset.csv",
    "olist_orders_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
    "product_category_name_translation.csv",
]

# Candidate primary keys for initial diagnostics.
KEY_COLUMNS = {
    "olist_customers_dataset.csv": "customer_id",
    "olist_orders_dataset.csv": "order_id",
    "olist_order_items_dataset.csv": None,  # Composite key: order_id + order_item_id
    "olist_order_payments_dataset.csv": None,
    "olist_order_reviews_dataset.csv": "review_id",
    "olist_products_dataset.csv": "product_id",
    "olist_sellers_dataset.csv": "seller_id",
}


def profile_file(filename: str) -> None:
    path = RAW_DIR / filename

    if not path.exists():
        print(f"\nMISSING: {filename}")
        return

    # Read in chunks to avoid unnecessarily loading large files into memory.
    rows = 0
    missing_by_column = None
    columns = None

    for chunk in pd.read_csv(path, chunksize=20_000, low_memory=False):
        rows += len(chunk)
        columns = list(chunk.columns)
        missing = chunk.isna().sum()

        if missing_by_column is None:
            missing_by_column = missing
        else:
            missing_by_column = missing_by_column.add(
                missing, fill_value=0
            )

    print(f"\n{'=' * 65}")
    print(f"FILE: {filename}")
    print(f"Rows: {rows:,}")
    print(f"Columns ({len(columns or [])}): {columns}")

    if missing_by_column is not None:
        missing_by_column = missing_by_column.astype(int)
        missing_by_column = missing_by_column[
            missing_by_column > 0
        ].sort_values(ascending=False)

        print("Columns with missing values:")
        if missing_by_column.empty:
            print("  None")
        else:
            print(missing_by_column.to_string())


def main() -> None:
    print("OLIST DATA QUALITY PROFILE")
    print(f"Data directory: {RAW_DIR.resolve()}")

    if not RAW_DIR.exists():
        raise SystemExit("ERROR: data/raw directory does not exist.")

    for filename in EXPECTED_FILES:
        profile_file(filename)

    print(f"\n{'=' * 65}")
    print("Initial profiling completed.")
    print("No source files have been modified.")


if __name__ == "__main__":
    main()
