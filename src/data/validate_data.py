
from pathlib import Path

import pandas as pd

RAW_DIR = Path("data/raw")


def inspect_key(
    filename: str,
    columns: list[str],
    key_columns: list[str],
) -> None:
    path = RAW_DIR / filename

    df = pd.read_csv(
        path,
        usecols=columns,
        low_memory=False,
    )

    missing_rows = int(df[key_columns].isna().any(axis=1).sum())
    duplicate_rows = int(
        df.duplicated(subset=key_columns, keep=False).sum()
    )

    print(f"\n{'=' * 60}")
    print(f"FILE: {filename}")
    print(f"Rows: {len(df):,}")
    print(f"Key columns: {key_columns}")
    print(f"Rows with missing key values: {missing_rows:,}")
    print(f"Rows involved in duplicate keys: {duplicate_rows:,}")

    if duplicate_rows:
        print("Example duplicate keys:")
        print(
            df.loc[
                df.duplicated(
                    subset=key_columns,
                    keep=False,
                ),
                key_columns,
            ]
            .head(10)
            .to_string(index=False)
        )


def main() -> None:
    print("OLIST KEY AND RELATIONSHIP VALIDATION")

    # Expected unique identifiers in these source tables.
    inspect_key(
        "olist_customers_dataset.csv",
        ["customer_id"],
        ["customer_id"],
    )
    inspect_key(
        "olist_orders_dataset.csv",
        ["order_id", "customer_id"],
        ["order_id"],
    )
    inspect_key(
        "olist_products_dataset.csv",
        ["product_id"],
        ["product_id"],
    )
    inspect_key(
        "olist_sellers_dataset.csv",
        ["seller_id"],
        ["seller_id"],
    )
    inspect_key(
        "olist_order_reviews_dataset.csv",
        ["review_id", "order_id"],
        ["review_id"],
    )

    # Order items use a composite key.
    inspect_key(
        "olist_order_items_dataset.csv",
        ["order_id", "order_item_id"],
        ["order_id", "order_item_id"],
    )

    # Payment rows use a composite key for this diagnostic.
    inspect_key(
        "olist_order_payments_dataset.csv",
        ["order_id", "payment_sequential"],
        ["order_id", "payment_sequential"],
    )

    # Relationship checks: child records whose parent is absent.
    orders = pd.read_csv(
        RAW_DIR / "olist_orders_dataset.csv",
        usecols=["order_id", "customer_id"],
    )
    customers = pd.read_csv(
        RAW_DIR / "olist_customers_dataset.csv",
        usecols=["customer_id"],
    )
    items = pd.read_csv(
        RAW_DIR / "olist_order_items_dataset.csv",
        usecols=["order_id", "product_id", "seller_id"],
    )
    payments = pd.read_csv(
        RAW_DIR / "olist_order_payments_dataset.csv",
        usecols=["order_id"],
    )
    products = pd.read_csv(
        RAW_DIR / "olist_products_dataset.csv",
        usecols=["product_id"],
    )
    sellers = pd.read_csv(
        RAW_DIR / "olist_sellers_dataset.csv",
        usecols=["seller_id"],
    )

    order_ids = set(orders["order_id"].dropna())
    customer_ids = set(customers["customer_id"].dropna())
    product_ids = set(products["product_id"].dropna())
    seller_ids = set(sellers["seller_id"].dropna())

    print(f"\n{'=' * 60}")
    print("RELATIONSHIP VALIDATION")
    print(
        "Orders referencing missing customers:",
        int((~orders["customer_id"].isin(customer_ids)).sum()),
    )
    print(
        "Items referencing missing orders:",
        int((~items["order_id"].isin(order_ids)).sum()),
    )
    print(
        "Items referencing missing products:",
        int((~items["product_id"].isin(product_ids)).sum()),
    )
    print(
        "Items referencing missing sellers:",
        int((~items["seller_id"].isin(seller_ids)).sum()),
    )
    print(
        "Payments referencing missing orders:",
        int((~payments["order_id"].isin(order_ids)).sum()),
    )

    print("\nValidation completed. Source CSV files were not modified.")


if __name__ == "__main__":
    main()
