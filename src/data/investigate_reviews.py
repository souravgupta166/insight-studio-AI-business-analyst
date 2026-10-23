
from pathlib import Path

import pandas as pd

RAW_DIR = Path("data/raw")
REVIEW_FILE = RAW_DIR / "olist_order_reviews_dataset.csv"


def main() -> None:
    reviews = pd.read_csv(
        REVIEW_FILE,
        low_memory=False,
    )

    print("OLIST REVIEW DUPLICATE INVESTIGATION")
    print("=" * 65)

    # Identify every review_id that occurs more than once.
    duplicate_mask = reviews.duplicated(
        subset=["review_id"],
        keep=False,
    )
    duplicate_rows = reviews.loc[duplicate_mask].copy()

    duplicate_ids = duplicate_rows["review_id"].nunique()

    print(f"Total review rows: {len(reviews):,}")
    print(f"Unique review IDs: {reviews['review_id'].nunique():,}")
    print(f"Rows involved in repeated review IDs: {len(duplicate_rows):,}")
    print(f"Distinct repeated review IDs: {duplicate_ids:,}")

    # Determine how many orders are associated with each review ID.
    per_review = (
        reviews.groupby("review_id", dropna=False)
        .agg(
            row_count=("order_id", "size"),
            distinct_orders=("order_id", "nunique"),
            distinct_scores=("review_score", "nunique"),
        )
        .reset_index()
    )

    repeated = per_review.loc[
        per_review["row_count"] > 1
    ].sort_values("row_count", ascending=False)

    print("\nRepeated review ID patterns:")
    print(
        repeated[
            [
                "row_count",
                "distinct_orders",
                "distinct_scores",
            ]
        ]
        .value_counts()
        .head(15)
        .to_string()
    )

    print("\nSample repeated review records:")
    display_columns = [
        "review_id",
        "order_id",
        "review_score",
        "review_creation_date",
        "review_answer_timestamp",
        "review_comment_title",
        "review_comment_message",
    ]

    print(
        duplicate_rows[display_columns]
        .sort_values(["review_id", "order_id"])
        .head(20)
        .to_string(index=False)
    )

    # Exact duplicate rows are a separate question from duplicate IDs.
    exact_duplicate_count = int(reviews.duplicated(keep=False).sum())

    print(f"\nRows involved in exact duplicate rows: {exact_duplicate_count:,}")
    print("\nInvestigation completed. Source CSV was not modified.")


if __name__ == "__main__":
    main()
