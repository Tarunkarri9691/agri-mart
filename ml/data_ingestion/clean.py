"""Clean raw price data -> ml/data/market_prices.csv  (python -m ml.data_ingestion.clean [raw.csv])"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .generate_synthetic import DATA_PATH

PRICE_COLS = ["min_price", "max_price", "modal_price"]


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["crop"] = df["crop"].str.strip().str.lower()
    df["market"] = df["market"].str.strip().str.title()
    df = df[(df["modal_price"] > 0)].drop_duplicates(["date", "market", "crop"])
    parts = []
    for (_, _), g in df.groupby(["market", "crop"]):
        g = g.set_index("date").sort_index()
        g = g.reindex(pd.date_range(g.index.min(), g.index.max(), freq="D"))
        g[["market", "crop"]] = g[["market", "crop"]].ffill().bfill()
        for c in PRICE_COLS + ["arrivals", "rainfall"]:
            g[c] = g[c].interpolate(limit=5)
        q1, q3 = g["modal_price"].quantile([0.25, 0.75])
        iqr = q3 - q1
        g["modal_price"] = g["modal_price"].clip(q1 - 3 * iqr, q3 + 3 * iqr)
        parts.append(g.dropna(subset=["modal_price"]).rename_axis("date").reset_index())
    out = pd.concat(parts, ignore_index=True)
    out["arrivals"] = out["arrivals"].fillna(out.groupby(["market", "crop"])["arrivals"].transform("median")).fillna(0)
    out["rainfall"] = out["rainfall"].fillna(0)
    return out


if __name__ == "__main__":
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DATA_PATH
    cleaned = clean(pd.read_csv(src))
    cleaned.to_csv(DATA_PATH, index=False)
    print(f"Cleaned {len(cleaned):,} rows -> {DATA_PATH}")
