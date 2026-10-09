import polars as pl


def transform() -> pl.DataFrame:
    return (
        pl.scan_csv("data/sales.csv")
        .group_by("product")
        .agg(pl.col("amount").sum().alias("total_amount"))
        .sort("total_amount", descending=True)
        .collect()
    )
